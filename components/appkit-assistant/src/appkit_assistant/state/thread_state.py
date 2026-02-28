"""Thread state management for the assistant.

This module contains ThreadState which manages the current active thread:
- Creating new threads (not persisted until first response)
- Loading threads from database when selected from list
- Processing messages and handling responses
- Persisting thread data to database
- Notifying ThreadListState when a new thread is created

Method groups are split into mixins under ``state.thread``:
- ModelSelectionMixin   - AI model listing and capability checks
- CommandPaletteMixin   - slash-command palette navigation
- McpToolsMixin         - MCP server tool selection
- McpAppsMixin          - MCP App view management
- SkillsMixin           - skill selection
- FileUploadMixin       - file upload management
- MessageEditMixin      - message editing / copy / download / retry
- OAuthMixin            - MCP OAuth authentication flow
- MessageProcessingMixin - message submission, streaming, persistence

See thread_list_state.py for ThreadListState which manages the
thread list sidebar.
"""

import asyncio
import logging
import uuid
from collections.abc import AsyncGenerator
from typing import Any

import reflex as rx

from appkit_assistant.backend.database.models import (
    MCPServer,
    Skill,
    ThreadStatus,
)
from appkit_assistant.backend.model_manager import ModelManager
from appkit_assistant.backend.schemas import (
    AIModel,
    Chunk,
    CommandDefinition,
    McpAppViewData,
    Message,
    MessageType,
    Suggestion,
    Thinking,
    ThinkingType,
    ThreadModel,
    UploadedFile,
)
from appkit_assistant.backend.services.thread_service import ThreadService
from appkit_assistant.configuration import AssistantConfig
from appkit_assistant.state.thread.command_palette import (
    CommandPaletteMixin,
)
from appkit_assistant.state.thread.file_upload import FileUploadMixin
from appkit_assistant.state.thread.mcp_apps import McpAppsMixin
from appkit_assistant.state.thread.mcp_tools import McpToolsMixin
from appkit_assistant.state.thread.message_edit import MessageEditMixin
from appkit_assistant.state.thread.message_processing import (
    MessageProcessingMixin,
)
from appkit_assistant.state.thread.model_selection import (
    ModelSelectionMixin,
)
from appkit_assistant.state.thread.oauth import OAuthMixin
from appkit_assistant.state.thread.skills import SkillsMixin
from appkit_assistant.state.thread_list_state import ThreadListState
from appkit_commons.registry import service_registry
from appkit_user.authentication.states import UserSession

logger = logging.getLogger(__name__)


