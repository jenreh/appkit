"""State management for image generator models (admin)."""

import json
import logging
from collections.abc import AsyncGenerator
from typing import Any

import reflex as rx

from appkit_commons.database.session import get_asyncdb_session
from appkit_imagecreator.backend.generator_registry import (
    generator_registry,
)
from appkit_imagecreator.backend.generator_repository import (
    generator_model_repo,
)
from appkit_imagecreator.backend.models import ImageGeneratorModel

logger = logging.getLogger(__name__)


class ImageGeneratorAdminState(rx.State):
    """State for managing image generator models in the admin UI."""

    generators: list[ImageGeneratorModel] = []
    current_generator: ImageGeneratorModel | None = None
    loading: bool = False
    search_filter: str = ""
    updating_active_generator_id: int | None = None
    updating_role_generator_id: int | None = None
    available_roles: list[dict[str, str]] = []
    role_labels: dict[str, str] = {}
    add_modal_open: bool = False
    edit_modal_open: bool = False

    def set_search_filter(self, value: str) -> None:
        """Update the search filter."""
        self.search_filter = value

    @rx.var
    def filtered_generators(self) -> list[ImageGeneratorModel]:
        """Return generators filtered by search text."""
        if not self.search_filter:
            return self.generators
        search = self.search_filter.lower()
        return [
            g
            for g in self.generators
            if search in g.label.lower() or search in g.model_id.lower()
        ]

    def set_available_roles(
        self,
        available_roles: list[dict[str, str]],
        role_labels: dict[str, str],
    ) -> None:
        """Initialize role data from caller."""
        self.available_roles = available_roles
        self.role_labels = role_labels

    def open_add_modal(self) -> None:
        """Open the add generator modal."""
        self.add_modal_open = True

    def close_add_modal(self) -> None:
        """Close the add generator modal."""
        self.add_modal_open = False

    def open_edit_modal(self) -> None:
        """Open the edit generator modal."""
        self.edit_modal_open = True

    def close_edit_modal(self) -> None:
        """Close the edit generator modal."""
        self.edit_modal_open = False

    async def load_generators(self) -> None:
        """Load all generator models from DB."""
        self.loading = True
        try:
            async with get_asyncdb_session() as session:
                models = await generator_model_repo.find_all_ordered_by_name(session)
                self.generators = [
                    ImageGeneratorModel(**m.model_dump()) for m in models
                ]
            logger.debug(
                "Loaded %d image generator models",
                len(self.generators),
            )
        except Exception as e:
            logger.error("Failed to load image generator models: %s", e)
            raise
        finally:
            self.loading = False

    async def load_generators_with_toast(
        self,
    ) -> AsyncGenerator[Any, Any]:
        """Load generators, show toast on error."""
        try:
            await self.load_generators()
        except Exception:
            yield rx.toast.error(
                "Fehler beim Laden der Bildgeneratoren.",
                position="top-right",
            )

    async def get_generator(self, generator_id: int) -> None:
        """Fetch a single generator for the edit dialog."""
        try:
            async with get_asyncdb_session() as session:
                gen = await generator_model_repo.find_by_id(session, generator_id)
                if gen:
                    self.current_generator = ImageGeneratorModel(**gen.model_dump())
                else:
                    self.current_generator = None
            if not self.current_generator:
                logger.warning(
                    "Image generator with ID %d not found",
                    generator_id,
                )
        except Exception as e:
            logger.error(
                "Failed to get image generator %d: %s",
                generator_id,
                e,
            )

    async def add_generator(
        self, form_data: dict[str, Any]
    ) -> AsyncGenerator[Any, Any]:
        """Create a new generator model."""
        try:
            entity = ImageGeneratorModel(
                model_id=form_data["model_id"],
                model=form_data.get("model") or form_data["model_id"],
                label=form_data["label"],
                processor_type=form_data["processor_type"],
                api_key=form_data.get("api_key") or "",
                base_url=form_data.get("base_url") or None,
                extra_config=self._parse_extra_config(form_data),
                required_role=form_data.get("required_role") or None,
                active=True,
            )
            async with get_asyncdb_session() as session:
                saved = await generator_model_repo.save(session, entity)
                saved_label = saved.label
            self.add_modal_open = False
            await self.load_generators()
            await generator_registry.reload()
            yield rx.toast.info(
                f"Bildgenerator {saved_label} wurde hinzugefügt.",
                position="top-right",
            )
            logger.debug("Added image generator: %s", saved_label)
        except ValueError as e:
            logger.error("Invalid form data for image generator: %s", e)
            yield rx.toast.error(str(e), position="top-right")
        except Exception as e:
            logger.error("Failed to add image generator: %s", e)
            yield rx.toast.error(
                "Fehler beim Hinzufügen des Bildgenerators.",
                position="top-right",
            )

    async def modify_generator(
        self, form_data: dict[str, Any]
    ) -> AsyncGenerator[Any, Any]:
        """Update an existing generator model."""
        if not self.current_generator:
            yield rx.toast.error("Kein Generator ausgewählt.", position="top-right")
            return
        try:
            updated_label = ""
            async with get_asyncdb_session() as session:
                existing = await generator_model_repo.find_by_id(
                    session, self.current_generator.id
                )
                if existing:
                    existing.model_id = form_data["model_id"]
                    existing.model = form_data.get("model") or form_data["model_id"]
                    existing.label = form_data["label"]
                    existing.processor_type = form_data["processor_type"]
                    # Only update api_key if provided (not empty)
                    new_key = form_data.get("api_key", "").strip()
                    if new_key:
                        existing.api_key = new_key
                    existing.base_url = form_data.get("base_url") or None
                    existing.extra_config = self._parse_extra_config(form_data)
                    existing.required_role = form_data.get("required_role") or None
                    saved = await generator_model_repo.save(session, existing)
                    updated_label = saved.label
            if updated_label:
                self.edit_modal_open = False
                await self.load_generators()
                await generator_registry.reload()
                yield rx.toast.info(
                    f"Bildgenerator {updated_label} wurde aktualisiert.",
                    position="top-right",
                )
                logger.debug("Updated image generator: %s", updated_label)
            else:
                yield rx.toast.error(
                    "Bildgenerator konnte nicht gefunden werden.",
                    position="top-right",
                )
        except ValueError as e:
            logger.error("Invalid form data for image generator: %s", e)
            yield rx.toast.error(str(e), position="top-right")
        except Exception as e:
            logger.error("Failed to update image generator: %s", e)
            yield rx.toast.error(
                "Fehler beim Aktualisieren des Bildgenerators.",
                position="top-right",
            )

    async def delete_generator(self, generator_id: int) -> AsyncGenerator[Any, Any]:
        """Delete a generator model."""
        try:
            async with get_asyncdb_session() as session:
                gen = await generator_model_repo.find_by_id(session, generator_id)
                if not gen:
                    yield rx.toast.error(
                        "Bildgenerator nicht gefunden.",
                        position="top-right",
                    )
                    return
                gen_label = gen.label
                success = await generator_model_repo.delete_by_id(session, generator_id)
            if success:
                await self.load_generators()
                await generator_registry.reload()
                yield rx.toast.info(
                    f"Bildgenerator {gen_label} wurde gelöscht.",
                    position="top-right",
                )
                logger.debug("Deleted image generator: %s", gen_label)
            else:
                yield rx.toast.error(
                    "Bildgenerator konnte nicht gelöscht werden.",
                    position="top-right",
                )
        except Exception as e:
            logger.error(
                "Failed to delete image generator %d: %s",
                generator_id,
                e,
            )
            yield rx.toast.error(
                "Fehler beim Löschen des Bildgenerators.",
                position="top-right",
            )

    async def toggle_generator_active(
        self, generator_id: int, active: bool
    ) -> AsyncGenerator[Any, Any]:
        """Toggle the active status of a generator (optimistic)."""
        self.updating_active_generator_id = generator_id
        # Optimistic update
        original_generators = list(self.generators)
        for i, g in enumerate(self.generators):
            if g.id == generator_id:
                new_gen = g.model_copy(update={"active": active})
                self.generators[i] = new_gen
                break
        self.generators = list(self.generators)
        yield
        try:
            async with get_asyncdb_session() as session:
                gen = await generator_model_repo.find_by_id(session, generator_id)
                if not gen:
                    self.generators = original_generators
                    self.updating_active_generator_id = None
                    yield rx.toast.error(
                        "Bildgenerator nicht gefunden.",
                        position="top-right",
                    )
                    return
                gen.active = active
                await generator_model_repo.save(session, gen)
                gen_label = gen.label
            await generator_registry.reload()
            status_text = "aktiviert" if active else "deaktiviert"
            self.updating_active_generator_id = None
            yield rx.toast.info(
                f"Bildgenerator {gen_label} wurde {status_text}.",
                position="top-right",
            )
            logger.debug("Toggled generator %s active=%s", gen_label, active)
        except Exception as e:
            self.generators = original_generators
            self.updating_active_generator_id = None
            logger.error(
                "Failed to toggle generator %d: %s",
                generator_id,
                e,
            )
            yield rx.toast.error(
                "Fehler beim Ändern des Generator-Status.",
                position="top-right",
            )

    async def update_generator_role(
        self, generator_id: int, new_role: str | None
    ) -> AsyncGenerator[Any, Any]:
        """Update the required role for a generator (optimistic)."""
        self.updating_role_generator_id = generator_id
        yield
        original_generators = []
        for g in self.generators:
            original_generators.append(g.model_copy())
            if g.id == generator_id:
                g.required_role = new_role
        self.generators = list(self.generators)
        yield
        try:
            async with get_asyncdb_session() as session:
                gen = await generator_model_repo.find_by_id(session, generator_id)
                if not gen:
                    self.generators = original_generators
                    self.updating_role_generator_id = None
                    yield rx.toast.error(
                        "Bildgenerator nicht gefunden.",
                        position="top-right",
                    )
                    return
                gen.required_role = new_role
                await generator_model_repo.save(session, gen)
                gen_label = gen.label
            self.updating_role_generator_id = None
            yield rx.toast.info(
                f"Rolle für {gen_label} aktualisiert.",
                position="top-right",
            )
        except Exception as e:
            self.generators = original_generators
            self.updating_role_generator_id = None
            logger.error(
                "Failed to update role for generator %d: %s",
                generator_id,
                e,
            )
            yield rx.toast.error(
                "Fehler beim Ändern der Rolle.",
                position="top-right",
            )

    @rx.var
    def generator_count(self) -> int:
        """Return total number of generators."""
        return len(self.generators)

    @rx.var
    def has_generators(self) -> bool:
        """Return whether any generators exist."""
        return len(self.generators) > 0

    @staticmethod
    def _parse_extra_config(
        form_data: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Parse extra_config JSON from form data."""
        raw = form_data.get("extra_config", "").strip()
        if not raw:
            return None
        try:
            parsed = json.loads(raw)
            if not isinstance(parsed, dict):
                raise ValueError("Extra-Konfiguration muss ein JSON-Objekt sein.")
            return parsed
        except json.JSONDecodeError as e:
            raise ValueError(
                "Ungültiges JSON-Format in der Extra-Konfiguration."
            ) from e
