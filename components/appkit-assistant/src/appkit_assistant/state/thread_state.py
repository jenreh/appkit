import base64
import json
import logging
import re
import uuid
from collections.abc import AsyncGenerator
from enum import StrEnum
from re import Match
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
from appkit_assistant.backend.repositories import MCPServerRepository

logger = logging.getLogger(__name__)

MERMAID_BLOCK_PATTERN = re.compile(
    r"```mermaid\s*\r?\n(.*?)```", re.IGNORECASE | re.DOTALL
)
BRACKET_PAIRS: dict[str, str] = {
    "[": "]",
    "(": ")",
    "{": "}",
    "<": ">",
}


def _escape_mermaid_label_newlines(block: str) -> str:
    """Convert literal newlines inside node labels to escaped sequences.

    Ensures Mermaid labels that previously used ``\n`` survive JSON roundtrips
    where sequences were converted into raw newlines.
    """

    if "\n" not in block:
        return block

    result: list[str] = []
    stack: list[str] = []
    for char in block:
        if stack:
            if char == "\r":
                continue
            if char == "\n":
                result.append("\\n")
                continue
            if char == stack[-1]:
                stack.pop()
                result.append(char)
                continue
            if char in BRACKET_PAIRS:
                stack.append(BRACKET_PAIRS[char])
                result.append(char)
                continue
            result.append(char)
            continue

        if char in BRACKET_PAIRS:
            stack.append(BRACKET_PAIRS[char])
        result.append(char)

    return "".join(result)


