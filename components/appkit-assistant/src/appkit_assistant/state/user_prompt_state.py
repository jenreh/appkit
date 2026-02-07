import logging
from collections.abc import AsyncGenerator
from typing import Any, Final

import reflex as rx
from pydantic import BaseModel
from reflex.state import State

from appkit_assistant.backend.database.models import UserPrompt
from appkit_assistant.backend.database.repositories import user_prompt_repo
from appkit_assistant.backend.services.user_prompt_service import validate_handle
from appkit_assistant.state.thread_state import ThreadState
from appkit_commons.database.session import get_asyncdb_session
from appkit_user.authentication.states import UserSession

logger = logging.getLogger(__name__)

MAX_PROMPT_LENGTH: Final[int] = 20000
MAX_DESCRIPTION_LENGTH: Final[int] = 100
MAX_HANDLE_LENGTH: Final[int] = 50


class UserPromptDisplay(BaseModel):
    """Display model for user prompts in the UI."""

    handle: str = ""
    description: str = ""
    is_shared: bool = False
    user_id: int = 0
    creator_name: str = ""

    @classmethod
    def from_model(
        cls, prompt: UserPrompt, creator_name: str = ""
    ) -> "UserPromptDisplay":
        """Create display model from database model."""
        return cls(
            handle=prompt.handle,
            description=prompt.description,
            is_shared=prompt.is_shared,
            user_id=prompt.user_id,
            creator_name=creator_name,
        )


