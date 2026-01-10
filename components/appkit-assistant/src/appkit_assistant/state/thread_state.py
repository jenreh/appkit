"""Thread state management for the assistant.

This module contains ThreadState which manages the current active thread:
- Creating new threads (not persisted until first response)
- Loading threads from database when selected from list
- Processing messages and handling responses
- Persisting thread data to database
- Notifying ThreadListState when a new thread is created

See thread_list_state.py for ThreadListState which manages the thread list sidebar.
"""

import json
import logging
import uuid
from collections.abc import AsyncGenerator
from enum import StrEnum
from typing import Any

import reflex as rx
from pydantic import BaseModel

from appkit_assistant.backend.model_manager import ModelManager
from appkit_assistant.backend.models import (
    AIModel,
    AssistantThread,
    Chunk,
    ChunkType,
    MCPServer,
    Message,
    MessageType,
    Suggestion,
    ThreadModel,
    ThreadStatus,
)
from appkit_assistant.backend.repositories import mcp_server_repo, thread_repo
from appkit_assistant.state.thread_list_state import ThreadListState
from appkit_commons.database.session import get_asyncdb_session
from appkit_user.authentication.states import UserSession

logger = logging.getLogger(__name__)


class ThinkingType(StrEnum):
    REASONING = "reasoning"
    TOOL_CALL = "tool_call"


