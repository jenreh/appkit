"""State management for file manager in assistant administration."""

import logging
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any, Final

import reflex as rx
from pydantic import BaseModel

from appkit_assistant.backend.database.repositories import file_upload_repo
from appkit_assistant.backend.services.file_cleanup_service import run_cleanup
from appkit_assistant.backend.services.openai_client_service import (
    get_openai_client_service,
)
from appkit_commons.database.session import get_asyncdb_session
from appkit_user.authentication.backend.user_repository import user_repo

logger = logging.getLogger(__name__)

# Toast messages
ERROR_LOAD_STORES: Final[str] = "Fehler beim Laden der Vector Stores."
ERROR_LOAD_FILES: Final[str] = "Fehler beim Laden der Dateien."
ERROR_FILE_NOT_FOUND: Final[str] = "Datei nicht gefunden."
ERROR_DELETE_FAILED: Final[str] = "Datei konnte nicht gelöscht werden."
ERROR_DELETE_GENERAL: Final[str] = "Fehler beim Löschen der Datei."
ERROR_LOAD_OPENAI_FILES: Final[str] = "Fehler beim Laden der OpenAI-Dateien."
ERROR_DELETE_OPENAI_FILE: Final[str] = "Fehler beim Löschen der OpenAI-Datei."
ERROR_OPENAI_NOT_CONFIGURED: Final[str] = "OpenAI API Key ist nicht konfiguriert."
ERROR_DELETE_VECTOR_STORE: Final[str] = "Fehler beim Löschen des Vector Stores."
INFO_VECTOR_STORE_EXPIRED: Final[str] = (
    "Vector Store ist abgelaufen und wurde bereinigt."
)
INFO_VECTOR_STORE_DELETED: Final[str] = "Vector Store wurde gelöscht."
INFO_CLEANUP_COMPLETED: Final[str] = "Bereinigung abgeschlossen."
ERROR_CLEANUP_FAILED: Final[str] = "Fehler bei der Bereinigung."

# File size constants
KB: Final[int] = 1024
MB: Final[int] = 1024 * 1024
GB: Final[int] = 1024 * 1024 * 1024


def format_file_size_for_display(size_bytes: int) -> tuple[float, str]:
    """Format file size to appropriate unit and return (formatted_value, suffix).

    Args:
        size_bytes: File size in bytes.

    Returns:
        Tuple of (formatted_value, suffix) e.g., (2.5, " MB")
    """
    if size_bytes >= GB:
        return (size_bytes / GB, " GB")
    if size_bytes >= MB:
        return (size_bytes / MB, " MB")
    if size_bytes >= KB:
        return (size_bytes / KB, " KB")
    return (float(size_bytes), " B")


def _format_unix_timestamp(timestamp: int | None) -> str:
    """Format a Unix timestamp to a human-readable date string.

    Args:
        timestamp: Unix timestamp in seconds, or None.

    Returns:
        Formatted date string or "-" if timestamp is None/invalid.
    """
    if timestamp is None:
        return "-"
    try:
        # Convert UTC timestamp to local time for display
        dt = datetime.fromtimestamp(timestamp, tz=UTC).astimezone()
        return dt.strftime("%d.%m.%Y %H:%M")
    except (ValueError, OSError, TypeError):
        return "-"


class FileInfo(BaseModel):
    """Model for file information displayed in the table."""

    id: int
    filename: str
    created_at: str
    user_name: str
    file_size: int
    formatted_size: float
    size_suffix: str
    openai_file_id: str


class OpenAIFileInfo(BaseModel):
    """Model for OpenAI file information."""

    openai_id: str
    filename: str
    created_at: str
    expires_at: str
    purpose: str
    file_size: int
    formatted_size: float
    size_suffix: str


class VectorStoreInfo(BaseModel):
    """Model for vector store information."""

    store_id: str
    name: str


class CleanupStats(BaseModel):
    """Model for cleanup progress statistics."""

    status: str = "idle"  # idle, starting, checking, deleting, completed, error
    vector_stores_checked: int = 0
    vector_stores_expired: int = 0
    vector_stores_deleted: int = 0
    threads_updated: int = 0
    current_vector_store: str | None = None
    total_vector_stores: int = 0
    error: str | None = None


