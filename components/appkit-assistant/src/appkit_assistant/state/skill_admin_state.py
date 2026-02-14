"""State management for skill administration."""

import logging
from collections.abc import AsyncGenerator
from typing import Any

import reflex as rx

from appkit_assistant.backend.database.models import Skill
from appkit_assistant.backend.database.repositories import skill_repo
from appkit_assistant.backend.services.skill_service import get_skill_service
from appkit_commons.database.session import get_asyncdb_session

logger = logging.getLogger(__name__)


class SkillAdminState(rx.State):
    """State for the admin skill management page."""

    # Data State
    skills: list[Skill] = []
    available_roles: list[dict[str, str]] = []
    role_labels: dict[str, str] = {}

    # UI State
    loading: bool = False
    syncing: bool = False
    search_filter: str = ""
    create_modal_open: bool = False
    uploading: bool = False

    # Helpers
    updating_role_skill_id: int | None = None
    updating_active_skill_id: int | None = None

    @rx.event
    def set_search_filter(self, value: str) -> None:
        """Set the search filter value."""
        self.search_filter = value

    @rx.var
    def filtered_skills(self) -> list[Skill]:
        """Return skills filtered by search_filter (contains in name)."""
        if not self.search_filter:
            return self.skills
        term = self.search_filter.lower()
        return [s for s in self.skills if term in s.name.lower()]

    @rx.var
    def skill_count(self) -> int:
        """Number of skills."""
        return len(self.skills)

    @rx.var
    def has_skills(self) -> bool:
        """Whether any skills exist."""
        return len(self.skills) > 0

    async def open_create_modal(self) -> AsyncGenerator[Any, Any]:
        """Open the create skill modal."""
        yield rx.clear_selected_files("skill_zip_upload")
        self.create_modal_open = True

    async def close_create_modal(self) -> AsyncGenerator[Any, Any]:
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
                # Convert DB models to Pydantic models for State
                self.skills = [Skill(**s.model_dump()) for s in items]
            logger.debug("Loaded %d skills", len(self.skills))
        except Exception as e:
            logger.error("Failed to load skills: %s", e)
            raise
        finally:
            self.loading = False

    async def load_skills_with_toast(self) -> AsyncGenerator[Any, Any]:
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

    def _validate_upload(self, files: list[rx.UploadFile]) -> tuple[bool, str | None]:
        """Validate the uploaded file."""
        if not files:
            return False, "Bitte eine ZIP-Datei auswählen."

        filename = files[0].filename or "skill.zip"
        if not filename.endswith(".zip"):
            return False, "Nur ZIP-Dateien sind erlaubt."

        return True, None

    async def handle_upload(
        self, files: list[rx.UploadFile]
    ) -> AsyncGenerator[Any, Any]:
        """Handle zip file upload to create a new skill."""
        is_valid, error = self._validate_upload(files)
        if not is_valid:
            yield rx.toast.error(error, position="top-right")
            return

        upload_file = files[0]
        filename = upload_file.filename or "skill.zip"

        self.uploading = True
        yield

        try:
            file_bytes = await upload_file.read()
            service = get_skill_service()

            async with get_asyncdb_session() as session:
                result = await service.create_or_update_skill(
                    session, file_bytes, filename
                )
                # Sync the newly created skill into the DB
                await service.sync_skill(session, result["id"])

            await self.load_skills()
            yield rx.toast.info(
                f"Skill '{result['name']}' wurde erstellt.",
                position="top-right",
            )
            # Close modal and cleanup
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
        self.updating_role_skill_id = skill_id
        yield

        try:
            async with get_asyncdb_session() as session:
                await skill_repo.update_required_role(session, skill_id, target_role)

            await self.load_skills()

            role_label = self.role_labels.get(
                target_role or "", target_role or "nicht eingeschränkt"
            )
            yield rx.toast.info(
                f"Rolle auf '{role_label}' geändert.",
                position="top-right",
            )
        except Exception as e:
            logger.error("Failed to update skill role: %s", e)
            yield rx.toast.error(
                "Fehler beim Ändern der Rolle.",
                position="top-right",
            )
        finally:
            self.updating_role_skill_id = None

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
        self.updating_active_skill_id = skill_id
        original_skills = self.skills
        yield

        # Optimistic update: create new list with updated item
        # Using model_copy (Pydantic V2 / SQLModel)
        self.skills = [
            s.model_copy(update={"active": active}) if s.id == skill_id else s
            for s in self.skills
        ]
        yield

        try:
            async with get_asyncdb_session() as session:
                skill = await skill_repo.find_by_id(session, skill_id)
                if not skill:
                    # Revert if not found
                    self.skills = original_skills
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
            # Revert on error
            self.skills = original_skills
            logger.error("Failed to toggle skill %d: %s", skill_id, e)
            yield rx.toast.error(
                "Fehler beim Ändern des Skill-Status.",
                position="top-right",
            )
        finally:
            self.updating_active_skill_id = None
