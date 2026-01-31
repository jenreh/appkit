"""
Gemini responses processor for generating AI responses using Google's GenAI API.
"""

import asyncio
import copy
import json
import logging
import uuid
from collections.abc import AsyncGenerator
from contextlib import AsyncExitStack, asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, Final

import reflex as rx
from google.genai import types
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from appkit_assistant.backend.mcp_auth_service import MCPAuthService
from appkit_assistant.backend.models import (
    AIModel,
    AssistantMCPUserToken,
    Chunk,
    ChunkType,
    MCPAuthType,
    MCPServer,
    Message,
    MessageType,
)
from appkit_assistant.backend.processor import mcp_oauth_redirect_uri
from appkit_assistant.backend.processors.gemini_base import BaseGeminiProcessor
from appkit_assistant.backend.system_prompt_cache import get_system_prompt

logger = logging.getLogger(__name__)
default_oauth_redirect_uri: Final[str] = mcp_oauth_redirect_uri()

# Maximum characters to show in tool result preview
TOOL_RESULT_PREVIEW_LENGTH: Final[int] = 500


@dataclass
class MCPToolContext:
    """Context for MCP tool execution."""

    session: ClientSession
    server_name: str
    tools: dict[str, Any] = field(default_factory=dict)


class GeminiResponsesProcessor(BaseGeminiProcessor):
    """Gemini processor using the GenAI API with native MCP support."""

    def __init__(
        self,
        models: dict[str, AIModel],
        api_key: str | None = None,
        oauth_redirect_uri: str = default_oauth_redirect_uri,
    ) -> None:
        super().__init__(models, api_key)
        self._current_reasoning_session: str | None = None
        self._current_user_id: int | None = None
        self._mcp_auth_service = MCPAuthService(redirect_uri=oauth_redirect_uri)
        self._pending_auth_servers: list[MCPServer] = []

        logger.debug("Using redirect URI for MCP OAuth: %s", oauth_redirect_uri)

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
        self._current_user_id = user_id
        self._pending_auth_servers = []
        self._current_reasoning_session = None

        # Prepare configuration
        config = self._create_generation_config(model, payload)

        # Connect to MCP servers and create sessions
        mcp_sessions = []
        mcp_prompt = ""
        if mcp_servers:
            sessions_result = await self._create_mcp_sessions(mcp_servers, user_id)
            mcp_sessions = sessions_result["sessions"]
            self._pending_auth_servers = sessions_result["auth_required"]
            mcp_prompt = self._build_mcp_prompt(mcp_servers)

            if mcp_sessions:
                # Pass sessions directly to tools - SDK handles everything!
                config.tools = mcp_sessions

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

            # Handle any pending auth
            for server in self._pending_auth_servers:
                yield await self._create_auth_required_chunk(server)

        except Exception as e:
            logger.exception("Error in Gemini processor: %s", str(e))
            yield self._create_chunk(ChunkType.ERROR, f"Error: {e!s}")

    async def _create_mcp_sessions(
        self, servers: list[MCPServer], user_id: int | None
    ) -> dict[str, Any]:
        """Create MCP ClientSession objects for each server.

        Returns:
            Dict with 'sessions' and 'auth_required' lists
        """
        sessions = []
        auth_required = []

        for server in servers:
            try:
                # Parse headers
                headers = self._parse_mcp_headers(server)

                # Handle OAuth - inject token
                if (
                    server.auth_type == MCPAuthType.OAUTH_DISCOVERY
                    and user_id is not None
                ):
                    token = await self._get_valid_token_for_server(server, user_id)
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

        return {"sessions": sessions, "auth_required": auth_required}

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
                function_declarations = []
                for ctx in tool_contexts:
                    for tool_name, tool_def in ctx.tools.items():
                        func_decl = self._mcp_tool_to_gemini_function(
                            tool_name, tool_def
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

            response = await self.client.aio.models.generate_content(
                model=model_name, contents=current_contents, config=config
            )

            if not response.candidates:
                return

            candidate = response.candidates[0]
            content = candidate.content

            # Check for function calls
            function_calls = [
                part.function_call
                for part in content.parts
                if part.function_call is not None
            ]

            if function_calls:
                # Add model response with function calls to conversation
                current_contents.append(content)

                # Execute tool calls and collect results
                function_responses = []
                for fc in function_calls:
                    # Find server name for this tool
                    server_name = "unknown"
                    for ctx in tool_contexts:
                        if fc.name in ctx.tools:
                            server_name = ctx.server_name
                            break

                    # Generate a unique tool call ID
                    tool_call_id = f"mcp_{uuid.uuid4().hex[:32]}"

                    # Yield TOOL_CALL chunk to show in UI
                    yield self._create_chunk(
                        ChunkType.TOOL_CALL,
                        f"Werkzeug: {server_name}.{fc.name}",
                        {
                            "tool_name": fc.name,
                            "tool_id": tool_call_id,
                            "server_label": server_name,
                            "arguments": json.dumps(fc.args),
                            "status": "starting",
                        },
                    )

                    result = await self._execute_mcp_tool(
                        fc.name, fc.args, tool_contexts
                    )

                    # Yield TOOL_RESULT chunk with preview
                    preview = (
                        result[:TOOL_RESULT_PREVIEW_LENGTH]
                        if len(result) > TOOL_RESULT_PREVIEW_LENGTH
                        else result
                    )
                    yield self._create_chunk(
                        ChunkType.TOOL_RESULT,
                        preview,
                        {
                            "tool_name": fc.name,
                            "tool_id": tool_call_id,
                            "server_label": server_name,
                            "status": "completed",
                            "result_length": str(len(result)),
                        },
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
                continue

            # No function calls - yield text response
            text_parts = [part.text for part in content.parts if part.text]
            if text_parts:
                yield self._create_chunk(
                    ChunkType.TEXT,
                    "".join(text_parts),
                    {"delta": "".join(text_parts)},
                )

            # Done - no more function calls
            return

        logger.warning("Max tool rounds (%d) exceeded", max_tool_rounds)

    async def _execute_mcp_tool(
        self,
        tool_name: str,
        args: dict[str, Any],
        tool_contexts: list[MCPToolContext],
    ) -> str:
        """Execute an MCP tool and return the result."""
        # Find which context has this tool
        for ctx in tool_contexts:
            if tool_name in ctx.tools:
                try:
                    logger.debug(
                        "Executing tool %s on server %s with args: %s",
                        tool_name,
                        ctx.server_name,
                        args,
                    )
                    result = await ctx.session.call_tool(tool_name, args)
                    # Extract text from result
                    if hasattr(result, "content") and result.content:
                        texts = [
                            item.text
                            for item in result.content
                            if hasattr(item, "text")
                        ]
                        return "\n".join(texts) if texts else str(result)
                    return str(result)
                except Exception as e:
                    logger.exception("Error executing tool %s: %s", tool_name, str(e))
                    return f"Error executing tool: {e!s}"

        return f"Tool {tool_name} not found in any MCP server"

    def _mcp_tool_to_gemini_function(
        self, name: str, tool_def: dict[str, Any]
    ) -> types.FunctionDeclaration | None:
        """Convert MCP tool definition to Gemini FunctionDeclaration."""
        try:
            description = tool_def.get("description", "")
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
        """Fix JSON schema for Gemini API compatibility.

        Gemini requires 'items' field for array types and doesn't allow certain
        JSON Schema fields like '$schema', '$id', 'definitions', etc.
        This recursively fixes the schema.
        """
        if not schema:
            return schema

        # Deep copy to avoid modifying original
        schema = copy.deepcopy(schema)

        # Fields that Gemini doesn't allow in FunctionDeclaration parameters
        # Note: additionalProperties gets converted to additional_properties by SDK
        forbidden_fields = {
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
            # Composition keywords - Gemini doesn't support these
            "allOf",
            "oneOf",
            "not",
            "if",
            "then",
            "else",
            "dependentSchemas",
            "dependentRequired",
        }

        def fix_property(prop: dict[str, Any]) -> dict[str, Any]:
            """Recursively fix a property schema."""
            if not isinstance(prop, dict):
                return prop

            # Remove forbidden fields
            for forbidden in forbidden_fields:
                prop.pop(forbidden, None)

            prop_type = prop.get("type")

            # Fix array without items
            if prop_type == "array" and "items" not in prop:
                prop["items"] = {"type": "string"}
                logger.debug("Added missing 'items' to array property")

            # Recurse into items
            if "items" in prop and isinstance(prop["items"], dict):
                prop["items"] = fix_property(prop["items"])

            # Recurse into properties
            if "properties" in prop and isinstance(prop["properties"], dict):
                for key, val in prop["properties"].items():
                    prop["properties"][key] = fix_property(val)

            # Recurse into anyOf/any_of arrays (Gemini accepts these but not
            # forbidden fields inside them)
            for any_of_key in ("anyOf", "any_of"):
                if any_of_key in prop and isinstance(prop[any_of_key], list):
                    prop[any_of_key] = [
                        fix_property(item) if isinstance(item, dict) else item
                        for item in prop[any_of_key]
                    ]

            return prop

        return fix_property(schema)

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
                    read, write, _ = await stack.enter_async_context(
                        streamablehttp_client(
                            url=wrapper.url,
                            headers=wrapper.headers,
                            timeout=60.0,
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
        # "medium" is only supported by Flash, Pro uses "high" (default dynamic)
        thinking_level = "high"
        if "flash" in model.model.lower():
            thinking_level = "medium"

        # Override from payload if present
        if payload and "thinking_level" in payload:
            thinking_level = payload.pop("thinking_level")

        return types.GenerateContentConfig(
            temperature=model.temperature,
            thinking_config=types.ThinkingConfig(thinking_level=thinking_level),
            **(payload or {}),
            response_modalities=["TEXT"],
        )

    def _build_mcp_prompt(self, mcp_servers: list[MCPServer]) -> str:
        """Build MCP tool selection prompt from server prompts."""
        prompts = [f"- {server.prompt}" for server in mcp_servers if server.prompt]
        return "\n".join(prompts) if prompts else ""

    async def _convert_messages_to_gemini_format(
        self, messages: list[Message], mcp_prompt: str = ""
    ) -> tuple[list[types.Content], str | None]:
        """Convert app messages to Gemini Content objects."""
        contents: list[types.Content] = []
        system_instruction: str | None = None

        # Build MCP prompt section if tools are available
        mcp_section = ""
        if mcp_prompt:
            mcp_section = (
                "\n\n### Tool-Auswahlrichtlinien (Einbettung externer Beschreibungen)\n"
                f"{mcp_prompt}"
            )

        # Get system prompt content first
        system_prompt_template = await get_system_prompt()
        if system_prompt_template:
            # Format with MCP prompts placeholder
            system_instruction = system_prompt_template.format(mcp_prompts=mcp_section)

        for msg in messages:
            if msg.type == MessageType.SYSTEM:
                # Append to system instruction
                if system_instruction:
                    system_instruction += f"\n{msg.text}"
                else:
                    system_instruction = msg.text
            elif msg.type in (MessageType.HUMAN, MessageType.ASSISTANT):
                role = "user" if msg.type == MessageType.HUMAN else "model"
                contents.append(
                    types.Content(role=role, parts=[types.Part(text=msg.text)])
                )

        return contents, system_instruction

    def _handle_chunk(self, chunk: Any) -> Chunk | None:
        """Handle a single chunk from Gemini stream."""
        # Gemini chunks contain candidates. First candidate.
        if not chunk.candidates or not chunk.candidates[0].content:
            return None

        candidate = chunk.candidates[0]
        content = candidate.content

        # List comprehension for text parts
        if not content.parts:
            return None

        text_parts = [part.text for part in content.parts if part.text]

        if text_parts:
            return self._create_chunk(
                ChunkType.TEXT, "".join(text_parts), {"delta": "".join(text_parts)}
            )

        return None

    def _create_chunk(
        self,
        chunk_type: ChunkType,
        content: str,
        extra_metadata: dict[str, str] | None = None,
    ) -> Chunk:
        """Create a Chunk."""
        metadata = {
            "processor": "gemini_responses",
        }
        if extra_metadata:
            metadata.update(extra_metadata)

        return Chunk(
            type=chunk_type,
            text=content,
            chunk_metadata=metadata,
        )

    async def _create_auth_required_chunk(self, server: MCPServer) -> Chunk:
        """Create an AUTH_REQUIRED chunk."""
        # reusing logic from other processors, simplified here
        return Chunk(
            type=ChunkType.AUTH_REQUIRED,
            text=f"{server.name} authentication required",
            chunk_metadata={"server_name": server.name},
        )

    def _parse_mcp_headers(self, server: MCPServer) -> dict[str, str]:
        """Parse headers from server config.

        Returns:
            Dictionary of HTTP headers to send to the MCP server.
        """
        if not server.headers or server.headers == "{}":
            return {}

        try:
            headers_dict = json.loads(server.headers)
            return dict(headers_dict)
        except json.JSONDecodeError:
            logger.warning("Invalid headers JSON for server %s", server.name)
            return {}

    async def _get_valid_token_for_server(
        self, server: MCPServer, user_id: int
    ) -> AssistantMCPUserToken | None:
        """Get a valid OAuth token for the server/user."""
        if server.id is None:
            return None

        with rx.session() as session:
            token = self._mcp_auth_service.get_user_token(session, user_id, server.id)

            if token is None:
                return None

            return await self._mcp_auth_service.ensure_valid_token(
                session, server, token
            )


class MCPSessionWrapper:
    """Wrapper to store MCP connection details before creating actual session."""

    def __init__(self, url: str, headers: dict[str, str], name: str) -> None:
        self.url = url
        self.headers = headers
        self.name = name
