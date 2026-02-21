"""
Gemini responses processor for generating AI responses using Google's GenAI API.
"""

import asyncio
import copy
import logging
import uuid
from collections.abc import AsyncGenerator
from contextlib import AsyncExitStack, asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, Final, NamedTuple

import httpx
from google import genai
from google.genai import types
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from appkit_assistant.backend.database.models import (
    MCPServer,
)
from appkit_assistant.backend.processors.mcp_mixin import MCPCapabilities
from appkit_assistant.backend.processors.processor_base import mcp_oauth_redirect_uri
from appkit_assistant.backend.processors.streaming_base import StreamingProcessorBase
from appkit_assistant.backend.schemas import (
    AIModel,
    Chunk,
    MCPAuthType,
    Message,
    MessageType,
)
from appkit_assistant.backend.services.system_prompt_builder import SystemPromptBuilder

logger = logging.getLogger(__name__)
default_oauth_redirect_uri: Final[str] = mcp_oauth_redirect_uri()

# Maximum characters to show in tool result preview
TOOL_RESULT_PREVIEW_LENGTH: Final[int] = 500

GEMINI_FORBIDDEN_SCHEMA_FIELDS: Final[set[str]] = {
    "$schema",
    "$id",
    "$ref",
    "$defs",
    "definitions",
    "$comment",
    "examples",
    "default",
    "const",
    "contentMediaType",
    "contentEncoding",
    "additionalProperties",
    "additional_properties",
    "patternProperties",
    "unevaluatedProperties",
    "unevaluatedItems",
    "minItems",
    "maxItems",
    "minLength",
    "maxLength",
    "minimum",
    "maximum",
    "exclusiveMinimum",
    "exclusiveMaximum",
    "multipleOf",
    "pattern",
    "format",
    "title",
    "allOf",
    "oneOf",
    "not",
    "if",
    "then",
    "else",
    "dependentSchemas",
    "dependentRequired",
}


@dataclass
class MCPToolContext:
    """Context for MCP tool execution."""

    session: ClientSession
    server_name: str
    tools: dict[str, Any] = field(default_factory=dict)


class MCPSessionWrapper(NamedTuple):
    """Wrapper to store MCP connection details before creating actual session."""

    url: str
    headers: dict[str, str]
    name: str


