import logging
from collections.abc import AsyncGenerator
from typing import Any, Final

import reflex as rx
from reflex.state import State

from appkit_assistant.backend.database.repositories import user_prompt_repo
from appkit_assistant.backend.services.user_prompt_service import validate_handle
from appkit_assistant.state.thread_state import ThreadState
from appkit_commons.database.session import get_asyncdb_session
from appkit_user.authentication.states import UserSession

logger = logging.getLogger(__name__)

MAX_PROMPT_LENGTH: Final[int] = 20000
MAX_DESCRIPTION_LENGTH: Final[int] = 100
MAX_HANDLE_LENGTH: Final[int] = 50


class UserPromptState(State):
    """State for User Prompt Management (Command Palette Modal)."""

    # UI State
    is_loading: bool = False

    # Edit modal state (for command palette quick-edit)
    modal_open: bool = False
    modal_is_new: bool = False
    modal_handle: str = ""  # Handle being edited (display only)
    modal_original_handle: str = ""  # Original handle when editing (for rename)
    modal_description: str = ""
    modal_prompt: str = ""
    modal_is_shared: bool = False
    modal_char_count: int = 0
    modal_error: str = ""
    modal_textarea_key: int = 0

    # Modal validation errors
    modal_handle_error: str = ""
    modal_description_error: str = ""
    modal_prompt_error: str = ""

    # Modal versioning
    modal_versions: list[dict[str, str | int]] = []
    modal_prompt_map: dict[str, str] = {}  # version_id_str -> prompt_text
    modal_selected_version_id: int = 0

    @rx.var
    def modal_title(self) -> str:
        """Return modal title based on mode."""
        return "Neuer Prompt" if self.modal_is_new else "Prompt bearbeiten"

    @rx.var
    def modal_save_button_text(self) -> str:
        """Return save button text based on modal mode."""
        return "Erstellen" if self.modal_is_new else "Neue Version speichern"

    @rx.var
    def has_modal_validation_errors(self) -> bool:
        """Check if the modal form has any validation errors."""
        return bool(
            self.modal_handle_error
            or self.modal_description_error
            or self.modal_prompt_error
        )

    # -------------------------------------------------------------------------
    # Modal methods (for command palette quick-edit)
    # -------------------------------------------------------------------------

    def _reset_modal(self) -> None:
        """Reset modal state."""
        self.modal_open = False
        self.modal_is_new = False
        self.modal_handle = ""
        self.modal_original_handle = ""
        self.modal_description = ""
        self.modal_prompt = ""
        self.modal_is_shared = False
        self.modal_char_count = 0
        self.modal_error = ""
        self.modal_textarea_key += 1
        self.modal_versions = []
        self.modal_prompt_map = {}
        self.modal_selected_version_id = 0
        # Clear validation errors
        self.modal_handle_error = ""
        self.modal_description_error = ""
        self.modal_prompt_error = ""

    @rx.var
    def modal_selected_version_str(self) -> str:
        """Return modal selected version ID as string for select component."""
        if self.modal_selected_version_id:
            return str(self.modal_selected_version_id)
        return ""

    def set_modal_selected_version_id(self, value: str | None) -> None:
        """Handle modal version selection change."""
        if not value:
            return

        self.modal_selected_version_id = int(value)
        if value in self.modal_prompt_map:
            self.modal_prompt = self.modal_prompt_map[value]
            self.modal_char_count = len(self.modal_prompt)
            self.modal_textarea_key += 1

    @rx.event
    async def open_edit_modal(self, handle: str) -> None:
        """Open modal to edit an existing prompt."""
        self._reset_modal()
        self.modal_handle = handle
        self.modal_original_handle = handle

        try:
            user_session: UserSession = await self.get_state(UserSession)
            user_id = user_session.user_id

            async with get_asyncdb_session() as session:
                # Load all versions for version selector
                versions_list = await user_prompt_repo.find_all_versions(
                    session, user_id, handle
                )

                self.modal_versions = [
                    {
                        "value": str(v.id),
                        "label": (
                            f"Version {v.version} - "
                            f"{v.created_at.strftime('%d.%m.%Y %H:%M')}"
                        ),
                    }
                    for v in versions_list
                ]

                # Map DB ID to prompt text
                self.modal_prompt_map = {
                    str(v.id): v.prompt_text for v in versions_list
                }

                # Get latest version
                latest = next(
                    (v for v in versions_list if v.is_latest),
                    versions_list[0] if versions_list else None,
                )

                if latest:
                    self.modal_selected_version_id = latest.id
                    self.modal_description = latest.description
                    self.modal_prompt = latest.prompt_text
                    self.modal_is_shared = latest.is_shared
                    self.modal_char_count = len(latest.prompt_text)
                    self.modal_open = True
                else:
                    self.modal_error = "Prompt nicht gefunden"
        except Exception as e:
            logger.error("Error loading prompt for modal: %s", e)
            self.modal_error = f"Fehler beim Laden: {e!s}"

    @rx.event
    def open_new_modal(self) -> None:
        """Open modal to create a new prompt."""
        self._reset_modal()
        self.modal_is_new = True
        self.modal_open = True

    @rx.event
    def close_modal(self) -> None:
        """Close the modal and reset state."""
        self._reset_modal()

    @rx.event
    def handle_modal_open_change(self, is_open: bool) -> None:
        """Handle dialog open state change from UI."""
        if not is_open:
            self._reset_modal()

    @rx.event
    def set_modal_handle(self, value: str) -> None:
        """Set modal handle and validate."""
        self.modal_handle = value
        is_valid, error_msg = validate_handle(value)
        self.modal_handle_error = error_msg if not is_valid else ""

    def _get_description_error(self, value: str) -> str:
        """Validate description and return error message."""
        if len(value) > MAX_DESCRIPTION_LENGTH:
            return f"Beschreibung max. {MAX_DESCRIPTION_LENGTH} Zeichen"
        return ""

    def _get_prompt_error(self, value: str) -> str:
        """Validate prompt and return error message."""
        if not value or not value.strip():
            return "Der Prompt darf nicht leer sein."
        if len(value) > MAX_PROMPT_LENGTH:
            return f"Der Prompt max. {MAX_PROMPT_LENGTH} Zeichen"
        return ""

    @rx.event
    def set_modal_description(self, value: str) -> None:
        """Set modal description."""
        self.modal_description = value

    def set_modal_description_and_validate(self, value: str) -> None:
        """Set modal description on blur and validate."""
        self.modal_description = value
        self.modal_description_error = self._get_description_error(value)

    @rx.event
    def set_modal_prompt(self, value: str) -> None:
        """Set modal prompt text."""
        self.modal_prompt = value
        self.modal_char_count = len(value)

    def set_modal_prompt_and_validate(self, value: str) -> None:
        """Set modal prompt on blur and validate."""
        self.modal_prompt = value
        self.modal_char_count = len(value)
        self.modal_prompt_error = self._get_prompt_error(value)

    @rx.event
    def set_modal_is_shared(self, value: Any) -> None:
        """Set modal share toggle."""
        self.modal_is_shared = bool(value)

    async def save_from_modal(self) -> AsyncGenerator[Any, Any]:
        """Save prompt from modal (create new or update existing)."""
        handle = self.modal_handle.strip().lower()
        description = self.modal_description.strip()
        prompt_text = self.modal_prompt.strip()

        # Validation
        is_handle_valid, handle_error = validate_handle(handle)
        if not is_handle_valid:
            self.modal_error = handle_error
            return

        if prompt_error := self._get_prompt_error(prompt_text):
            self.modal_error = prompt_error
            return

        if desc_error := self._get_description_error(description):
            self.modal_error = desc_error
            return

        self.is_loading = True
        self.modal_error = ""
        yield

        try:
            user_session: UserSession = await self.get_state(UserSession)
            user_id = user_session.user_id

            async with get_asyncdb_session() as session:
                if self.modal_is_new:
                    # Check handle uniqueness
                    is_unique = await user_prompt_repo.validate_handle_unique(
                        session, user_id, handle
                    )
                    if not is_unique:
                        self.modal_error = f"Handle '/{handle}' existiert bereits"
                        self.is_loading = False
                        return

                    # Create new prompt
                    await user_prompt_repo.create_new_prompt(
                        session,
                        user_id=user_id,
                        handle=handle,
                        description=description,
                        prompt_text=prompt_text,
                        is_shared=self.modal_is_shared,
                    )
                else:
                    # Update existing (create new version)
                    original_handle = self.modal_original_handle

                    # Check if handle was changed
                    if handle != original_handle:
                        # Validate new handle is unique
                        is_unique = await user_prompt_repo.validate_handle_unique(
                            session, user_id, handle
                        )
                        if not is_unique:
                            self.modal_error = f"Handle '/{handle}' existiert bereits"
                            self.is_loading = False
                            return

                        # Update all old versions to new handle
                        await user_prompt_repo.update_handle(
                            session, user_id, original_handle, handle
                        )

                    # Create new version (now handle is consistent)
                    await user_prompt_repo.create_next_version(
                        session,
                        user_id=user_id,
                        handle=handle,
                        description=description,
                        prompt_text=prompt_text,
                        is_shared=self.modal_is_shared,
                    )

            self._reset_modal()
            yield ThreadState.reload_commands

        except Exception as e:
            logger.error("Error saving prompt from modal: %s", e)
            self.modal_error = f"Speichern fehlgeschlagen: {e!s}"
        finally:
            self.is_loading = False

    async def delete_from_modal(self) -> AsyncGenerator[Any, Any]:
        """Delete prompt from modal."""
        if self.modal_is_new:
            self._reset_modal()
            return

        handle = self.modal_handle
        if not handle:
            return

        self.is_loading = True
        self.modal_error = ""
        yield

        try:
            user_session: UserSession = await self.get_state(UserSession)
            user_id = user_session.user_id

            async with get_asyncdb_session() as session:
                await user_prompt_repo.delete_all_versions(session, user_id, handle)

            self._reset_modal()
            yield ThreadState.reload_commands

        except Exception as e:
            logger.error("Error deleting prompt from modal: %s", e)
            self.modal_error = f"Löschen fehlgeschlagen: {e!s}"
        finally:
            self.is_loading = False
