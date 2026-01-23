"""
Claude responses processor for generating AI responses using Anthropic's Claude API.

Supports MCP tools, file uploads (images and documents), extended thinking,
and automatic citation extraction.
"""

import base64
import json
import logging
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any, Final

import reflex as rx

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
from appkit_assistant.backend.processors.claude_base import BaseClaudeProcessor
from appkit_assistant.backend.system_prompt_cache import get_system_prompt
from appkit_commons.database.session import get_session_manager

logger = logging.getLogger(__name__)
default_oauth_redirect_uri: Final[str] = mcp_oauth_redirect_uri()

# Beta headers required for MCP and files API
MCP_BETA_HEADER: Final[str] = "mcp-client-2025-11-20"
FILES_BETA_HEADER: Final[str] = "files-api-2025-04-14"


class ClaudeResponsesProcessor(BaseClaudeProcessor):
    """Claude processor using the Messages API with MCP tools and file uploads."""

    def __init__(
        self,
        models: dict[str, AIModel],
        api_key: str | None = None,
        base_url: str | None = None,
        oauth_redirect_uri: str = default_oauth_redirect_uri,
    ) -> None:
        super().__init__(models, api_key, base_url)
        self._current_reasoning_session: str | None = None
        self._current_user_id: int | None = None
        self._mcp_auth_service = MCPAuthService(redirect_uri=oauth_redirect_uri)
        self._pending_auth_servers: list[MCPServer] = []
        self._uploaded_file_ids: list[str] = []
        # Track current tool context for streaming
        self._current_tool_context: dict[str, Any] | None = None
        # Track if we need a newline before next text block
        self._needs_text_separator: bool = False

        logger.debug("Using redirect URI for MCP OAuth: %s", oauth_redirect_uri)

    async def process(
        self,
        messages: list[Message],
        model_id: str,
        files: list[str] | None = None,
        mcp_servers: list[MCPServer] | None = None,
        payload: dict[str, Any] | None = None,
        user_id: int | None = None,
    ) -> AsyncGenerator[Chunk, None]:
        """Process messages using Claude Messages API with streaming."""
        if not self.client:
            raise ValueError("Claude Client not initialized.")

        if model_id not in self.models:
            msg = f"Model {model_id} not supported by Claude processor"
            raise ValueError(msg)

        model = self.models[model_id]
        self._current_user_id = user_id
        self._pending_auth_servers = []
        self._uploaded_file_ids = []

        try:
            # Upload files if provided
            file_content_blocks = []
            if files:
                file_content_blocks = await self._process_files(files)

            # Create the request
            stream = await self._create_messages_request(
                messages,
                model,
                mcp_servers,
                payload,
                user_id,
                file_content_blocks,
            )

            try:
                # Process streaming events
                async with stream as response:
                    async for event in response:
                        chunk = self._handle_event(event)
                        if chunk:
                            yield chunk
            except Exception as e:
                error_msg = str(e)
                logger.error("Error during Claude response processing: %s", error_msg)
                # Only yield error chunk if NOT an auth error
                is_auth_related = (
                    self._is_auth_error(error_msg) or self._pending_auth_servers
                )
                if not is_auth_related:
                    yield Chunk(
                        type=ChunkType.ERROR,
                        text=f"Ein Fehler ist aufgetreten: {error_msg}",
                        chunk_metadata={
                            "source": "claude_api",
                            "error_type": type(e).__name__,
                        },
                    )

            # Yield any pending auth requirements
            logger.debug(
                "Processing pending auth servers: %d", len(self._pending_auth_servers)
            )
            for server in self._pending_auth_servers:
                logger.debug("Yielding auth chunk for server: %s", server.name)
                yield await self._create_auth_required_chunk(server)

        except Exception as e:
            logger.error("Critical error in Claude processor: %s", e)
            raise

    def _handle_event(self, event: Any) -> Chunk | None:
        """Handle streaming events from Claude API."""
        event_type = getattr(event, "type", None)
        if not event_type:
            return None

        handlers = {
            "message_start": self._handle_message_start,
            "message_delta": self._handle_message_delta,
            "message_stop": self._handle_message_stop,
            "content_block_start": self._handle_content_block_start,
            "content_block_delta": self._handle_content_block_delta,
            "content_block_stop": self._handle_content_block_stop,
        }

        handler = handlers.get(event_type)
        if handler:
            return handler(event)

        logger.debug("Unhandled Claude event type: %s", event_type)
        return None

    def _handle_message_start(self, event: Any) -> Chunk | None:  # noqa: ARG002
        """Handle message_start event."""
        return self._create_chunk(
            ChunkType.LIFECYCLE,
            "created",
            {"stage": "created"},
        )

    def _handle_message_delta(self, event: Any) -> Chunk | None:
        """Handle message_delta event (contains stop_reason)."""
        delta = getattr(event, "delta", None)
        if delta:
            stop_reason = getattr(delta, "stop_reason", None)
            if stop_reason:
                return self._create_chunk(
                    ChunkType.LIFECYCLE,
                    f"stop_reason: {stop_reason}",
                    {"stop_reason": stop_reason},
                )
        return None

    def _handle_message_stop(self, event: Any) -> Chunk | None:  # noqa: ARG002
        """Handle message_stop event."""
        return self._create_chunk(
            ChunkType.COMPLETION,
            "Response generation completed",
            {"status": "response_complete"},
        )

    def _handle_content_block_start(self, event: Any) -> Chunk | None:
        """Handle content_block_start event."""
        content_block = getattr(event, "content_block", None)
        if not content_block:
            return None

        block_type = getattr(content_block, "type", None)

        # Use dispatch map to reduce branches
        handlers = {
            "text": self._handle_text_block_start,
            "thinking": self._handle_thinking_block_start,
            "tool_use": self._handle_tool_use_block_start,
            "mcp_tool_use": self._handle_mcp_tool_use_block_start,
            "mcp_tool_result": self._handle_mcp_tool_result_block_start,
        }

        handler = handlers.get(block_type)
        if handler:
            return handler(content_block)

        return None

    def _handle_text_block_start(self, content_block: Any) -> Chunk | None:  # noqa: ARG002
        """Handle start of text content block."""
        if self._needs_text_separator:
            self._needs_text_separator = False
            return self._create_chunk(ChunkType.TEXT, "\n\n", {"separator": "true"})
        return None

    def _handle_thinking_block_start(self, content_block: Any) -> Chunk:
        """Handle start of thinking content block."""
        thinking_id = getattr(content_block, "id", "thinking")
        self._current_reasoning_session = thinking_id
        self._needs_text_separator = True
        return self._create_chunk(
            ChunkType.THINKING,
            "Denke nach...",
            {"reasoning_id": thinking_id, "status": "starting"},
        )

    def _handle_tool_use_block_start(self, content_block: Any) -> Chunk:
        """Handle start of tool_use content block."""
        tool_name = getattr(content_block, "name", "unknown_tool")
        tool_id = getattr(content_block, "id", "unknown_id")
        self._current_tool_context = {
            "tool_name": tool_name,
            "tool_id": tool_id,
            "server_label": None,
        }
        return self._create_chunk(
            ChunkType.TOOL_CALL,
            f"Benutze Werkzeug: {tool_name}",
            {
                "tool_name": tool_name,
                "tool_id": tool_id,
                "status": "starting",
                "reasoning_session": self._current_reasoning_session,
            },
        )

    def _handle_mcp_tool_use_block_start(self, content_block: Any) -> Chunk:
        """Handle start of mcp_tool_use content block."""
        tool_name = getattr(content_block, "name", "unknown_tool")
        tool_id = getattr(content_block, "id", "unknown_id")
        server_name = getattr(content_block, "server_name", "unknown_server")
        self._current_tool_context = {
            "tool_name": tool_name,
            "tool_id": tool_id,
            "server_label": server_name,
        }
        return self._create_chunk(
            ChunkType.TOOL_CALL,
            f"Benutze Werkzeug: {server_name}.{tool_name}",
            {
                "tool_name": tool_name,
                "tool_id": tool_id,
                "server_label": server_name,
                "status": "starting",
                "reasoning_session": self._current_reasoning_session,
            },
        )

    def _handle_mcp_tool_result_block_start(self, content_block: Any) -> Chunk:
        """Handle start of mcp_tool_result content block."""
        self._needs_text_separator = True
        tool_use_id = getattr(content_block, "tool_use_id", "unknown_id")
        is_error = bool(getattr(content_block, "is_error", False))
        content = getattr(content_block, "content", "")

        logger.debug(
            "MCP tool result - tool_use_id: %s, is_error: %s, content type: %s",
            tool_use_id,
            is_error,
            type(content).__name__,
        )

        result_text = self._extract_mcp_result_text(content)
        status = "error" if is_error else "completed"
        return self._create_chunk(
            ChunkType.TOOL_RESULT,
            result_text or ("Werkzeugfehler" if is_error else "Erfolgreich"),
            {
                "tool_id": tool_use_id,
                "status": status,
                "error": is_error,
                "reasoning_session": self._current_reasoning_session,
            },
        )

    def _extract_mcp_result_text(self, content: Any) -> str:
        """Extract text from MCP tool result content."""
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, dict):
                    parts.append(item.get("text", str(item)))
                elif hasattr(item, "text"):
                    parts.append(getattr(item, "text", str(item)))
                else:
                    parts.append(str(item))
            return "".join(parts)
        return str(content) if content else ""

        return None

    def _handle_content_block_delta(self, event: Any) -> Chunk | None:
        """Handle content_block_delta event."""
        delta = getattr(event, "delta", None)
        if not delta:
            return None

        delta_type = getattr(delta, "type", None)

        if delta_type == "text_delta":
            text = getattr(delta, "text", "")
            # Extract citations from text if present
            citations = self._extract_citations_from_delta(delta)
            metadata = {"delta": text}
            if citations:
                metadata["citations"] = json.dumps(citations)
            return self._create_chunk(ChunkType.TEXT, text, metadata)

        if delta_type == "thinking_delta":
            thinking_text = getattr(delta, "thinking", "")
            return self._create_chunk(
                ChunkType.THINKING,
                thinking_text,
                {
                    "reasoning_id": self._current_reasoning_session,
                    "status": "in_progress",
                    "delta": thinking_text,
                },
            )

        if delta_type == "input_json_delta":
            partial_json = getattr(delta, "partial_json", "")
            # Include tool context in streaming chunks
            metadata: dict[str, Any] = {
                "status": "arguments_streaming",
                "delta": partial_json,
                "reasoning_session": self._current_reasoning_session,
            }
            if self._current_tool_context:
                metadata["tool_name"] = self._current_tool_context.get("tool_name")
                metadata["tool_id"] = self._current_tool_context.get("tool_id")
                if self._current_tool_context.get("server_label"):
                    metadata["server_label"] = self._current_tool_context[
                        "server_label"
                    ]
            return self._create_chunk(
                ChunkType.TOOL_CALL,
                partial_json,
                metadata,
            )

        return None

    def _handle_content_block_stop(self, event: Any) -> Chunk | None:  # noqa: ARG002
        """Handle content_block_stop event."""
        # Check if this was a thinking block ending
        if self._current_reasoning_session:
            # Reset reasoning session after thinking completes
            reasoning_id = self._current_reasoning_session
            self._current_reasoning_session = None
            return self._create_chunk(
                ChunkType.THINKING_RESULT,
                "beendet.",
                {"reasoning_id": reasoning_id, "status": "completed"},
            )

        # Check if this was a tool block ending
        if self._current_tool_context:
            tool_context = self._current_tool_context
            self._current_tool_context = None
            metadata: dict[str, Any] = {
                "tool_name": tool_context.get("tool_name"),
                "tool_id": tool_context.get("tool_id"),
                "status": "arguments_complete",
            }
            if tool_context.get("server_label"):
                metadata["server_label"] = tool_context["server_label"]
            return self._create_chunk(
                ChunkType.TOOL_CALL,
                "Werkzeugargumente vollständig",
                metadata,
            )

        return None

    def _extract_citations_from_delta(self, delta: Any) -> list[dict[str, Any]]:
        """Extract citation information from a text delta."""
        citations = []

        # Claude provides citations in the text block's citations field
        text_block_citations = getattr(delta, "citations", None)
        if text_block_citations:
            for citation in text_block_citations:
                citation_data = {
                    "cited_text": getattr(citation, "cited_text", ""),
                    "document_index": getattr(citation, "document_index", 0),
                    "document_title": getattr(citation, "document_title", None),
                }

                # Handle different citation location types
                citation_type = getattr(citation, "type", None)
                if citation_type == "char_location":
                    citation_data["start_char_index"] = getattr(
                        citation, "start_char_index", 0
                    )
                    citation_data["end_char_index"] = getattr(
                        citation, "end_char_index", 0
                    )
                elif citation_type == "page_location":
                    citation_data["start_page_number"] = getattr(
                        citation, "start_page_number", 0
                    )
                    citation_data["end_page_number"] = getattr(
                        citation, "end_page_number", 0
                    )
                elif citation_type == "content_block_location":
                    citation_data["start_block_index"] = getattr(
                        citation, "start_block_index", 0
                    )
                    citation_data["end_block_index"] = getattr(
                        citation, "end_block_index", 0
                    )

                citations.append(citation_data)

        return citations

    def _is_auth_error(self, error: Any) -> bool:
        """Check if an error indicates authentication failure (401/403)."""
        error_str = str(error).lower()
        auth_indicators = [
            "401",
            "403",
            "unauthorized",
            "forbidden",
            "authentication required",
            "access denied",
            "invalid token",
            "token expired",
        ]
        return any(indicator in error_str for indicator in auth_indicators)

    def _create_chunk(
        self,
        chunk_type: ChunkType,
        content: str,
        extra_metadata: dict[str, Any] | None = None,
    ) -> Chunk:
        """Create a Chunk with content from the event."""
        metadata: dict[str, str] = {
            "processor": "claude_responses",
        }

        if extra_metadata:
            for key, value in extra_metadata.items():
                if value is not None:
                    metadata[key] = str(value)

        return Chunk(
            type=chunk_type,
            text=content,
            chunk_metadata=metadata,
        )

    async def _process_files(self, files: list[str]) -> list[dict[str, Any]]:
        """Process and upload files for use in messages.

        Args:
            files: List of file paths to process

        Returns:
            List of content blocks for file attachments
        """
        content_blocks = []

        for file_path in files:
            is_valid, error_msg = self._validate_file(file_path)
            if not is_valid:
                logger.warning("Skipping invalid file %s: %s", file_path, error_msg)
                continue

            try:
                content_block = await self._create_file_content_block(file_path)
                if content_block:
                    content_blocks.append(content_block)
            except Exception as e:
                logger.error("Failed to process file %s: %s", file_path, e)
                continue
            finally:
                # Clean up local file after upload attempt
                try:
                    Path(file_path).unlink(missing_ok=True)
                except Exception as e:
                    logger.warning("Failed to delete local file %s: %s", file_path, e)

        return content_blocks

    async def _create_file_content_block(self, file_path: str) -> dict[str, Any] | None:
        """Create a content block for a file.

        For images, uses base64 encoding directly.
        For documents, uploads via Files API.

        Args:
            file_path: Path to the file

        Returns:
            Content block dict or None if failed
        """
        path = Path(file_path)

        # Read file content
        file_data = path.read_bytes()

        media_type = self._get_media_type(file_path)

        if self._is_image_file(file_path):
            # For images, use base64 encoding directly in the message
            base64_data = base64.standard_b64encode(file_data).decode("utf-8")
            return {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": base64_data,
                },
            }

        # For documents, upload via Files API and reference
        try:
            file_upload = await self.client.beta.files.upload(
                file=(path.name, file_data, media_type),
            )
            self._uploaded_file_ids.append(file_upload.id)
            return {
                "type": "document",
                "source": {
                    "type": "file",
                    "file_id": file_upload.id,
                },
                "citations": {"enabled": True},
            }
        except Exception as e:
            logger.error("Failed to upload file %s: %s", file_path, e)
            return None

    async def _create_messages_request(
        self,
        messages: list[Message],
        model: AIModel,
        mcp_servers: list[MCPServer] | None = None,
        payload: dict[str, Any] | None = None,
        user_id: int | None = None,
        file_content_blocks: list[dict[str, Any]] | None = None,
    ) -> Any:
        """Create a Claude Messages API request with streaming.

        Args:
            messages: List of conversation messages
            model: AI model configuration
            mcp_servers: Optional list of MCP servers for tools
            payload: Optional additional parameters
            user_id: Optional user ID for OAuth token lookup
            file_content_blocks: Optional list of file content blocks

        Returns:
            Streaming response object
        """
        # Configure MCP tools and servers
        tools, mcp_server_configs, mcp_prompt = await self._configure_mcp_tools(
            mcp_servers, user_id
        )

        # Convert messages to Claude format
        claude_messages = await self._convert_messages_to_claude_format(
            messages, file_content_blocks
        )

        # Build system prompt
        system_prompt = await self._build_system_prompt(mcp_prompt)

        # Determine which beta features to enable
        betas = []
        if mcp_servers:
            betas.append(MCP_BETA_HEADER)
        if file_content_blocks:
            betas.append(FILES_BETA_HEADER)

        # Build request parameters
        # max_tokens must be > thinking.budget_tokens when thinking is enabled
        params: dict[str, Any] = {
            "model": model.model,
            "max_tokens": 32000,
            "messages": claude_messages,
        }

        # Add system prompt
        if system_prompt:
            params["system"] = system_prompt

        # Add MCP servers if configured
        if mcp_server_configs:
            params["mcp_servers"] = mcp_server_configs

        # Add tools if configured
        if tools:
            params["tools"] = tools

        # Add extended thinking (always enabled with fixed budget)
        params["thinking"] = {
            "type": "enabled",
            "budget_tokens": self.THINKING_BUDGET_TOKENS,
        }

        # Add temperature
        if model.temperature is not None:
            params["temperature"] = model.temperature

        # Merge any additional payload
        if payload:
            params.update(payload)

        # Create streaming request
        if betas:
            return self.client.beta.messages.stream(
                betas=betas,
                **params,
            )

        return self.client.messages.stream(**params)

    def _parse_mcp_headers(
        self,
        server: MCPServer,
    ) -> tuple[str | None, str]:
        """Parse MCP server headers and extract auth token + query params.

        Claude's MCP connector only supports authorization_token (Bearer token).
        Custom headers like X-Project-ID are converted to URL query parameters.

        Args:
            server: MCP server configuration

        Returns:
            Tuple of (authorization_token, url_suffix_with_query_params)
        """
        auth_token = None
        query_suffix = ""

        if not server.headers or server.headers == "{}":
            return auth_token, query_suffix

        try:
            headers = json.loads(server.headers)
        except json.JSONDecodeError as e:
            logger.error(
                "Failed to parse headers JSON for server %s: %s",
                server.name,
                e,
            )
            return auth_token, query_suffix

        # Extract Bearer token from Authorization header
        auth_header = headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            auth_token = auth_header[7:]  # Remove "Bearer " prefix
            logger.debug(
                "Extracted Bearer token from headers for server %s", server.name
            )
        elif auth_header:
            auth_token = auth_header
            logger.debug("Using raw Authorization header for server %s", server.name)

        # Convert non-auth headers to URL query parameters
        query_params = []
        for key, value in headers.items():
            if key.lower() == "authorization":
                continue
            # Convert header name: X-Project-ID -> project_id
            param_name = key.lower()
            if param_name.startswith("x-"):
                param_name = param_name[2:]
            param_name = param_name.replace("-", "_")
            query_params.append(f"{param_name}={value}")

        if query_params:
            query_suffix = "&".join(query_params)
            logger.info(
                "Converted headers to query params for server %s: %s",
                server.name,
                query_params,
            )

        return auth_token, query_suffix

    async def _configure_mcp_tools(
        self,
        mcp_servers: list[MCPServer] | None,
        user_id: int | None = None,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str]:
        """Configure MCP servers and tools for the request.

        Args:
            mcp_servers: List of MCP server configurations
            user_id: Optional user ID for OAuth token lookup

        Returns:
            Tuple of (tools list, mcp_servers list, concatenated prompts)
        """
        if not mcp_servers:
            return [], [], ""

        tools = []
        server_configs = []
        prompts = []

        for server in mcp_servers:
            # Parse headers to get auth token and query params
            auth_token, query_suffix = self._parse_mcp_headers(server)

            # Build URL with query params if needed
            server_url = server.url
            if query_suffix:
                separator = "&" if "?" in server_url else "?"
                server_url = f"{server_url}{separator}{query_suffix}"

            # Build MCP server configuration
            server_config: dict[str, Any] = {
                "type": "url",
                "name": server.name,
            }

            if auth_token:
                server_config["authorization_token"] = auth_token

            # Inject OAuth token if required (overrides static header token)
            if server.auth_type == MCPAuthType.OAUTH_DISCOVERY and user_id is not None:
                token = await self._get_valid_token_for_server(server, user_id)
                if token:
                    server_config["authorization_token"] = token.access_token
                    logger.debug("Injected OAuth token for server %s", server.name)
                else:
                    # Track for potential auth flow
                    self._pending_auth_servers.append(server)
                    logger.debug(
                        "No valid token for OAuth server %s, auth may be required",
                        server.name,
                    )

            # Set the final URL (may include query params from headers)
            server_config["url"] = server_url
            server_configs.append(server_config)

            # Add MCP toolset for this server
            tools.append(
                {
                    "type": "mcp_toolset",
                    "mcp_server_name": server.name,
                }
            )

            # Collect prompts
            if server.prompt:
                prompts.append(f"- {server.prompt}")

        prompt_string = "\n".join(prompts) if prompts else ""
        return tools, server_configs, prompt_string

    async def _convert_messages_to_claude_format(
        self,
        messages: list[Message],
        file_content_blocks: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """Convert messages to Claude API format.

        Args:
            messages: List of conversation messages
            file_content_blocks: Optional file content blocks to attach

        Returns:
            List of Claude-formatted messages
        """
        claude_messages = []

        for i, msg in enumerate(messages):
            if msg.type == MessageType.SYSTEM:
                continue  # System messages handled separately

            role = "user" if msg.type == MessageType.HUMAN else "assistant"

            # Build content
            content: list[dict[str, Any]] = []

            # For the last user message, attach files if present
            is_last_user = (
                role == "user" and i == len(messages) - 1 and file_content_blocks
            )

            if is_last_user and file_content_blocks:
                content.extend(file_content_blocks)

            # Add text content
            content.append(
                {
                    "type": "text",
                    "text": msg.text,
                }
            )

            claude_messages.append(
                {
                    "role": role,
                    "content": content if len(content) > 1 else msg.text,
                }
            )

        return claude_messages

    async def _build_system_prompt(self, mcp_prompt: str = "") -> str:
        """Build the system prompt with optional MCP tool descriptions.

        Args:
            mcp_prompt: Optional MCP tool prompts

        Returns:
            Complete system prompt string
        """
        # Get base system prompt
        system_prompt_template = await get_system_prompt()

        # Format with MCP prompts
        if mcp_prompt:
            mcp_section = (
                "### Tool-Auswahlrichtlinien (Einbettung externer Beschreibungen)\n"
                f"{mcp_prompt}"
            )
        else:
            mcp_section = ""

        return system_prompt_template.format(mcp_prompts=mcp_section)

    async def _get_valid_token_for_server(
        self,
        server: MCPServer,
        user_id: int,
    ) -> AssistantMCPUserToken | None:
        """Get a valid OAuth token for the given server and user.

        Args:
            server: The MCP server configuration
            user_id: The user's ID

        Returns:
            A valid token or None if not available
        """
        if server.id is None:
            return None

        with rx.session() as session:
            token = self._mcp_auth_service.get_user_token(session, user_id, server.id)

            if token is None:
                return None

            return await self._mcp_auth_service.ensure_valid_token(
                session, server, token
            )

    async def _create_auth_required_chunk(self, server: MCPServer) -> Chunk:
        """Create an AUTH_REQUIRED chunk for a server that needs authentication.

        Args:
            server: The MCP server requiring authentication

        Returns:
            A chunk signaling auth is required with the auth URL
        """
        try:
            with get_session_manager().session() as session:
                auth_service = self._mcp_auth_service
                (
                    auth_url,
                    state,
                ) = await auth_service.build_authorization_url_with_registration(
                    server,
                    session=session,
                    user_id=self._current_user_id,
                )
                logger.info(
                    "Built auth URL for server %s, state=%s, url=%s",
                    server.name,
                    state,
                    auth_url[:100] if auth_url else "None",
                )
        except (ValueError, Exception) as e:
            logger.error("Cannot build auth URL for server %s: %s", server.name, str(e))
            auth_url = ""
            state = ""

        return Chunk(
            type=ChunkType.AUTH_REQUIRED,
            text=f"{server.name} benötigt Ihre Autorisierung",
            chunk_metadata={
                "server_id": str(server.id) if server.id else "",
                "server_name": server.name,
                "auth_url": auth_url,
                "state": state,
                "processor": "claude_responses",
            },
        )
