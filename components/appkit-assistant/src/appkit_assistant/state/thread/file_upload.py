"""File upload mixin for ThreadState.

Handles uploading, removing, and clearing attached files.
"""

import logging
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

import reflex as rx

from appkit_assistant.backend.schemas import UploadedFile
from appkit_assistant.backend.services import file_manager
from appkit_user.authentication.states import UserSession

logger = logging.getLogger(__name__)


class FileUploadMixin:
    """Mixin for file upload management.

    Expects state vars: ``uploaded_files``, ``max_file_size_mb``,
    ``max_files_per_thread``.
    """

    @rx.event
    async def handle_upload(
        self, files: list[rx.UploadFile]
    ) -> AsyncGenerator[Any, Any]:
        """Handle uploaded files from the browser.

        Moves files to user-specific directory and adds them to state.
        """
        if len(files) > self.max_files_per_thread:
            yield rx.toast.error(
                (
                    f"Bitte laden Sie maximal "
                    f"{self.max_files_per_thread} "
                    "Dateien gleichzeitig hoch."
                ),
                position="top-right",
                close_button=True,
            )
            return

        user_session: UserSession = await self.get_state(UserSession)
        user_id = user_session.user.user_id if user_session.user else "anonymous"

        for upload_file in files:
            try:
                filename = file_manager.sanitize_upload_filename(upload_file.filename)
                upload_data = await upload_file.read()
                if len(upload_data) > self.max_file_size_mb * 1024 * 1024:
                    raise ValueError("File exceeds the maximum size")
                temp_path = rx.get_upload_dir() / filename
                temp_path.parent.mkdir(parents=True, exist_ok=True)
                temp_path.write_bytes(upload_data)

                final_path = file_manager.move_to_user_directory(
                    str(temp_path), str(user_id)
                )
                file_size = file_manager.get_file_size(final_path)

                uploaded = UploadedFile(
                    filename=filename,
                    file_path=final_path,
                    size=file_size,
                )
                self.uploaded_files = [*self.uploaded_files, uploaded]
                logger.info(
                    "Uploaded file: %s (total files: %d)",
                    upload_file.filename,
                    len(self.uploaded_files),
                )
            except ValueError as e:
                logger.warning("Rejected upload %r: %s", upload_file.filename, e)
                yield rx.toast.error(
                    f"{Path(upload_file.filename or 'Datei').name}: "
                    "Datei nicht erlaubt oder zu groß.",
                    position="top-right",
                    close_button=True,
                )
            except Exception as e:
                logger.error(
                    "Failed to upload file %s: %s",
                    upload_file.filename,
                    e,
                )

    @rx.event
    def remove_file_from_prompt(self, file_path: str) -> None:
        """Remove an uploaded file from the prompt."""
        file_manager.cleanup_uploaded_files([file_path])
        self.uploaded_files = [
            f for f in self.uploaded_files if f.file_path != file_path
        ]
        logger.debug("Removed uploaded file: %s", file_path)

    def _clear_uploaded_files(self) -> None:
        """Clear all uploaded files from state and disk."""
        if not self.uploaded_files:
            return
        count = len(self.uploaded_files)
        file_paths = [f.file_path for f in self.uploaded_files]
        file_manager.cleanup_uploaded_files(file_paths)
        self.uploaded_files = []
        logger.debug("Cleared %d uploaded files", count)
