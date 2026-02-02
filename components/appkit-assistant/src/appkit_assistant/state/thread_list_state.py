"""Thread list state management for the assistant.

This module contains ThreadListState which manages the thread list sidebar:
- Loading thread summaries from database
- Adding new threads to the list (called by ThreadState)
- Deleting threads from database and list
- Tracking which thread is currently active/loading
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, Any

import reflex as rx

from appkit_assistant.backend.database.models import ThreadStatus
from appkit_assistant.backend.database.repositories import thread_repo
from appkit_assistant.backend.schemas import ThreadModel
from appkit_commons.database.session import get_asyncdb_session
from appkit_user.authentication.states import UserSession

if TYPE_CHECKING:
    from appkit_assistant.state.thread_state import ThreadState

logger = logging.getLogger(__name__)


class ThreadListState(rx.State):
    """State for managing the thread list sidebar.

    Responsibilities:
    - Loading thread summaries from database on initialization
    - Adding new threads to the list (called by ThreadState)
    - Deleting threads from database and list
    - Tracking active/loading thread IDs

    Does NOT:
    - Create new threads (ThreadState.new_thread does this)
    - Load full thread data (ThreadState.get_thread does this)
    - Persist thread data (ThreadState handles this)
    """

    # Public state
    threads: list[ThreadModel] = []
    active_thread_id: str = ""
    loading_thread_id: str = ""
    loading: bool = True

    # Private state
    _initialized: bool = False
    _current_user_id: str = ""

    # -------------------------------------------------------------------------
    # Computed properties
    # -------------------------------------------------------------------------

    @rx.var
    def has_threads(self) -> bool:
        """Check if there are any threads."""
        return len(self.threads) > 0

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    @rx.event(background=True)
    async def initialize(self) -> AsyncGenerator[Any, Any]:
        """Initialize thread list - load summaries from database."""
        async with self:
            if self._initialized or self.loading:
                return
            self.loading = True
        yield

        async for _ in self._load_threads():
            yield

    async def _load_threads(self) -> AsyncGenerator[Any, Any]:
        """Load thread summaries from database (internal)."""
        # Late import to avoid circular dependency
        from appkit_assistant.state.thread_state import ThreadState  # noqa: PLC0415

        async with self:
            user_session: UserSession = await self.get_state(UserSession)
            current_user_id = user_session.user.user_id if user_session.user else ""
            is_authenticated = await user_session.is_authenticated

            # Handle user change
            if self._current_user_id != current_user_id:
                logger.debug(
                    "User changed from '%s' to '%s' - resetting state",
                    self._current_user_id or "(none)",
                    current_user_id or "(none)",
                )
                self._initialized = False
                self._current_user_id = current_user_id
                self._clear_threads()
                yield

                # Reset ThreadState
                thread_state: ThreadState = await self.get_state(ThreadState)
                await thread_state.new_thread()

            if self._initialized:
                self.loading = False
                yield
                return

            # Check authentication
            if not is_authenticated:
                self._clear_threads()
                self._current_user_id = ""
                self.loading = False
                yield
                return

            user_id = user_session.user.user_id if user_session.user else None

        if not user_id:
            async with self:
                self.loading = False
            yield
            return

        # Fetch threads from database
        try:
            async with get_asyncdb_session() as session:
                thread_entities = await thread_repo.find_summaries_by_user(
                    session, user_id
                )

                # Convert entities to models inside the session context
                threads = [
                    ThreadModel(
                        thread_id=t.thread_id,
                        title=t.title,
                        state=ThreadStatus(t.state),
                        ai_model=t.ai_model,
                        active=t.active,
                        messages=[],
                    )
                    for t in thread_entities
                ]

            async with self:
                self.threads = threads
                self._initialized = True
                logger.debug("Loaded %d threads", len(threads))
            yield
        except Exception as e:
            logger.error("Error loading threads: %s", e)
            async with self:
                self._clear_threads()
            yield
        finally:
            async with self:
                self.loading = False
            yield

    # -------------------------------------------------------------------------
    # Thread list management
    # -------------------------------------------------------------------------

    async def add_thread(self, thread: ThreadModel) -> None:
        """Add a new thread to the list.

        Called by ThreadState via get_state() after first successful response.
        Not an @rx.event so it can be called directly from background tasks.
        Does not persist to DB - ThreadState handles persistence.

        Args:
            thread: The thread model to add.
        """
        # Check if already in list (idempotent)
        existing = next(
            (t for t in self.threads if t.thread_id == thread.thread_id),
            None,
        )
        if existing:
            logger.debug("Thread already in list: %s", thread.thread_id)
            return

        # Deactivate other threads
        self.threads = [
            ThreadModel(**{**t.model_dump(), "active": False}) for t in self.threads
        ]
        # Add new thread at beginning (mark as active)
        thread.active = True
        self.threads = [thread, *self.threads]
        self.active_thread_id = thread.thread_id
        logger.debug("Added thread to list: %s", thread.thread_id)

    @rx.event(background=True)
    async def delete_thread(self, thread_id: str) -> AsyncGenerator[Any, Any]:
        """Delete a thread from database and list.

        If the deleted thread was the active thread, resets ThreadState
        to show an empty thread. Also triggers background cleanup of
        associated OpenAI files and vector store.

        Args:
            thread_id: The ID of the thread to delete.
        """
        # Late import to avoid circular dependency
        from appkit_assistant.state.thread_state import ThreadState  # noqa: PLC0415

        async with self:
            user_session: UserSession = await self.get_state(UserSession)
            is_authenticated = await user_session.is_authenticated
            user_id = user_session.user.user_id if user_session.user else None

            thread_to_delete = next(
                (t for t in self.threads if t.thread_id == thread_id), None
            )
            was_active = thread_id == self.active_thread_id

            if thread_to_delete:
                self.loading_thread_id = thread_id
                yield

        if not is_authenticated or not user_id:
            async with self:
                self.loading_thread_id = ""
            return

        if not thread_to_delete:
            yield rx.toast.error(
                "Chat nicht gefunden.", position="top-right", close_button=True
            )
            logger.warning("Thread %s not found for deletion", thread_id)
            async with self:
                self.loading_thread_id = ""
            return

        # Capture thread info for cleanup before deletion
        thread_db_id: int | None = None
        vector_store_id: str | None = None
        openai_file_ids: list[str] = []

        try:
            # Get thread details and file IDs from database BEFORE deletion
            async with get_asyncdb_session() as session:
                db_thread = await thread_repo.find_by_thread_id_and_user(
                    session, thread_id, user_id
                )
                if db_thread:
                    thread_db_id = db_thread.id
                    vector_store_id = db_thread.vector_store_id

                    # Fetch file IDs before deletion (cascade will delete records)
                    from appkit_assistant.backend.database.repositories import (  # noqa: PLC0415
                        file_upload_repo,
                    )

                    files = await file_upload_repo.find_by_thread(session, thread_db_id)
                    openai_file_ids = [f.openai_file_id for f in files]

                # Delete thread from database (cascades to file records)
                await thread_repo.delete_by_thread_id_and_user(
                    session, thread_id, user_id
                )

            async with self:
                # Remove from list immediately
                self.threads = [t for t in self.threads if t.thread_id != thread_id]
                self.loading_thread_id = ""

                if was_active:
                    self.active_thread_id = ""
                    # Reset ThreadState to empty thread
                    thread_state: ThreadState = await self.get_state(ThreadState)
                    await thread_state.new_thread()

            yield rx.toast.info(
                f"Chat '{thread_to_delete.title}' gelöscht.",
                position="top-right",
                close_button=True,
            )

            # Trigger background cleanup of OpenAI files (fire-and-forget)
            if openai_file_ids:
                yield ThreadListState.cleanup_thread_openai_files(
                    openai_file_ids, vector_store_id
                )
            elif vector_store_id:
                # No files but has vector store - clean it up
                yield ThreadListState.cleanup_thread_openai_files([], vector_store_id)

        except Exception as e:
            async with self:
                self.loading_thread_id = ""
            logger.error("Error deleting thread %s: %s", thread_id, e)
            yield rx.toast.error(
                "Fehler beim Löschen des Chats.",
                position="top-right",
                close_button=True,
            )

    @rx.event(background=True)
    async def cleanup_thread_openai_files(
        self, openai_file_ids: list[str], vector_store_id: str | None
    ) -> AsyncGenerator[Any, Any]:
        """Background task to clean up OpenAI files for a deleted thread.

        This runs in the background so the user can continue working.
        Failures are logged but not shown to the user.

        Note: This is called AFTER DB records are cascade-deleted, so it only
        handles OpenAI resource cleanup.

        Args:
            openai_file_ids: List of OpenAI file IDs to delete.
            vector_store_id: The vector store ID to delete.
        """
        from appkit_assistant.backend.services.file_upload_service import (  # noqa: PLC0415
            FileUploadService,
        )
        from appkit_assistant.backend.services.openai_client_service import (  # noqa: PLC0415
            get_openai_client_service,
        )

        openai_service = get_openai_client_service()
        if not openai_service.is_available:
            logger.warning(
                "OpenAI not configured, skipping file cleanup for %d files",
                len(openai_file_ids),
            )
            return

        client = openai_service.create_client()
        if not client:
            logger.warning(
                "Could not create OpenAI client, skipping file cleanup for %d files",
                len(openai_file_ids),
            )
            return

        file_service = FileUploadService(client)

        # Delete vector store (which deletes files FROM store first)
        if vector_store_id:
            await file_service.delete_vector_store(vector_store_id)

        # Delete files from OpenAI (independent cleanup)
        if openai_file_ids:
            await file_service.delete_files(openai_file_ids)

        yield  # Required for async generator

    # -------------------------------------------------------------------------
    # Logout handling
    # -------------------------------------------------------------------------

    @rx.event
    async def reset_on_logout(self) -> None:
        """Reset state on user logout to prevent data leakage."""
        # Late import to avoid circular dependency
        from appkit_assistant.state.thread_state import ThreadState  # noqa: PLC0415

        logger.debug(
            "Resetting ThreadListState on logout for user: %s",
            self._current_user_id,
        )

        self._clear_threads()
        self.loading = False
        self._initialized = False
        self._current_user_id = ""

        # Reset ThreadState
        thread_state: ThreadState = await self.get_state(ThreadState)
        await thread_state.new_thread()

        logger.debug("ThreadListState reset complete")

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    def _clear_threads(self) -> None:
        """Clear thread-related state."""
        self.threads = []
        self.active_thread_id = ""
        self.loading_thread_id = ""
