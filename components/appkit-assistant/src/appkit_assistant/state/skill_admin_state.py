"""State management for skill administration."""

import logging
from collections.abc import AsyncGenerator
from typing import Any

import reflex as rx

from appkit_assistant.backend.database.models import Skill
from appkit_assistant.backend.database.repositories import skill_repo
from appkit_assistant.backend.services.skill_service import (
    get_skill_service,
)
from appkit_commons.database.session import get_asyncdb_session

logger = logging.getLogger(__name__)


class SkillAdminState(rx.State):
    """State for the admin skill management page."""

    skills: list[Skill] = []
    loading: bool = False
    syncing: bool = False
    available_roles: list[dict[str, str]] = []
    role_labels: dict[str, str] = {}
    search_filter: str = ""

    @rx.var
    def filtered_skills(self) -> list[Skill]:
        """Return skills filtered by search_filter (contains in name)."""
        if not self.search_filter:
            return self.skills
        term = self.search_filter.lower()
        return [s for s in self.skills if term in s.name.lower()]

    # Upload / create modal state
    create_modal_open: bool = False
    uploading: bool = False

    def open_create_modal(self) -> AsyncGenerator[Any, Any]:
        """Open the create skill modal."""
        yield rx.clear_selected_files("skill_zip_upload")
        self.create_modal_open = True

    def close_create_modal(self) -> AsyncGenerator[Any, Any]:
        """Close the create skill modal."""
        yield rx.clear_selected_files("skill_zip_upload")
        self.create_modal_open = False

    def set_available_roles(
        self,
        available_roles: list[dict[str, str]],
        role_labels: dict[str, str],
    ) -> None:
        """Set the available roles for skill access control."""
        self.available_roles = available_roles
        self.role_labels = role_labels

    async def load_skills(self) -> None:
        """Load all skills from the database."""
        self.loading = True
        try:
            async with get_asyncdb_session() as session:
                items = await skill_repo.find_all_ordered_by_name(session)
                self.skills = [Skill(**s.model_dump()) for s in items]
            logger.debug("Loaded %d skills", len(self.skills))
        except Exception as e:
            logger.error("Failed to load skills: %s", e)
            raise
        finally:
            self.loading = False

    async def load_skills_with_toast(
        self,
    ) -> AsyncGenerator[Any, Any]:
        """Load skills and show error toast on failure."""
        try:
            await self.load_skills()
        except Exception:
            yield rx.toast.error(
                "Fehler beim Laden der Skills.",
                position="top-right",
            )

    async def sync_skills(self) -> AsyncGenerator[Any, Any]:
        """Sync all skills from the OpenAI API."""
        self.syncing = True
        yield
        try:
            service = get_skill_service()
            async with get_asyncdb_session() as session:
                count = await service.sync_all_skills(session)
            await self.load_skills()
            yield rx.toast.info(
                f"{count} Skills synchronisiert.",
                position="top-right",
            )
        except Exception as e:
            logger.error("Failed to sync skills: %s", e)
            yield rx.toast.error(
                "Fehler beim Synchronisieren der Skills.",
                position="top-right",
            )
        finally:
            self.syncing = False

    async def handle_upload(
        self, files: list[rx.UploadFile]
    ) -> AsyncGenerator[Any, Any]:
        """Handle zip file upload to create a new skill."""
        if not files:
            yield rx.toast.error(
                "Bitte eine ZIP-Datei auswählen.",
                position="top-right",
            )
            return

        upload_file = files[0]
        filename = upload_file.filename or "skill.zip"
        if not filename.endswith(".zip"):
            yield rx.toast.error(
                "Nur ZIP-Dateien sind erlaubt.",
                position="top-right",
            )
            return

        self.uploading = True
        yield

        try:
            file_bytes = await upload_file.read()
            service = get_skill_service()
            result = await service.create_skill(file_bytes, filename)

            # Sync the newly created skill into the DB
            async with get_asyncdb_session() as session:
                await service.sync_skill(session, result["id"])

            await self.load_skills()
            yield rx.toast.info(
                f"Skill '{result['name']}' wurde erstellt.",
                position="top-right",
            )
            # Close modal and clear files
            self.create_modal_open = False
            yield rx.clear_selected_files("skill_zip_upload")

        except Exception as e:
            logger.error("Failed to create skill: %s", e)
            yield rx.toast.error(
                "Fehler beim Erstellen des Skills.",
                position="top-right",
            )
        finally:
            self.uploading = False

    async def update_skill_role(
        self, skill_id: int, role: str
    ) -> AsyncGenerator[Any, Any]:
        """Update the required role for a skill."""
        target_role = None if role in ["None", ""] else role

        # Optimistic update
        original_skills = list(self.skills)
        for i, skill in enumerate(self.skills):
            if skill.id == skill_id:
                # Update attributes directly on the model instance copy
                updated_data = skill.model_dump()
                updated_data["required_role"] = target_role
                self.skills[i] = Skill(**updated_data)
                break
        yield

        try:
            async with get_asyncdb_session() as session:
                await skill_repo.update_required_role(session, skill_id, target_role)

            role_label = (
                self.role_labels.get(target_role, target_role)
                if target_role
                else "keine Rolle"
            )
            yield rx.toast.info(
                f"Rolle auf '{role_label}' geändert.",
                position="top-right",
            )
        except Exception as e:
            logger.error("Failed to update skill role: %s", e)
            self.skills = original_skills  # Revert
            yield rx.toast.error(
                "Fehler beim Ändern der Rolle.",
                position="top-right",
            )

    async def delete_skill(self, skill_id: int) -> AsyncGenerator[Any, Any]:
        """Delete a skill from OpenAI and the database."""
        try:
            service = get_skill_service()
            async with get_asyncdb_session() as session:
                name = await service.delete_skill_full(session, skill_id)
            await self.load_skills()
            yield rx.toast.info(
                f"Skill '{name}' wurde gelöscht.",
                position="top-right",
            )
        except Exception as e:
            logger.error("Failed to delete skill %d: %s", skill_id, e)
            yield rx.toast.error(
                "Fehler beim Löschen des Skills.",
                position="top-right",
            )

    async def toggle_skill_active(
        self, skill_id: int, active: bool
    ) -> AsyncGenerator[Any, Any]:
        """Toggle the active status of a skill (optimistic)."""
        original = list(self.skills)
        for i, s in enumerate(self.skills):
            if s.id == skill_id:
                self.skills[i].active = active
                break
        yield

        try:
            async with get_asyncdb_session() as session:
                skill = await skill_repo.find_by_id(session, skill_id)
                if not skill:
                    self.skills = original
                    yield rx.toast.error(
                        "Skill nicht gefunden.",
                        position="top-right",
                    )
                    return
                skill.active = active
                await skill_repo.save(session, skill)

            status = "aktiviert" if active else "deaktiviert"
            yield rx.toast.info(
                f"Skill wurde {status}.",
                position="top-right",
            )
        except Exception as e:
            self.skills = original
            logger.error("Failed to toggle skill %d: %s", skill_id, e)
            yield rx.toast.error(
                "Fehler beim Ändern des Skill-Status.",
                position="top-right",
            )

    async def update_skill_role(
        self, skill_id: int, role: str
    ) -> AsyncGenerator[Any, Any]:
        """Update the required role for a skill."""
        try:
            async with get_asyncdb_session() as session:
                skill = await skill_repo.find_by_id(session, skill_id)
                if not skill:
                    yield rx.toast.error(
                        "Skill nicht gefunden.",
                        position="top-right",
                    )
                    return
                skill.required_role = role or None
                await skill_repo.save(session, skill)
            await self.load_skills()
            yield rx.toast.info(
                "Rolle aktualisiert.",
                position="top-right",
            )
        except Exception as e:
            logger.error("Failed to update skill role %d: %s", skill_id, e)
            yield rx.toast.error(
                "Fehler beim Aktualisieren der Rolle.",
                position="top-right",
            )

    @rx.var
    def skill_count(self) -> int:
        """Number of skills."""
        return len(self.skills)

    @rx.var
    def has_skills(self) -> bool:
        """Whether any skills exist."""
        return len(self.skills) > 0
