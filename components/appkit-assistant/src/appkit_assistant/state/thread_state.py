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
    Chunk,
    ChunkType,
    MCPServer,
    Message,
    MessageType,
    Suggestion,
    ThreadModel,
    ThreadStatus,
)
from appkit_assistant.backend.repositories import MCPServerRepository, ThreadRepository
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
    _thread: ThreadModel = ThreadModel(thread_id=str(uuid.uuid4()), prompt="")
    ai_models: list[AIModel] = []
    selected_model: str = ""
    processing: bool = False
    messages: list[Message] = []
    prompt: str = ""
    suggestions: list[Suggestion] = [Suggestion(prompt="Wie kann ich dir helfen?")]

    # Chunk processing state
    thinking_items: list[Thinking] = []  # Consolidated reasoning and tool calls
    image_chunks: list[Chunk] = []
    show_thinking: bool = False
    thinking_expanded: bool = False
    current_activity: str = ""
    current_reasoning_session: str = ""  # Track current reasoning session

    # MCP Server tool support state
    selected_mcp_servers: list[MCPServer] = []
    show_tools_modal: bool = False
    available_mcp_servers: list[MCPServer] = []
    temp_selected_mcp_servers: list[int] = []
    server_selection_state: dict[int, bool] = {}

    # Thread list integration
    with_thread_list: bool = False

    def initialize(self) -> None:
        """Initialize the state."""
        model_manager = ModelManager()
        self.ai_models = model_manager.get_all_models()
        self.selected_model = model_manager.get_default_model()

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
        logger.debug("Initialized thread state: %s", self._thread)

    def set_thread(self, thread: ThreadModel) -> None:
        """Set the current thread model."""
        self._thread = thread
        self.messages = thread.messages
        self.selected_model = thread.ai_model
        logger.debug("Set current thread: %s", thread.thread_id)

    def set_prompt(self, prompt: str) -> None:
        """Set the current prompt."""
        self.prompt = prompt

    @rx.var
    def has_ai_models(self) -> bool:
        """Check if there are any chat models."""
        return len(self.ai_models) > 0

    @rx.var
    def has_suggestions(self) -> bool:
        """Check if there are any suggestions."""
        return self.suggestions is not None and len(self.suggestions) > 0

    @rx.var
    def get_ai_model(self) -> str | None:
        """Get the selected chat model."""
        return self.selected_model

    @rx.var
    def current_model_supports_tools(self) -> bool:
        """Check if the currently selected model supports tools."""
        if not self.selected_model:
            return False
        model = ModelManager().get_model(self.selected_model)
        return model.supports_tools if model else False

    @rx.var
    def unique_reasoning_sessions(self) -> list[str]:
        """Get unique reasoning session IDs."""
        return [
            item.id
            for item in self.thinking_items
            if item.type == ThinkingType.REASONING
        ]

    @rx.var
    def unique_tool_calls(self) -> list[str]:
        """Get unique tool call IDs."""
        return [
            item.id
            for item in self.thinking_items
            if item.type == ThinkingType.TOOL_CALL
        ]

    @rx.var
    def last_assistant_message_text(self) -> str:
        """Get the text of the last assistant message in the conversation."""
        for message in reversed(self.messages):
            if message.type == MessageType.ASSISTANT:
                return message.text
        return ""

    @rx.var
    def has_thinking_content(self) -> bool:
        """Check if there are any thinking items to display."""
        return len(self.thinking_items) > 0

    @rx.event
    def update_prompt(self, value: str) -> None:
        self.prompt = value

    @rx.event
    def set_suggestions(self, suggestions: list[Suggestion]) -> None:
        """Set custom suggestions for the thread."""
        self.suggestions = suggestions

    @rx.event
    def set_initial_suggestions(self, suggestions: list[dict | Suggestion]) -> None:
        """Set initial suggestions during page load.

        Can be called via on_load callback to initialize suggestions
        from the assistant page or other sources.

        Args:
            suggestions: List of suggestions (dict or Suggestion objects) to display.
        """
        # Convert dicts to Suggestion objects
        # (Reflex serializes Pydantic models to dicts during event invocation)
        converted = []
        for item in suggestions:
            if isinstance(item, dict):
                converted.append(Suggestion(**item))
            elif isinstance(item, Suggestion):
                converted.append(item)
            else:
                log = logging.getLogger(__name__)
                log.warning("Unknown suggestion type: %s", type(item))
        self.suggestions = converted

    @rx.event
    def clear(self) -> None:
        self._thread.messages = []
        self._thread.state = ThreadStatus.NEW
        self._thread.ai_model = ModelManager().get_default_model()
        self._thread.active = True
        self._thread.prompt = ""
        self.prompt = ""
        self.messages = []
        self.selected_mcp_servers = []
        self.thinking_items = []  # Clear thinking items only on explicit clear
        self.image_chunks = []
        self.show_thinking = False

    @rx.event(background=True)
    async def process_message(self) -> None:
        logger.debug("Sending message: %s", self.prompt)

        async with self:
            if self.processing or not self.prompt.strip():
                return

            self.processing = True
            self._clear_chunks()
            self.thinking_items = []

            current_prompt = self.prompt.strip()
            self.prompt = ""

            # Add user message and empty assistant message
            self.messages.extend(
                [
                    Message(text=current_prompt, type=MessageType.HUMAN),
                    Message(text="", type=MessageType.ASSISTANT),
                ]
            )

            if not self.get_ai_model:
                self._add_error_message("Kein Chat-Modell ausgewählt")
                self.processing = False
                return

        # Get processor outside context to avoid blocking
        processor = ModelManager().get_processor_for_model(self.get_ai_model)
        if not processor:
            async with self:
                self._add_error_message(
                    f"Keinen Adapter für das Modell gefunden: {self.get_ai_model}"
                )
                self.processing = False
            return

        try:
            # Process chunks
            async for chunk in processor.process(
                self.messages,
                self.get_ai_model,
                mcp_servers=self.selected_mcp_servers,
            ):
                async with self:
                    self._handle_chunk(chunk)

            async with self:
                self.show_thinking = False

                # Update thread if using thread list
                if self.with_thread_list:
                    await self._update_thread_list()

        except Exception as ex:
            async with self:
                if self.messages and self.messages[-1].type == MessageType.ASSISTANT:
                    self.messages.pop()  # Remove empty assistant message
                self.messages.append(Message(text=str(ex), type=MessageType.ERROR))
        finally:
            async with self:
                if self.messages:
                    self.messages[-1].done = True
                self.processing = False

    @rx.event
    async def persist_current_thread(self, prompt: str = "") -> None:
        """Persist the current temporary thread to the thread list.

        Converts the temporary ThreadState._thread to a persistent entry in
        ThreadListState so it appears in the thread list. This is called
        when the user first submits a message.

        Args:
            prompt: The user's message prompt (used for thread title).

        Idempotent: calling multiple times won't create duplicates if the
        thread is already in the list.
        """
        # Get ThreadListState to add the thread
        threadlist_state: ThreadListState = await self.get_state(ThreadListState)

        # Check if thread already exists in list (idempotency check)
        existing_thread = await threadlist_state.get_thread(self._thread.thread_id)
        if not existing_thread:
            # Only add to list if not already present
            # Update thread title based on first message if title is still default
            if self._thread.title in {"", "Neuer Chat"}:
                self._thread.title = prompt.strip() if prompt.strip() else "Neuer Chat"

            # Add current thread to thread list (create new list for reactivity)
            self._thread.active = True
            threadlist_state.threads = [self._thread, *threadlist_state.threads]

            # Set as active thread in list
            threadlist_state.active_thread_id = self._thread.thread_id
            logger.debug("Added thread to list: %s", self._thread.thread_id)
        else:
            # Thread exists - update existing (create new list for reactivity)
            threadlist_state.threads = [
                self._thread if t.thread_id == self._thread.thread_id else t
                for t in threadlist_state.threads
            ]
            logger.debug("Updated existing thread in list: %s", self._thread.thread_id)

        # Always save to database if autosave is enabled
        # (thread content may have changed)
        if threadlist_state.autosave:
            await threadlist_state.save_thread(self._thread)

        logger.debug("Persisted thread: %s", self._thread.thread_id)

    @rx.event
    async def submit_message(self) -> AsyncGenerator[Any, Any]:
        """Submit a message and reset the textarea."""
        # Persist the current thread before processing the message
        # Pass the prompt so we can use it as the thread title
        await self.persist_current_thread(prompt=self.prompt)
        yield ThreadState.process_message

        yield rx.call_script("""
            const textarea = document.getElementById('composer-area');
            if (textarea) {
                textarea.value = '';
                textarea.style.height = 'auto';
                textarea.style.height = textarea.scrollHeight + 'px';
            }
        """)

    def _clear_chunks(self) -> None:
        """Clear all chunk categorization lists except thinking_items for display."""
        self.image_chunks = []
        self.current_reasoning_session = ""  # Reset reasoning session for new message

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
        elif chunk.type == ChunkType.ERROR:
            self.messages.append(Message(text=chunk.text, type=MessageType.ERROR))
            logger.error("Chunk error: %s", chunk.text)
        else:
            logger.warning("Unhandled chunk type: %s - %s", chunk.type, chunk.text)

    def _get_or_create_thinking_item(
        self, item_id: str, type: ThinkingType, **kwargs
    ) -> Thinking:
        """Get existing thinking item or create new one."""
        for item in self.thinking_items:
            if item.type == type and item.id == item_id:
                return item

        new_item = Thinking(type=type, id=item_id, **kwargs)
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
        tool_id = chunk.chunk_metadata.get("tool_id")
        if not tool_id:
            # Generate a tool ID if not provided
            # Use generator expression for memory efficiency
            tool_count = sum(
                1 for i in self.thinking_items if i.type == ThinkingType.TOOL_CALL
            )
            tool_id = f"tool_{tool_count}"

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

    def _add_error_message(self, error_msg: str) -> None:
        """Add an error message to the conversation."""
        logger.error(error_msg)
        self.messages.append(Message(text=error_msg, type=MessageType.ERROR))

    async def _update_thread_list(self) -> None:
        """Update the thread list with current messages."""
        threadlist_state: ThreadListState = await self.get_state(ThreadListState)
        if self._thread.title in {"", "Neuer Chat"}:
            self._thread.title = (
                self.messages[0].text if self.messages else "Neuer Chat"
            )

        self._thread.messages = self.messages
        self._thread.ai_model = self.selected_model
        await threadlist_state.update_thread(self._thread)

    def toggle_thinking_expanded(self) -> None:
        """Toggle the expanded state of the thinking section."""
        self.thinking_expanded = not self.thinking_expanded

    # MCP Server tool support event handlers
    @rx.event
    async def load_available_mcp_servers(self) -> None:
        """Load available MCP servers from the database."""
        self.available_mcp_servers = await MCPServerRepository.get_all()

    @rx.event
    def open_tools_modal(self) -> None:
        """Open the tools modal."""
        self.temp_selected_mcp_servers = [
            server.id for server in self.selected_mcp_servers if server.id
        ]
        self.server_selection_state = {
            server.id: server.id in self.temp_selected_mcp_servers
            for server in self.available_mcp_servers
            if server.id
        }
        self.show_tools_modal = True

    @rx.event
    def set_show_tools_modal(self, show: bool) -> None:
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

    def is_mcp_server_selected(self, server_id: int) -> bool:
        """Check if an MCP server is selected."""
        return server_id in self.temp_selected_mcp_servers

    def set_selected_model(self, model_id: str) -> None:
        """Set the selected model."""
        self.selected_model = model_id
        self._thread.ai_model = model_id


