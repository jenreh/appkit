import json
import logging
from collections.abc import AsyncGenerator
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
from appkit_assistant.backend.processors.openai_base import BaseOpenAIProcessor
from appkit_assistant.backend.system_prompt_cache import get_system_prompt
from appkit_commons.database.session import get_session_manager

logger = logging.getLogger(__name__)
default_oauth_redirect_uri: Final[str] = mcp_oauth_redirect_uri()


class OpenAIResponsesProcessor(BaseOpenAIProcessor):
    """Simplified processor using content accumulator pattern."""

    def __init__(
        self,
        models: dict[str, AIModel],
        api_key: str | None = None,
        base_url: str | None = None,
        is_azure: bool = False,
        oauth_redirect_uri: str = default_oauth_redirect_uri,
    ) -> None:
        super().__init__(models, api_key, base_url, is_azure)
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
    ) -> AsyncGenerator[Chunk, None]:
        """Process messages using simplified content accumulator pattern."""
        if not self.client:
            raise ValueError("OpenAI Client not initialized.")

        if model_id not in self.models:
            msg = f"Model {model_id} not supported by OpenAI processor"
            raise ValueError(msg)

        model = self.models[model_id]
        self._current_user_id = user_id
        self._pending_auth_servers = []

        try:
            session = await self._create_responses_request(
                messages, model, mcp_servers, payload, user_id
            )

            try:
                if hasattr(session, "__aiter__"):  # Streaming
                    async for event in session:
                        chunk = self._handle_event(event)
                        if chunk:
                            yield chunk
                else:  # Non-streaming
                    content = self._extract_responses_content(session)
                    if content:
                        yield Chunk(
                            type=ChunkType.TEXT,
                            text=content,
                            chunk_metadata={
                                "source": "responses_api",
                                "streaming": "false",
                            },
                        )
            except Exception as e:
                error_msg = str(e)
                logger.error("Error during response processing: %s", error_msg)
                # Only yield error chunk if NOT an auth error
                # and no auth servers are pending (they'll show auth card instead)
                is_auth_related = (
                    self._is_auth_error(error_msg) or self._pending_auth_servers
                )
                if not is_auth_related:
                    yield Chunk(
                        type=ChunkType.ERROR,
                        text=f"Ein Fehler ist aufgetreten: {error_msg}",
                        chunk_metadata={
                            "source": "responses_api",
                            "error_type": type(e).__name__,
                        },
                    )

            # After processing (or on error), yield any pending auth requirements
            logger.debug(
                "Processing pending auth servers: %d", len(self._pending_auth_servers)
            )
            for server in self._pending_auth_servers:
                logger.debug("Yielding auth chunk for server: %s", server.name)
                yield await self._create_auth_required_chunk(server)

        except Exception as e:
            logger.error("Critical error in OpenAI processor: %s", e)
            raise e

    def _handle_event(self, event: Any) -> Chunk | None:
        """Simplified event handler returning actual event content in chunks."""
        if not hasattr(event, "type"):
            return None

        event_type = event.type
        handlers = [
            self._handle_lifecycle_events,
            lambda et: self._handle_text_events(et, event),
            lambda et: self._handle_item_events(et, event),
            lambda et: self._handle_mcp_events(et, event),
            lambda et: self._handle_content_events(et, event),
            lambda et: self._handle_completion_events(et, event),
            lambda et: self._handle_image_events(et, event),
        ]

        for handler in handlers:
            result = handler(event_type)
            if result:
                # content_preview = result.text[:50] if result.text else ""
                # logger.debug(
                #     "Event %s → Chunk: type=%s, content=%s",
                #     event_type,
                #     result.type,
                #     content_preview,
                # )
                return result

        logger.debug("Unhandled event type: %s", event_type)
        return None

    def _handle_lifecycle_events(self, event_type: str) -> Chunk | None:
        """Handle lifecycle events."""
        lifecycle_events = {
            "response.created": ("created", {"stage": "created"}),
            "response.in_progress": ("in_progress", {"stage": "in_progress"}),
            "response.done": ("done", {"stage": "done"}),
        }

        if event_type in lifecycle_events:
            content, metadata = lifecycle_events[event_type]
            chunk_type = (
                ChunkType.LIFECYCLE
                if event_type != "response.done"
                else ChunkType.COMPLETION
            )
            return self._create_chunk(chunk_type, content, metadata)
        return None

    def _handle_text_events(self, event_type: str, event: Any) -> Chunk | None:
        """Handle text-related events."""
        if event_type == "response.output_text.delta":
            return self._create_chunk(
                ChunkType.TEXT, event.delta, {"delta": event.delta}
            )

        if event_type == "response.output_text.annotation.added":
            return self._create_chunk(
                ChunkType.ANNOTATION,
                event.annotation,
                {"annotation": event.annotation},
            )

        return None

    def _handle_item_events(self, event_type: str, event: Any) -> Chunk | None:
        """Handle item added/done events for MCP calls and reasoning."""
        if (
            event_type == "response.output_item.added"
            and hasattr(event, "item")
            and hasattr(event.item, "type")
        ):
            return self._handle_item_added(event.item)

        if (
            event_type == "response.output_item.done"
            and hasattr(event, "item")
            and hasattr(event.item, "type")
        ):
            return self._handle_item_done(event.item)

        return None

    def _handle_item_added(self, item: Any) -> Chunk | None:
        """Handle when an item is added."""
        if item.type == "mcp_call":
            tool_name = getattr(item, "name", "unknown_tool")
            tool_id = getattr(item, "id", "unknown_id")
            server_label = getattr(item, "server_label", "unknown_server")
            logger.debug(
                "MCP call started: %s.%s (id=%s)",
                server_label,
                tool_name,
                tool_id,
            )
            return self._create_chunk(
                ChunkType.TOOL_CALL,
                f"Benutze Werkzeug: {server_label}.{tool_name}",
                {
                    "tool_name": tool_name,
                    "tool_id": tool_id,
                    "server_label": server_label,
                    "status": "starting",
                    "reasoning_session": self._current_reasoning_session,
                },
            )

        if item.type == "reasoning":
            reasoning_id = getattr(item, "id", "unknown_id")
            # Track the current reasoning session
            self._current_reasoning_session = reasoning_id
            return self._create_chunk(
                ChunkType.THINKING,
                "Denke nach...",
                {"reasoning_id": reasoning_id, "status": "starting"},
            )
        return None

    def _handle_item_done(self, item: Any) -> Chunk | None:
        """Handle when an item is completed."""
        if item.type == "mcp_call":
            return self._handle_mcp_call_done(item)

        if item.type == "reasoning":
            reasoning_id = getattr(item, "id", "unknown_id")
            summary = getattr(item, "summary", [])
            summary_text = str(summary) if summary else "beendet."
            return self._create_chunk(
                ChunkType.THINKING_RESULT,
                summary_text,
                {"reasoning_id": reasoning_id, "status": "completed"},
            )
        return None

    def _handle_mcp_call_done(self, item: Any) -> Chunk | None:
        """Handle MCP call completion.

        Detects 401/403 authentication errors and marks servers for auth flow.
        """
        tool_id = getattr(item, "id", "unknown_id")
        tool_name = getattr(item, "name", "unknown_tool")
        server_label = getattr(item, "server_label", "unknown_server")
        error = getattr(item, "error", None)
        output = getattr(item, "output", None)

        if error:
            error_text = self._extract_error_text(error)

            # Check for authentication errors (401/403)
            if self._is_auth_error(error):
                # Find the server config and queue for auth flow
                return self._create_chunk(
                    ChunkType.TOOL_RESULT,
                    f"Authentifizierung erforderlich für {server_label}",
                    {
                        "tool_id": tool_id,
                        "tool_name": tool_name,
                        "server_label": server_label,
                        "status": "auth_required",
                        "error": True,
                        "auth_required": True,
                        "reasoning_session": self._current_reasoning_session,
                    },
                )

            return self._create_chunk(
                ChunkType.TOOL_RESULT,
                f"Werkzeugfehler: {error_text}",
                {
                    "tool_id": tool_id,
                    "tool_name": tool_name,
                    "status": "error",
                    "error": True,
                    "error_details": str(error),
                    "reasoning_session": self._current_reasoning_session,
                },
            )

        output_text = str(output) if output else "Werkzeug erfolgreich aufgerufen"
        return self._create_chunk(
            ChunkType.TOOL_RESULT,
            output_text,
            {
                "tool_id": tool_id,
                "tool_name": tool_name,
                "status": "completed",
                "reasoning_session": self._current_reasoning_session,
            },
        )

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

    def _extract_error_text(self, error: Any) -> str:
        """Extract readable error text from error object."""
        if isinstance(error, dict) and "content" in error:
            content = error["content"]
            if isinstance(content, list) and content:
                return content[0].get("text", str(error))
        return "Unknown error"

    def _handle_mcp_events(self, event_type: str, event: Any) -> Chunk | None:  # noqa: PLR0911, PLR0912
        """Handle MCP-specific events."""
        if event_type == "response.mcp_call_arguments.delta":
            tool_id = getattr(event, "item_id", "unknown_id")
            arguments_delta = getattr(event, "delta", "")
            return self._create_chunk(
                ChunkType.TOOL_CALL,
                arguments_delta,
                {
                    "tool_id": tool_id,
                    "status": "arguments_streaming",
                    "delta": arguments_delta,
                    "reasoning_session": self._current_reasoning_session,
                },
            )

        if event_type == "response.mcp_call_arguments.done":
            tool_id = getattr(event, "item_id", "unknown_id")
            arguments = getattr(event, "arguments", "")
            return self._create_chunk(
                ChunkType.TOOL_CALL,
                f"Parameter: {arguments}",
                {
                    "tool_id": tool_id,
                    "status": "arguments_complete",
                    "arguments": arguments,
                    "reasoning_session": self._current_reasoning_session,
                },
            )

        if event_type == "response.mcp_call.failed":
            tool_id = getattr(event, "item_id", "unknown_id")
            return self._create_chunk(
                ChunkType.TOOL_RESULT,
                f"Werkzeugnutzung abgebrochen: {tool_id}",
                {
                    "tool_id": tool_id,
                    "status": "failed",
                    "error": True,
                    "reasoning_session": self._current_reasoning_session,
                },
            )

        if event_type == "response.mcp_call.in_progress":
            tool_id = getattr(event, "item_id", "unknown_id")
            # This event doesn't have tool details, just acknowledge it
            logger.debug("MCP call in progress: %s", tool_id)
            return None

        if event_type == "response.mcp_call.completed":
            # MCP call completed successfully - handled via response.output_item.done
            # but we can log for debugging
            tool_id = getattr(event, "item_id", "unknown_id")
            logger.debug("MCP call completed: %s", tool_id)
            return None

        if event_type == "response.mcp_list_tools.in_progress":
            # This is a setup event, not a tool call - just log and return None
            tool_id = getattr(event, "item_id", "unknown_id")
            logger.debug("MCP list_tools in progress: %s", tool_id)
            return None

        if event_type == "response.mcp_list_tools.completed":
            # This is a setup event, not a tool call - just log and return None
            tool_id = getattr(event, "item_id", "unknown_id")
            logger.debug("MCP list_tools completed: %s", tool_id)
            return None

        if event_type == "response.mcp_list_tools.failed":
            tool_id = getattr(event, "item_id", "unknown_id")
            error = getattr(event, "error", None)

            # Debugging: Log available attributes to help diagnosis
            if logger.isEnabledFor(logging.DEBUG) and error:
                logger.debug("Error object type: %s, content: %s", type(error), error)

            # Extract error message safely
            error_str = ""
            if error:
                if isinstance(error, dict):
                    error_str = error.get("message", str(error))
                elif hasattr(error, "message"):
                    error_str = getattr(error, "message", str(error))
                else:
                    error_str = str(error)

            # Check for authentication errors (401/403)
            # OR if we have pending auth servers (strong signal we missed a token)
            is_auth_error = self._is_auth_error(error_str)
            pending_server = None

            # 1. Try to find matching server by name in error message
            for server in self._pending_auth_servers:
                if server.name.lower() in error_str.lower():
                    pending_server = server
                    break

            # 2. If no match but we have pending servers and it looks like an auth error
            # OR if we have pending servers and likely one of them failed (len=1)
            # We assume the failure belongs to the pending server if we can't be sure
            if (
                not pending_server
                and self._pending_auth_servers
                and (is_auth_error or len(self._pending_auth_servers) == 1)
            ):
                pending_server = self._pending_auth_servers[0]
                logger.debug(
                    "Assuming pending server %s for list_tools failure '%s'",
                    pending_server.name,
                    error_str,
                )

            if pending_server:
                logger.debug(
                    "Queuing Auth Card for server: %s (Error: %s)",
                    pending_server.name,
                    error_str,
                )
                # Queue for async processing in the main process loop
                # The auth chunk will be yielded after event processing completes
                if pending_server not in self._pending_auth_servers:
                    self._pending_auth_servers.append(pending_server)
                return self._create_chunk(
                    ChunkType.TOOL_RESULT,
                    f"Authentifizierung erforderlich für {pending_server.name}",
                    {
                        "tool_id": tool_id,
                        "status": "auth_required",
                        "server_name": pending_server.name,
                        "auth_pending": True,
                        "reasoning_session": self._current_reasoning_session,
                    },
                )

            logger.error("MCP tool listing failed for tool_id: %s", str(event))
            return self._create_chunk(
                ChunkType.TOOL_RESULT,
                f"Werkzeugliste konnte nicht geladen werden: {tool_id}",
                {
                    "tool_id": tool_id,
                    "status": "listing_failed",
                    "error": True,
                    "reasoning_session": self._current_reasoning_session,
                },
            )

        return None

    def _handle_content_events(self, event_type: str, event: Any) -> Chunk | None:  # noqa: ARG002
        """Handle content-related events."""
        if event_type == "response.content_part.added":
            # Content part added - this typically starts text streaming
            return None  # No need to show this as a separate chunk

        if event_type == "response.content_part.done":
            # Content part completed - this typically ends text streaming
            return None  # No need to show this as a separate chunk

        if event_type == "response.output_text.done":
            # Text output completed - already received via delta events
            # Skip to avoid duplicate content
            return None

        return None

    def _handle_completion_events(self, event_type: str, event: Any) -> Chunk | None:  # noqa: ARG002
        """Handle completion-related events."""
        if event_type == "response.completed":
            return self._create_chunk(
                ChunkType.COMPLETION,
                "Response generation completed",
                {"status": "response_complete"},
            )
        return None

    def _handle_image_events(self, event_type: str, event: Any) -> Chunk | None:
        """Handle image-related events."""
        if "image" in event_type and (hasattr(event, "url") or hasattr(event, "data")):
            image_data = {
                "url": getattr(event, "url", ""),
                "data": getattr(event, "data", ""),
            }
            image_str = str(image_data)
            return self._create_chunk(ChunkType.IMAGE, image_str, image_data)
        return None

    def _create_chunk(
        self,
        chunk_type: ChunkType,
        content: str,
        extra_metadata: dict[str, str] | None = None,
    ) -> Chunk:
        """Create a Chunk with actual content from the event"""
        metadata = {
            "processor": "openai_responses_simplified",
        }

        if extra_metadata:
            # Ensure all metadata values are strings
            for key, value in extra_metadata.items():
                if value is not None:
                    metadata[key] = str(value)

        return Chunk(
            type=chunk_type,
            text=content,
            chunk_metadata=metadata,
        )

    async def _create_responses_request(
        self,
        messages: list[Message],
        model: AIModel,
        mcp_servers: list[MCPServer] | None = None,
        payload: dict[str, Any] | None = None,
        user_id: int | None = None,
    ) -> Any:
        """Create a simplified responses API request."""
        # Configure MCP tools if provided (now async for token lookup)
        tools, mcp_prompt = (
            await self._configure_mcp_tools(mcp_servers, user_id)
            if mcp_servers
            else ([], "")
        )

        # Convert messages to responses format with system message
        input_messages = await self._convert_messages_to_responses_format(
            messages, mcp_prompt=mcp_prompt
        )

        params = {
            "model": model.model,
            "input": input_messages,
            "stream": model.stream,
            "temperature": model.temperature,
            "tools": tools,
            "reasoning": {"effort": "medium"},
            **(payload or {}),
        }

        return await self.client.responses.create(**params)

    async def _configure_mcp_tools(
        self,
        mcp_servers: list[MCPServer] | None,
        user_id: int | None = None,
    ) -> tuple[list[dict[str, Any]], str]:
        """Configure MCP servers as tools for the responses API.

        Injects OAuth Bearer tokens for servers that require authentication.

        Returns:
            tuple: (tools list, concatenated prompts string)
        """
        if not mcp_servers:
            return [], ""

        tools = []
        prompts = []

        for server in mcp_servers:
            tool_config = {
                "type": "mcp",
                "server_label": server.name,
                "server_url": server.url,
                "require_approval": "never",
            }

            # Start with existing headers
            headers = {}
            if server.headers and server.headers != "{}":
                headers = json.loads(server.headers)

            # Inject OAuth token if server requires OAuth and user is authenticated
            if server.auth_type == MCPAuthType.OAUTH_DISCOVERY and user_id is not None:
                token = await self._get_valid_token_for_server(server, user_id)
                if token:
                    headers["Authorization"] = f"Bearer {token.access_token}"
                    logger.debug("Injected OAuth token for server %s", server.name)
                else:
                    # No valid token - server will likely fail with 401
                    # Track this server for potential auth flow
                    self._pending_auth_servers.append(server)
                    logger.debug(
                        "No valid token for OAuth server %s, auth may be required",
                        server.name,
                    )

            if headers:
                tool_config["headers"] = headers

            tools.append(tool_config)

            if server.prompt:
                prompts.append(f"- {server.prompt}")

        prompt_string = "\n".join(prompts) if prompts else ""
        return tools, prompt_string

    async def _convert_messages_to_responses_format(
        self,
        messages: list[Message],
        mcp_prompt: str = "",
        use_system_prompt: bool = True,
    ) -> list[dict[str, Any]]:
        """Convert messages to the responses API input format.

        The system message is always prepended as the first message with role="system".
        """
        input_messages = []

        # Always add system message as first message
        if mcp_prompt:
            mcp_prompt = (
                "### Tool-Auswahlrichtlinien (Einbettung externer Beschreibungen)\n"
                f"{mcp_prompt}"
            )
        else:
            mcp_prompt = ""

        if use_system_prompt:
            system_prompt_template = await get_system_prompt()
            system_text = system_prompt_template.format(mcp_prompts=mcp_prompt)
            input_messages.append(
                {
                    "role": "system",
                    "content": [{"type": "input_text", "text": system_text}],
                }
            )

        # Add conversation messages
        for msg in messages:
            if msg.type == MessageType.SYSTEM:
                continue  # System messages are handled above

            role = "user" if msg.type == MessageType.HUMAN else "assistant"
            content_type = "input_text" if role == "user" else "output_text"
            input_messages.append(
                {"role": role, "content": [{"type": content_type, "text": msg.text}]}
            )

        return input_messages

    def _extract_responses_content(self, session: Any) -> str | None:
        """Extract content from non-streaming responses."""
        if (
            hasattr(session, "output")
            and session.output
            and isinstance(session.output, list)
            and session.output
        ):
            first_output = session.output[0]
            if hasattr(first_output, "content") and first_output.content:
                if isinstance(first_output.content, list):
                    return first_output.content[0].get("text", "")
                return str(first_output.content)
        return None

    async def _get_valid_token_for_server(
        self,
        server: MCPServer,
        user_id: int,
    ) -> AssistantMCPUserToken | None:
        """Get a valid OAuth token for the given server and user.

        Refreshes the token if expired and refresh token is available.

        Args:
            server: The MCP server configuration.
            user_id: The user's ID.

        Returns:
            A valid token or None if not available.
        """
        if server.id is None:
            return None

        with rx.session() as session:
            token = self._mcp_auth_service.get_user_token(session, user_id, server.id)

            if token is None:
                return None

            # Check if token is valid or can be refreshed
            return await self._mcp_auth_service.ensure_valid_token(
                session, server, token
            )

    async def _create_auth_required_chunk(self, server: MCPServer) -> Chunk:
        """Create an AUTH_REQUIRED chunk for a server that needs authentication.

        Args:
            server: The MCP server requiring authentication.

        Returns:
            A chunk signaling auth is required with the auth URL.
        """
        # Build the authorization URL
        try:
            # We use a session to store the PKCE state
            # NOTE: rx.session() is for Reflex user session, not DB session.
            # We use get_session_manager().session() for DB access required by PKCE.
            with get_session_manager().session() as session:
                # Use the async method that supports DCR
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
                "processor": "openai_responses",
            },
        )
