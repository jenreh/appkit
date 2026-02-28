"""Skills selection mixin for ThreadState.

Handles loading, toggling, and applying skill selections.
"""

import logging

import reflex as rx

from appkit_assistant.backend.database.models import Skill
from appkit_assistant.backend.database.repositories import (
    ai_model_repo,
    skill_repo,
)
from appkit_assistant.backend.services.skill_service import (
    compute_api_key_hash,
)
from appkit_commons.database.session import get_asyncdb_session
from appkit_user.authentication.states import UserSession

logger = logging.getLogger(__name__)


class SkillsMixin:
    """Mixin for skill selection management.

    Expects state vars: ``selected_skills``,
    ``available_skills_for_selection``, ``temp_selected_skill_ids``,
    ``skill_selection_state``, ``modal_active_tab``, ``selected_model``.
    """

    @rx.event
    async def load_available_skills_for_user(self) -> None:
        """Load active skills filtered by user roles and selected model."""
        user_session = await self.get_state(UserSession)
        user = await user_session.authenticated_user
        user_roles: list[str] = user.roles if user else []

        async with get_asyncdb_session() as session:
            api_key_hash: str | None = None
            if self.selected_model:
                db_model = await ai_model_repo.find_by_model_id(
                    session, self.selected_model
                )
                if db_model and db_model.api_key:
                    api_key_hash = compute_api_key_hash(db_model.api_key)

            if api_key_hash:
                skills = await skill_repo.find_all_active_by_api_key_hash(
                    session, api_key_hash
                )
            else:
                skills = await skill_repo.find_all_active_ordered_by_name(session)

            filtered = [
                Skill(**s.model_dump())
                for s in skills
                if not s.required_role or s.required_role in user_roles
            ]
            self.available_skills_for_selection = filtered

    @rx.event
    def set_modal_active_tab(self, tab: str | list[str]) -> None:
        """Set the active tab in the tools modal."""
        if isinstance(tab, list):
            self.modal_active_tab = tab[0] if tab else "tools"
        else:
            self.modal_active_tab = tab

    @rx.event
    def toggle_skill_selection(self, openai_id: str, selected: bool) -> None:
        """Toggle skill selection in the modal."""
        self.skill_selection_state[openai_id] = selected
        if selected and openai_id not in self.temp_selected_skill_ids:
            self.temp_selected_skill_ids.append(openai_id)
        elif not selected and openai_id in self.temp_selected_skill_ids:
            self.temp_selected_skill_ids.remove(openai_id)

    @rx.event
    def apply_skill_selection(self) -> None:
        """Apply the temporary skill selection."""
        self.selected_skills = [
            skill
            for skill in self.available_skills_for_selection
            if skill.openai_id in self.temp_selected_skill_ids
        ]

    @rx.event
    def deselect_all_skills(self) -> None:
        """Deselect all skills in the modal."""
        self.skill_selection_state = {}
        self.temp_selected_skill_ids = []

    def _restore_skill_selection(self, skill_ids: list[str]) -> None:
        """Restore skill selection state from a list of openai IDs."""
        if not skill_ids:
            self.selected_skills = []
            self.temp_selected_skill_ids = []
            self.skill_selection_state = {}
            return

        self.selected_skills = [
            skill
            for skill in self.available_skills_for_selection
            if skill.openai_id in skill_ids
        ]
        self.temp_selected_skill_ids = list(skill_ids)
        self.skill_selection_state = dict.fromkeys(skill_ids, True)
