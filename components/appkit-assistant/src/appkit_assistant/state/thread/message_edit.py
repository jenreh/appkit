"""Message editing mixin for ThreadState.

Provides editing, deleting, copying, and downloading of messages.
"""

import json
import logging
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any

import reflex as rx

from appkit_assistant.backend.database.models import ThreadStatus
from appkit_assistant.backend.services.thread_service import ThreadService

logger = logging.getLogger(__name__)


class MessageEditMixin:
    """Mixin for message editing, copy, download, and retry.

    Expects state vars: ``editing_message_id``, ``edited_message_content``,
    ``expanded_message_ids``, ``messages``, ``_thread``, ``prompt``,
    ``_skip_user_message``, ``_current_user_id``.
    """

    @rx.event
    def set_editing_mode(self, message_id: str, content: str) -> None:
        """Enable editing mode for a message."""
        self.editing_message_id = message_id
        self.edited_message_content = content

    @rx.event
    def set_edited_message_content(self, content: str) -> None:
        """Set the content of the message currently being edited."""
        self.edited_message_content = content

    @rx.event
    def cancel_edit(self) -> None:
        """Cancel editing mode."""
        self.editing_message_id = None
        self.edited_message_content = ""

    @rx.event
    def toggle_message_expanded(self, message_id: str) -> None:
        """Toggle expanded state for a user message."""
        if message_id in self.expanded_message_ids:
            self.expanded_message_ids = [
                mid for mid in self.expanded_message_ids if mid != message_id
            ]
        else:
            self.expanded_message_ids = [
                *self.expanded_message_ids,
                message_id,
            ]

    @rx.event(background=True)
    async def submit_edited_message(
        self,
    ) -> AsyncGenerator[Any, Any]:
        """Submit edited message."""
        async with self:
            content = self.edited_message_content.strip()
            if not content:
                yield rx.toast.error(
                    "Nachricht darf nicht leer sein",
                    position="top-right",
                )
                return

            msg_index = next(
                (
                    i
                    for i, m in enumerate(self.messages)
                    if m.id == self.editing_message_id
                ),
                -1,
            )

            if msg_index == -1:
                self.cancel_edit()
                return

            target = self.messages[msg_index]
            target.original_text = target.original_text or target.text
            target.text = content

            # Remove all messages after this one
            self.messages = self.messages[: msg_index + 1]
            self.prompt = content
            self._skip_user_message = True

            self.editing_message_id = None
            self.edited_message_content = ""

        await self._process_message()

    @rx.event(background=True)
    async def delete_message(self, message_id: str) -> None:
        """Delete a message from the conversation."""
        async with self:
            self.messages = [m for m in self.messages if m.id != message_id]
            self._thread.messages = self.messages

            if self._thread.state != ThreadStatus.NEW:
                await ThreadService().save_thread(self._thread, self.current_user_id)

    @rx.event
    def copy_message(self, text: str) -> list[Any]:
        """Copy message text to clipboard."""
        return [
            rx.set_clipboard(text),
            rx.toast.success("Nachricht kopiert"),
        ]

    @rx.event
    def download_message(self, text: str, message_id: str) -> Any:
        """Download message as markdown file."""
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        filename = (
            f"message_{message_id}_{timestamp}.md"
            if message_id
            else f"message_{timestamp}.md"
        )

        return rx.call_script(f"""
            const blob = new Blob(
                [{json.dumps(text)}],
                {{type: 'text/markdown'}}
            );
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = '{filename}';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        """)

    @rx.event(background=True)
    async def retry_message(self, message_id: str) -> None:
        """Retry generating a message."""
        async with self:
            index = next(
                (i for i, msg in enumerate(self.messages) if msg.id == message_id),
                -1,
            )
            if index == -1:
                return

            self.messages = self.messages[:index]
            self.prompt = "Regenerate"
            self._skip_user_message = True

        await self._process_message()
