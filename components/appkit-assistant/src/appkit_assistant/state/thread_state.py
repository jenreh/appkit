"""Thread state management for the assistant.

This module contains ThreadState which manages the current active thread:
- Creating new threads (not persisted until first response)
- Loading threads from database when selected from list
- Processing messages and handling responses
- Persisting thread data to database
- Notifying ThreadListState when a new thread is created

See thread_list_state.py for ThreadListState which manages the thread list sidebar.
"""

import asyncio
import json
import logging
import re
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any

import reflex as rx

from appkit_assistant.backend.database.models import (
    MCPServer,
    ThreadStatus,
)
from appkit_assistant.backend.database.repositories import (
    mcp_server_repo,
    user_prompt_repo,
)
from appkit_assistant.backend.model_manager import ModelManager
from appkit_assistant.backend.schemas import (
    AIModel,
    Chunk,
    ChunkType,
    CommandDefinition,
    Message,
    MessageType,
    Suggestion,
    Thinking,
    ThinkingType,
    ThreadModel,
    UploadedFile,
)
from appkit_assistant.backend.services import file_manager
from appkit_assistant.backend.services.response_accumulator import ResponseAccumulator
from appkit_assistant.backend.services.thread_service import ThreadService
from appkit_assistant.configuration import AssistantConfig
from appkit_assistant.state.thread_list_state import ThreadListState
from appkit_commons.database.session import get_asyncdb_session
from appkit_commons.registry import service_registry
from appkit_user.authentication.states import UserSession

