"""State management for user skill selections."""

import logging
from collections.abc import AsyncGenerator
from typing import Any

import reflex as rx

from appkit_assistant.backend.database.repositories import (
    skill_repo,
    user_skill_repo,
)
from appkit_commons.database.session import get_asyncdb_session
from appkit_user.authentication.states import UserSession

logger = logging.getLogger(__name__)


class SkillState(rx.State):
    """State for user-scoped skill enable/disable preferences."""

    available_skills: list[dict[str, Any]] = []
    loading: bool = False

    async def load_user_skills(self) -> AsyncGenerator[Any, Any]:
        """Load active skills with the user's enable/disable state."""
        self.loading = True
        yield
        try:
            session_state = await self.get_state(UserSession)
            user_id = session_state.user_id
            if not user_id:
                self.available_skills = []
                return

            async with get_asyncdb_session() as session:
                active_skills = await skill_repo.find_all_active_ordered_by_name(
                    session
                )
                selections = await user_skill_repo.find_by_user_id(session, user_id)

            enabled_map: dict[str, bool] = {
                sel.skill_openai_id: sel.enabled for sel in selections
            }

            self.available_skills = [
                {
                    "openai_id": s.openai_id,
                    "name": s.name,
                    "description": s.description or "",
                    "enabled": enabled_map.get(s.openai_id, False),
                }
                for s in active_skills
            ]
            logger.debug(
                "Loaded %d skills for user %d",
                len(self.available_skills),
                user_id,
            )
        except Exception as e:
            logger.error("Failed to load user skills: %s", e)
            yield rx.toast.error(
                "Fehler beim Laden der Skills.",
                position="top-right",
            )
        finally:
            self.loading = False

    async def toggle_skill_enabled(
        self, openai_id: str, enabled: bool
    ) -> AsyncGenerator[Any, Any]:
        """Toggle the enabled state of a skill for the current user."""
        # Optimistic update
        for i, skill in enumerate(self.available_skills):
            if skill["openai_id"] == openai_id:
                self.available_skills[i]["enabled"] = enabled
                break
        yield

        try:
            session_state = await self.get_state(UserSession)
            user_id = session_state.user_id
            if not user_id:
                return

            async with get_asyncdb_session() as session:
                await user_skill_repo.upsert(session, user_id, openai_id, enabled)

            status = "aktiviert" if enabled else "deaktiviert"
            yield rx.toast.info(
                f"Skill {status}.",
                position="top-right",
            )
        except Exception as e:
            logger.error("Failed to toggle skill %s: %s", openai_id, e)
            # Revert optimistic update
            for i, skill in enumerate(self.available_skills):
                if skill["openai_id"] == openai_id:
                    self.available_skills[i]["enabled"] = not enabled
                    break
            yield rx.toast.error(
                "Fehler beim Ändern des Skill-Status.",
                position="top-right",
            )

    @rx.var
    def has_skills(self) -> bool:
        """Whether any skills are available."""
        return len(self.available_skills) > 0

    @rx.var
    def enabled_skill_ids(self) -> list[str]:
        """Return a list of enabled skill OpenAI IDs."""
        return [s["openai_id"] for s in self.available_skills if s.get("enabled")]