class GeminiResponsesProcessor(StreamingProcessorBase, MCPCapabilities):
    """Gemini processor using the GenAI API with native MCP support."""

    def __init__(
        self,
        models: dict[str, AIModel],
        api_key: str | None = None,
        oauth_redirect_uri: str = default_oauth_redirect_uri,
    ) -> None:
        StreamingProcessorBase.__init__(self, models, "gemini_responses")
        MCPCapabilities.__init__(self, oauth_redirect_uri, "gemini_responses")
        self.client: genai.Client | None = None
        self._system_prompt_builder = SystemPromptBuilder()

        if api_key:
            try:
                self.client = genai.Client(
                    api_key=api_key, http_options={"api_version": "v1beta"}
                )
            except Exception as e:
                logger.error("Failed to initialize Gemini client: %s", e)
        else:
            logger.warning("Gemini API key not found. Processor disabled.")

        logger.debug("Using redirect URI for MCP OAuth: %s", oauth_redirect_uri)

    def _get_event_handlers(self) -> dict[str, Any]:
        """Get event handlers (empty for Gemini - uses chunk-based handling)."""
        return {}

    async def process(
        self,
        messages: list[Message],
        model_id: str,
        files: list[str] | None = None,  # noqa: ARG002
        mcp_servers: list[MCPServer] | None = None,
        payload: dict[str, Any] | None = None,
        user_id: int | None = None,
        cancellation_token: asyncio.Event | None = None,
    ) -> AsyncGenerator[Chunk, None]:
        """Process messages using Google GenAI API with native MCP support."""
        if not self.client:
            raise ValueError("Gemini Client not initialized.")

        if model_id not in self.models:
            msg = f"Model {model_id} not supported by Gemini processor"
            raise ValueError(msg)

        model = self.models[model_id]
        self.current_user_id = user_id
        self.clear_pending_auth_servers()

        # Initialize statistics
        self._reset_statistics(model.model)

        # Prepare configuration
        config = self._create_generation_config(model, payload)

        # Connect to MCP servers and create sessions
        mcp_sessions = []
        mcp_prompt = ""
        if mcp_servers:
            mcp_sessions, auth_required = await self._create_mcp_sessions(
                mcp_servers, user_id
            )
            for server in auth_required:
                self.add_pending_auth_server(server)
            mcp_prompt = self._build_mcp_prompt(mcp_servers)
            # Note: tools are configured in _stream_with_mcp after connecting to MCP

        # Prepare messages with MCP prompts for tool selection
        contents, system_instruction = await self._convert_messages_to_gemini_format(
            messages, mcp_prompt
        )

        # Add system instruction to config if present
        if system_instruction:
            config.system_instruction = system_instruction

        if mcp_sessions:
            logger.info(
                "Connected to %d MCP servers for native tool support",
                len(mcp_sessions),
            )

        try:
            # Generate content with MCP tools
            async for chunk in self._stream_with_mcp(
                model.model, contents, config, mcp_sessions, cancellation_token
            ):
                yield chunk

            # Yield final completion chunk with statistics
            stats = self._get_statistics()
            logger.debug("Completion statistics: %s", stats)
            yield self.chunk_factory.completion(
                status="response_complete",
                statistics=stats,
            )

            # Handle any pending auth
            async for auth_chunk in self.yield_pending_auth_chunks():
                yield auth_chunk

        except Exception as e:
            logger.exception("Error in Gemini processor: %s", str(e))
            yield self.chunk_factory.error(f"Error: {e!s}")

    async def _create_mcp_sessions(
        self, servers: list[MCPServer], user_id: int | None
    ) -> tuple[list[MCPSessionWrapper], list[MCPServer]]:
        """Create MCP ClientSession objects for each server.

        Returns:
            Tuple with (sessions, auth_required_servers)
        """
        sessions = []
        auth_required = []

        for server in servers:
            try:
                # Parse headers using MCPCapabilities
                headers = self.parse_mcp_headers(server)

                # Handle OAuth - inject token
                if (
                    server.auth_type == MCPAuthType.OAUTH_DISCOVERY
                    and user_id is not None
                ):
                    token = await self.get_valid_token(server, user_id)
                    if token:
                        headers["Authorization"] = f"Bearer {token.access_token}"
                    else:
                        auth_required.append(server)
                        logger.warning(
                            "Skipping MCP server %s - OAuth token required",
                            server.name,
                        )
                        continue

                # Create SSE client connection
                # Use URL directly as configured (server determines endpoint)
                logger.debug(
                    "Connecting to MCP server %s at %s (headers: %s)",
                    server.name,
                    server.url,
                    {
                        k: "***" if k.lower() == "authorization" else v
                        for k, v in headers.items()
                    },
                )

                # Create a session wrapper with URL and headers
                session = MCPSessionWrapper(server.url, headers, server.name)
                sessions.append(session)

            except Exception as e:
                logger.error(
                    "Failed to connect to MCP server %s: %s", server.name, str(e)
                )

        return sessions, auth_required

    async def _stream_with_mcp(
        self,
        model_name: str,
        contents: list[types.Content],
        config: types.GenerateContentConfig,
        mcp_sessions: list[Any],
        cancellation_token: asyncio.Event | None = None,
    ) -> AsyncGenerator[Chunk, None]:
        """Stream responses with MCP tool support."""
        if not mcp_sessions:
            # No MCP sessions, direct streaming
            async for chunk in self._stream_generation(
                model_name, contents, config, cancellation_token
            ):
                yield chunk
            return

        # Enter all session contexts and fetch tools
        async with self._mcp_context_manager(mcp_sessions) as tool_contexts:
            if tool_contexts:
                # Convert MCP tools to Gemini FunctionDeclarations
                # Use unique naming: server_name__tool_name to avoid duplicates
                function_declarations = []
                for ctx in tool_contexts:
                    for tool_name, tool_def in ctx.tools.items():
                        # Create unique name: server_name__tool_name
                        unique_name = f"{ctx.server_name}__{tool_name}"
                        func_decl = self._mcp_tool_to_gemini_function(
                            unique_name, tool_def, original_name=tool_name
                        )
                        if func_decl:
                            function_declarations.append(func_decl)

                if function_declarations:
                    config.tools = [
                        types.Tool(function_declarations=function_declarations)
                    ]
                    logger.info(
                        "Configured %d tools for Gemini from MCP",
                        len(function_declarations),
                    )

            # Stream with automatic function calling loop
            async for chunk in self._stream_with_tool_loop(
                model_name, contents, config, tool_contexts, cancellation_token
            ):
                yield chunk

    async def _stream_with_tool_loop(
        self,
        model_name: str,
        contents: list[types.Content],
        config: types.GenerateContentConfig,
        tool_contexts: list[MCPToolContext],
        cancellation_token: asyncio.Event | None = None,
    ) -> AsyncGenerator[Chunk, None]:
        """Stream generation with tool call handling loop."""
        max_tool_rounds = 10
        current_contents = list(contents)

        for _round_num in range(max_tool_rounds):
            if cancellation_token and cancellation_token.is_set():
                logger.info("Processing cancelled by user")
                break

            # Use streaming API
            stream = await self.client.aio.models.generate_content_stream(
                model=model_name, contents=current_contents, config=config
            )

            # Collect function calls and stream text as it arrives
            collected_function_calls: list[Any] = []
            collected_parts: list[types.Part] = []
            streamed_text = ""

            async for chunk in stream:
                if cancellation_token and cancellation_token.is_set():
                    logger.info("Processing cancelled by user")
                    return

                if chunk.usage_metadata:
                    self._update_statistics(
                        input_tokens=chunk.usage_metadata.prompt_token_count,
                        output_tokens=chunk.usage_metadata.candidates_token_count,
                    )

                if not chunk.candidates or not chunk.candidates[0].content:
                    continue

                for part in chunk.candidates[0].content.parts:
                    # Stream text immediately
                    if part.text:
                        streamed_text += part.text
                        yield self.chunk_factory.text(part.text, delta=part.text)
                    # Collect function calls
                    if part.function_call is not None:
                        collected_function_calls.append(part.function_call)
                        collected_parts.append(part)

            # If no function calls, we're done (text was already streamed)
            if not collected_function_calls:
                return

            # Build the model's response content with function calls
            model_response_parts = []
            if streamed_text:
                model_response_parts.append(types.Part(text=streamed_text))
            model_response_parts.extend(collected_parts)
            current_contents.append(
                types.Content(role="model", parts=model_response_parts)
            )

            # Execute tool calls and collect results
            function_responses = []
            for fc in collected_function_calls:
                # Parse unique tool name: server_name__tool_name
                server_name, original_tool_name = self._parse_unique_tool_name(fc.name)

                # Generate a unique tool call ID
                tool_call_id = f"mcp_{uuid.uuid4().hex[:32]}"

                # Yield TOOL_CALL chunk to show in UI (use original name)
                yield self.chunk_factory.tool_call(
                    f"Benutze Werkzeug: {server_name}.{original_tool_name}",
                    tool_name=original_tool_name,
                    tool_id=tool_call_id,
                    server_label=server_name,
                    status="starting",
                )

                result = await self._execute_mcp_tool(fc.name, fc.args, tool_contexts)

                # Yield TOOL_RESULT chunk with preview
                preview = (
                    result[:TOOL_RESULT_PREVIEW_LENGTH]
                    if len(result) > TOOL_RESULT_PREVIEW_LENGTH
                    else result
                )
                yield self.chunk_factory.tool_result(
                    preview,
                    tool_id=tool_call_id,
                    status="completed",
                )

                function_responses.append(
                    types.Part(
                        function_response=types.FunctionResponse(
                            name=fc.name,
                            response={"result": result},
                        )
                    )
                )
                logger.debug(
                    "Tool %s executed, result length: %d",
                    fc.name,
                    len(str(result)),
                )

            # Add function responses
            current_contents.append(
                types.Content(role="user", parts=function_responses)
            )

            # Continue to next round

        logger.warning("Max tool rounds (%d) exceeded", max_tool_rounds)

    def _parse_unique_tool_name(self, unique_name: str) -> tuple[str, str]:
        """Parse unique tool name back to server name and original tool name.

        Args:
            unique_name: Tool name in format 'server_name__tool_name'

        Returns:
            Tuple of (server_name, original_tool_name)
        """
        if "__" in unique_name:
            parts = unique_name.split("__", 1)
            return parts[0], parts[1]
        # Fallback for tools without prefix
        return "unknown", unique_name

    async def _execute_mcp_tool(
        self,
        unique_tool_name: str,
        args: dict[str, Any],
        tool_contexts: list[MCPToolContext],
    ) -> str:
        """Execute an MCP tool and return the result."""
        server_name, tool_name = self._parse_unique_tool_name(unique_tool_name)

        for ctx in tool_contexts:
            if ctx.server_name == server_name and tool_name in ctx.tools:
                try:
                    logger.debug(
                        "Executing tool %s on server %s with args: %s",
                        tool_name,
                        server_name,
                        args,
                    )
                    result = await ctx.session.call_tool(tool_name, args)
                    if hasattr(result, "content") and result.content:
                        texts = [i.text for i in result.content if hasattr(i, "text")]
                        return "\n".join(texts) if texts else str(result)
                    return str(result)
                except Exception as e:
                    logger.exception("Error executing tool %s: %s", tool_name, e)
                    return f"Error executing tool: {e!s}"

        return f"Tool {tool_name} not found on server {server_name}"

    def _mcp_tool_to_gemini_function(
        self,
        name: str,
        tool_def: dict[str, Any],
        original_name: str | None = None,
    ) -> types.FunctionDeclaration | None:
        """Convert MCP tool definition to Gemini FunctionDeclaration.

        Args:
            name: Unique function name (may include server prefix)
            tool_def: MCP tool definition with description and inputSchema
            original_name: Original tool name for description enhancement
        """
        try:
            description = tool_def.get("description", "")
            # Enhance description with original name if using prefixed naming
            if original_name and original_name != name:
                description = f"[{original_name}] {description}"
            input_schema = tool_def.get("inputSchema", {})

            # Fix the schema for Gemini compatibility
            fixed_schema = self._fix_schema_for_gemini(input_schema)

            return types.FunctionDeclaration(
                name=name,
                description=description,
                parameters=fixed_schema if fixed_schema else None,
            )
        except Exception as e:
            logger.warning("Failed to convert MCP tool %s: %s", name, str(e))
            return None

    def _fix_schema_for_gemini(self, schema: dict[str, Any]) -> dict[str, Any]:
        """Fix JSON schema for Gemini API compatibility (recursive)."""
        if not isinstance(schema, dict):
            return schema

        result = copy.deepcopy(schema)

        # Remove forbidden fields
        for key in GEMINI_FORBIDDEN_SCHEMA_FIELDS:
            result.pop(key, None)

        # Fix array without items
        if result.get("type") == "array" and "items" not in result:
            result["items"] = {"type": "string"}

        # Recurse into nested schemas
        if isinstance(result.get("items"), dict):
            result["items"] = self._fix_schema_for_gemini(result["items"])

        if isinstance(result.get("properties"), dict):
            result["properties"] = {
                k: self._fix_schema_for_gemini(v)
                for k, v in result["properties"].items()
            }

        for key in ("anyOf", "any_of"):
            if isinstance(result.get(key), list):
                result[key] = [
                    self._fix_schema_for_gemini(item) for item in result[key]
                ]

        return result

    @asynccontextmanager
    async def _mcp_context_manager(
        self, session_wrappers: list[Any]
    ) -> AsyncGenerator[list[MCPToolContext], None]:
        """Context manager to enter all MCP session contexts and fetch tools."""
        async with AsyncExitStack() as stack:
            tool_contexts: list[MCPToolContext] = []

            for wrapper in session_wrappers:
                try:
                    logger.debug(
                        "Connecting to MCP server %s via streamablehttp_client",
                        wrapper.name,
                    )
                    # Create httpx client with headers and timeout
                    http_client = httpx.AsyncClient(
                        headers=wrapper.headers,
                        timeout=60.0,
                    )
                    # Register client for cleanup
                    await stack.enter_async_context(http_client)

                    read, write, _ = await stack.enter_async_context(
                        streamable_http_client(
                            url=wrapper.url,
                            http_client=http_client,
                        )
                    )

                    session = await stack.enter_async_context(
                        ClientSession(read, write)
                    )
                    await session.initialize()

                    # Fetch tools from this session
                    tools_result = await session.list_tools()
                    tools_dict = {}
                    for tool in tools_result.tools:
                        tools_dict[tool.name] = {
                            "description": tool.description or "",
                            "inputSchema": (
                                tool.inputSchema if hasattr(tool, "inputSchema") else {}
                            ),
                        }

                    ctx = MCPToolContext(
                        session=session,
                        server_name=wrapper.name,
                        tools=tools_dict,
                    )
                    tool_contexts.append(ctx)

                    logger.info(
                        "MCP session initialized for %s with %d tools",
                        wrapper.name,
                        len(tools_dict),
                    )
                except Exception as e:
                    logger.exception(
                        "Failed to initialize MCP session for %s: %s",
                        wrapper.name,
                        str(e),
                    )

            try:
                yield tool_contexts
            except Exception as e:
                logger.exception("Error during MCP session usage: %s", str(e))
                raise

    async def _stream_generation(
        self,
        model_name: str,
        contents: list[types.Content],
        config: types.GenerateContentConfig,
        cancellation_token: asyncio.Event | None = None,
    ) -> AsyncGenerator[Chunk, None]:
        """Stream generation from Gemini model."""
        # generate_content_stream returns an awaitable that yields an async generator
        stream = await self.client.aio.models.generate_content_stream(
            model=model_name, contents=contents, config=config
        )
        async for chunk in stream:
            if cancellation_token and cancellation_token.is_set():
                logger.info("Processing cancelled by user")
                break
            processed = self._handle_chunk(chunk)
            if processed:
                yield processed

    def _create_generation_config(
        self, model: AIModel, payload: dict[str, Any] | None
    ) -> types.GenerateContentConfig:
        """Create generation config from model and payload."""
        # Default thinking level depends on model
        thinking_level = "medium" if "flash" in model.model.lower() else "high"

        # Override from payload if present
        if payload:
            thinking_level = payload.get("thinking_level", thinking_level)

        # Filter out fields not accepted by GenerateContentConfig
        filtered_payload = {}
        if payload:
            ignored_fields = {"thread_uuid", "user_id", "thinking_level"}
            filtered_payload = {
                k: v for k, v in payload.items() if k not in ignored_fields
            }

        return types.GenerateContentConfig(
            temperature=model.temperature,
            thinking_config=types.ThinkingConfig(thinking_level=thinking_level),
            **filtered_payload,
            response_modalities=["TEXT"],
        )

    def _build_mcp_prompt(self, mcp_servers: list[MCPServer]) -> str:
        """Build MCP tool selection prompt from server prompts."""
        return "\n".join(f"- {s.prompt}" for s in mcp_servers if s.prompt)

    async def _convert_messages_to_gemini_format(
        self, messages: list[Message], mcp_prompt: str = ""
    ) -> tuple[list[types.Content], str | None]:
        """Convert app messages to Gemini Content objects."""
        system_instruction = await self._system_prompt_builder.build(mcp_prompt)
        contents: list[types.Content] = []

        for msg in messages:
            match msg.type:
                case MessageType.SYSTEM:
                    system_instruction = (
                        f"{system_instruction}\n{msg.text}"
                        if system_instruction
                        else msg.text
                    )
                case MessageType.HUMAN | MessageType.ASSISTANT:
                    role = "user" if msg.type == MessageType.HUMAN else "model"
                    contents.append(
                        types.Content(role=role, parts=[types.Part(text=msg.text)])
                    )

        return contents, system_instruction

    def _extract_text_from_parts(self, parts: list[Any]) -> str:
        """Extract and join text from content parts."""
        return "".join(p.text for p in parts if p.text)

    def _handle_chunk(self, chunk: Any) -> Chunk | None:
        """Handle a single chunk from Gemini stream."""
        # Update statistics if usage metadata is present in the chunk
        if hasattr(chunk, "usage_metadata") and chunk.usage_metadata:
            self._update_statistics(
                input_tokens=chunk.usage_metadata.prompt_token_count,
                output_tokens=chunk.usage_metadata.candidates_token_count,
            )

        if (
            not chunk.candidates
            or not chunk.candidates[0].content
            or not chunk.candidates[0].content.parts
        ):
            return None

        if text := self._extract_text_from_parts(chunk.candidates[0].content.parts):
            return self.chunk_factory.text(text, delta=text)
        return None