logger = logging.getLogger(__name__)


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
    cancellation_requested: bool = False
    messages: list[Message] = []
    prompt: str = ""
    suggestions: list[Suggestion] = []

    # Chunk processing state
    thinking_items: list[Thinking] = []  # Consolidated reasoning and tool calls
    image_chunks: list[Chunk] = []
    show_thinking: bool = False
    thinking_expanded: bool = False
    current_activity: str = ""

    # File upload state
    uploaded_files: list[UploadedFile] = []
    max_file_size_mb: int = 50
    max_files_per_thread: int = 10

    # Editing state
    editing_message_id: str | None = None
    edited_message_content: str = ""

    # Expanded message state (for long user messages)
    expanded_message_ids: list[str] = []

    # Internal logic helper (not reactive)
    @property
    def _thread_service(self) -> ThreadService:
        return ThreadService()

    # MCP Server tool support state
    selected_mcp_servers: list[MCPServer] = []
    show_tools_modal: bool = False
    available_mcp_servers: list[MCPServer] = []
    temp_selected_mcp_servers: list[int] = []
    server_selection_state: dict[int, bool] = {}

    # Web Search state
    web_search_enabled: bool = False

    # MCP OAuth state
    pending_auth_server_id: str = ""
    pending_auth_server_name: str = ""
    pending_auth_url: str = ""
    show_auth_card: bool = False
    pending_oauth_message: str = ""  # Message that triggered OAuth, resent on success
    # Cross-tab synced localStorage - triggers re-render when popup sets value
    oauth_result: str = rx.LocalStorage(name="mcp-oauth-result", sync=True)

    # Command palette state
    show_command_palette: bool = False
    filtered_commands: list[CommandDefinition] = []
    selected_command_index: int = 0
    command_search_prefix: str = ""
    command_trigger_position: int = 0  # Position of "/" in textarea

    # Available slash commands (hardcoded for now)
    available_commands: list[CommandDefinition] = []

    # Thread list integration
    with_thread_list: bool = False

    # Internal state
    _initialized: bool = False
    _current_user_id: str = ""
    _skip_user_message: bool = False  # Skip adding user message (for OAuth resend)
    _pending_file_cleanup: list[str] = []  # Files to delete after processing
    # Internal cancellation event
    _cancel_event: asyncio.Event | None = None

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
    def selected_model_supports_attachments(self) -> bool:
        """Check if the currently selected model supports attachments."""
        if not self.selected_model:
            return False
        model = ModelManager().get_model(self.selected_model)
        return model.supports_attachments if model else False

    @rx.var
    def selected_model_supports_search(self) -> bool:
        """Check if the currently selected model supports web search."""
        if not self.selected_model:
            return False
        model = ModelManager().get_model(self.selected_model)
        return model.supports_search if model else False

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

    @rx.var
    def filtered_user_prompts(self) -> list[CommandDefinition]:
        """User's own prompts (editable), sorted alphabetically."""
        return sorted(
            [cmd for cmd in self.filtered_commands if cmd.is_editable],
            key=lambda c: c.id.lower(),
        )

    @rx.var
    def filtered_shared_prompts(self) -> list[CommandDefinition]:
        """Shared prompts from others (not editable), sorted alphabetically."""
        return sorted(
            [cmd for cmd in self.filtered_commands if not cmd.is_editable],
            key=lambda c: c.id.lower(),
        )

    @rx.var
    def has_filtered_user_prompts(self) -> bool:
        """Check if there are any filtered user prompts."""
        return any(cmd.is_editable for cmd in self.filtered_commands)

    @rx.var
    def has_filtered_shared_prompts(self) -> bool:
        """Check if there are any filtered shared prompts."""
        return any(not cmd.is_editable for cmd in self.filtered_commands)

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

        self._setup_models(user)

        self._thread = self._thread_service.create_new_thread(
            current_model=self.selected_model,
            user_roles=user.roles if user else [],
        )
        self._reset_ui_state()
        self._current_user_id = current_user_id

        self._load_config()

        if current_user_id:
            try:
                await self._load_user_prompts_as_commands(int(current_user_id))
            except Exception as e:
                logger.warning("Failed to load user prompts as commands: %s", e)

        self._initialized = True
        logger.debug("Initialized thread state: %s", self._thread.thread_id)

    def _setup_models(self, user: Any) -> None:
        """Setup available AI models based on user roles."""
        model_manager = ModelManager()
        all_models = model_manager.get_all_models()
        self.selected_model = model_manager.get_default_model()

        user_roles = user.roles if user else []
        self.ai_models = [
            m
            for m in all_models
            if not m.requires_role or m.requires_role in user_roles
        ]

        # Ensure selected model is available
        available_ids = {m.id for m in self.ai_models}
        if self.selected_model not in available_ids:
            if self.ai_models:
                self.selected_model = self.ai_models[0].id
            else:
                logger.warning("No models available for user")
                self.selected_model = ""

    def _load_config(self) -> None:
        """Load assistant configuration."""
        config: AssistantConfig | None = service_registry().get(AssistantConfig)
        if config:
            self.max_file_size_mb = config.file_upload.max_file_size_mb
            self.max_files_per_thread = config.file_upload.max_files_per_thread

    def _reset_ui_state(self) -> None:
        """Reset UI-related state variables."""
        self.messages = []
        self.thinking_items = []
        self.image_chunks = []
        self.prompt = ""
        self.show_thinking = False
        self.available_commands = []

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

        # Need user roles for create_new_thread
        user_session: UserSession = await self.get_state(UserSession)
        user = await user_session.authenticated_user
        user_roles = user.roles if user else []

        self._thread = self._thread_service.create_new_thread(
            current_model=self.selected_model, user_roles=user_roles
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
            yield
            return

        try:
            full_thread = await self._thread_service.load_thread(thread_id, user_id)

            if not full_thread:  # it was not found
                logger.warning("Thread %s not found in database", thread_id)
                async with self:
                    threadlist_state: ThreadListState = await self.get_state(
                        ThreadListState
                    )
                    threadlist_state.loading_thread_id = ""
                yield
                return

            # Mark all messages as done (loaded from DB)
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
            yield

        except Exception as e:
            logger.error("Error loading thread %s: %s", thread_id, e)
            async with self:
                threadlist_state: ThreadListState = await self.get_state(
                    ThreadListState
                )
                threadlist_state.loading_thread_id = ""
            yield

    # -------------------------------------------------------------------------
    # Prompt and model management
    # -------------------------------------------------------------------------

    @rx.event
    def set_prompt(self, prompt: str) -> None:
        """Set the current prompt and handle command palette detection."""
        self.prompt = prompt
        self._update_command_palette(prompt)

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
    # Command palette management
    # -------------------------------------------------------------------------

    @rx.event
    async def reload_commands(self) -> None:
        """Reload user prompts as commands.

        Call this after creating, updating, or deleting prompts to refresh
        the command palette.
        """
        if self._current_user_id:
            await self._load_user_prompts_as_commands(int(self._current_user_id))
            # Refresh palette filtering with new commands list
            self._update_command_palette(self.prompt)

    async def _load_user_prompts_as_commands(self, user_id: int) -> None:
        """Load user prompts from database and convert to CommandDefinitions."""
        try:
            async with get_asyncdb_session() as session:
                own_prompts = await user_prompt_repo.find_latest_prompts_by_user(
                    session, user_id
                )
                shared_prompts = await user_prompt_repo.find_latest_shared_prompts(
                    session, user_id
                )

                self.available_commands = [
                    CommandDefinition(
                        id=p.handle,
                        label=f"/{p.handle}",
                        description=p.description,
                        icon="",
                        is_editable=True,
                        user_id=user_id,
                    )
                    for p in own_prompts
                ] + [
                    CommandDefinition(
                        id=p["handle"],
                        label=f"/{p['handle']}",
                        description=p.get("description", ""),
                        icon="share",
                        is_editable=False,
                        user_id=p.get("user_id", 0),
                    )
                    for p in shared_prompts
                ]

                logger.debug(
                    "Loaded %d commands (%d own, %d shared) for user %d",
                    len(self.available_commands),
                    len(own_prompts),
                    len(shared_prompts),
                    user_id,
                )
        except Exception as e:
            logger.error("Error loading user prompts as commands: %s", e)
            self.available_commands = []

    def _update_command_palette(self, prompt: str) -> None:
        """Update command palette state based on prompt content."""
        # Find the last "/" that starts a word (at start or after whitespace)
        # and has no whitespace after it.
        match = re.search(r"(?:^|\s)/([^\s]*)$", prompt)

        if not match:
            self._hide_command_palette()
            return

        text_after_slash = match.group(1)
        # Calculate slash position: match end - length of text - 1 (for the slash)
        slash_pos = match.end() - len(text_after_slash) - 1

        # Filter commands
        search_term = text_after_slash.lower()
        self.filtered_commands = [
            cmd
            for cmd in self.available_commands
            if cmd.id.lower().startswith(search_term)
            or cmd.label.lower().startswith(f"/{search_term}")
        ]

        if self.filtered_commands:
            self.show_command_palette = True
            self.command_search_prefix = text_after_slash
            self.command_trigger_position = slash_pos
            self.selected_command_index = 0
        else:
            self._hide_command_palette()

    def _hide_command_palette(self) -> None:
        """Hide the command palette and reset state."""
        self.show_command_palette = False
        self.filtered_commands = []
        self.selected_command_index = 0
        self.command_search_prefix = ""
        self.command_trigger_position = 0

    @rx.event
    def navigate_command_palette(self, direction: str) -> None:
        """Navigate through command palette items.

        Args:
            direction: "up" or "down" to move selection
        """
        if not self.show_command_palette or not self.filtered_commands:
            return

        count = len(self.filtered_commands)
        if direction == "up":
            self.selected_command_index = (self.selected_command_index - 1) % count
        elif direction == "down":
            self.selected_command_index = (self.selected_command_index + 1) % count

    @rx.event
    def select_command(self, command_id: str) -> None:
        """Select a command from the palette and insert it into the prompt.

        Args:
            command_id: The ID of the command to select.
        """
        # Find the command
        command = None
        for cmd in self.filtered_commands:
            if cmd.id == command_id:
                command = cmd
                break

        if not command:
            self._hide_command_palette()
            return

        # Replace "/" + search text with the full command label
        before_slash = self.prompt[: self.command_trigger_position]
        after_command = ""  # Since we search to end of string

        # Insert the command label followed by a space
        self.prompt = before_slash + command.label + " " + after_command

        # Hide palette
        self._hide_command_palette()

    @rx.event
    def select_current_command(self) -> None:
        """Select the currently highlighted command in the palette."""
        if not self.show_command_palette or not self.filtered_commands:
            return

        if 0 <= self.selected_command_index < len(self.filtered_commands):
            command = self.filtered_commands[self.selected_command_index]
            self.select_command(command.id)

    @rx.event
    def dismiss_command_palette(self) -> None:
        """Dismiss the command palette without selecting."""
        self._hide_command_palette()

    # -------------------------------------------------------------------------
    # UI state management
    # -------------------------------------------------------------------------

    @rx.event
    def toggle_thinking_expanded(self) -> None:
        """Toggle the expanded state of the thinking section."""
        self.thinking_expanded = not self.thinking_expanded

    @rx.event
    def toggle_web_search(self) -> None:
        """Toggle web search."""
        self.web_search_enabled = not self.web_search_enabled

    # -------------------------------------------------------------------------
    # MCP Server tool support
    # -------------------------------------------------------------------------

    @rx.event
    async def load_mcp_servers(self) -> None:
        """Load available active MCP servers filtered by user roles."""
        # Get the user session to check roles
        user_session = await self.get_state(UserSession)
        user = await user_session.authenticated_user
        user_roles: list[str] = user.roles if user else []

        async with get_asyncdb_session() as session:
            servers = await mcp_server_repo.find_all_active_ordered_by_name(session)
            # Filter servers by user roles:
            # - Include if required_role is empty/None (no restriction)
            # - Include if user has the required_role
            filtered_servers = [
                MCPServer(**s.model_dump())
                for s in servers
                if not s.required_role or s.required_role in user_roles
            ]
            self.available_mcp_servers = filtered_servers

    @rx.event
    def toggle_tools_modal(self, show: bool) -> None:
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
    def deselect_all_mcp_servers(self) -> None:
        """Deselect all MCP servers in the modal."""
        self.server_selection_state = {}
        self.temp_selected_mcp_servers = []

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
        self._clear_uploaded_files()

    # -------------------------------------------------------------------------
    # File upload handling
    # -------------------------------------------------------------------------

    @rx.event
    async def handle_upload(
        self, files: list[rx.UploadFile]
    ) -> AsyncGenerator[Any, Any]:
        """Handle uploaded files from the browser.

        Moves files to user-specific directory and adds them to state.
        """
        # Validate file count (using state variables from config)
        if len(files) > self.max_files_per_thread:
            yield rx.toast.error(
                (
                    f"Bitte laden Sie maximal {self.max_files_per_thread} "
                    "Dateien gleichzeitig hoch."
                ),
                position="top-right",
                close_button=True,
            )
            return

        user_session: UserSession = await self.get_state(UserSession)
        user_id = user_session.user.user_id if user_session.user else "anonymous"

        for upload_file in files:
            try:
                # Save uploaded file to disk first
                upload_data = await upload_file.read()
                temp_path = rx.get_upload_dir() / upload_file.filename
                temp_path.parent.mkdir(parents=True, exist_ok=True)
                temp_path.write_bytes(upload_data)

                # Move to user directory
                final_path = file_manager.move_to_user_directory(
                    str(temp_path), str(user_id)
                )
                file_size = file_manager.get_file_size(final_path)

                uploaded = UploadedFile(
                    filename=upload_file.filename,
                    file_path=final_path,
                    size=file_size,
                )
                self.uploaded_files = [*self.uploaded_files, uploaded]
                logger.info(
                    "Uploaded file: %s (total files: %d)",
                    upload_file.filename,
                    len(self.uploaded_files),
                )
            except Exception as e:
                logger.error("Failed to upload file %s: %s", upload_file.filename, e)

    @rx.event
    def remove_file_from_prompt(self, file_path: str) -> None:
        """Remove an uploaded file from the prompt."""
        # Delete the file from disk
        file_manager.cleanup_uploaded_files([file_path])
        # Remove from state
        self.uploaded_files = [
            f for f in self.uploaded_files if f.file_path != file_path
        ]
        logger.debug("Removed uploaded file: %s", file_path)

    def _clear_uploaded_files(self) -> None:
        """Clear all uploaded files from state and disk."""
        if not self.uploaded_files:
            return
        count = len(self.uploaded_files)
        file_paths = [f.file_path for f in self.uploaded_files]
        file_manager.cleanup_uploaded_files(file_paths)
        self.uploaded_files = []
        logger.debug("Cleared %d uploaded files", count)

    # -------------------------------------------------------------------------
    # Message processing
    # -------------------------------------------------------------------------

    @rx.event
    def set_editing_mode(self, message_id: str, content: str) -> None:
        """Enable editing mode for a message."""
        self.editing_message_id = message_id
        self.edited_message_content = content

    @rx.event
    def set_edited_message_content(self, content: str) -> None:
        """Set the content of the message currently being edited."""
        self.edited_message_content = content

    @rx.event
    def cancel_edit(self) -> None:
        """Cancel editing mode."""
        self.editing_message_id = None
        self.edited_message_content = ""

    @rx.event
    def toggle_message_expanded(self, message_id: str) -> None:
        """Toggle expanded state for a user message."""
        if message_id in self.expanded_message_ids:
            self.expanded_message_ids = [
                mid for mid in self.expanded_message_ids if mid != message_id
            ]
        else:
            self.expanded_message_ids = [*self.expanded_message_ids, message_id]

    @rx.event(background=True)
    async def submit_edited_message(self) -> AsyncGenerator[Any, Any]:
        """Submit edited message."""
        async with self:
            content = self.edited_message_content.strip()
            if not content:
                yield rx.toast.error(
                    "Nachricht darf nicht leer sein", position="top-right"
                )
                return

            # Find message index
            msg_index = next(
                (
                    i
                    for i, m in enumerate(self.messages)
                    if m.id == self.editing_message_id
                ),
                -1,
            )

            if msg_index == -1:
                self.cancel_edit()
                return

            target_message = self.messages[msg_index]

            # Update message
            target_message.original_text = (
                target_message.original_text or target_message.text
            )
            target_message.text = content

            # Remove all messages AFTER this one
            self.messages = self.messages[: msg_index + 1]

            # Set prompt to bypass empty check in _begin_message_processing
            self.prompt = content
            self._skip_user_message = True

            # Clear edit state
            self.editing_message_id = None
            self.edited_message_content = ""

        # Trigger processing
        await self._process_message()

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

    @rx.event(background=True)
    async def delete_message(self, message_id: str) -> None:
        """Delete a message from the conversation."""
        async with self:
            self.messages = [m for m in self.messages if m.id != message_id]
            self._thread.messages = self.messages

            if self._thread.state != ThreadStatus.NEW:
                await self._thread_service.save_thread(
                    self._thread, self.current_user_id
                )

    @rx.event
    def copy_message(self, text: str) -> list[Any]:
        """Copy message text to clipboard."""
        return [
            rx.set_clipboard(text),
            rx.toast.success("Nachricht kopiert"),
        ]

    @rx.event
    def download_message(self, text: str, message_id: str) -> Any:
        """Download message as markdown file."""
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        filename = (
            f"message_{message_id}_{timestamp}.md"
            if message_id
            else f"message_{timestamp}.md"
        )

        # Use JavaScript to trigger download
        return rx.call_script(f"""
            const blob = new Blob([{json.dumps(text)}], {{type: 'text/markdown'}});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = '{filename}';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        """)

    @rx.event(background=True)
    async def retry_message(self, message_id: str) -> None:
        """Retry generating a message."""
        async with self:
            # Find message index
            index = -1
            for i, msg in enumerate(self.messages):
                if msg.id == message_id:
                    index = i
                    break

            if index == -1:
                return

            # Keep context up to this message
            # effectively removing this message and everything after
            self.messages = self.messages[:index]

            # Set prompt to bypass check (content checks)
            self.prompt = "Regenerate"

            # Flag to skip adding a new user message
            self._skip_user_message = True

        # Trigger processing directly
        await self._process_message()

    @rx.event
    def request_cancellation(self) -> None:
        """Signal that the current processing should be cancelled."""
        self.cancellation_requested = True
        if self._cancel_event:
            self._cancel_event.set()
            logger.info("Cancellation requested by user")

    async def _process_message(self) -> None:
        """Process the current message and stream the response."""
        logger.debug("Processing message: %s", self.prompt)

        start = await self._begin_message_processing()
        if not start:
            return
        current_prompt, selected_model, mcp_servers, file_paths, is_new_thread = start

        processor = ModelManager().get_processor_for_model(selected_model)
        if not processor:
            await self._stop_processing_with_error(
                f"Keinen Adapter für das Modell gefunden: {selected_model}"
            )
            return

        async with self:
            user_session: UserSession = await self.get_state(UserSession)
            user_id = user_session.user.user_id if user_session.user else None

            logger.debug(
                "Pre-save check: is_new_thread=%s, file_paths=%d, user_id=%s",
                is_new_thread,
                len(file_paths) if file_paths else 0,
                user_id,
            )

            # Save thread to DB if new and has files to enable file uploads
            if is_new_thread and file_paths and user_id:
                self._thread.state = ThreadStatus.ACTIVE
                await self._thread_service.save_thread(self._thread, user_id)
                logger.debug(
                    "Saved new thread %s to DB before file upload",
                    self._thread.thread_id,
                )

            # Initialize ResponseAccumulator logic
            accumulator = ResponseAccumulator()
            accumulator.attach_messages_ref(self.messages)

            # Clear uploaded files from UI and mark for cleanup after processing
            self.uploaded_files = []
            self._pending_file_cleanup = file_paths

            # Initialize cancellation event
            self._cancel_event = asyncio.Event()

        first_response_received = False
        try:
            # Build payload with thread_uuid for file upload support
            payload = {"thread_uuid": self._thread.thread_id}

            # Pass web search state to processor via payload
            if self.web_search_enabled:
                payload["web_search_enabled"] = True

            async for chunk in processor.process(
                self.messages,
                selected_model,
                files=file_paths or None,
                mcp_servers=mcp_servers,
                payload=payload,
                user_id=user_id,
                cancellation_token=self._cancel_event,
            ):
                first_response_received = await self._handle_stream_chunk(
                    chunk=chunk,
                    accumulator=accumulator,
                    current_prompt=current_prompt,
                    is_new_thread=is_new_thread,
                    first_response_received=first_response_received,
                )

            await self._finalize_successful_response(accumulator)

        except Exception as ex:
            await self._handle_process_error(
                ex=ex,
                current_prompt=current_prompt,
                is_new_thread=is_new_thread,
                first_response_received=first_response_received,
            )

        finally:
            await self._finalize_processing()

    def _parse_prompt_segments(self, prompt: str) -> list[dict]:
        """Parse prompt into text and command segments.

        Identifies command patterns (/command_name) and splits text into
        segments of type "text" or "command".

        Commands are only recognized when "/" is at the start of the string
        or preceded by whitespace, matching the command palette trigger behavior.
        Handle pattern matches validate_handle: letters, numbers, and hyphens only.

        Args:
            prompt: The user prompt text.

        Returns:
            List of dicts with "type" and "content"/"handle" keys.
            Example: [
                {"type": "text", "content": "do something"},
                {"type": "command", "handle": "boost"},
                {"type": "text", "content": "i want to..."}
            ]
        """
        segments = []
        # Pattern: "/" at start or after whitespace, followed by valid handle chars
        # Matches validate_handle pattern: [a-zA-Z0-9-]+
        pattern = r"(?:^|(?<=\s))/([a-zA-Z0-9-]+)"

        last_end = 0
        for match in re.finditer(pattern, prompt):
            # Add text before command (include any whitespace before the "/")
            text_before = prompt[last_end : match.start()].strip()
            if text_before:
                segments.append({"type": "text", "content": text_before})

            # Add command
            command_handle = match.group(1)
            segments.append({"type": "command", "handle": command_handle})

            last_end = match.end()

        # Add remaining text after last command
        if last_end < len(prompt):
            text_after = prompt[last_end:].strip()
            if text_after:
                segments.append({"type": "text", "content": text_after})

        return segments

    async def _load_command_prompt_text(
        self, user_id: int, command_handle: str
    ) -> str | None:
        """Load the prompt text for a command from the database.

        Args:
            user_id: The user ID to filter prompts by.
            command_handle: The command handle (ID) to load.

        Returns:
            The prompt_text from the user_prompt, or None if not found.
        """
        try:
            # Strip leading "/" if present
            handle = command_handle.lstrip("/")

            async with get_asyncdb_session() as session:
                prompt = await user_prompt_repo.find_latest_accessible_by_handle(
                    session, user_id, handle
                )
                if prompt:
                    logger.debug(
                        "Loaded command prompt for handle '%s'",
                        handle,
                    )
                    return prompt.prompt_text

                logger.debug(
                    "Command prompt not found for handle '%s'",
                    handle,
                )
        except Exception as e:
            logger.error(
                "Error loading command prompt for %s: %s",
                command_handle,
                e,
            )
        return None

    async def _begin_message_processing(
        self,
    ) -> tuple[str, str, list[MCPServer], list[str], bool] | None:
        """Prepare state for sending a message. Returns None if no-op."""
        async with self:
            current_prompt = self.prompt.strip()
            if self.processing or not current_prompt:
                return None

            self.processing = True
            # Clearing chunks now only resets direct UI state if needed,
            # but accumulator handles logic
            self.image_chunks = []
            self.thinking_items = []

            self.prompt = ""

            is_new_thread = self._thread.state == ThreadStatus.NEW

            # Capture file paths before clearing
            file_paths = [f.file_path for f in self.uploaded_files]
            # Capture filenames for message display
            attachment_names = [f.filename for f in self.uploaded_files]

            logger.debug(
                "Begin processing: is_new_thread=%s, uploaded_files=%d, file_paths=%s",
                is_new_thread,
                len(self.uploaded_files),
                file_paths,
            )

            # Add user message(s) unless skipped (e.g., OAuth resend)
            if self._skip_user_message:
                self._skip_user_message = False
            else:
                # Parse prompt into segments (text and commands)
                segments = self._parse_prompt_segments(current_prompt)

                if segments:
                    # Process each segment
                    for i, segment in enumerate(segments):
                        if segment["type"] == "text":
                            # Add text segment as message
                            is_first = i == 0
                            self.messages.append(
                                Message(
                                    text=segment["content"],
                                    type=MessageType.HUMAN,
                                    attachments=(attachment_names if is_first else []),
                                )
                            )
                        elif segment["type"] == "command":
                            # Load command prompt and add as message
                            command_handle = segment["handle"]
                            command_prompt = await self._load_command_prompt_text(
                                int(self.current_user_id), command_handle
                            )

                            if command_prompt:
                                self.messages.append(
                                    Message(
                                        text=command_prompt,
                                        type=MessageType.HUMAN,
                                    )
                                )
                                logger.debug(
                                    "Loaded command %s prompt",
                                    command_handle,
                                )
                            else:
                                logger.warning(
                                    "Command %s not found for user %s",
                                    command_handle,
                                    self.current_user_id,
                                )

                    logger.debug(
                        "Split prompt into %d segments and %d messages",
                        len(segments),
                        len([m for m in self.messages if m.type == MessageType.HUMAN]),
                    )
                else:
                    # No segments - add original message as-is
                    self.messages.append(
                        Message(
                            text=current_prompt,
                            type=MessageType.HUMAN,
                            attachments=attachment_names,
                        )
                    )
            # Always add assistant placeholder
            self.messages.append(Message(text="", type=MessageType.ASSISTANT))

            selected_model = self.get_selected_model
            if not selected_model:
                self._add_error_message("Kein Chat-Modell ausgewählt")
                self.processing = False
                return None

            mcp_servers = self.selected_mcp_servers
            return (
                current_prompt,
                selected_model,
                mcp_servers,
                file_paths,
                is_new_thread,
            )

    async def _stop_processing_with_error(self, error_msg: str) -> None:
        """Stop processing and show an error message."""
        async with self:
            self._add_error_message(error_msg)
            self.processing = False

    async def _handle_stream_chunk(
        self,
        *,
        chunk: Chunk,
        accumulator: ResponseAccumulator,
        current_prompt: str,
        is_new_thread: bool,
        first_response_received: bool,
    ) -> bool:
        """Handle one streamed chunk. Returns updated first_response_received."""
        async with self:
            accumulator.process_chunk(chunk)

            # Sync UI state from accumulator
            # Create copy to trigger update
            self.thinking_items = list(accumulator.thinking_items)
            self.current_activity = accumulator.current_activity
            if accumulator.show_thinking:
                self.show_thinking = True
            if accumulator.image_chunks:
                # Append only new ones or sync list? image_chunks is list[Chunk]
                # Accumulator has all of them.
                self.image_chunks = list(accumulator.image_chunks)

            # Handle Auth Required which might be set on accumulator state
            if accumulator.auth_required:
                self._handle_auth_required_from_accumulator(accumulator)

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

    async def _finalize_successful_response(
        self, accumulator: ResponseAccumulator
    ) -> None:
        """Finalize state after a successful full response."""
        async with self:
            self.show_thinking = False

            # Final sync
            self.thinking_items = list(accumulator.thinking_items)

            # Convert Reflex proxy list to standard list to avoid Pydantic
            # serializer warnings
            self._thread.messages = list(self.messages)  # noqa: E501
            self._thread.ai_model = self.selected_model

            if self.with_thread_list:
                user_session: UserSession = await self.get_state(UserSession)
                user_id = user_session.user.user_id if user_session.user else None
                if user_id:
                    await self._thread_service.save_thread(self._thread, user_id)

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
                user_session: UserSession = await self.get_state(UserSession)
                user_id = user_session.user.user_id if user_session.user else None
                if user_id:
                    await self._thread_service.save_thread(self._thread, user_id)

    async def _finalize_processing(self) -> None:
        """Mark processing done and close out the last message."""
        async with self:
            if self.messages:
                self.messages[-1].done = True
            self.processing = False
            self.cancellation_requested = False
            self.current_activity = ""
            self._cancel_event = None

            # Clean up uploaded files from disk
            if self._pending_file_cleanup:
                file_manager.cleanup_uploaded_files(self._pending_file_cleanup)
                self._pending_file_cleanup = []

    def _handle_auth_required_from_accumulator(
        self, accumulator: ResponseAccumulator
    ) -> None:
        """Handle auth required state from accumulator."""
        self.pending_auth_server_id = accumulator.auth_required_data.get(
            "server_id", ""
        )
        self.pending_auth_server_name = accumulator.auth_required_data.get(
            "server_name", ""
        )
        self.pending_auth_url = accumulator.auth_required_data.get("auth_url", "")
        self.show_auth_card = True

        # Reset flag in accumulator so we don't trigger this again for same event
        accumulator.auth_required = False

        # Store the last user message to resend after successful OAuth
        for msg in reversed(self.messages):
            if msg.type == MessageType.HUMAN:
                self.pending_oauth_message = msg.text
                break
        logger.debug(
            "Auth required for server %s, showing auth card",
            self.pending_auth_server_name,
        )

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

    # _save_thread_to_db removed, using self._thread_service.save_thread

    # -------------------------------------------------------------------------
    # Chunk handling (internal)
    # Logic moved to ResponseAccumulator
    # -------------------------------------------------------------------------

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
    async def process_oauth_result(self) -> AsyncGenerator[Any, Any]:
        """Process OAuth result from synced LocalStorage.

        Called via on_mount when oauth_result becomes non-empty.
        The rx.LocalStorage(sync=True) automatically syncs from popup.
        """
        if not self.oauth_result:
            return

        try:
            data = json.loads(self.oauth_result)
            if data.get("type") != "mcp-oauth-success":
                return

            server_id = data.get("serverId", "")
            server_name = data.get("serverName", "Unknown")
            user_id = data.get("userId", "")

            # Security: verify user_id matches
            if (
                user_id
                and self._current_user_id
                and str(user_id) != str(self._current_user_id)
            ):
                logger.warning(
                    "OAuth user mismatch: got %s, expected %s",
                    user_id,
                    self._current_user_id,
                )
                # Clear invalid data
                self.oauth_result = ""
                return

            logger.info(
                "Processing OAuth success: server_id=%s, server_name=%s",
                server_id,
                server_name,
            )

            # Clear localStorage before processing to prevent re-triggers
            self.oauth_result = ""

            # Process the OAuth success
            async for event in self.handle_mcp_oauth_success(server_id, server_name):
                yield event

        except json.JSONDecodeError:
            logger.warning("Failed to parse OAuth result: %s", self.oauth_result)
            self.oauth_result = ""

    @rx.event
    def dismiss_auth_card(self) -> None:
        """Dismiss the auth card without authenticating."""
        self.show_auth_card = False

    def _add_error_message(self, error_msg: str) -> None:
        """Add an error message to the conversation."""
        logger.error(error_msg)
        self.messages.append(Message(text=error_msg, type=MessageType.ERROR))
