import logging
from collections.abc import AsyncGenerator
from typing import Any, Final

import reflex as rx
from reflex.state import State

from appkit_assistant.backend.database.repositories import system_prompt_repo
from appkit_assistant.backend.system_prompt_cache import invalidate_prompt_cache
from appkit_commons.database.session import get_asyncdb_session
from appkit_user.authentication.states import UserSession

logger = logging.getLogger(__name__)

MAX_PROMPT_LENGTH: Final[int] = 10000


class SystemPromptState(State):
    """State für System Prompt Editing und Versionierung."""

    current_prompt: str = ""
    last_saved_prompt: str = ""
    versions: list[dict[str, str | int]] = []
    prompt_map: dict[str, str] = {}
    selected_version_id: int = 0
    is_loading: bool = False
    error_message: str = ""
    char_count: int = 0
    textarea_key: int = 0

    async def load_versions(self) -> None:
        """Alle System Prompt Versionen laden."""
        self.is_loading = True
        self.error_message = ""
        try:
            async with get_asyncdb_session() as session:
                prompts = await system_prompt_repo.find_all_ordered_by_version_desc(
                    session
                )

                self.versions = [
                    {
                        "value": str(p.version),
                        "label": (
                            f"Version {p.version} - "
                            f"{p.created_at.strftime('%d.%m.%Y %H:%M')}"
                        ),
                    }
                    for p in prompts
                ]

                self.prompt_map = {str(p.version): p.prompt for p in prompts}

                latest_prompt = None
                if prompts:
                    latest_prompt = prompts[0]
                    # Access attributes to ensure they are loaded/available
                    self.selected_version_id = latest_prompt.version
                    latest_prompt_text = latest_prompt.prompt
                else:
                    self.selected_version_id = 0
                    latest_prompt_text = None

            if latest_prompt_text is not None:
                if not self.current_prompt:
                    self.current_prompt = latest_prompt_text
                    self.last_saved_prompt = latest_prompt_text
                else:
                    self.last_saved_prompt = latest_prompt_text
            else:
                if not self.current_prompt:
                    self.current_prompt = ""
                self.last_saved_prompt = self.current_prompt

            self.char_count = len(self.current_prompt)
            # Force textarea to re-render with loaded content
            self.textarea_key += 1

            logger.debug("Loaded %s system prompt versions", len(self.versions))
        except Exception as exc:
            self.error_message = f"Fehler beim Laden: {exc!s}"
            logger.exception("Failed to load system prompt versions")
        finally:
            self.is_loading = False

    async def save_current(self) -> AsyncGenerator[Any, Any]:
        if self.current_prompt == self.last_saved_prompt:
            yield rx.toast.info("Es wurden keine Änderungen erkannt.")
            return

        if not self.current_prompt.strip():
            self.error_message = "Prompt darf nicht leer sein."
            yield rx.toast.error("Prompt darf nicht leer sein.")
            return

        if len(self.current_prompt) > MAX_PROMPT_LENGTH:
            self.error_message = "Prompt darf maximal 20.000 Zeichen enthalten."
            yield rx.toast.error("Prompt ist zu lang (max. 20.000 Zeichen).")
            return

        self.is_loading = True
        self.error_message = ""
        try:
            user_session: UserSession = await self.get_state(UserSession)
            user_id = user_session.user_id

            async with get_asyncdb_session() as session:
                await system_prompt_repo.create_next_version(
                    session,
                    prompt=self.current_prompt,
                    user_id=user_id,
                )

            self.last_saved_prompt = self.current_prompt

            # Invalidate cache to force reload of new prompt version
            await invalidate_prompt_cache()
            logger.debug("System prompt cache invalidated after save")

            await self.load_versions()

            yield rx.toast.success("Neue Version erfolgreich gespeichert.")
            logger.debug("Saved new system prompt version by user %s", user_id)
        except Exception as exc:
            self.error_message = f"Fehler beim Speichern: {exc!s}"
            logger.exception("Failed to save system prompt")
            yield rx.toast.error(f"Fehler: {exc!s}")
        finally:
            self.is_loading = False

    async def delete_version(self) -> AsyncGenerator[Any, Any]:
        if not self.selected_version_id:
            self.error_message = "Keine Version ausgewählt."
            yield rx.toast.error("Bitte zuerst eine Version auswählen.")
            return

        self.is_loading = True
        self.error_message = ""
        try:
            async with get_asyncdb_session() as session:
                if self.selected_version_id:
                    prompt = await system_prompt_repo.find_by_id(
                        session, self.selected_version_id
                    )
                    if prompt:
                        success = await system_prompt_repo.delete(session, prompt)
                    else:
                        success = False
                else:
                    success = False

            if success:
                self.selected_version_id = 0

                # Invalidate cache since latest version might have changed
                await invalidate_prompt_cache()
                logger.debug("System prompt cache invalidated after deletion")

                await self.load_versions()
                yield rx.toast.success("Version erfolgreich gelöscht.")
            else:
                self.error_message = "Version nicht gefunden."
                yield rx.toast.error("Version nicht gefunden.")
        except Exception as exc:
            self.error_message = f"Fehler beim Löschen: {exc!s}"
            logger.exception("Failed to delete version")
            yield rx.toast.error(f"Fehler: {exc!s}")
        finally:
            self.is_loading = False

    def set_current_prompt(self, value: str) -> None:
        """Update current prompt text and char count.

        This is called on every keystroke but doesn't cause cursor jumping
        because we use default_value in the textarea component.
        """
        self.current_prompt = value
        self.char_count = len(value)

    def set_selected_version(self, value: str | None) -> None:
        """Handle version selection and load corresponding prompt.

        When a version is selected, we update the prompt content and force
        the textarea to re-render by changing its key.
        """
        if value is None or value == "":
            return

        self.selected_version_id = int(value)

        # Load the prompt for the selected version
        if value in self.prompt_map:
            self.current_prompt = self.prompt_map[value]
            self.char_count = len(self.current_prompt)
            # Force textarea to re-render with new content
            self.textarea_key += 1

    @rx.var
    def selected_version_str(self) -> str:
        """Return selected version as string for the select component."""
        if self.selected_version_id == 0:
            return ""
        return str(self.selected_version_id)