class FileManagerState(rx.State):
    """State class for managing uploaded files in vector stores."""

    vector_stores: list[VectorStoreInfo] = []
    selected_vector_store_id: str = ""
    selected_vector_store_name: str = ""
    files: list[FileInfo] = []
    openai_files: list[OpenAIFileInfo] = []
    loading: bool = False
    deleting_file_id: int | None = None
    deleting_openai_file_id: str | None = None
    deleting_vector_store_id: str | None = None

    # Cleanup state
    cleanup_modal_open: bool = False
    cleanup_running: bool = False
    cleanup_stats: CleanupStats = CleanupStats()

    def _get_file_by_id(self, file_id: int) -> FileInfo | None:
        """Get a file by ID from the current files list."""
        return next((f for f in self.files if f.id == file_id), None)

    def _get_openai_file_by_id(self, openai_id: str) -> OpenAIFileInfo | None:
        """Get an OpenAI file by ID from the current OpenAI files list."""
        return next((f for f in self.openai_files if f.openai_id == openai_id), None)

    async def on_tab_change(self, tab_value: str) -> AsyncGenerator[Any, Any]:
        """Handle tab change events."""
        if tab_value == "openai_files":
            yield FileManagerState.load_openai_files
        else:
            yield FileManagerState.load_vector_stores

    async def load_vector_stores(self) -> AsyncGenerator[Any, Any]:
        """Load all unique vector stores from the database."""
        self.loading = True
        try:
            async with get_asyncdb_session() as session:
                stores = await file_upload_repo.find_unique_vector_stores(session)
                self.vector_stores = [
                    VectorStoreInfo(store_id=store_id, name=name)
                    for store_id, name in stores
                ]

            logger.debug("Loaded %d vector stores", len(self.vector_stores))

            # If no vector stores exist, clear selection and files
            if not self.vector_stores:
                self.selected_vector_store_id = ""
                self.selected_vector_store_name = ""
                self.files = []
                return

            # Check if currently selected store still exists
            store_ids = {s.store_id for s in self.vector_stores}
            if self.selected_vector_store_id and (
                self.selected_vector_store_id not in store_ids
            ):
                # Selected store no longer exists, clear it
                self.selected_vector_store_id = ""
                self.selected_vector_store_name = ""
                self.files = []

        except Exception as e:
            logger.error("Failed to load vector stores: %s", e)
            yield rx.toast.error(
                ERROR_LOAD_STORES,
                position="top-right",
            )
        finally:
            self.loading = False

    async def delete_vector_store(self, store_id: str) -> AsyncGenerator[Any, Any]:
        """Delete a vector store and all its associated files.

        Deletes the vector store from OpenAI, all associated files from OpenAI,
        and removes all database records.

        Args:
            store_id: The ID of the vector store to delete.
        """
        self.deleting_vector_store_id = store_id
        try:
            openai_service = get_openai_client_service()
            if not openai_service.is_available:
                yield rx.toast.error(
                    ERROR_OPENAI_NOT_CONFIGURED,
                    position="top-right",
                )
                return

            client = openai_service.create_client()
            if not client:
                yield rx.toast.error(
                    ERROR_OPENAI_NOT_CONFIGURED,
                    position="top-right",
                )
                return

            # Get files from DB to know which OpenAI files to delete
            async with get_asyncdb_session() as session:
                files = await file_upload_repo.find_by_vector_store(session, store_id)
                openai_file_ids = [f.openai_file_id for f in files]

                # Delete vector store from OpenAI
                try:
                    await client.vector_stores.delete(vector_store_id=store_id)
                    logger.info("Deleted vector store from OpenAI: %s", store_id)
                except Exception as e:
                    error_msg = str(e).lower()
                    if "not found" not in error_msg and "404" not in error_msg:
                        logger.error(
                            "Failed to delete vector store %s from OpenAI: %s",
                            store_id,
                            e,
                        )

                # Delete files from OpenAI
                for file_id in openai_file_ids:
                    try:
                        await client.files.delete(file_id=file_id)
                        logger.debug("Deleted file from OpenAI: %s", file_id)
                    except Exception as e:
                        logger.warning(
                            "Failed to delete file %s from OpenAI: %s",
                            file_id,
                            e,
                        )

                # Delete records from database
                await file_upload_repo.delete_by_vector_store(session, store_id)
                await session.commit()
                logger.info(
                    "Deleted %d files for vector store %s",
                    len(files),
                    store_id,
                )

            # Reset selection if this was the selected store
            if self.selected_vector_store_id == store_id:
                self.selected_vector_store_id = ""
                self.selected_vector_store_name = ""
                self.files = []

            # Remove from local list
            self.vector_stores = [
                s for s in self.vector_stores if s.store_id != store_id
            ]

            yield rx.toast.success(
                INFO_VECTOR_STORE_DELETED,
                position="top-right",
            )

        except Exception as e:
            logger.error("Failed to delete vector store %s: %s", store_id, e)
            yield rx.toast.error(
                ERROR_DELETE_VECTOR_STORE,
                position="top-right",
            )
        finally:
            self.deleting_vector_store_id = None

    async def select_vector_store(
        self, store_id: str, store_name: str = ""
    ) -> AsyncGenerator[Any, Any]:
        """Select a vector store and load its files.

        Validates that the vector store exists in OpenAI. If expired/deleted,
        cleans up the database records and associated OpenAI files.
        """
        self.loading = True
        try:
            # First validate the vector store exists in OpenAI
            openai_service = get_openai_client_service()
            if openai_service.is_available:
                client = openai_service.create_client()
                if client:
                    try:
                        await client.vector_stores.retrieve(store_id)
                        logger.debug("Vector store %s exists in OpenAI", store_id)
                    except Exception as e:
                        # Vector store not found - clean up
                        error_msg = str(e).lower()
                        if "not found" in error_msg or "404" in error_msg:
                            logger.info(
                                "Vector store %s expired/deleted, cleaning up",
                                store_id,
                            )
                            async for event in self._cleanup_expired_vector_store(
                                store_id
                            ):
                                yield event
                            return
                        # Other error - log and continue
                        logger.warning(
                            "Error checking vector store %s: %s",
                            store_id,
                            e,
                        )

            self.selected_vector_store_id = store_id
            self.selected_vector_store_name = store_name
            yield FileManagerState.load_files
        finally:
            self.loading = False

    async def _cleanup_expired_vector_store(
        self, store_id: str
    ) -> AsyncGenerator[Any, Any]:
        """Clean up an expired vector store: delete DB records and OpenAI files."""
        try:
            # Get files from DB to know which OpenAI files to delete
            async with get_asyncdb_session() as session:
                files = await file_upload_repo.find_by_vector_store(session, store_id)
                openai_file_ids = [f.openai_file_id for f in files]

                # Delete files from OpenAI
                openai_service = get_openai_client_service()
                if openai_service.is_available:
                    client = openai_service.create_client()
                    if client:
                        for file_id in openai_file_ids:
                            try:
                                await client.files.delete(file_id=file_id)
                                logger.debug(
                                    "Deleted expired file from OpenAI: %s", file_id
                                )
                            except Exception as e:
                                logger.warning(
                                    "Failed to delete file %s from OpenAI: %s",
                                    file_id,
                                    e,
                                )

                # Delete records from database
                await file_upload_repo.delete_by_vector_store(session, store_id)
                await session.commit()
                logger.info(
                    "Cleaned up %d files for expired vector store %s",
                    len(files),
                    store_id,
                )

            # Reset selection and reload
            self.selected_vector_store_id = ""
            self.selected_vector_store_name = ""
            yield rx.toast.info(
                INFO_VECTOR_STORE_EXPIRED,
                position="top-right",
            )
            yield FileManagerState.load_vector_stores

        except Exception as e:
            logger.error("Failed to cleanup expired vector store %s: %s", store_id, e)
            yield rx.toast.error(
                "Fehler beim Bereinigen des abgelaufenen Vector Stores.",
                position="top-right",
            )

    async def load_files(self) -> AsyncGenerator[Any, Any]:
        """Load files for the selected vector store."""
        if not self.selected_vector_store_id:
            self.files = []
            return

        self.loading = True
        try:
            # Cache for user names to avoid repeated queries
            user_cache: dict[int, str] = {}

            async with get_asyncdb_session() as session:
                file_uploads = await file_upload_repo.find_by_vector_store(
                    session, self.selected_vector_store_id
                )

                files_list = []
                for upload in file_uploads:
                    # Get user name from cache or database
                    if upload.user_id not in user_cache:
                        user = await user_repo.find_by_id(session, upload.user_id)
                        user_cache[upload.user_id] = (
                            user.name or user.email if user else "Unbekannt"
                        )

                    # Format file size for display
                    formatted_size, size_suffix = format_file_size_for_display(
                        upload.file_size
                    )

                    files_list.append(
                        FileInfo(
                            id=upload.id,
                            filename=upload.filename,
                            created_at=upload.created_at.strftime("%d.%m.%Y %H:%M"),
                            user_name=user_cache[upload.user_id],
                            file_size=upload.file_size,
                            formatted_size=formatted_size,
                            size_suffix=size_suffix,
                            openai_file_id=upload.openai_file_id,
                        )
                    )

                self.files = files_list

            logger.debug(
                "Loaded %d files for vector store %s",
                len(self.files),
                self.selected_vector_store_id,
            )

        except Exception as e:
            logger.error("Failed to load files: %s", e)
            yield rx.toast.error(
                ERROR_LOAD_FILES,
                position="top-right",
            )
        finally:
            self.loading = False

    async def load_openai_files(self) -> AsyncGenerator[Any, Any]:
        """Load files directly from OpenAI API."""
        self.loading = True
        try:
            openai_service = get_openai_client_service()
            if not openai_service.is_available:
                yield rx.toast.error(
                    ERROR_OPENAI_NOT_CONFIGURED,
                    position="top-right",
                )
                return

            client = openai_service.create_client()
            if not client:
                yield rx.toast.error(
                    ERROR_OPENAI_NOT_CONFIGURED,
                    position="top-right",
                )
                return

            # Fetch files from OpenAI
            response = await client.files.list()
            openai_files_list = []

            for file in response.data:
                # Format file size for display (OpenAI uses 'bytes' attribute)
                formatted_size, size_suffix = format_file_size_for_display(file.bytes)

                # Convert Unix timestamp to formatted date
                created_at = _format_unix_timestamp(file.created_at)
                expires_at = _format_unix_timestamp(getattr(file, "expires_at", None))

                openai_files_list.append(
                    OpenAIFileInfo(
                        openai_id=file.id,
                        filename=file.filename,
                        created_at=created_at,
                        expires_at=expires_at,
                        purpose=file.purpose or "-",
                        file_size=file.bytes,
                        formatted_size=formatted_size,
                        size_suffix=size_suffix,
                    )
                )

            self.openai_files = openai_files_list
            logger.debug("Loaded %d files from OpenAI", len(self.openai_files))

        except Exception as e:
            logger.error("Failed to load OpenAI files: %s", e)
            yield rx.toast.error(
                ERROR_LOAD_OPENAI_FILES,
                position="top-right",
            )
        finally:
            self.loading = False

    async def delete_file(self, file_id: int) -> AsyncGenerator[Any, Any]:
        """Delete a file from OpenAI and the database."""
        self.deleting_file_id = file_id

        try:
            # Find the file to get OpenAI file ID
            file_info = self._get_file_by_id(file_id)
            if not file_info:
                yield rx.toast.error(
                    ERROR_FILE_NOT_FOUND,
                    position="top-right",
                )
                return

            openai_file_id = file_info.openai_file_id
            filename = file_info.filename

            # Delete from OpenAI
            try:
                openai_service = get_openai_client_service()
                if openai_service.is_available:
                    client = openai_service.create_client()
                    if client:
                        await client.files.delete(file_id=openai_file_id)
                        logger.debug("Deleted OpenAI file: %s", openai_file_id)
                else:
                    logger.warning(
                        "OpenAI API key not configured, skipping OpenAI deletion"
                    )
            except Exception as e:
                logger.warning(
                    "Failed to delete file from OpenAI %s: %s",
                    openai_file_id,
                    e,
                )
                # Continue with DB deletion even if OpenAI deletion fails

            # Delete from database
            async with get_asyncdb_session() as session:
                deleted = await file_upload_repo.delete_file(session, file_id)
                if deleted:
                    await session.commit()
                    logger.debug("Deleted file record: %s", file_id)
                else:
                    yield rx.toast.error(
                        ERROR_DELETE_FAILED,
                        position="top-right",
                    )
                    return

            yield rx.toast.success(
                f"Datei '{filename}' wurde gelöscht.",
                position="top-right",
            )

            # Reload files
            yield FileManagerState.load_files

            # Check if vector store is now empty and reload stores
            if not self.files:
                self.selected_vector_store_id = ""
                yield FileManagerState.load_vector_stores

        except Exception as e:
            logger.error("Failed to delete file %d: %s", file_id, e)
            yield rx.toast.error(
                ERROR_DELETE_GENERAL,
                position="top-right",
            )
        finally:
            self.deleting_file_id = None

    async def delete_openai_file(self, openai_id: str) -> AsyncGenerator[Any, Any]:
        """Delete a file directly from OpenAI API."""
        self.deleting_openai_file_id = openai_id

        try:
            file_info = self._get_openai_file_by_id(openai_id)
            if not file_info:
                yield rx.toast.error(
                    ERROR_FILE_NOT_FOUND,
                    position="top-right",
                )
                return

            filename = file_info.filename

            openai_service = get_openai_client_service()
            if not openai_service.is_available:
                yield rx.toast.error(
                    ERROR_OPENAI_NOT_CONFIGURED,
                    position="top-right",
                )
                return

            client = openai_service.create_client()
            if not client:
                yield rx.toast.error(
                    ERROR_OPENAI_NOT_CONFIGURED,
                    position="top-right",
                )
                return

            await client.files.delete(file_id=openai_id)
            logger.debug("Deleted OpenAI file: %s", openai_id)

            yield rx.toast.success(
                f"Datei '{filename}' wurde von OpenAI gelöscht.",
                position="top-right",
            )

            # Reload OpenAI files
            yield FileManagerState.load_openai_files

        except Exception as e:
            logger.error("Failed to delete OpenAI file %s: %s", openai_id, e)
            yield rx.toast.error(
                ERROR_DELETE_OPENAI_FILE,
                position="top-right",
            )
        finally:
            self.deleting_openai_file_id = None

    def open_cleanup_modal(self) -> None:
        """Open the cleanup modal and reset stats."""
        self.cleanup_stats = CleanupStats()
        self.cleanup_modal_open = True

    def close_cleanup_modal(self) -> None:
        """Close the cleanup modal."""
        self.cleanup_modal_open = False

    def set_cleanup_modal_open(self, is_open: bool) -> None:
        """Set the cleanup modal open state.

        Used by on_open_change handler which receives a boolean.
        """
        self.cleanup_modal_open = is_open

    @rx.event(background=True)
    async def start_cleanup(self) -> AsyncGenerator[Any, Any]:
        """Start the cleanup process and track progress.

        This is a background task that iterates through the run_cleanup()
        async generator and updates the cleanup_stats for each progress update.
        """
        async with self:
            self.cleanup_running = True
            self.cleanup_stats = CleanupStats(status="starting")

        try:
            async for stats in run_cleanup():
                async with self:
                    self.cleanup_stats = CleanupStats(
                        status=stats.get("status", "checking"),
                        vector_stores_checked=stats.get("vector_stores_checked", 0),
                        vector_stores_expired=stats.get("vector_stores_expired", 0),
                        vector_stores_deleted=stats.get("vector_stores_deleted", 0),
                        threads_updated=stats.get("threads_updated", 0),
                        current_vector_store=stats.get("current_vector_store"),
                        total_vector_stores=stats.get("total_vector_stores", 0),
                        error=stats.get("error"),
                    )

            async with self:
                self.cleanup_running = False
                if self.cleanup_stats.status == "completed":
                    yield rx.toast.success(
                        INFO_CLEANUP_COMPLETED,
                        position="top-right",
                    )
                    # Reload vector stores to reflect changes
                    yield FileManagerState.load_vector_stores

        except Exception as e:
            logger.error("Cleanup failed: %s", e)
            async with self:
                self.cleanup_running = False
                self.cleanup_stats = CleanupStats(
                    status="error",
                    error=str(e),
                )
            yield rx.toast.error(
                ERROR_CLEANUP_FAILED,
                position="top-right",
            )
