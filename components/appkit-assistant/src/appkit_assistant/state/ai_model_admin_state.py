"""State management for AI model configuration (admin)."""

import logging
from collections.abc import AsyncGenerator
from typing import Any

import reflex as rx

from appkit_assistant.backend.ai_model_registry import ai_model_registry
from appkit_assistant.backend.database.models import AssistantAIModel
from appkit_assistant.backend.database.repositories import ai_model_repo
from appkit_commons.database.session import get_asyncdb_session

logger = logging.getLogger(__name__)


class AIModelAdminState(rx.State):
    """State for managing AI models in the admin UI."""

    models: list[AssistantAIModel] = []
    current_model: AssistantAIModel | None = None
    loading: bool = False
    search_filter: str = ""
    updating_active_model_id: int | None = None
    updating_role_model_id: int | None = None
    available_roles: list[dict[str, str]] = []
    role_labels: dict[str, str] = {}
    add_modal_open: bool = False
    edit_modal_open: bool = False

    def set_search_filter(self, value: str) -> None:
        """Update the search filter."""
        self.search_filter = value

    @rx.var
    def filtered_models(self) -> list[AssistantAIModel]:
        """Return models filtered by search text."""
        if not self.search_filter:
            return self.models
        search = self.search_filter.lower()
        return [
            m
            for m in self.models
            if search in m.text.lower() or search in m.model_id.lower()
        ]

    @rx.var
    def model_count(self) -> int:
        """Return total number of AI models."""
        return len(self.models)

    @rx.var
    def has_models(self) -> bool:
        """Return whether any models exist."""
        return len(self.models) > 0

    def set_available_roles(
        self,
        available_roles: list[dict[str, str]],
        role_labels: dict[str, str],
    ) -> None:
        """Initialise role data from the caller."""
        self.available_roles = available_roles
        self.role_labels = role_labels

    def open_add_modal(self) -> None:
        """Open the add model modal."""
        self.add_modal_open = True

    def close_add_modal(self) -> None:
        """Close the add model modal."""
        self.add_modal_open = False

    def open_edit_modal(self) -> None:
        """Open the edit model modal."""
        self.edit_modal_open = True

    def close_edit_modal(self) -> None:
        """Close the edit model modal."""
        self.edit_modal_open = False

    async def load_models(self) -> None:
        """Load all AI models from DB."""
        self.loading = True
        try:
            async with get_asyncdb_session() as session:
                db_models = await ai_model_repo.find_all_ordered_by_text(session)
                self.models = [AssistantAIModel(**m.model_dump()) for m in db_models]
            logger.debug("Loaded %d AI models", len(self.models))
        except Exception as e:
            logger.error("Failed to load AI models: %s", e)
            raise
        finally:
            self.loading = False

    async def load_models_with_toast(self) -> AsyncGenerator[Any, Any]:
        """Load models, show error toast on failure."""
        try:
            await self.load_models()
        except Exception:
            yield rx.toast.error(
                "Fehler beim Laden der KI-Modelle.",
                position="top-right",
            )

    async def get_model(self, model_id: int) -> None:
        """Fetch a single model for the edit dialog."""
        try:
            async with get_asyncdb_session() as session:
                rec = await ai_model_repo.find_by_id(session, model_id)
                self.current_model = (
                    AssistantAIModel(**rec.model_dump()) if rec else None
                )
        except Exception as e:
            logger.error("Failed to get AI model %d: %s", model_id, e)

    async def add_model(self, form_data: dict[str, Any]) -> AsyncGenerator[Any, Any]:
        """Create a new AI model."""
        self.loading = True
        yield
        try:
            entity = AssistantAIModel(
                model_id=form_data["model_id"].strip(),
                text=form_data["text"].strip(),
                icon=(form_data.get("icon") or "codesandbox").strip() or "codesandbox",
                model=form_data.get("model", "").strip()
                or form_data["model_id"].strip(),
                processor_type=form_data["processor_type"],
                stream=form_data.get("stream") in (True, "true", "on", "1"),
                temperature=float(form_data.get("temperature") or 0.05),
                supports_tools=form_data.get("supports_tools")
                in (True, "true", "on", "1"),
                supports_attachments=form_data.get("supports_attachments")
                in (True, "true", "on", "1"),
                supports_search=form_data.get("supports_search")
                in (True, "true", "on", "1"),
                supports_skills=form_data.get("supports_skills")
                in (True, "true", "on", "1"),
                active=True,
                requires_role=form_data.get("requires_role") or None,
                api_key=form_data.get("api_key") or None,
                base_url=form_data.get("base_url") or None,
                on_azure=form_data.get("on_azure") in (True, "true", "on", "1"),
                enable_tracking=form_data.get("enable_tracking")
                not in (False, "false", "off", "0"),
            )
            async with get_asyncdb_session() as session:
                saved = await ai_model_repo.save(session, entity)
                saved_text = saved.text
            self.add_modal_open = False
            await self.load_models()
            await ai_model_registry.reload()
            yield rx.toast.info(
                f"KI-Modell {saved_text} wurde hinzugefügt.",
                position="top-right",
            )
            logger.debug("Added AI model: %s", saved_text)
        except ValueError as e:
            logger.error("Invalid form data for AI model: %s", e)
            yield rx.toast.error(str(e), position="top-right")
        except Exception as e:
            logger.error("Failed to add AI model: %s", e)
            yield rx.toast.error(
                "Fehler beim Hinzufügen des KI-Modells.",
                position="top-right",
            )
        finally:
            self.loading = False

    async def modify_model(self, form_data: dict[str, Any]) -> AsyncGenerator[Any, Any]:
        """Update an existing AI model."""
        if not self.current_model:
            yield rx.toast.error("Kein Modell ausgewählt.", position="top-right")
            return

        self.loading = True
        yield
        try:
            updated_text = ""
            async with get_asyncdb_session() as session:
                existing = await ai_model_repo.find_by_id(
                    session, self.current_model.id
                )
                if existing:
                    existing.model_id = form_data["model_id"].strip()
                    existing.text = form_data["text"].strip()
                    existing.icon = (
                        form_data.get("icon") or "codesandbox"
                    ).strip() or "codesandbox"
                    existing.model = (
                        form_data.get("model", "").strip()
                        or form_data["model_id"].strip()
                    )
                    existing.processor_type = form_data["processor_type"]
                    existing.stream = form_data.get("stream") in (
                        True,
                        "true",
                        "on",
                        "1",
                    )
                    existing.temperature = float(form_data.get("temperature") or 0.05)
                    existing.supports_tools = form_data.get("supports_tools") in (
                        True,
                        "true",
                        "on",
                        "1",
                    )
                    existing.supports_attachments = form_data.get(
                        "supports_attachments"
                    ) in (True, "true", "on", "1")
                    existing.supports_search = form_data.get("supports_search") in (
                        True,
                        "true",
                        "on",
                        "1",
                    )
                    existing.supports_skills = form_data.get("supports_skills") in (
                        True,
                        "true",
                        "on",
                        "1",
                    )
                    existing.requires_role = form_data.get("requires_role") or None
                    # Always write api_key (empty = clear the stored key)
                    new_key = form_data.get("api_key") or ""
                    existing.api_key = new_key.strip() or None
                    existing.base_url = form_data.get("base_url") or None
                    existing.on_azure = form_data.get("on_azure") in (
                        True,
                        "true",
                        "on",
                        "1",
                    )
                    existing.enable_tracking = form_data.get("enable_tracking") not in (
                        False,
                        "false",
                        "off",
                        "0",
                    )
                    saved = await ai_model_repo.save(session, existing)
                    updated_text = saved.text
            if updated_text:
                self.edit_modal_open = False
                await self.load_models()
                await ai_model_registry.reload()
                yield rx.toast.info(
                    f"KI-Modell {updated_text} wurde aktualisiert.",
                    position="top-right",
                )
                logger.debug("Updated AI model: %s", updated_text)
            else:
                yield rx.toast.error(
                    "KI-Modell konnte nicht gefunden werden.",
                    position="top-right",
                )
        except ValueError as e:
            logger.error("Invalid form data for AI model: %s", e)
            yield rx.toast.error(str(e), position="top-right")
        except Exception as e:
            logger.error("Failed to update AI model: %s", e)
            yield rx.toast.error(
                "Fehler beim Aktualisieren des KI-Modells.",
                position="top-right",
            )
        finally:
            self.loading = False

    async def delete_model(self, model_id: int) -> AsyncGenerator[Any, Any]:
        """Delete an AI model."""
        try:
            async with get_asyncdb_session() as session:
                rec = await ai_model_repo.find_by_id(session, model_id)
                if not rec:
                    yield rx.toast.error(
                        "KI-Modell nicht gefunden.",
                        position="top-right",
                    )
                    return
                rec_text = rec.text
                success = await ai_model_repo.delete_by_id(session, model_id)
            if success:
                await self.load_models()
                await ai_model_registry.reload()
                yield rx.toast.info(
                    f"KI-Modell {rec_text} wurde gelöscht.",
                    position="top-right",
                )
                logger.debug("Deleted AI model: %s", rec_text)
            else:
                yield rx.toast.error(
                    "KI-Modell konnte nicht gelöscht werden.",
                    position="top-right",
                )
        except Exception as e:
            logger.error("Failed to delete AI model %d: %s", model_id, e)
            yield rx.toast.error(
                "Fehler beim Löschen des KI-Modells.",
                position="top-right",
            )

    async def toggle_model_active(
        self, model_id: int, active: bool
    ) -> AsyncGenerator[Any, Any]:
        """Toggle the active status of a model (optimistic update)."""
        self.updating_active_model_id = model_id
        original = list(self.models)
        for i, m in enumerate(self.models):
            if m.id == model_id:
                self.models[i] = m.model_copy(update={"active": active})
                break
        self.models = list(self.models)
        yield
        try:
            async with get_asyncdb_session() as session:
                rec = await ai_model_repo.update_active(session, model_id, active)
                if not rec:
                    self.models = original
                    self.updating_active_model_id = None
                    yield rx.toast.error(
                        "KI-Modell nicht gefunden.",
                        position="top-right",
                    )
                    return
                rec_text = rec.text
            await ai_model_registry.reload()
            status = "aktiviert" if active else "deaktiviert"
            self.updating_active_model_id = None
            yield rx.toast.info(
                f"KI-Modell {rec_text} wurde {status}.",
                position="top-right",
            )
            logger.debug("Toggled AI model %s active=%s", rec_text, active)
        except Exception as e:
            self.models = original
            self.updating_active_model_id = None
            logger.error("Failed to toggle AI model %d: %s", model_id, e)
            yield rx.toast.error(
                "Fehler beim Ändern des Modell-Status.",
                position="top-right",
            )

    async def update_model_role(
        self, model_id: int, new_role: str | None
    ) -> AsyncGenerator[Any, Any]:
        """Update required_role for a model (optimistic update)."""
        self.updating_role_model_id = model_id
        original = [m.model_copy() for m in self.models]
        for m in self.models:
            if m.id == model_id:
                m.requires_role = new_role
        self.models = list(self.models)
        yield
        try:
            async with get_asyncdb_session() as session:
                rec = await ai_model_repo.update_role(session, model_id, new_role)
                if not rec:
                    self.models = original
                    self.updating_role_model_id = None
                    yield rx.toast.error(
                        "KI-Modell nicht gefunden.",
                        position="top-right",
                    )
                    return
                rec_text = rec.text
            await ai_model_registry.reload()
            self.updating_role_model_id = None
            yield rx.toast.info(
                f"Rolle für {rec_text} aktualisiert.",
                position="top-right",
            )
        except Exception as e:
            self.models = original
            self.updating_role_model_id = None
            logger.error("Failed to update role for AI model %d: %s", model_id, e)
            yield rx.toast.error(
                "Fehler beim Ändern der Rolle.",
                position="top-right",
            )
