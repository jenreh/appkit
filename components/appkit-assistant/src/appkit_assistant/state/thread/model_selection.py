"""Model selection mixin for ThreadState.

Provides AI model listing, selection, and capability checks.
"""

import logging
from typing import Any

import reflex as rx

from appkit_assistant.backend.database.models import ThreadStatus
from appkit_assistant.backend.model_manager import ModelManager
from appkit_assistant.backend.schemas import AIModel

logger = logging.getLogger(__name__)


class ModelSelectionMixin:
    """Mixin for AI model selection and capability queries.

    Expects state vars: ``ai_models``, ``selected_model``.
    """

    ai_models: list[AIModel]
    selected_model: str

    @rx.var
    def get_selected_model(self) -> str:
        """Get the currently selected model ID."""
        return self.selected_model

    @rx.var
    def has_ai_models(self) -> bool:
        """Check if there are any chat models."""
        return len(self.ai_models) > 0

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
    def selected_model_supports_skills(self) -> bool:
        """Check if the currently selected model supports skills."""
        if not self.selected_model:
            return False
        model = ModelManager().get_model(self.selected_model)
        return model.supports_skills if model else False

    def _setup_models(self, user: Any) -> None:
        """Setup available AI models based on user roles."""
        model_manager = ModelManager()
        all_models = model_manager.get_all_models()

        user_roles = user.roles if user else []
        self.ai_models = [
            m
            for m in all_models
            if not m.requires_role or m.requires_role in user_roles
        ]

        # Ensure selected model is still available; keep current selection
        # when possible so refreshes don't disrupt the user's choice.
        available_ids = {m.id for m in self.ai_models}
        if self.selected_model not in available_ids:
            default = model_manager.get_default_model()
            if default in available_ids:
                self.selected_model = default
            elif self.ai_models:
                self.selected_model = self.ai_models[0].id
            else:
                logger.warning("No models available for user")
                self.selected_model = ""

    @rx.event
    def set_selected_model(self, model_id: str) -> list | None:
        """Set the selected model and deactivate unsupported tools.

        Automatically deactivates web search, MCP servers (tools), and file
        uploads if the selected model doesn't support them.
        """
        self.selected_model = model_id
        self._thread.ai_model = model_id

        model = ModelManager().get_model(model_id)
        if not model:
            return None

        if not model.supports_search:
            self.web_search_enabled = False

        if not model.supports_tools:
            self._restore_mcp_selection([])

        if not model.supports_attachments:
            self._clear_uploaded_files()

        if not model.supports_skills:
            self._restore_skill_selection([])

        # Reset modal tab to "tools" when model changes
        self.modal_active_tab = "tools"

        # Reload skills and persist model change for active threads
        events: list = [type(self).load_available_skills_for_user]
        if self._thread.state != ThreadStatus.NEW and self._current_user_id:
            events.append(type(self).persist_current_thread)
        return events