class ThinkingStatus(StrEnum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ERROR = "error"


class Thinking(BaseModel):
    type: ThinkingType
    id: str  # reasoning_session_id or tool_id
    text: str
    status: ThinkingStatus = ThinkingStatus.IN_PROGRESS
    tool_name: str | None = None
    parameters: str | None = None
    result: str | None = None
    error: str | None = None


class ThreadState(rx.State):
    """State for managing the current active thread.

    Responsibilities:
    - Managing the current thread data and messages
    - Creating new empty threads
    - Loading threads from database when selected
    - Processing messages and streaming responses
    - Persisting thread data to database (incrementally)
    - Notifying ThreadListState when new threads are created
    """

    _thread: ThreadModel = ThreadModel(thread_id=str(uuid.uuid4()), prompt="")
    ai_models: list[AIModel] = []
    selected_model: str = ""
    processing: bool = False
    messages: list[Message] = []
    prompt: str = ""
    suggestions: list[Suggestion] = []

    # Chunk processing state
    thinking_items: list[Thinking] = []  # Consolidated reasoning and tool calls
    image_chunks: list[Chunk] = []
    show_thinking: bool = False
    thinking_expanded: bool = False
    current_activity: str = ""
    current_reasoning_session: str = ""  # Track current reasoning session
    current_tool_session: str = ""  # Track current tool session when tool_id missing

    # MCP Server tool support state
    selected_mcp_servers: list[MCPServer] = []
    show_tools_modal: bool = False
    available_mcp_servers: list[MCPServer] = []
    temp_selected_mcp_servers: list[int] = []
    server_selection_state: dict[int, bool] = {}

    # MCP OAuth state
    pending_auth_server_id: str = ""
    pending_auth_server_name: str = ""
    pending_auth_url: str = ""
    show_auth_card: bool = False
    pending_oauth_message: str = ""  # Message that triggered OAuth, resent on success

    # Thread list integration
    with_thread_list: bool = False

    # Internal state
    _initialized: bool = False
    _current_user_id: str = ""
    _skip_user_message: bool = False  # Skip adding user message (for OAuth resend)

    # -------------------------------------------------------------------------
    # Computed properties
    # -------------------------------------------------------------------------

    @rx.var
    def current_user_id(self) -> str:
        """Get the current user ID for OAuth validation."""
        return self._current_user_id

    @rx.var
    def get_selected_model(self) -> str:
        """Get the currently selected model ID."""
        return self.selected_model

    @rx.var
    def has_ai_models(self) -> bool:
        """Check if there are any chat models."""
        return len(self.ai_models) > 0

    @rx.var
    def has_suggestions(self) -> bool:
        """Check if there are any suggestions."""
        return len(self.suggestions) > 0

    @rx.var
    def has_thinking_content(self) -> bool:
        """Check if there are any thinking items to display."""
        return len(self.thinking_items) > 0

    @rx.var
    def selected_model_supports_tools(self) -> bool:
        """Check if the currently selected model supports tools."""
        if not self.selected_model:
            return False
        model = ModelManager().get_model(self.selected_model)
        return model.supports_tools if model else False

    @rx.var
    def get_unique_reasoning_sessions(self) -> list[str]:
        """Get unique reasoning session IDs."""
        return [
            item.id
            for item in self.thinking_items
            if item.type == ThinkingType.REASONING
        ]

    @rx.var
    def get_unique_tool_calls(self) -> list[str]:
        """Get unique tool call IDs."""
        return [
            item.id
            for item in self.thinking_items
            if item.type == ThinkingType.TOOL_CALL
        ]

    @rx.var
    def get_last_assistant_message_text(self) -> str:
        """Get the text of the last assistant message in the conversation."""
        for message in reversed(self.messages):
            if message.type == MessageType.ASSISTANT:
                return message.text
        return ""

    # -------------------------------------------------------------------------
    # Initialization and thread management
    # -------------------------------------------------------------------------

    @rx.event
    async def initialize(self) -> None:
        """Initialize the state with models and a new empty thread.

        Only initializes once per user session. Resets when user changes.
        """
        user_session: UserSession = await self.get_state(UserSession)
        user = await user_session.authenticated_user
        current_user_id = str(user.user_id) if user else ""

        # If already initialized and user hasn't changed, skip
        if self._initialized and self._current_user_id == current_user_id:
            logger.debug(
                "Thread state already initialized for user %s", current_user_id
            )
            return

        model_manager = ModelManager()
        all_models = model_manager.get_all_models()
        self.selected_model = model_manager.get_default_model()

        # Filter models based on user roles
        user_roles = user.roles if user else []

        self.ai_models = [
            m
            for m in all_models
            if not m.requires_role or m.requires_role in user_roles
        ]

        # If selected model is not in available models, pick the first one
        available_model_ids = [m.id for m in self.ai_models]
        if self.selected_model not in available_model_ids:
            if available_model_ids:
                self.selected_model = available_model_ids[0]
            else:
                logger.warning("No models available for user")
                self.selected_model = ""

        self._thread = ThreadModel(
            thread_id=str(uuid.uuid4()),
            title="Neuer Chat",
            prompt="",
            messages=[],
            state=ThreadStatus.NEW,
            ai_model=self.selected_model,
            active=True,
        )
        self.messages = []
        self.thinking_items = []
        self.image_chunks = []
        self.prompt = ""
        self.show_thinking = False
        self._current_user_id = current_user_id
        self._initialized = True
        logger.debug("Initialized thread state: %s", self._thread.thread_id)

    @rx.event
    async def new_thread(self) -> None:
        """Create a new empty thread (not persisted, not in list yet).

        Called when user clicks "New Chat" or when active thread is deleted.
        If current thread is already empty/new with no messages, does nothing.
        """
        # Ensure state is initialized first
        if not self._initialized:
            await self.initialize()

        # Don't create new if current thread is already empty
        if self._thread.state == ThreadStatus.NEW and not self.messages:
            logger.debug("Thread already empty, skipping new_thread")
            return

        self._thread = ThreadModel(
            thread_id=str(uuid.uuid4()),
            title="Neuer Chat",
            prompt="",
            messages=[],
            state=ThreadStatus.NEW,
            ai_model=self.selected_model or ModelManager().get_default_model(),
            active=True,
        )
        self.messages = []
        self.thinking_items = []
        self.image_chunks = []
        self.prompt = ""
        self.show_thinking = False
        logger.debug("Created new empty thread: %s", self._thread.thread_id)

    @rx.event
    def set_thread(self, thread: ThreadModel) -> None:
        """Set the current thread model (internal use)."""
        self._thread = thread
        self.messages = thread.messages
        self.selected_model = thread.ai_model
        self.thinking_items = []
        self.prompt = ""
        logger.debug("Set current thread: %s", thread.thread_id)

    @rx.event(background=True)
    async def load_thread(self, thread_id: str) -> AsyncGenerator[Any, Any]:
        """Load and select a thread by ID from database.

        Called when user clicks on a thread in the sidebar.
        Loads full thread data and updates both ThreadState and ThreadListState.

        Args:
            thread_id: The ID of the thread to load.
        """
        async with self:
            user_session: UserSession = await self.get_state(UserSession)
            is_authenticated = await user_session.is_authenticated
            user_id = user_session.user.user_id if user_session.user else None

            # Set loading state in ThreadListState
            threadlist_state: ThreadListState = await self.get_state(ThreadListState)
            threadlist_state.loading_thread_id = thread_id
        yield

        if not is_authenticated or not user_id:
            async with self:
                threadlist_state: ThreadListState = await self.get_state(
                    ThreadListState
                )
                threadlist_state.loading_thread_id = ""
            return

        try:
            async with get_asyncdb_session() as session:
                thread_entity = await thread_repo.find_by_thread_id_and_user(
                    session, thread_id, user_id
                )

                if not thread_entity:
                    logger.warning("Thread %s not found in database", thread_id)

                # Convert to ThreadModel if found
                full_thread = None
                if thread_entity:
                    full_thread = ThreadModel(
                        thread_id=thread_entity.thread_id,
                        title=thread_entity.title,
                        state=ThreadStatus(thread_entity.state),
                        ai_model=thread_entity.ai_model,
                        active=thread_entity.active,
                        messages=[Message(**m) for m in thread_entity.messages],
                    )

            if not full_thread and not thread_entity:  # it was not found
                async with self:
                    threadlist_state: ThreadListState = await self.get_state(
                        ThreadListState
                    )
                    threadlist_state.loading_thread_id = ""
                return

            # Mark all messages as done (loaded from DB)
            if full_thread:
                for msg in full_thread.messages:
                    msg.done = True

            async with self:
                # Update self with loaded thread
                self._thread = full_thread
                self.messages = full_thread.messages
                self.selected_model = full_thread.ai_model
                self.thinking_items = []
                self.prompt = ""

                # Update active state in ThreadListState
                threadlist_state: ThreadListState = await self.get_state(
                    ThreadListState
                )
                threadlist_state.threads = [
                    ThreadModel(
                        **{**t.model_dump(), "active": t.thread_id == thread_id}
                    )
                    for t in threadlist_state.threads
                ]
                threadlist_state.active_thread_id = thread_id
                threadlist_state.loading_thread_id = ""

                logger.debug("Loaded thread: %s", thread_id)

        except Exception as e:
            logger.error("Error loading thread %s: %s", thread_id, e)
            async with self:
                threadlist_state: ThreadListState = await self.get_state(
                    ThreadListState
                )
                threadlist_state.loading_thread_id = ""

    # -------------------------------------------------------------------------
    # Prompt and model management
    # -------------------------------------------------------------------------

    @rx.event
    def set_prompt(self, prompt: str) -> None:
        """Set the current prompt."""
        self.prompt = prompt

    @rx.event
    def set_suggestions(self, suggestions: list[Suggestion] | list[dict]) -> None:
        """Set custom suggestions for the thread.

        Accepts either Suggestion objects or dicts (for Reflex serialization).
        """
        if suggestions and isinstance(suggestions[0], dict):
            self.suggestions = [Suggestion(**s) for s in suggestions]
        else:
            self.suggestions = suggestions  # type: ignore[assignment]

    @rx.event
    def set_selected_model(self, model_id: str) -> None:
        """Set the selected model."""
        self.selected_model = model_id
        self._thread.ai_model = model_id

    @rx.event
    def set_with_thread_list(self, with_thread_list: bool) -> None:
        """Set whether thread list integration is enabled."""
        self.with_thread_list = with_thread_list

    # -------------------------------------------------------------------------
    # UI state management
    # -------------------------------------------------------------------------

    @rx.event
    def toggle_thinking_expanded(self) -> None:
        """Toggle the expanded state of the thinking section."""
        self.thinking_expanded = not self.thinking_expanded

    # -------------------------------------------------------------------------
    # MCP Server tool support
    # -------------------------------------------------------------------------

    @rx.event
    async def load_mcp_servers(self) -> None:
        """Load available MCP servers from the database."""
        async with get_asyncdb_session() as session:
            servers = await mcp_server_repo.find_all_ordered_by_name(session)
            # Create detached copies
            self.available_mcp_servers = [MCPServer(**s.model_dump()) for s in servers]

    @rx.event
    def toogle_tools_modal(self, show: bool) -> None:
        """Set the visibility of the tools modal."""
        self.show_tools_modal = show

    @rx.event
    def toggle_mcp_server_selection(self, server_id: int, selected: bool) -> None:
        """Toggle MCP server selection in the modal."""
        self.server_selection_state[server_id] = selected
        if selected and server_id not in self.temp_selected_mcp_servers:
            self.temp_selected_mcp_servers.append(server_id)
        elif not selected and server_id in self.temp_selected_mcp_servers:
            self.temp_selected_mcp_servers.remove(server_id)

    @rx.event
    def apply_mcp_server_selection(self) -> None:
        """Apply the temporary MCP server selection."""
        self.selected_mcp_servers = [
            server
            for server in self.available_mcp_servers
            if server.id in self.temp_selected_mcp_servers
        ]
        self.show_tools_modal = False

    @rx.event
    def is_mcp_server_selected(self, server_id: int) -> bool:
        """Check if an MCP server is selected."""
        return server_id in self.temp_selected_mcp_servers

    # -------------------------------------------------------------------------
    # Clear/reset
    # -------------------------------------------------------------------------

    @rx.event
    def clear(self) -> None:
        """Clear the current thread messages (keeps thread ID)."""
        self._thread.messages = []
        self._thread.state = ThreadStatus.NEW
        self._thread.ai_model = ModelManager().get_default_model()
        self._thread.active = True
        self._thread.prompt = ""
        self.prompt = ""
        self.messages = []
        self.selected_mcp_servers = []
        self.thinking_items = []
        self.image_chunks = []
        self.show_thinking = False

    # -------------------------------------------------------------------------
    # Message processing
    # -------------------------------------------------------------------------

    @rx.event(background=True)
    async def submit_message(self) -> AsyncGenerator[Any, Any]:
        """Submit a message and process the response."""
        await self._process_message()

        yield rx.call_script("""
            const textarea = document.getElementById('composer-area');
            if (textarea) {
                textarea.value = '';
                textarea.style.height = 'auto';
                textarea.style.height = textarea.scrollHeight + 'px';
            }
        """)

    async def _process_message(self) -> None:
        """Process the current message and stream the response."""
        logger.debug("Processing message: %s", self.prompt)

        start = await self._begin_message_processing()
        if not start:
            return
        current_prompt, selected_model, mcp_servers, is_new_thread = start

        processor = ModelManager().get_processor_for_model(selected_model)
        if not processor:
            await self._stop_processing_with_error(
                f"Keinen Adapter für das Modell gefunden: {selected_model}"
            )
            return

        async with self:
            user_session: UserSession = await self.get_state(UserSession)
            user_id = user_session.user.user_id if user_session.user else None

        first_response_received = False
        try:
            async for chunk in processor.process(
                self.messages,
                selected_model,
                mcp_servers=mcp_servers,
                user_id=user_id,
            ):
                first_response_received = await self._handle_stream_chunk(
                    chunk=chunk,
                    current_prompt=current_prompt,
                    is_new_thread=is_new_thread,
                    first_response_received=first_response_received,
                )

            await self._finalize_successful_response()

        except Exception as ex:
            await self._handle_process_error(
                ex=ex,
                current_prompt=current_prompt,
                is_new_thread=is_new_thread,
                first_response_received=first_response_received,
            )

        finally:
            await self._finalize_processing()

    async def _begin_message_processing(
        self,
    ) -> tuple[str, str, list[MCPServer], bool] | None:
        """Prepare state for sending a message. Returns None if no-op."""
        async with self:
            current_prompt = self.prompt.strip()
            if self.processing or not current_prompt:
                return None

            self.processing = True
            self._clear_chunks()
            self.thinking_items = []

            self.prompt = ""

            is_new_thread = self._thread.state == ThreadStatus.NEW

            # Add user message unless skipped (e.g., OAuth resend)
            if self._skip_user_message:
                self._skip_user_message = False
            else:
                self.messages.append(
                    Message(text=current_prompt, type=MessageType.HUMAN)
                )
            # Always add assistant placeholder
            self.messages.append(Message(text="", type=MessageType.ASSISTANT))

            selected_model = self.get_selected_model
            if not selected_model:
                self._add_error_message("Kein Chat-Modell ausgewählt")
                self.processing = False
                return None

            mcp_servers = self.selected_mcp_servers
            return current_prompt, selected_model, mcp_servers, is_new_thread

    async def _stop_processing_with_error(self, error_msg: str) -> None:
        """Stop processing and show an error message."""
        async with self:
            self._add_error_message(error_msg)
            self.processing = False

    async def _handle_stream_chunk(
        self,
        *,
        chunk: Chunk,
        current_prompt: str,
        is_new_thread: bool,
        first_response_received: bool,
    ) -> bool:
        """Handle one streamed chunk. Returns updated first_response_received."""
        async with self:
            self._handle_chunk(chunk)

            should_create_thread = (
                not first_response_received
                and chunk.type == ChunkType.TEXT
                and is_new_thread
                and self.with_thread_list
            )
            if not should_create_thread:
                return first_response_received

            self._thread.state = ThreadStatus.ACTIVE
            if self._thread.title in {"", "Neuer Chat"}:
                self._thread.title = current_prompt[:100]
            await self._notify_thread_created()
            return True

    async def _finalize_successful_response(self) -> None:
        """Finalize state after a successful full response."""
        async with self:
            self.show_thinking = False
            # Convert Reflex proxy list to standard list to avoid Pydantic
            # serializer warnings
            self._thread.messages = list(self.messages)  # noqa: E501
            self._thread.ai_model = self.selected_model

            if self.with_thread_list:
                await self._save_thread_to_db()

    async def _handle_process_error(
        self,
        *,
        ex: Exception,
        current_prompt: str,
        is_new_thread: bool,
        first_response_received: bool,
    ) -> None:
        """Handle failures during streaming and persist error state."""
        async with self:
            self._thread.state = ThreadStatus.ERROR

            if self.messages and self.messages[-1].type == MessageType.ASSISTANT:
                self.messages.pop()
            self.messages.append(Message(text=str(ex), type=MessageType.ERROR))

            if is_new_thread and self.with_thread_list and not first_response_received:
                if self._thread.title in {"", "Neuer Chat"}:
                    self._thread.title = current_prompt[:100]
                await self._notify_thread_created()

            # Convert Reflex proxy list to standard list to avoid Pydantic serializer
            # warnings
            self._thread.messages = list(self.messages)  # noqa: E501
            if self.with_thread_list:
                await self._save_thread_to_db()

    async def _finalize_processing(self) -> None:
        """Mark processing done and close out the last message."""
        async with self:
            if self.messages:
                self.messages[-1].done = True
            self.processing = False

    # -------------------------------------------------------------------------
    # Thread persistence (internal)
    # -------------------------------------------------------------------------

    async def _notify_thread_created(self) -> None:
        """Notify ThreadListState that a new thread was created.

        Called after the first successful response chunk.
        Adds the thread to ThreadListState without a full reload.

        Note: Called from within an async with self block, so don't create a new one.
        """
        threadlist_state: ThreadListState = await self.get_state(ThreadListState)
        await threadlist_state.add_thread(self._thread)

    async def _save_thread_to_db(self) -> None:
        """Persist current thread to database.

        Called incrementally after each successful response.
        """
        user_session: UserSession = await self.get_state(UserSession)
        user_id = user_session.user.user_id if user_session.user else None

        if user_id:
            try:
                # Prepare entity data
                messages_dict = [m.dict() for m in self._thread.messages]

                async with get_asyncdb_session() as session:
                    # Check if exists
                    existing = await thread_repo.find_by_thread_id_and_user(
                        session, self._thread.thread_id, user_id
                    )

                    if existing:
                        existing.title = self._thread.title
                        existing.state = (
                            self._thread.state.value
                            if hasattr(self._thread.state, "value")
                            else self._thread.state
                        )
                        existing.ai_model = self._thread.ai_model
                        existing.active = self._thread.active
                        existing.messages = messages_dict
                        await thread_repo.save(session, existing)
                    else:
                        new_thread = AssistantThread(
                            thread_id=self._thread.thread_id,
                            user_id=user_id,
                            title=self._thread.title,
                            state=self._thread.state.value
                            if hasattr(self._thread.state, "value")
                            else self._thread.state,
                            ai_model=self._thread.ai_model,
                            active=self._thread.active,
                            messages=messages_dict,
                        )
                        await thread_repo.save(session, new_thread)

                logger.debug("Saved thread to DB: %s", self._thread.thread_id)
            except Exception as e:
                logger.error("Error saving thread %s: %s", self._thread.thread_id, e)

    # -------------------------------------------------------------------------
    # Chunk handling (internal)
    # -------------------------------------------------------------------------

    def _clear_chunks(self) -> None:
        """Clear all chunk categorization lists except thinking_items for display."""
        self.image_chunks = []
        self.current_reasoning_session = ""  # Reset reasoning session for new message
        self.current_tool_session = ""  # Reset tool session for new message

    def _get_or_create_tool_session(self, chunk: Chunk) -> str:
        """Get tool session ID from metadata or derive one.

        If the model doesn't include tool_id in chunk metadata, we track the latest
        tool session so TOOL_RESULT can be associated with the preceding TOOL_CALL.
        """
        tool_id = chunk.chunk_metadata.get("tool_id")
        if tool_id:
            self.current_tool_session = tool_id
            return tool_id

        if chunk.type == ChunkType.TOOL_CALL:
            tool_count = sum(
                1 for i in self.thinking_items if i.type == ThinkingType.TOOL_CALL
            )
            self.current_tool_session = f"tool_{tool_count}"
            return self.current_tool_session

        if self.current_tool_session:
            return self.current_tool_session

        tool_count = sum(
            1 for i in self.thinking_items if i.type == ThinkingType.TOOL_CALL
        )
        self.current_tool_session = f"tool_{tool_count}"
        return self.current_tool_session

    def _handle_chunk(self, chunk: Chunk) -> None:
        """Handle incoming chunk based on its type."""
        if chunk.type == ChunkType.TEXT:
            self.messages[-1].text += chunk.text
        elif chunk.type in (ChunkType.THINKING, ChunkType.THINKING_RESULT):
            self._handle_reasoning_chunk(chunk)
        elif chunk.type in (
            ChunkType.TOOL_CALL,
            ChunkType.TOOL_RESULT,
            ChunkType.ACTION,
        ):
            self._handle_tool_chunk(chunk)
        elif chunk.type in (ChunkType.IMAGE, ChunkType.IMAGE_PARTIAL):
            self.image_chunks.append(chunk)
        elif chunk.type == ChunkType.COMPLETION:
            self.show_thinking = False
            logger.debug("Response generation completed")
        elif chunk.type == ChunkType.AUTH_REQUIRED:
            self._handle_auth_required_chunk(chunk)
        elif chunk.type == ChunkType.ERROR:
            self.messages.append(Message(text=chunk.text, type=MessageType.ERROR))
            logger.error("Chunk error: %s", chunk.text)
        else:
            logger.warning("Unhandled chunk type: %s - %s", chunk.type, chunk.text)

    def _get_or_create_thinking_item(
        self, item_id: str, thinking_type: ThinkingType, **kwargs
    ) -> Thinking:
        """Get existing thinking item or create new one."""
        for item in self.thinking_items:
            if item.type == thinking_type and item.id == item_id:
                return item

        new_item = Thinking(type=thinking_type, id=item_id, **kwargs)
        self.thinking_items = [*self.thinking_items, new_item]
        return new_item

    def _handle_reasoning_chunk(self, chunk: Chunk) -> None:
        """Handle reasoning chunks by consolidating them into thinking items."""
        if chunk.type == ChunkType.THINKING:
            self.show_thinking = True

        reasoning_session = self._get_or_create_reasoning_session(chunk)

        # Determine status and text
        status = ThinkingStatus.IN_PROGRESS
        text = ""
        if chunk.type == ChunkType.THINKING:
            text = chunk.text
        elif chunk.type == ChunkType.THINKING_RESULT:
            status = ThinkingStatus.COMPLETED

        item = self._get_or_create_thinking_item(
            reasoning_session, ThinkingType.REASONING, text=text, status=status
        )

        # Update existing item
        if chunk.type == ChunkType.THINKING:
            if item.text and item.text != text:  # Append if not new
                item.text += f"\n{chunk.text}"
        elif chunk.type == ChunkType.THINKING_RESULT:
            item.status = ThinkingStatus.COMPLETED
            if chunk.text:
                item.text += f" {chunk.text}"

        self.thinking_items = self.thinking_items.copy()

    def _get_or_create_reasoning_session(self, chunk: Chunk) -> str:
        """Get reasoning session ID from metadata or create new one."""
        reasoning_session = chunk.chunk_metadata.get("reasoning_session")
        if reasoning_session:
            return reasoning_session

        # If no session ID in metadata, create separate sessions based on context
        last_item = self.thinking_items[-1] if self.thinking_items else None

        # Create new session if needed
        should_create_new_session = (
            not self.current_reasoning_session
            or (last_item and last_item.type == ThinkingType.TOOL_CALL)
            or (
                last_item
                and last_item.type == ThinkingType.REASONING
                and last_item.status == ThinkingStatus.COMPLETED
            )
        )

        if should_create_new_session:
            self.current_reasoning_session = f"reasoning_{uuid.uuid4().hex[:8]}"

        return self.current_reasoning_session

    def _handle_tool_chunk(self, chunk: Chunk) -> None:
        """Handle tool chunks by consolidating them into thinking items."""
        tool_id = self._get_or_create_tool_session(chunk)

        # Determine initial properties
        tool_name = chunk.chunk_metadata.get("tool_name", "Unknown")
        status = ThinkingStatus.IN_PROGRESS
        text = ""
        parameters = None
        result = None
        error = None

        if chunk.type == ChunkType.TOOL_CALL:
            parameters = chunk.chunk_metadata.get("parameters", chunk.text)
            text = chunk.chunk_metadata.get("description", "")
        elif chunk.type == ChunkType.TOOL_RESULT:
            is_error = (
                "error" in chunk.text.lower()
                or "failed" in chunk.text.lower()
                or chunk.chunk_metadata.get("error")
            )
            status = ThinkingStatus.ERROR if is_error else ThinkingStatus.COMPLETED
            result = chunk.text
            if is_error:
                error = chunk.text
        else:
            text = chunk.text

        item = self._get_or_create_thinking_item(
            tool_id,
            ThinkingType.TOOL_CALL,
            text=text,
            status=status,
            tool_name=tool_name,
            parameters=parameters,
            result=result,
            error=error,
        )

        # Update existing item
        if chunk.type == ChunkType.TOOL_CALL:
            item.parameters = parameters
            item.text = text
            if not item.tool_name or item.tool_name == "Unknown":
                item.tool_name = tool_name
            item.status = ThinkingStatus.IN_PROGRESS
        elif chunk.type == ChunkType.TOOL_RESULT:
            item.status = status
            item.result = result
            item.error = error
        elif chunk.type == ChunkType.ACTION:
            item.text += f"\n---\nAktion: {chunk.text}"

        self.thinking_items = self.thinking_items.copy()

    def _handle_auth_required_chunk(self, chunk: Chunk) -> None:
        """Handle AUTH_REQUIRED chunks by showing the auth card."""
        self.pending_auth_server_id = chunk.chunk_metadata.get("server_id", "")
        self.pending_auth_server_name = chunk.chunk_metadata.get("server_name", "")
        self.pending_auth_url = chunk.chunk_metadata.get("auth_url", "")
        self.show_auth_card = True
        # Store the last user message to resend after successful OAuth
        for msg in reversed(self.messages):
            if msg.type == MessageType.HUMAN:
                self.pending_oauth_message = msg.text
                break
        logger.debug(
            "Auth required for server %s, showing auth card, pending message: %s",
            self.pending_auth_server_name,
            self.pending_oauth_message[:50] if self.pending_oauth_message else "None",
        )

    @rx.event
    def start_mcp_oauth(self) -> rx.event.EventSpec:
        """Start the OAuth flow by opening the auth URL in a popup window."""
        if not self.pending_auth_url:
            return rx.toast.error("Keine Authentifizierungs-URL verfügbar")

        # NOTE: We do not append server_id here anymore to avoid errors with strict
        # OAuth providers. server_id must be recovered from the state parameter in the
        # callback.
        auth_url = self.pending_auth_url

        return rx.call_script(
            f"window.open('{auth_url}', 'mcp_oauth', 'width=600,height=700')"
        )

    @rx.event
    async def handle_mcp_oauth_success(
        self, server_id: str, server_name: str
    ) -> AsyncGenerator[Any, Any]:
        """Handle successful OAuth completion from popup window."""
        logger.debug("OAuth success for server %s (%s)", server_name, server_id)
        self.show_auth_card = False
        self.pending_auth_server_id = ""
        self.pending_auth_server_name = ""
        self.pending_auth_url = ""

        # Check if we have a pending message to resend
        pending_message = self.pending_oauth_message
        self.pending_oauth_message = ""

        if pending_message:
            # Remove the incomplete assistant message from the failed attempt
            if self.messages and self.messages[-1].type == MessageType.ASSISTANT:
                self.messages = self.messages[:-1]
            # Show success toast instead of adding to messages
            yield rx.toast.success(
                f"Erfolgreich mit {server_name} verbunden. "
                "Anfrage wird erneut gesendet...",
                position="top-right",
            )
            # Resend the original message by setting prompt and yielding the event
            self.prompt = pending_message
            self._skip_user_message = True  # User message already in list
            yield ThreadState.submit_message
        else:
            # No pending message - just show success toast
            yield rx.toast.success(
                f"Erfolgreich mit {server_name} verbunden.",
                position="top-right",
            )

    @rx.event
    def handle_mcp_oauth_success_from_js(self) -> rx.event.EventSpec:
        """Handle OAuth success triggered from JS - retrieves data from window."""
        return rx.call_script(
            "window._mcpOAuthData ? JSON.stringify(window._mcpOAuthData) : '{}'",
            callback=ThreadState.process_oauth_success_data,
        )

    @rx.event
    async def process_oauth_success_data(
        self, data_str: str
    ) -> AsyncGenerator[Any, Any]:
        """Process OAuth success data retrieved from window."""
        try:
            data = json.loads(data_str) if data_str else {}
            server_id = data.get("serverId", "")
            server_name = data.get("serverName", "Unknown")
            logger.info(
                "Processing OAuth success from JS: server_id=%s, server_name=%s",
                server_id,
                server_name,
            )
            # Yield events from handle_mcp_oauth_success
            async for event in self.handle_mcp_oauth_success(server_id, server_name):
                yield event
        except json.JSONDecodeError:
            logger.warning("Failed to parse OAuth data from JS: %s", data_str)

    @rx.event
    def dismiss_auth_card(self) -> None:
        """Dismiss the auth card without authenticating."""
        self.show_auth_card = False

    def _add_error_message(self, error_msg: str) -> None:
        """Add an error message to the conversation."""
        logger.error(error_msg)
        self.messages.append(Message(text=error_msg, type=MessageType.ERROR))