class ThreadState(
    ModelSelectionMixin,
    CommandPaletteMixin,
    McpToolsMixin,
    McpAppsMixin,
    SkillsMixin,
    FileUploadMixin,
    MessageEditMixin,
    OAuthMixin,
    MessageProcessingMixin,
    rx.State,
):
    """State for managing the current active thread.

    State variables are declared here; behaviour is provided by the
    mixin classes listed in the base-class tuple.
    """

    # -----------------------------------------------------------------
    # Thread core
    # -----------------------------------------------------------------
    _thread: ThreadModel = ThreadModel(thread_id=str(uuid.uuid4()), prompt="")
    ai_models: list[AIModel] = []
    selected_model: str = ""
    processing: bool = False
    cancellation_requested: bool = False
    messages: list[Message] = []
    prompt: str = ""
    suggestions: list[Suggestion] = []

    # Chunk processing state
    thinking_items: list[Thinking] = []
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
    expanded_message_ids: list[str] = []

    # MCP Server tool support state
    selected_mcp_servers: list[MCPServer] = []
    show_tools_modal: bool = False
    available_mcp_servers: list[MCPServer] = []
    temp_selected_mcp_servers: list[int] = []
    server_selection_state: dict[int, bool] = {}

    # MCP Apps state
    mcp_app_views: list[McpAppViewData] = []
    _ui_tool_registry: dict[str, dict] = {}

    # Skills selection state
    selected_skills: list[Skill] = []
    available_skills_for_selection: list[Skill] = []
    temp_selected_skill_ids: list[str] = []
    skill_selection_state: dict[str, bool] = {}
    modal_active_tab: str = "tools"

    # Web Search state
    web_search_enabled: bool = False

    # MCP OAuth state
    pending_auth_server_id: str = ""
    pending_auth_server_name: str = ""
    pending_auth_url: str = ""
    show_auth_card: bool = False
    pending_oauth_message: str = ""
    oauth_result: str = rx.LocalStorage(name="mcp-oauth-result", sync=True)

    # Command palette state
    show_command_palette: bool = False
    filtered_commands: list[CommandDefinition] = []
    selected_command_index: int = 0
    command_search_prefix: str = ""
    command_trigger_position: int = 0
    available_commands: list[CommandDefinition] = []

    # Thread list integration
    with_thread_list: bool = False

    # Internal state
    _initialized: bool = False
    _current_user_id: str = ""
    _skip_user_message: bool = False
    _pending_file_cleanup: list[str] = []
    _cancel_event: asyncio.Event | None = None

    # -----------------------------------------------------------------
    # Re-export mixin @rx.event and @rx.var members so that Reflex's
    # StateMeta metaclass registers them as proper EventHandlers /
    # ComputedVars.  Without these assignments the metaclass only sees
    # members defined directly in this class body.
    #
    # For @rx.var we access the descriptor via ``__dict__`` to bypass
    # ComputedVar.__get__ which requires an rx.State owner.
    # -----------------------------------------------------------------

    # -- ModelSelectionMixin (@rx.event) --
    set_selected_model = ModelSelectionMixin.set_selected_model

    # -- ModelSelectionMixin (@rx.var) --
    get_selected_model = ModelSelectionMixin.__dict__["get_selected_model"]
    has_ai_models = ModelSelectionMixin.__dict__["has_ai_models"]
    selected_model_supports_tools = ModelSelectionMixin.__dict__[
        "selected_model_supports_tools"
    ]
    selected_model_supports_attachments = ModelSelectionMixin.__dict__[
        "selected_model_supports_attachments"
    ]
    selected_model_supports_search = ModelSelectionMixin.__dict__[
        "selected_model_supports_search"
    ]
    selected_model_supports_skills = ModelSelectionMixin.__dict__[
        "selected_model_supports_skills"
    ]

    # -- CommandPaletteMixin (@rx.event) --
    reload_commands = CommandPaletteMixin.reload_commands
    navigate_command_palette = CommandPaletteMixin.navigate_command_palette
    select_command = CommandPaletteMixin.select_command
    select_current_command = CommandPaletteMixin.select_current_command
    dismiss_command_palette = CommandPaletteMixin.dismiss_command_palette

    # -- CommandPaletteMixin (@rx.var) --
    filtered_user_prompts = CommandPaletteMixin.__dict__["filtered_user_prompts"]
    filtered_shared_prompts = CommandPaletteMixin.__dict__["filtered_shared_prompts"]
    has_filtered_user_prompts = CommandPaletteMixin.__dict__[
        "has_filtered_user_prompts"
    ]
    has_filtered_shared_prompts = CommandPaletteMixin.__dict__[
        "has_filtered_shared_prompts"
    ]

    # -- McpToolsMixin --
    load_mcp_servers = McpToolsMixin.load_mcp_servers
    toggle_tools_modal = McpToolsMixin.toggle_tools_modal
    toggle_mcp_server_selection = McpToolsMixin.toggle_mcp_server_selection
    apply_mcp_server_selection = McpToolsMixin.apply_mcp_server_selection
    deselect_all_mcp_servers = McpToolsMixin.deselect_all_mcp_servers
    is_mcp_server_selected = McpToolsMixin.is_mcp_server_selected

    # -- SkillsMixin --
    load_available_skills_for_user = SkillsMixin.load_available_skills_for_user
    set_modal_active_tab = SkillsMixin.set_modal_active_tab
    toggle_skill_selection = SkillsMixin.toggle_skill_selection
    apply_skill_selection = SkillsMixin.apply_skill_selection
    deselect_all_skills = SkillsMixin.deselect_all_skills

    # -- FileUploadMixin --
    handle_upload = FileUploadMixin.handle_upload
    remove_file_from_prompt = FileUploadMixin.remove_file_from_prompt

    # -- MessageEditMixin --
    set_editing_mode = MessageEditMixin.set_editing_mode
    set_edited_message_content = MessageEditMixin.set_edited_message_content
    cancel_edit = MessageEditMixin.cancel_edit
    toggle_message_expanded = MessageEditMixin.toggle_message_expanded
    submit_edited_message = MessageEditMixin.submit_edited_message
    delete_message = MessageEditMixin.delete_message
    copy_message = MessageEditMixin.copy_message
    download_message = MessageEditMixin.download_message
    retry_message = MessageEditMixin.retry_message

    # -- OAuthMixin --
    start_mcp_oauth = OAuthMixin.start_mcp_oauth
    handle_mcp_oauth_success = OAuthMixin.handle_mcp_oauth_success
    process_oauth_result = OAuthMixin.process_oauth_result
    dismiss_auth_card = OAuthMixin.dismiss_auth_card

    # -- MessageProcessingMixin --
    submit_message = MessageProcessingMixin.submit_message
    request_cancellation = MessageProcessingMixin.request_cancellation

    # -----------------------------------------------------------------
    # Internal helper
    # -----------------------------------------------------------------

    @property
    def _thread_service(self) -> ThreadService:
        return ThreadService()

    # -----------------------------------------------------------------
    # Computed properties (general)
    # -----------------------------------------------------------------

    @rx.var
    def current_user_id(self) -> str:
        """Get the current user ID for OAuth validation."""
        return self._current_user_id

    @rx.var
    def has_suggestions(self) -> bool:
        """Check if there are any suggestions."""
        return len(self.suggestions) > 0

    @rx.var
    def has_thinking_content(self) -> bool:
        """Check if there are any thinking items to display."""
        return len(self.thinking_items) > 0

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
        """Get the text of the last assistant message."""
        for message in reversed(self.messages):
            if message.type == MessageType.ASSISTANT:
                return message.text
        return ""

    @rx.var
    def has_mcp_app_views(self) -> bool:
        """Check if there are any MCP App views to display."""
        return len(self.mcp_app_views) > 0

    # -----------------------------------------------------------------
    # Initialization and thread management
    # -----------------------------------------------------------------

    @rx.event
    async def initialize(self) -> None:
        """Initialize the state with models and a new empty thread.

        Only initializes once per user session. Resets when user
        changes.
        """
        user_session: UserSession = await self.get_state(UserSession)
        user = await user_session.authenticated_user
        current_user_id = str(user.user_id) if user else ""

        self._setup_models(user)

        if self._initialized and self._current_user_id == current_user_id:
            logger.debug(
                "Thread state already initialized for user %s",
                current_user_id,
            )
            return

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
                logger.warning(
                    "Failed to load user prompts as commands: %s",
                    e,
                )

        self._initialized = True
        logger.debug(
            "Initialized thread state: %s",
            self._thread.thread_id,
        )

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
        self.mcp_app_views = []
        self._ui_tool_registry = {}

    @rx.event
    async def new_thread(self) -> None:
        """Create a new empty thread.

        Called when user clicks "New Chat" or when active thread is
        deleted.  Does nothing if current thread is already empty/new.
        """
        if not self._initialized:
            await self.initialize()

        if self._thread.state == ThreadStatus.NEW and not self.messages:
            logger.debug("Thread already empty, skipping new_thread")
            return

        user_session: UserSession = await self.get_state(UserSession)
        user = await user_session.authenticated_user
        user_roles = user.roles if user else []

        self._thread = self._thread_service.create_new_thread(
            current_model=self.selected_model,
            user_roles=user_roles,
        )
        self.messages = []
        self.thinking_items = []
        self.image_chunks = []
        self.prompt = ""
        self.show_thinking = False
        self.mcp_app_views = []
        self._ui_tool_registry = {}
        logger.debug(
            "Created new empty thread: %s",
            self._thread.thread_id,
        )

    @rx.event
    def set_thread(self, thread: ThreadModel) -> None:
        """Set the current thread model (internal use)."""
        self._thread = thread
        self.messages = thread.messages
        self.selected_model = thread.ai_model
        self.thinking_items = []
        self.mcp_app_views = []
        self._ui_tool_registry = {}
        self.prompt = ""
        logger.debug("Set current thread: %s", thread.thread_id)

    @rx.event(background=True)
    async def load_thread(self, thread_id: str) -> AsyncGenerator[Any, Any]:
        """Load and select a thread by ID from database."""
        async with self:
            user_session: UserSession = await self.get_state(UserSession)
            if not (await user_session.is_authenticated) or not user_session.user:
                return

            user_id = user_session.user.user_id

            threadlist_state: ThreadListState = await self.get_state(ThreadListState)
            threadlist_state.loading_thread_id = thread_id
        yield

        try:
            full_thread = await self._thread_service.load_thread(thread_id, user_id)

            if not full_thread:
                logger.warning("Thread %s not found in database", thread_id)
                async with self:
                    await self._stop_loading_state()
                yield
                return

            for msg in full_thread.messages:
                msg.done = True

            async with self:
                self._thread = full_thread
                self.messages = full_thread.messages
                self.selected_model = full_thread.ai_model
                self.thinking_items = []
                self.mcp_app_views = []
                self._ui_tool_registry = {}
                self.prompt = ""
                self.web_search_enabled = False

                model = ModelManager().get_model(full_thread.ai_model)

                if model and model.supports_tools:
                    self._restore_mcp_selection(full_thread.mcp_server_ids)
                else:
                    self._restore_mcp_selection([])

                if model and model.supports_skills:
                    self._restore_skill_selection(full_thread.skill_openai_ids or [])
                else:
                    self._restore_skill_selection([])

                threadlist_state: ThreadListState = await self.get_state(
                    ThreadListState
                )
                threadlist_state.threads = [
                    ThreadModel(
                        **{
                            **t.model_dump(),
                            "active": t.thread_id == thread_id,
                        }
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
                await self._stop_loading_state()
            yield

    # -----------------------------------------------------------------
    # Prompt and simple setters
    # -----------------------------------------------------------------

    @rx.event
    def set_prompt(self, prompt: str) -> None:
        """Set the current prompt and handle command palette."""
        self.prompt = prompt
        self._update_command_palette(prompt)

    @rx.event
    def set_suggestions(self, suggestions: list[Suggestion] | list[dict]) -> None:
        """Set custom suggestions for the thread."""
        if suggestions and isinstance(suggestions[0], dict):
            self.suggestions = [Suggestion(**s) for s in suggestions]
        else:
            self.suggestions = suggestions  # type: ignore[assignment]

    @rx.event
    def set_with_thread_list(self, with_thread_list: bool) -> None:
        """Set whether thread list integration is enabled."""
        self.with_thread_list = with_thread_list

    # -----------------------------------------------------------------
    # UI state management
    # -----------------------------------------------------------------

    @rx.event
    def toggle_thinking_expanded(self) -> None:
        """Toggle the expanded state of the thinking section."""
        self.thinking_expanded = not self.thinking_expanded

    @rx.event
    def toggle_web_search(self) -> None:
        """Toggle web search."""
        self.web_search_enabled = not self.web_search_enabled

    # -----------------------------------------------------------------
    # Clear / reset
    # -----------------------------------------------------------------

    @rx.event
    def clear(self) -> None:
        """Clear the current thread messages (keeps thread ID)."""
        self._thread.messages = []
        self._thread.state = ThreadStatus.NEW
        self._thread.ai_model = ModelManager().get_default_model()
        self._thread.active = True
        self._thread.prompt = ""
        self._thread.mcp_server_ids = []
        self.prompt = ""
        self.messages = []

        self._restore_mcp_selection([])

        self.thinking_items = []
        self.image_chunks = []
        self.mcp_app_views = []
        self._ui_tool_registry = {}
        self.show_thinking = False
        self._clear_uploaded_files()

    # -----------------------------------------------------------------
    # Thread persistence
    # -----------------------------------------------------------------

    @rx.event(background=True)
    async def persist_current_thread(
        self,
    ) -> AsyncGenerator[Any, Any]:
        """Persist the current thread to the database."""
        async with self:
            if self._thread.state == ThreadStatus.NEW:
                return

            user_session: UserSession = await self.get_state(UserSession)
            user_id = user_session.user.user_id if user_session.user else None
            if not user_id:
                return

            thread_copy = self._thread.model_copy()

        try:
            await self._thread_service.save_thread(thread_copy, user_id)
            logger.debug(
                "Persisted thread %s to DB",
                thread_copy.thread_id,
            )
        except Exception as e:
            logger.error(
                "Failed to persist thread %s: %s",
                thread_copy.thread_id,
                e,
            )
        yield

    # -----------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------

    async def _stop_loading_state(self) -> None:
        """Clear the loading state in ThreadListState."""
        threadlist_state: ThreadListState = await self.get_state(ThreadListState)
        threadlist_state.loading_thread_id = ""
