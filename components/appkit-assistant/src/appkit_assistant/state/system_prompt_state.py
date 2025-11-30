# app/state/system_prompt_state.py

import logging

import reflex as rx
from reflex.state import State

from appkit_assistant.backend.repositories import SystemPromptRepository

logger = logging.getLogger(__name__)


class SystemPromptState(State):
    """State für System Prompt Editing und Versionierung."""

    current_prompt: str = ""
    last_saved_prompt: str = ""
    versions: list[dict[str, str | int]] = []
    selected_version_id: int = 0
    is_loading: bool = False
    error_message: str = ""
    char_count: int = 0

    async def load_versions(self) -> None:
        """Alle System Prompt Versionen laden."""
        self.is_loading = True
        self.error_message = ""
        try:
            prompts = await SystemPromptRepository.get_all()
            self.versions = [
                {
                    "id": p.id,
                    "version": p.version,
                    "created_at": p.created_at.strftime("%d.%m.%Y %H:%M"),
                    "user_id": p.user_id,
                }
                for p in prompts
            ]

            if prompts:
                latest = prompts[0]
                if not self.current_prompt:
                    self.current_prompt = latest.prompt
                self.last_saved_prompt = latest.prompt
            else:
                if not self.current_prompt:
                    self.current_prompt = ""
                self.last_saved_prompt = self.current_prompt

            # Zähler initial setzen
            self.char_count = len(self.current_prompt)

            logger.info("Loaded %s system prompt versions", len(self.versions))
        except Exception as exc:
            self.error_message = f"Fehler beim Laden: {exc!s}"
            logger.exception("Failed to load system prompt versions")
        finally:
            self.is_loading = False

    def set_current_prompt(self, value: str) -> None:
        """Update current prompt text and char count."""
        self.current_prompt = value
        self.char_count = len(value)

    async def save_current(self) -> None:
        # ... (unverändert)
        if self.current_prompt == self.last_saved_prompt:
            await rx.toast.info("Es wurden keine Änderungen erkannt.")
            return

        if not self.current_prompt.strip():
            self.error_message = "Prompt darf nicht leer sein."
            await rx.toast.error("Prompt darf nicht leer sein.")
            return

        if len(self.current_prompt) > 20000:
            self.error_message = "Prompt darf maximal 20.000 Zeichen enthalten."
            await rx.toast.error("Prompt ist zu lang (max. 20.000 Zeichen).")
            return

        self.is_loading = True
        self.error_message = ""
        try:
            user_id = int(self.router.session.client_token.get("user_id", 0))

            await SystemPromptRepository.create(
                prompt=self.current_prompt,
                user_id=user_id,
            )

            self.last_saved_prompt = self.current_prompt
            await self.load_versions()

            await rx.toast.success("Neue Version erfolgreich gespeichert.")
            logger.info("Saved new system prompt version by user %s", user_id)
        except Exception as exc:
            self.error_message = f"Fehler beim Speichern: {exc!s}"
            logger.exception("Failed to save system prompt")
            await rx.toast.error(f"Fehler: {exc!s}")
        finally:
            self.is_loading = False

    async def revert_to_version(self) -> None:
        # ... (unverändert, aber char_count update beachten)
        if not self.selected_version_id:
            self.error_message = "Keine Version ausgewählt."
            await rx.toast.error("Bitte zuerst eine Version auswählen.")
            return

        self.is_loading = True
        self.error_message = ""
        try:
            prompt = await SystemPromptRepository.get_by_id(self.selected_version_id)
            if prompt:
                self.current_prompt = prompt.prompt
                self.char_count = len(prompt.prompt)  # Update Zähler
                await rx.toast.success(
                    f"Auf Version {prompt.version} zurückgesetzt (noch nicht gespeichert)."
                )
                logger.info("Reverted current draft to version %s", prompt.version)
            else:
                self.error_message = "Version nicht gefunden."
                await rx.toast.error("Version nicht gefunden.")
        except Exception as exc:
            self.error_message = f"Fehler beim Zurücksetzen: {exc!s}"
            logger.exception("Failed to revert to version")
            await rx.toast.error(f"Fehler: {exc!s}")
        finally:
            self.is_loading = False

    async def delete_version(self) -> None:
        # ... (unverändert)
        if not self.selected_version_id:
            self.error_message = "Keine Version ausgewählt."
            await rx.toast.error("Bitte zuerst eine Version auswählen.")
            return

        self.is_loading = True
        self.error_message = ""
        try:
            success = await SystemPromptRepository.delete(self.selected_version_id)
            if success:
                self.selected_version_id = 0
                await self.load_versions()
                await rx.toast.success("Version erfolgreich gelöscht.")
            else:
                self.error_message = "Version nicht gefunden."
                await rx.toast.error("Version nicht gefunden.")
        except Exception as exc:
            self.error_message = f"Fehler beim Löschen: {exc!s}"
            logger.exception("Failed to delete version")
            await rx.toast.error(f"Fehler: {exc!s}")
        finally:
            self.is_loading = False

    def set_selected_version(self, value: str | None) -> None:
        # ... (unverändert)
        if value is None or value == "":
            self.selected_version_id = 0
        else:
            self.selected_version_id = int(value)
