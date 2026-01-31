import asyncio
import logging
from collections.abc import AsyncGenerator
from typing import Any, Final

from openai import AsyncOpenAI
from sqlalchemy import select

from appkit_assistant.backend.database.models import (
    AssistantThread,
    MCPServer,
)
from appkit_assistant.backend.processors.mcp_mixin import MCPCapabilities
from appkit_assistant.backend.processors.processor_base import mcp_oauth_redirect_uri
from appkit_assistant.backend.processors.streaming_base import StreamingProcessorBase
from appkit_assistant.backend.schemas import (
    AIModel,
    Chunk,
    ChunkType,
    MCPAuthType,
    Message,
    MessageType,
)
from appkit_assistant.backend.services.file_upload_service import (
    FileUploadError,
    FileUploadService,
)
from appkit_assistant.backend.services.system_prompt_builder import SystemPromptBuilder
from appkit_assistant.configuration import FileUploadConfig
from appkit_commons.database.session import get_asyncdb_session

logger = logging.getLogger(__name__)
default_oauth_redirect_uri: Final[str] = mcp_oauth_redirect_uri()


class OpenAIResponsesProcessor(StreamingProcessorBase, MCPCapabilities):
    """Simplified processor using content accumulator pattern."""

    def __init__(
        self,
        models: dict[str, AIModel],
        api_key: str | None = None,
        base_url: str | None = None,
        is_azure: bool = False,
        oauth_redirect_uri: str = default_oauth_redirect_uri,
        file_upload_config: FileUploadConfig | None = None,
    ) -> None:
        StreamingProcessorBase.__init__(self, models, "openai_responses")
        MCPCapabilities.__init__(self, oauth_redirect_uri, "openai_responses")

        self.api_key = api_key
        self.base_url = base_url
        self.is_azure = is_azure
        self.client: AsyncOpenAI | None = None

        if self.api_key and self.base_url and is_azure:
            self.client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=f"{self.base_url}/openai/v1",
                default_query={"api-version": "preview"},
            )
        elif self.api_key and self.base_url:
            self.client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
        elif self.api_key:
            self.client = AsyncOpenAI(api_key=self.api_key)
        else:
            logger.warning("No API key found. Processor will not work.")

        # Services
        self._system_prompt_builder = SystemPromptBuilder()
        self._file_upload_config = file_upload_config or FileUploadConfig()
        self._file_upload_service: FileUploadService | None = None

        # Tool name tracking: tool_id -> tool_name for MCP streaming events
        self._tool_name_map: dict[str, str] = {}

        # Store available MCP servers for lookup during error handling
        self._available_mcp_servers: list[MCPServer] = []

        # Initialize file upload service if client is available
        if self.client:
            self._file_upload_service = FileUploadService(
                client=self.client,
                config=self._file_upload_config,
            )

    def get_supported_models(self) -> dict[str, AIModel]:
        """Return supported models if API key is available."""
        return self.models if self.api_key else {}

    async def process(  # noqa: PLR0912
        self,
        messages: list[Message],
        model_id: str,
        files: list[str] | None = None,
        mcp_servers: list[MCPServer] | None = None,
        payload: dict[str, Any] | None = None,
        user_id: int | None = None,
        cancellation_token: asyncio.Event | None = None,
    ) -> AsyncGenerator[Chunk, None]:
        """Process messages using simplified content accumulator pattern."""
        if not self.client:
            raise ValueError("OpenAI Client not initialized.")

        if model_id not in self.models:
            msg = f"Model {model_id} not supported by OpenAI processor"
            raise ValueError(msg)

        model = self.models[model_id]
        self.current_user_id = user_id
        self.clear_pending_auth_servers()

        # Process file uploads and yield progress in real-time
        vector_store_id: str | None = None
        async for chunk in self._process_file_uploads_streaming(
            files=files,
            payload=payload,
            user_id=user_id,
        ):
            # Extract vector_store_id from final chunk metadata
            if chunk.chunk_metadata and "vector_store_id" in chunk.chunk_metadata:
                vector_store_id = chunk.chunk_metadata["vector_store_id"]
            yield chunk

        try:
            session = await self._create_responses_request(
                messages, model, mcp_servers, payload, user_id, vector_store_id
            )

            try:
                if hasattr(session, "__aiter__"):  # Streaming
                    async for event in session:
                        if cancellation_token and cancellation_token.is_set():
                            logger.info("Processing cancelled by user")
                            break
                        chunk = self._handle_event(event)
                        if chunk:
                            yield chunk
                else:  # Non-streaming
                    content = self._extract_responses_content(session)
                    if content:
                        yield self.chunk_factory.text(
                            content, {"source": "responses_api", "streaming": "false"}
                        )
            except Exception as e:
                error_msg = str(e)
                logger.error("Error during response processing: %s", error_msg)
                # Only yield error chunk if NOT an auth error
                # and no auth servers are pending (they'll show auth card instead)
                is_auth_related = (
                    self.auth_detector.is_auth_error(error_msg)
                    or self.pending_auth_servers
                )
                if not is_auth_related:
                    yield self.chunk_factory.error(
                        f"Ein Fehler ist aufgetreten: {error_msg}",
                        error_type=type(e).__name__,
                    )

            # After processing (or on error), yield any pending auth requirements
            async for auth_chunk in self.yield_pending_auth_chunks():
                yield auth_chunk

        except Exception as e:
            logger.error("Critical error in OpenAI processor: %s", e)
            raise e

    def _get_event_handlers(self) -> dict[str, Any]:
        """Get the event handler mapping for OpenAI events."""
        # OpenAI uses a different event dispatch pattern with multiple handlers
        # This returns an empty dict as we use _handle_event directly
        return {}

    async def _process_file_uploads_streaming(  # noqa: PLR0911
        self,
        files: list[str] | None,
        payload: dict[str, Any] | None,
        user_id: int | None,
    ) -> AsyncGenerator[Chunk, None]:
        """Process file uploads and yield progress chunks in real-time.

        Args:
            files: List of local file paths to upload.
            payload: Request payload containing thread_uuid.
            user_id: ID of the user making the request.

        Yields:
            Chunk objects with real-time progress updates.
            Final chunk contains 'vector_store_id' in metadata.
        """
        thread_uuid = payload.get("thread_uuid") if payload else None

        if not thread_uuid:
            if files:
                logger.warning(
                    "Files provided but no thread_uuid in payload, skipping upload"
                )
            # Yield final chunk with no vector_store_id
            yield Chunk(
                type=ChunkType.PROCESSING,
                text="",
                chunk_metadata={"status": "skipped", "vector_store_id": None},
            )
            return

        if not user_id:
            if files:
                logger.warning("Files provided but no user_id, skipping upload")
            yield Chunk(
                type=ChunkType.PROCESSING,
                text="",
                chunk_metadata={"status": "skipped", "vector_store_id": None},
            )
            return

        # Look up thread to get database ID and existing vector store
        async with get_asyncdb_session() as session:
            result = await session.execute(
                select(AssistantThread).where(AssistantThread.thread_id == thread_uuid)
            )
            thread = result.scalar_one_or_none()

            if not thread:
                if files:
                    logger.warning(
                        "Thread %s not found in database, cannot upload files",
                        thread_uuid,
                    )
                yield Chunk(
                    type=ChunkType.PROCESSING,
                    text="",
                    chunk_metadata={"status": "skipped", "vector_store_id": None},
                )
                return

            thread_db_id = thread.id
            existing_vector_store_id = thread.vector_store_id

        # If no files but thread has existing vector store, validate and use it
        if not files:
            if existing_vector_store_id:
                logger.debug(
                    "Validating existing vector store %s for thread %s",
                    existing_vector_store_id,
                    thread_uuid,
                )
                # Validate vector store exists, recreate if needed
                if self._file_upload_service:
                    svc = self._file_upload_service
                    validated_id, _ = await svc.get_vector_store(
                        thread_id=thread_db_id,
                        thread_uuid=thread_uuid,
                    )
                    yield Chunk(
                        type=ChunkType.PROCESSING,
                        text="",
                        chunk_metadata={
                            "status": "completed",
                            "vector_store_id": validated_id,
                        },
                    )
                    return
            yield Chunk(
                type=ChunkType.PROCESSING,
                text="",
                chunk_metadata={
                    "status": "completed",
                    "vector_store_id": existing_vector_store_id,
                },
            )
            return

        # Process file uploads with streaming progress
        if not self._file_upload_service:
            logger.warning("File upload service not available")
            yield Chunk(
                type=ChunkType.PROCESSING,
                text="",
                chunk_metadata={
                    "status": "completed",
                    "vector_store_id": existing_vector_store_id,
                },
            )
            return

        try:
            async for chunk in self._file_upload_service.process_files(
                file_paths=files,
                thread_db_id=thread_db_id,
                thread_uuid=thread_uuid,
                user_id=user_id,
            ):
                yield chunk

            logger.info(
                "Processed %d files for thread %s",
                len(files),
                thread_uuid,
            )
        except FileUploadError as e:
            logger.error("File upload failed: %s", e)
            # Yield error and existing vector store if available
            yield Chunk(
                type=ChunkType.PROCESSING,
                text=f"Fehler beim Upload: {e}",
                chunk_metadata={
                    "status": "failed",
                    "vector_store_id": existing_vector_store_id,
                    "error": str(e),
                },
            )

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
        if event_type == "response.created":
            return self.chunk_factory.lifecycle("created", {"stage": "created"})
        if event_type == "response.in_progress":
            return self.chunk_factory.lifecycle("in_progress", {"stage": "in_progress"})
        if event_type == "response.done":
            return self.chunk_factory.completion(status="done")
        return None

    def _handle_text_events(self, event_type: str, event: Any) -> Chunk | None:
        """Handle text-related events."""
        if event_type == "response.output_text.delta":
            return self.chunk_factory.text(event.delta, {"delta": event.delta})

        if event_type == "response.output_text.annotation.added":
            # Annotation can be a dict (file_citation) or other object
            annotation = event.annotation
            if isinstance(annotation, dict):
                # Handle URL citations
                if annotation.get("type") == "url_citation":
                    annotation_text = annotation.get("url", str(annotation))
                else:
                    annotation_text = annotation.get("filename", str(annotation))

                annotation_str = str(annotation)
            else:
                annotation_text = str(annotation)
                annotation_str = annotation_text
            return self.chunk_factory.annotation(
                annotation_text, {"annotation": annotation_str}
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
            # Store tool name mapping for streaming events
            self._tool_name_map[tool_id] = f"{server_label}.{tool_name}"
            logger.debug(
                "MCP call started: %s.%s (id=%s)",
                server_label,
                tool_name,
                tool_id,
            )
            return self.chunk_factory.tool_call(
                f"Benutze Werkzeug: {server_label}.{tool_name}",
                tool_name=tool_name,
                tool_id=tool_id,
                server_label=server_label,
                status="starting",
                reasoning_session=self.current_reasoning_session,
            )

        if item.type == "reasoning":
            reasoning_id = getattr(item, "id", "unknown_id")
            # Track the current reasoning session
            self.current_reasoning_session = reasoning_id
            return self.chunk_factory.thinking(
                "Denke nach...", reasoning_id=reasoning_id, status="starting"
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
            return self.chunk_factory.create(
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
            if self.auth_detector.is_auth_error(error):
                # Find the server config and queue for auth flow
                return self.chunk_factory.tool_result(
                    f"Authentifizierung erforderlich für {server_label}.{tool_name}",
                    tool_id=tool_id,
                    status="auth_required",
                    is_error=True,
                    reasoning_session=self.current_reasoning_session,
                )

            return self.chunk_factory.tool_result(
                f"Werkzeugfehler bei {tool_name}: {error_text}",
                tool_id=tool_id,
                status="error",
                is_error=True,
                reasoning_session=self.current_reasoning_session,
            )

        output_text = str(output) if output else "Werkzeug erfolgreich aufgerufen"
        return self.chunk_factory.tool_result(
            output_text,
            tool_id=tool_id,
            status="completed",
            reasoning_session=self.current_reasoning_session,
        )

    def _extract_error_text(self, error: Any) -> str:
        """Extract readable error text from error object."""
        if isinstance(error, dict) and "content" in error:
            content = error["content"]
            if isinstance(content, list) and content:
                return content[0].get("text", str(error))
        return "Unknown error"

    def _handle_mcp_events(  # noqa: PLR0911, PLR0912, PLR0915
        self, event_type: str, event: Any
    ) -> Chunk | None:
        """Handle MCP-specific events."""
        if event_type == "response.mcp_call_arguments.delta":
            tool_id = getattr(event, "item_id", "unknown_id")
            arguments_delta = getattr(event, "delta", "")
            tool_name = self._tool_name_map.get(tool_id, "mcp_tool")
            return self.chunk_factory.tool_call(
                arguments_delta,
                tool_name=tool_name,
                tool_id=tool_id,
                status="arguments_streaming",
                reasoning_session=self.current_reasoning_session,
            )

        if event_type == "response.mcp_call_arguments.done":
            tool_id = getattr(event, "item_id", "unknown_id")
            arguments = getattr(event, "arguments", "")
            tool_name = self._tool_name_map.get(tool_id, "mcp_tool")
            return self.chunk_factory.tool_call(
                f"Parameter: {arguments}",
                tool_name=tool_name,
                tool_id=tool_id,
                status="arguments_complete",
                reasoning_session=self.current_reasoning_session,
            )

        if event_type == "response.mcp_call.failed":
            tool_id = getattr(event, "item_id", "unknown_id")
            tool_name = self._tool_name_map.get(tool_id, tool_id)
            return self.chunk_factory.tool_result(
                f"Werkzeugnutzung abgebrochen: {tool_name}",
                tool_id=tool_id,
                status="failed",
                is_error=True,
                reasoning_session=self.current_reasoning_session,
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
            is_auth_error = self.auth_detector.is_auth_error(error_str)
            auth_server = None

            # 1. Find matching server by name in error message from pending servers
            for server in self.pending_auth_servers:
                if server.name.lower() in error_str.lower():
                    auth_server = server
                    break

            # 2. If not found in pending, search available servers by name
            if not auth_server and is_auth_error:
                for server in self._available_mcp_servers:
                    if server.name.lower() in error_str.lower():
                        auth_server = server
                        logger.debug(
                            "Found server %s in available servers for auth error",
                            server.name,
                        )
                        break

            # 3. Fallback: if we have pending servers and it looks like an auth error,
            # assume the failure belongs to the first pending server
            if (
                not auth_server
                and self.pending_auth_servers
                and (is_auth_error or len(self.pending_auth_servers) == 1)
            ):
                auth_server = self.pending_auth_servers[0]
                logger.debug(
                    "Assuming pending server %s for list_tools failure '%s'",
                    auth_server.name,
                    error_str,
                )

            if auth_server:
                logger.debug(
                    "Queuing Auth Card for server: %s (Error: %s)",
                    auth_server.name,
                    error_str,
                )
                # Queue for async processing in the main process loop
                # The auth chunk will be yielded after event processing completes
                self.add_pending_auth_server(auth_server)
                return self.chunk_factory.tool_result(
                    f"Authentifizierung erforderlich für {auth_server.name}",
                    tool_id=tool_id,
                    status="auth_required",
                    is_error=True,
                    reasoning_session=self.current_reasoning_session,
                )

            logger.error("MCP tool listing failed for tool_id: %s", str(event))
            return self.chunk_factory.tool_result(
                f"Werkzeugliste konnte nicht geladen werden: {tool_id}",
                tool_id=tool_id,
                status="listing_failed",
                is_error=True,
                reasoning_session=self.current_reasoning_session,
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
            return self.chunk_factory.completion(status="response_complete")
        return None

    def _handle_image_events(self, event_type: str, event: Any) -> Chunk | None:
        """Handle image-related events."""
        if "image" in event_type and (hasattr(event, "url") or hasattr(event, "data")):
            image_data = {
                "url": getattr(event, "url", ""),
                "data": getattr(event, "data", ""),
            }
            image_str = str(image_data)
            return self.chunk_factory.create(ChunkType.IMAGE, image_str, image_data)
        return None

    async def _create_responses_request(
        self,
        messages: list[Message],
        model: AIModel,
        mcp_servers: list[MCPServer] | None = None,
        payload: dict[str, Any] | None = None,
        user_id: int | None = None,
        vector_store_id: str | None = None,
    ) -> Any:
        """Create a simplified responses API request."""
        # Configure MCP tools if provided (now async for token lookup)
        tools, mcp_prompt = (
            await self._configure_mcp_tools(mcp_servers, user_id)
            if mcp_servers
            else ([], "")
        )

        # Add file_search tool if vector store is available
        if vector_store_id:
            file_search_tool = {
                "type": "file_search",
                "vector_store_ids": [vector_store_id],
                "max_num_results": 20,
            }
            tools.append(file_search_tool)
            logger.debug(
                "Added file_search tool with vector_store: %s",
                vector_store_id,
            )

        # Add web_search tool if enabled and supported
        if model.supports_search and payload and payload.get("web_search_enabled"):
            tools.append({"type": "web_search"})
            payload.pop("web_search_enabled", None)
            logger.debug("Added web_search tool")

        # Convert messages to responses format with system message
        input_messages = await self._convert_messages_to_responses_format(
            messages, mcp_prompt=mcp_prompt
        )

        # Filter out internal payload keys that shouldn't go to OpenAI
        filtered_payload = {}
        if payload:
            internal_keys = {"thread_uuid"}
            filtered_payload = {
                k: v for k, v in payload.items() if k not in internal_keys
            }

        params = {
            "model": model.model,
            "input": input_messages,
            "stream": model.stream,
            "temperature": model.temperature,
            "tools": tools,
            "reasoning": {"effort": "medium"},
            **filtered_payload,
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
            self._available_mcp_servers = []
            return [], ""

        # Store for lookup during error handling (e.g., 401 errors)
        self._available_mcp_servers = mcp_servers

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
            headers = self.parse_mcp_headers(server)

            # Inject OAuth token if server requires OAuth and user is authenticated
            if server.auth_type == MCPAuthType.OAUTH_DISCOVERY and user_id is not None:
                token = await self.get_valid_token(server, user_id)
                if token:
                    headers["Authorization"] = f"Bearer {token.access_token}"
                    logger.debug("Injected OAuth token for server %s", server.name)
                else:
                    # No valid token - server will likely fail with 401
                    # Track this server for potential auth flow
                    self.add_pending_auth_server(server)
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

        if use_system_prompt:
            system_text = await self._system_prompt_builder.build(mcp_prompt)
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