def _rehydrate_mermaid_text(text: str) -> str:
    """Restore Mermaid code blocks by escaping label newlines when needed."""

    if "```mermaid" not in text.lower():
        return text

    def _replace(match: Match[str]) -> str:
        code_block = match.group(1)
        repaired = _escape_mermaid_label_newlines(code_block)
        return f"```mermaid\n{repaired}```"

    try:
        return MERMAID_BLOCK_PATTERN.sub(_replace, text)
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("Failed to rehydrate mermaid text: %s", exc)
        return text


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
    current_chunks: list[Chunk] = []
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
        self.current_chunks = []
        self.thinking_items = []  # Clear thinking items only on explicit clear
        self.image_chunks = []
        self.show_thinking = False

    @rx.event(background=True)
    async def process_message(self) -> None:
        logger.debug("Sending message: %s", self.prompt)

        async with self:
            # Check if already processing
            if self.processing:
                return

            self.processing = True
            self._clear_chunks()
            # Clear thinking items for new user question
            self.thinking_items = []

            current_prompt = self.prompt.strip()
            if not current_prompt:
                self.processing = False
                return

            self.prompt = ""

            # Add user message and empty assistant message
            self.messages.extend(
                [
                    Message(text=current_prompt, type=MessageType.HUMAN),
                    Message(text="", type=MessageType.ASSISTANT),
                ]
            )

            # Validate model and get processor
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
                self.messages.pop()  # Remove empty assistant message
                self.messages.append(Message(text=str(ex), type=MessageType.ERROR))
        finally:
            async with self:
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
        if existing_thread:
            logger.debug("Thread already persisted: %s", self._thread.thread_id)
            return

        # Update thread title based on first message if title is still default
        if self._thread.title in {"", "Neuer Chat"}:
            self._thread.title = prompt.strip() if prompt.strip() else "Neuer Chat"

        # Add current thread to thread list
        self._thread.active = True
        threadlist_state.threads.insert(0, self._thread)

        # Set as active thread in list
        threadlist_state.active_thread_id = self._thread.thread_id

        # Save to local storage if autosave is enabled
        if threadlist_state.autosave:
            await threadlist_state.save_threads()

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
        self.current_chunks = []
        # Don't clear thinking_items to preserve thinking display for previous messages
        # self.thinking_items = []
        self.image_chunks = []
        self.current_reasoning_session = ""  # Reset reasoning session for new message

    def _handle_chunk(self, chunk: Chunk) -> None:
        """Handle incoming chunk based on its type."""
        self.current_chunks.append(chunk)

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

    def _handle_reasoning_chunk(self, chunk: Chunk) -> None:
        """Handle reasoning chunks by consolidating them into thinking items."""
        if chunk.type == ChunkType.THINKING:
            self.show_thinking = True
            logger.debug("Thinking: %s", chunk.text)

        reasoning_session = self._get_or_create_reasoning_session(chunk)
        existing_item = self._find_existing_reasoning_item(reasoning_session)

        if existing_item:
            self._update_existing_reasoning_item(existing_item, chunk)
        else:
            self._create_new_reasoning_item(reasoning_session, chunk)

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

    def _find_existing_reasoning_item(self, reasoning_session: str) -> Thinking | None:
        """Find existing reasoning item by session ID."""
        for item in self.thinking_items:
            if item.type == ThinkingType.REASONING and item.id == reasoning_session:
                return item
        return None

    def _update_existing_reasoning_item(
        self, existing_item: Thinking, chunk: Chunk
    ) -> None:
        """Update existing reasoning item with new chunk data."""
        if chunk.type == ChunkType.THINKING:
            if existing_item.text:
                existing_item.text += f"\n{chunk.text}"
            else:
                existing_item.text = chunk.text
        elif chunk.type == ChunkType.THINKING_RESULT:
            existing_item.status = ThinkingStatus.COMPLETED
            if chunk.text:
                existing_item.text += f" {chunk.text}"
        # Trigger Reflex reactivity by reassigning the list
        self.thinking_items = self.thinking_items.copy()

    def _create_new_reasoning_item(self, reasoning_session: str, chunk: Chunk) -> None:
        """Create new reasoning item."""
        status = (
            ThinkingStatus.COMPLETED
            if chunk.type == ChunkType.THINKING_RESULT
            else ThinkingStatus.IN_PROGRESS
        )
        new_item = Thinking(
            type=ThinkingType.REASONING,
            id=reasoning_session,
            text=chunk.text,
            status=status,
        )
        self.thinking_items = [*self.thinking_items, new_item]

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

        # Find existing tool item or create new one
        existing_item = self._find_existing_tool_item(tool_id)

        if existing_item:
            self._update_existing_tool_item(existing_item, chunk)
        else:
            self._create_new_tool_item(tool_id, chunk)

        logger.debug("Tool event: %s - %s", chunk.type, chunk.text)

    def _find_existing_tool_item(self, tool_id: str) -> Thinking | None:
        """Find existing tool item by ID."""
        for item in self.thinking_items:
            if item.type == ThinkingType.TOOL_CALL and item.id == tool_id:
                return item
        return None

    def _update_existing_tool_item(self, existing_item: Thinking, chunk: Chunk) -> None:
        """Update existing tool item with new chunk data."""
        if chunk.type == ChunkType.TOOL_CALL:
            # Store parameters separately from text
            existing_item.parameters = chunk.chunk_metadata.get(
                "parameters", chunk.text
            )
            existing_item.text = chunk.chunk_metadata.get("description", "")
            # Only set tool_name if it's not already present
            if not existing_item.tool_name:
                existing_item.tool_name = chunk.chunk_metadata.get(
                    "tool_name", "Unknown"
                )
            existing_item.status = ThinkingStatus.IN_PROGRESS
        elif chunk.type == ChunkType.TOOL_RESULT:
            self._handle_tool_result(existing_item, chunk)
        elif chunk.type == ChunkType.ACTION:
            existing_item.text += f"\n---\nAktion: {chunk.text}"
        # Trigger Reflex reactivity by reassigning the list
        self.thinking_items = self.thinking_items.copy()

    def _handle_tool_result(self, existing_item: Thinking, chunk: Chunk) -> None:
        """Handle tool result chunk."""
        # Check if this is an error result
        is_error = (
            "error" in chunk.text.lower()
            or "failed" in chunk.text.lower()
            or chunk.chunk_metadata.get("error")
        )
        existing_item.status = (
            ThinkingStatus.ERROR if is_error else ThinkingStatus.COMPLETED
        )
        # Store result separately from text
        existing_item.result = chunk.text
        if is_error:
            existing_item.error = chunk.text

    def _create_new_tool_item(self, tool_id: str, chunk: Chunk) -> None:
        """Create new tool item."""
        tool_name = chunk.chunk_metadata.get("tool_name", "Unknown")
        status = ThinkingStatus.IN_PROGRESS
        text = ""
        parameters = None
        result = None

        if chunk.type == ChunkType.TOOL_CALL:
            # Store parameters separately from text
            parameters = chunk.chunk_metadata.get("parameters", chunk.text)
            text = chunk.chunk_metadata.get("description", "")
        elif chunk.type == ChunkType.TOOL_RESULT:
            is_error = "error" in chunk.text.lower() or "failed" in chunk.text.lower()
            status = ThinkingStatus.ERROR if is_error else ThinkingStatus.COMPLETED
            result = chunk.text
        else:
            text = chunk.text

        new_item = Thinking(
            type=ThinkingType.TOOL_CALL,
            id=tool_id,
            text=text,
            status=status,
            tool_name=tool_name,
            parameters=parameters,
            result=result,
            error=chunk.text if status == ThinkingStatus.ERROR else None,
        )
        self.thinking_items = [*self.thinking_items, new_item]

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

    thread_store: str = rx.LocalStorage("{}", name="asui-threads", sync=True)
    threads: list[ThreadModel] = []
    active_thread_id: str = ""
    autosave: bool = False

    @rx.var
    def has_threads(self) -> bool:
        """Check if there are any threads."""
        return len(self.threads) > 0

    async def initialize(
        self, autosave: bool = False, auto_create_default: bool = False
    ) -> None:
        """Initialize the thread list state.

        Args:
            autosave: Enable auto-saving threads to local storage.
            auto_create_default: If True, create and select a default thread
                when no threads exist (e.g., on first load or after clearing).
        """
        self.autosave = autosave
        await self.load_threads()

        # Auto-create default thread if enabled and no threads exist
        if auto_create_default and not self.has_threads:
            await self.create_thread()

        logger.debug("Initialized thread list state")

    async def load_threads(self) -> None:
        """Load threads from browser local storage."""
        try:
            thread_data = json.loads(self.thread_store)
            if thread_data and "threads" in thread_data:
                processed_threads: list[ThreadModel] = []
                needs_upgrade = False
                for thread in thread_data["threads"]:
                    thread_payload = dict(thread)
                    messages_payload: list[dict[str, Any]] = []
                    for message in thread_payload.get("messages", []):
                        msg_data = dict(message)
                        encoded = msg_data.pop("text_b64", None)
                        if encoded is not None:
                            try:
                                msg_data["text"] = base64.b64decode(encoded).decode(
                                    "utf-8"
                                )
                            except Exception as exc:
                                logger.warning(
                                    "Failed to decode stored message: %s", exc
                                )
                                msg_data["text"] = _rehydrate_mermaid_text(
                                    msg_data.get("text", "")
                                )
                                needs_upgrade = True
                        else:
                            msg_data["text"] = _rehydrate_mermaid_text(
                                msg_data.get("text", "")
                            )
                            needs_upgrade = True
                        messages_payload.append(msg_data)
                    thread_payload["messages"] = messages_payload
                    processed_threads.append(ThreadModel(**thread_payload))

                self.threads = processed_threads
                self.active_thread_id = thread_data.get("active_thread_id", "")
                if self.active_thread_id:
                    await self.select_thread(self.active_thread_id)
                if needs_upgrade:
                    await self.save_threads()
        except Exception as e:
            logger.error("Error loading threads from local storage: %s", e)
            self.threads = []
            self.active_thread_id = ""

    async def save_threads(self) -> None:
        """Save threads to browser local storage."""
        try:
            thread_list = []
            for thread in self.threads:
                thread_dict = thread.dict()
                encoded_messages: list[dict[str, Any]] = []
                for message in thread.messages:
                    msg_dict = message.dict()
                    text_value = msg_dict.get("text", "")
                    if isinstance(text_value, str):
                        try:
                            msg_dict["text_b64"] = base64.b64encode(
                                text_value.encode("utf-8")
                            ).decode("ascii")
                        except Exception as exc:
                            logger.warning("Failed to encode message text: %s", exc)
                            msg_dict["text_b64"] = None
                    else:
                        msg_dict["text_b64"] = None
                    encoded_messages.append(msg_dict)
                thread_dict["messages"] = encoded_messages
                thread_list.append(thread_dict)

            thread_data = {
                "threads": thread_list,
                "active_thread_id": self.active_thread_id,
            }
            self.thread_store = json.dumps(thread_data)
            logger.debug("Saved threads to local storage")
        except Exception as e:
            logger.error("Error saving threads to local storage: %s", e)

    async def reset_thread_store(self) -> None:
        self.thread_store = "{}"

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
        await self.select_thread(new_thread.thread_id)

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

        if self.autosave:
            await self.save_threads()
        logger.debug("Updated thread: %s", thread.thread_id)

    async def delete_thread(self, thread_id: str) -> AsyncGenerator[Any, Any]:
        """Delete a thread."""
        thread = await self.get_thread(thread_id)
        if not thread:
            yield rx.toast.error(
                "Chat nicht gefunden.", position="top-right", close_button=True
            )
            logger.warning("Thread with ID %s not found.", thread_id)
            return

        was_active = thread_id == self.active_thread_id
        self.threads.remove(thread)
        await self.save_threads()
        yield rx.toast.info(
            f"Chat '{thread.title}' erfolgreich gelöscht.",
            position="top-right",
            close_button=True,
        )

        # If the deleted thread was active, clear ThreadState and show empty view
        if was_active:
            thread_state: ThreadState = await self.get_state(ThreadState)
            thread_state.initialize()
            self.active_thread_id = ""
        # If other threads remain but we deleted the active one,
        # the empty state is now displayed
        # User can select from existing threads or create new one

    async def select_thread(self, thread_id: str) -> None:
        """Select a thread."""
        for thread in self.threads:
            thread.active = thread.thread_id == thread_id
        self.active_thread_id = thread_id
        active_thread = await self.get_thread(thread_id)

        if active_thread:
            thread_state: ThreadState = await self.get_state(ThreadState)
            thread_state.set_thread(active_thread)
            thread_state.messages = active_thread.messages
            thread_state.selected_model = active_thread.ai_model
            thread_state.with_thread_list = True