class ThreadListState(rx.State):
    """State for the thread list component."""

    threads: list[ThreadModel] = []
    active_thread_id: str = ""
    loading_thread_id: str = ""
    loading: bool = True
    autosave: bool = False
    _initialized: bool = False
    _current_user_id: str = ""

    @rx.var
    def has_threads(self) -> bool:
        """Check if there are any threads."""
        return len(self.threads) > 0

    async def initialize(self, autosave: bool = False) -> AsyncGenerator[Any, Any]:
        """Initialize the thread list state.

        Args:
            autosave: Enable auto-saving threads to database.

        Note: Does not activate any thread automatically. Threads are loaded
        in the background and user can start chatting immediately with the
        temporary thread from ThreadState.
        """
        if self._initialized:
            return

        self.autosave = autosave
        async for _ in self.load_threads():
            yield

        logger.debug(
            "Initialized thread list state with %d threads (autosave=%s)",
            len(self.threads),
            self.autosave,
        )

    async def load_threads(self) -> AsyncGenerator[Any, Any]:
        """Load threads from database."""
        user_session = await self.get_state(UserSession)

        # Check if user changed - if so, reset initialization
        current_user_id = user_session.user.user_id if user_session.user else ""
        if self._current_user_id != current_user_id:
            self._initialized = False
            self._current_user_id = current_user_id
            self.threads = []
            self.active_thread_id = ""

        if self._initialized:
            self.loading = False
            return

        self.loading = True
        yield

        if not await user_session.is_authenticated:
            self.threads = []
            self.loading = False
            return

        try:
            if user_session.user:
                self.threads = await ThreadRepository.get_summaries_by_user(
                    user_session.user.user_id
                )
                self._initialized = True
                logger.debug(
                    "Loaded %d threads without activating any", len(self.threads)
                )
        except Exception as e:
            logger.error("Error loading threads from database: %s", e)
            self.threads = []
            self.active_thread_id = ""

        self.loading = False

    async def save_thread(self, thread: ThreadModel) -> None:
        """Save a single thread to database."""
        user_session = await self.get_state(UserSession)
        if not await user_session.is_authenticated:
            logger.debug(
                "Skipping save - user not authenticated for thread %s", thread.thread_id
            )
            return

        try:
            if user_session.user:
                current_user_id = user_session.user.user_id
                logger.debug(
                    "Saving thread %s for user %s", thread.thread_id, current_user_id
                )

                # Check if thread is in current user's loaded threads
                thread_exists = any(
                    t.thread_id == thread.thread_id for t in self.threads
                )
                logger.debug(
                    "Thread %s exists in loaded threads: %s (total: %d)",
                    thread.thread_id,
                    thread_exists,
                    len(self.threads),
                )
                if not thread_exists:
                    logger.warning(
                        "Skipping save - thread %s not in loaded threads",
                        thread.thread_id,
                    )
                    return

                await ThreadRepository.save_thread(thread, current_user_id)
                logger.info(
                    "Successfully saved thread %s to database", thread.thread_id
                )
            else:
                logger.warning("No user in session, cannot save thread")
        except Exception as e:
            logger.error("Error saving thread %s: %s", thread.thread_id, e)

    async def save_threads(self) -> None:
        """Deprecated: Save all threads. Use save_thread instead."""
        logger.warning("save_threads called but is deprecated for DB storage")

    async def reset_thread_store(self) -> None:
        """Reset the thread store (clear list)."""
        self.threads = []
        self.active_thread_id = ""

    async def get_thread(self, thread_id: str) -> ThreadModel | None:
        """Get a thread by its ID."""
        for thread in self.threads:
            if thread.thread_id == thread_id:
                return thread
        return None

    async def create_thread(self) -> None:
        """Create a new thread."""
        new_thread = ThreadModel(
            thread_id=str(uuid.uuid4()),
            title="Neuer Chat",
            prompt="",
            messages=[],
            state=ThreadStatus.NEW,
            ai_model=ModelManager().get_default_model(),
            active=True,
        )
        self.threads.insert(0, new_thread)
        await self._select_thread_internal(new_thread.thread_id)

        # Save immediately to persist the new thread
        if self.autosave:
            await self.save_thread(new_thread)

        logger.debug("Created new thread: %s", new_thread)

    async def update_thread(self, thread: ThreadModel) -> None:
        """Update a thread."""
        existing_thread = await self.get_thread(thread.thread_id)
        if existing_thread:
            existing_thread.title = thread.title
            existing_thread.messages = thread.messages
            existing_thread.state = thread.state
            existing_thread.active = thread.active
            existing_thread.ai_model = thread.ai_model
            logger.debug(
                "Updated existing thread in list: %s (autosave=%s)",
                thread.thread_id,
                self.autosave,
            )
        else:
            logger.warning(
                "Thread %s not found in list during update", thread.thread_id
            )

        if self.autosave:
            logger.debug("Attempting to save thread: %s", thread.thread_id)
            await self.save_thread(thread)
        else:
            logger.debug("Autosave disabled, skipping save")
        logger.debug("Updated thread: %s", thread.thread_id)

    async def delete_thread(self, thread_id: str) -> AsyncGenerator[Any, Any]:
        """Delete a thread."""
        user_session = await self.get_state(UserSession)
        if not await user_session.is_authenticated:
            return

        thread = await self.get_thread(thread_id)
        if not thread:
            yield rx.toast.error(
                "Chat nicht gefunden.", position="top-right", close_button=True
            )
            logger.warning("Thread with ID %s not found.", thread_id)
            return

        was_active = thread_id == self.active_thread_id

        try:
            if user_session.user:
                await ThreadRepository.delete_thread(
                    thread_id, user_session.user.user_id
                )
                self.threads.remove(thread)

                yield rx.toast.info(
                    f"Chat '{thread.title}' erfolgreich gelöscht.",
                    position="top-right",
                    close_button=True,
                )

                if was_active:
                    thread_state: ThreadState = await self.get_state(ThreadState)
                    thread_state.initialize()
                    self.active_thread_id = ""

                    # If other threads remain, select the first one
                    if self.threads:
                        await self._select_thread_internal(self.threads[0].thread_id)

        except Exception as e:
            logger.error("Error deleting thread: %s", e)
            yield rx.toast.error("Fehler beim Löschen des Chats.")

    async def select_thread(self, thread_id: str) -> AsyncGenerator[Any, Any]:
        """Select a thread (Event Handler)."""
        self.loading_thread_id = thread_id
        yield
        await self._select_thread_internal(thread_id)
        self.loading_thread_id = ""

    async def _select_thread_internal(self, thread_id: str) -> None:
        """Internal logic to select a thread."""
        user_session = await self.get_state(UserSession)
        if not await user_session.is_authenticated:
            return

        # Find the thread in the list
        selected_thread = None
        for thread in self.threads:
            if thread.thread_id == thread_id:
                selected_thread = thread
                break

        if not selected_thread:
            return

        # Fetch full thread details from DB
        try:
            if user_session.user:
                full_thread = await ThreadRepository.get_thread_by_id(
                    thread_id, user_session.user.user_id
                )
                if full_thread:
                    # Ensure all messages are marked as done when loaded from DB
                    for msg in full_thread.messages:
                        msg.done = True

                    # Update list with full thread (create new list for reactivity)
                    self.threads = [
                        full_thread if t.thread_id == thread_id else t
                        for t in self.threads
                    ]
                    selected_thread = full_thread
        except Exception as e:
            logger.error("Error fetching full thread %s: %s", thread_id, e)

        # Update active status (create new list for reactivity)
        self.threads = [
            ThreadModel(**{**t.model_dump(), "active": t.thread_id == thread_id})
            for t in self.threads
        ]
        self.active_thread_id = thread_id

        if selected_thread:
            thread_state: ThreadState = await self.get_state(ThreadState)
            thread_state.set_thread(selected_thread)
            thread_state.messages = selected_thread.messages
            thread_state.selected_model = selected_thread.ai_model
            thread_state.with_thread_list = True
        self.active_thread_id = thread_id
        self.loading_thread_id = ""

        if selected_thread:
            thread_state: ThreadState = await self.get_state(ThreadState)
            thread_state.set_thread(selected_thread)
            thread_state.messages = selected_thread.messages
            thread_state.selected_model = selected_thread.ai_model
            thread_state.with_thread_list = True