class UserPromptState(State):
    """State for User Prompt Management."""

    # Data lists
    my_prompts: list[UserPromptDisplay] = []
    shared_prompts: list[UserPromptDisplay] = []

    # Selection & Filtering
    filter_tab: str = "my_prompts"  # "my_prompts" | "shared_prompts"

    # Current Selection Identifiers
    selected_handle: str = ""  # Stable identifier for the prompt concept
    selected_version_id: int = 0  # DB ID of the specific version row selected

    # Current Editor State
    current_name: str = ""
    current_handle: str = ""
    current_description: str = ""
    current_prompt: str = ""

    # Prompt Metadata (of the currently selected version)
    is_shared: bool = False
    is_active: bool = True
    created_by_username: str = ""

    # Versioning
    versions: list[dict[str, str | int]] = []
    prompt_map: dict[str, str] = {}  # version_id_str -> prompt_text

    # UI State
    char_count: int = 0
    textarea_key: int = 0
    is_loading: bool = False
    error_message: str = ""

    # Validation errors
    handle_error: str = ""
    description_error: str = ""
    prompt_error: str = ""

    # New prompt dialog state
    new_dialog_open: bool = False
    new_handle: str = ""
    new_description: str = ""
    new_handle_error: str = ""
    new_description_error: str = ""

    # Edit modal state (for command palette quick-edit)
    modal_open: bool = False
    modal_is_new: bool = False
    modal_handle: str = ""  # Handle being edited (display only)
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
    def is_owner(self) -> bool:
        """Check if current user owns the selected prompt."""
        return any(p.handle == self.selected_handle for p in self.my_prompts)

    @rx.var
    def modal_title(self) -> str:
        """Return modal title based on mode."""
        return "Neuer Prompt" if self.modal_is_new else "Prompt bearbeiten"

    @rx.var
    def modal_save_button_text(self) -> str:
        """Return save button text based on modal mode."""
        return "Erstellen" if self.modal_is_new else "Neue Version speichern"

    @rx.var
    def selected_version_str(self) -> str:
        """Return selected version ID as string for select component."""
        return str(self.selected_version_id) if self.selected_version_id else ""

    @rx.var
    def has_validation_errors(self) -> bool:
        """Check if the form has any validation errors."""
        return bool(self.handle_error or self.description_error or self.prompt_error)

    @rx.var
    def has_new_dialog_errors(self) -> bool:
        """Check if the new prompt dialog has any validation errors."""
        # Must have a valid handle (non-empty after validation)
        if not self.new_handle or self.new_handle.strip() == "":
            return True
        return bool(self.new_handle_error or self.new_description_error)

    @rx.var
    def has_modal_validation_errors(self) -> bool:
        """Check if the modal form has any validation errors."""
        return bool(
            self.modal_handle_error
            or self.modal_description_error
            or self.modal_prompt_error
        )

    @rx.event
    def validate_current_handle(self) -> None:
        """Validate the handle field using service validation."""
        is_valid, error_msg = validate_handle(self.current_handle)
        self.handle_error = error_msg if not is_valid else ""

    @rx.event
    def validate_new_handle(self) -> None:
        """Validate the new prompt handle field."""
        is_valid, error_msg = validate_handle(self.new_handle)
        self.new_handle_error = error_msg if not is_valid else ""

    def set_new_handle_and_validate(self, value: str) -> None:
        """Set new prompt handle and validate."""
        self.new_handle = value
        self.validate_new_handle()

    def set_new_description_and_validate(self, value: str) -> None:
        """Set new prompt description and validate."""
        self.new_description = value
        if len(value) > MAX_DESCRIPTION_LENGTH:
            self.new_description_error = (
                f"Beschreibung darf maximal {MAX_DESCRIPTION_LENGTH} Zeichen lang sein."
            )
        else:
            self.new_description_error = ""

    @rx.event
    def validate_description(self) -> None:
        """Validate the description field."""
        if len(self.current_description) > MAX_DESCRIPTION_LENGTH:
            self.description_error = (
                f"Beschreibung darf maximal {MAX_DESCRIPTION_LENGTH} Zeichen lang sein."
            )
        else:
            self.description_error = ""

    @rx.event
    def validate_prompt(self) -> None:
        """Validate the prompt field."""
        if not self.current_prompt or self.current_prompt.strip() == "":
            self.prompt_error = "Der Prompt darf nicht leer sein."
        elif len(self.current_prompt) > MAX_PROMPT_LENGTH:
            self.prompt_error = (
                f"Der Prompt darf maximal {MAX_PROMPT_LENGTH} Zeichen lang sein."
            )
        else:
            self.prompt_error = ""

    def set_filter_tab(self, tab: str | list[str]) -> None:
        """Switch between My Prompts and Shared Prompts."""
        if isinstance(tab, list):
            self.filter_tab = tab[0] if tab else "my_prompts"
        else:
            self.filter_tab = tab
        self._clear_selection()

    def _clear_selection(self) -> None:
        self.selected_handle = ""
        self.selected_version_id = 0
        self.current_name = ""
        self.current_handle = ""
        self.current_description = ""
        self.current_prompt = ""
        self.is_shared = False
        self.created_by_username = ""
        self.versions = []
        self.prompt_map = {}
        self.char_count = 0
        self.textarea_key += 1
        self.handle_error = ""
        self.description_error = ""
        self.prompt_error = ""

    def set_current_prompt(self, value: str) -> None:
        """Set prompt and update char count."""
        self.current_prompt = value
        self.char_count = len(value)

    def set_current_prompt_and_validate(self, value: str) -> None:
        """Set prompt, update char count, and validate."""
        self.current_prompt = value
        self.char_count = len(value)
        self.validate_prompt()

    def set_current_name(self, value: str) -> None:
        self.current_name = value

    def set_current_handle(self, value: str) -> None:
        """Set handle value."""
        self.current_handle = value

    def set_current_handle_and_validate(self, value: str) -> None:
        """Set handle and validate."""
        self.current_handle = value
        self.validate_current_handle()

    def set_current_description(self, value: str) -> None:
        self.current_description = value

    def set_current_description_and_validate(self, value: str) -> None:
        """Set description and validate."""
        self.current_description = value
        self.validate_description()

    async def load_user_prompts(self) -> None:
        """Load all user prompts (own + shared) from database."""
        self.is_loading = True
        self.error_message = ""

        try:
            user_session: UserSession = await self.get_state(UserSession)
            user_id = user_session.user_id

            if not user_id:
                return

            async with get_asyncdb_session() as session:
                # 1. Load own prompts (latest versions)
                own_prompts = await user_prompt_repo.find_latest_prompts_by_user(
                    session, user_id
                )
                self.my_prompts = [UserPromptDisplay.from_model(p) for p in own_prompts]

                # 2. Load shared prompts (latest versions)
                shared_prompts = await user_prompt_repo.find_latest_shared_prompts(
                    session, user_id
                )
                self.shared_prompts = [
                    UserPromptDisplay(
                        handle=p["handle"],
                        description=p["description"],
                        is_shared=p["is_shared"],
                        user_id=p["user_id"],
                        creator_name=p.get("creator_name", ""),
                    )
                    for p in shared_prompts
                ]

                # Auto-select first if nothing selected
                if not self.selected_handle:
                    if self.filter_tab == "my_prompts" and self.my_prompts:
                        await self.set_selected_by_handle(self.my_prompts[0].handle)
                    elif self.filter_tab == "shared_prompts" and self.shared_prompts:
                        await self.set_selected_by_handle(self.shared_prompts[0].handle)

        except Exception as exc:
            self.error_message = f"Fehler beim Laden: {exc!s}"
            logger.exception("Failed to load user prompts")
        finally:
            self.is_loading = False

    async def set_selected_by_handle(self, handle: str) -> None:
        """Select a prompt by handle."""
        if not handle:
            return

        self.selected_handle = handle
        self.current_handle = handle
        self.handle_error = ""

        # Look up metadata from lists (fetched as 'latest' versions)
        prompt_data: UserPromptDisplay | None = None
        creator = ""

        for p in self.my_prompts:
            if p.handle == handle:
                prompt_data = p
                break

        if not prompt_data:
            for p in self.shared_prompts:
                if p.handle == handle:
                    prompt_data = p
                    creator = p.creator_name
                    break

        if not prompt_data:
            return

        self.current_description = prompt_data.description
        self.is_shared = prompt_data.is_shared
        self.created_by_username = creator

        await self._load_versions(handle)

    async def _load_versions(self, handle: str) -> None:
        """Load history for the prompt handle."""
        self.is_loading = True
        try:
            user_session: UserSession = await self.get_state(UserSession)
            user_id = (
                user_session.user_id
            )  # Note: for shared, we might need owner's ID?

            # Logic: 'find_all_versions' filters by user_id and handle.
            # If viewing a shared prompt, user_id is ME, but the prompt is NOT mine.
            # I need to know the OWNER's user_id to fetch versions of a shared prompt.
            # IN Single Table design: Prompts are rows in `assistant_user_prompts`.
            # If I'm viewing shared, I need to fetch where handle=X and user_id=OWNER.

            # Find owner id from the list data which we already loaded
            target_user_id = user_id

            if self.filter_tab == "shared_prompts":
                for p in self.shared_prompts:
                    if p.handle == handle:
                        target_user_id = p.user_id
                        break

            async with get_asyncdb_session() as session:
                versions_list = await user_prompt_repo.find_all_versions(
                    session, target_user_id, handle
                )

                self.versions = [
                    {
                        "value": str(v.id),  # Use DB ID as value to unique identify row
                        "label": (
                            f"Version {v.version} - "
                            f"{v.created_at.strftime('%d.%m.%Y %H:%M')}"
                        ),
                    }
                    for v in versions_list
                ]

                # Map DB ID to prompt text
                self.prompt_map = {str(v.id): v.prompt_text for v in versions_list}

                # Select latest (first in list, sorted by version desc)
                latest = next(
                    (v for v in versions_list if v.is_latest),
                    versions_list[0] if versions_list else None,
                )

                if latest:
                    self.selected_version_id = latest.id
                    self.current_prompt = latest.prompt_text
                else:
                    self.selected_version_id = 0
                    self.current_prompt = ""

                self.char_count = len(self.current_prompt)
                self.textarea_key += 1

        except Exception:
            logger.exception("Failed to load versions for prompt %s", handle)
        finally:
            self.is_loading = False

    def set_selected_version_id(self, value: str | None) -> None:
        """Handle version selection change."""
        if not value:
            return

        self.selected_version_id = int(value)
        if value in self.prompt_map:
            self.current_prompt = self.prompt_map[value]
            self.char_count = len(self.current_prompt)
            self.textarea_key += 1

    def reset_new_dialog(self) -> None:
        """Reset the new prompt dialog state and close."""
        self.new_dialog_open = False
        self.new_handle = ""
        self.new_description = ""
        self.new_handle_error = ""
        self.new_description_error = ""

    def set_new_dialog_open(self, is_open: bool) -> None:
        """Set the new prompt dialog open state."""
        self.new_dialog_open = is_open
        if not is_open:
            # Reset errors when dialog closes
            self.new_handle_error = ""
            self.new_description_error = ""

    async def create_new_prompt(self) -> AsyncGenerator[Any, Any]:
        """Create a new user prompt from dialog state."""
        handle = self.new_handle.strip().lower()
        description = self.new_description.strip()

        is_valid, error = validate_handle(handle)
        if not is_valid:
            yield rx.toast.error(error)
            return

        self.is_loading = True
        yield  # Flush state to show loading indicator
        try:
            user_session: UserSession = await self.get_state(UserSession)
            user_id = user_session.user_id

            async with get_asyncdb_session() as session:
                is_unique = await user_prompt_repo.validate_handle_unique(
                    session, user_id, handle
                )
                if not is_unique:
                    yield rx.toast.error(f"Handle '{handle}' existiert bereits.")
                    return

                # Create prompt (Version 1)
                await user_prompt_repo.create_new_prompt(
                    session,
                    user_id=user_id,
                    handle=handle,
                    description=description,
                    prompt_text="",
                    is_shared=False,
                )

            self.reset_new_dialog()
            await self.load_user_prompts()
            await self.set_selected_by_handle(handle)
            yield rx.toast.success(f"Prompt '{handle}' erstellt.")
            yield ThreadState.reload_commands

        except Exception as exc:
            logger.exception("Failed to create prompt")
            yield rx.toast.error(f"Fehler: {exc!s}")
        finally:
            self.is_loading = False

    async def save_prompt(self) -> AsyncGenerator[Any, Any]:
        """Save a new version of the current prompt."""
        if not self.is_owner:
            yield rx.toast.error("Sie können nur eigene Prompts bearbeiten.")
            return

        if len(self.current_prompt) > MAX_PROMPT_LENGTH:
            yield rx.toast.error("Prompt ist zu lang.")
            return

        # Validate handle
        is_valid, error = validate_handle(self.current_handle)
        if not is_valid:
            yield rx.toast.error(error)
            return

        self.is_loading = True
        try:
            user_session: UserSession = await self.get_state(UserSession)
            user_id = user_session.user_id
            handle_changed = self.current_handle != self.selected_handle

            async with get_asyncdb_session() as session:
                # If handle changed, check uniqueness and update all versions
                if handle_changed:
                    is_unique = await user_prompt_repo.validate_handle_unique(
                        session, user_id, self.current_handle
                    )
                    if not is_unique:
                        yield rx.toast.error(
                            f"Handle '{self.current_handle}' existiert bereits."
                        )
                        return
                    # Update handle on all versions
                    await user_prompt_repo.update_handle(
                        session, user_id, self.selected_handle, self.current_handle
                    )

                # Creates new row, updates old latest=false
                await user_prompt_repo.create_next_version(
                    session,
                    user_id=user_id,
                    handle=self.current_handle,
                    description=self.current_description,
                    prompt_text=self.current_prompt,
                    is_shared=self.is_shared,
                )

            await self.load_user_prompts()  # Refresh sidebar list
            await self.set_selected_by_handle(self.current_handle)  # Re-select
            yield rx.toast.success("Gespeichert.")
            yield ThreadState.reload_commands

        except Exception as exc:
            logger.exception("Failed to save prompt version")
            yield rx.toast.error(f"Fehler: {exc!s}")
        finally:
            self.is_loading = False

    async def delete_prompt(self) -> AsyncGenerator[Any, Any]:
        """Hard delete of all versions."""
        if not self.is_owner:
            yield rx.toast.error("Keine Berechtigung.")
            return

        self.is_loading = True
        try:
            user_session: UserSession = await self.get_state(UserSession)
            user_id = user_session.user_id

            async with get_asyncdb_session() as session:
                await user_prompt_repo.delete_all_versions(
                    session, user_id, self.selected_handle
                )

            self._clear_selection()
            await self.load_user_prompts()
            yield rx.toast.success("Prompt gelöscht.")
            # Refresh command palette
            yield ThreadState.reload_commands

        except Exception as exc:
            logger.exception("Failed to delete prompt")
            yield rx.toast.error(f"Fehler: {exc!s}")
        finally:
            self.is_loading = False

    async def toggle_shared(self, value: bool) -> AsyncGenerator[Any, Any]:
        """Toggle shared status (saved immediately to latest version)."""
        if not self.is_owner:
            return

        self.is_shared = value

        try:
            user_session: UserSession = await self.get_state(UserSession)
            user_id = user_session.user_id

            async with get_asyncdb_session() as session:
                latest = await user_prompt_repo.find_latest_by_handle(
                    session, user_id, self.selected_handle
                )
                if latest:
                    latest.is_shared = value
                    await user_prompt_repo.update(session, latest)

            await self.load_user_prompts()  # Refresh so icon updates
            yield ThreadState.reload_commands

        except Exception:
            logger.exception("Failed to toggle shared")
            yield rx.toast.error("Fehler beim Aktualisieren.")

    # -------------------------------------------------------------------------
    # Modal methods (for command palette quick-edit)
    # -------------------------------------------------------------------------

    def _reset_modal(self) -> None:
        """Reset modal state."""
        self.modal_open = False
        self.modal_is_new = False
        self.modal_handle = ""
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

    @rx.event
    def set_modal_description(self, value: str) -> None:
        """Set modal description."""
        self.modal_description = value

    def set_modal_description_and_validate(self, value: str) -> None:
        """Set modal description on blur and validate."""
        self.modal_description = value
        if len(value) > MAX_DESCRIPTION_LENGTH:
            self.modal_description_error = (
                f"Beschreibung max. {MAX_DESCRIPTION_LENGTH} Zeichen"
            )
        else:
            self.modal_description_error = ""

    @rx.event
    def set_modal_prompt(self, value: str) -> None:
        """Set modal prompt text."""
        self.modal_prompt = value
        self.modal_char_count = len(value)

    def set_modal_prompt_and_validate(self, value: str) -> None:
        """Set modal prompt on blur and validate."""
        self.modal_prompt = value
        self.modal_char_count = len(value)
        if not value or value.strip() == "":
            self.modal_prompt_error = "Der Prompt darf nicht leer sein."
        elif len(value) > MAX_PROMPT_LENGTH:
            self.modal_prompt_error = f"Der Prompt max. {MAX_PROMPT_LENGTH} Zeichen"
        else:
            self.modal_prompt_error = ""

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
        is_valid, error = validate_handle(handle)
        if not is_valid:
            self.modal_error = error
            return
        if not prompt_text:
            self.modal_error = "Prompt-Text ist erforderlich"
            return
        if len(prompt_text) > MAX_PROMPT_LENGTH:
            self.modal_error = f"Prompt max. {MAX_PROMPT_LENGTH} Zeichen"
            return
        if len(description) > MAX_DESCRIPTION_LENGTH:
            self.modal_error = f"Beschreibung max. {MAX_DESCRIPTION_LENGTH} Zeichen"
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
