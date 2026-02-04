"""File cleanup scheduler with APScheduler integration.

Provides scheduled cleanup of expired OpenAI vector stores and associated files.
The scheduler runs as part of the FastAPI app lifecycle.

Note: HTTP endpoints have been removed for security. Use `run_cleanup()` for
manual triggers from Reflex UI or internal code.
"""

import logging
from collections.abc import AsyncGenerator
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from openai import AsyncOpenAI, NotFoundError

from appkit_assistant.backend.database.repositories import (
    file_upload_repo,
    thread_repo,
)
from appkit_assistant.backend.services.file_upload_service import FileUploadService
from appkit_assistant.backend.services.openai_client_service import (
    OpenAIClientService,
)
from appkit_assistant.configuration import AssistantConfig, FileUploadConfig
from appkit_commons.database.session import get_asyncdb_session
from appkit_commons.registry import service_registry

logger = logging.getLogger(__name__)

# Global scheduler instance
_scheduler: AsyncIOScheduler | None = None
_cleanup_service: "FileCleanupService | None" = None


class FileCleanupService:
    """Service for cleaning up expired files and vector stores.

    Delegates actual cleanup operations to FileUploadService.
    """

    def __init__(
        self,
        client: AsyncOpenAI,
        file_upload_service: FileUploadService,
        config: FileUploadConfig,
    ) -> None:
        """Initialize the cleanup service.

        Args:
            client: AsyncOpenAI client for checking vector store status.
            file_upload_service: Service for file/vector store operations.
            config: File upload configuration.
        """
        self._client = client
        self._file_upload_service = file_upload_service
        self.config = config

    async def cleanup_expired_files(
        self,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Clean up expired vector stores and their associated files.

        This method:
        1. Gets all unique vector store IDs from the database
        2. Checks if each vector store still exists in OpenAI
        3. For expired/deleted stores: delegates to FileUploadService
        4. Clears vector_store_id from threads with expired stores

        Yields:
            Progress updates with current statistics and status.
        """
        stats = {
            "vector_stores_checked": 0,
            "vector_stores_expired": 0,
            "vector_stores_deleted": 0,
            "files_found": 0,
            "files_deleted": 0,
            "threads_updated": 0,
            "current_vector_store": None,
            "total_vector_stores": 0,
            "status": "starting",
        }

        try:
            # Get all unique vector store IDs from BOTH file uploads AND threads
            async with get_asyncdb_session() as session:
                # Vector stores from file uploads
                file_stores = await file_upload_repo.find_unique_vector_stores(session)
                file_store_ids = {store_id for store_id, _ in file_stores if store_id}

                # Vector stores from threads (may have orphaned references)
                thread_store_ids = set(
                    await thread_repo.find_unique_vector_store_ids(session)
                )

                # Combine both sets
                vector_store_ids = list(file_store_ids | thread_store_ids)

            stats["total_vector_stores"] = len(vector_store_ids)
            stats["status"] = "checking"
            logger.info(
                "Checking %d vector stores for expiration",
                len(vector_store_ids),
            )
            yield stats.copy()

            for vs_id in vector_store_ids:
                stats["current_vector_store"] = vs_id
                stats["vector_stores_checked"] += 1
                yield stats.copy()

                is_expired = await self._check_vector_store_expired(vs_id)

                if is_expired:
                    stats["vector_stores_expired"] += 1
                    stats["status"] = "deleting"
                    yield stats.copy()

                    # Delegate cleanup to FileUploadService
                    result = await self._file_upload_service.delete_vector_store(vs_id)
                    if result["deleted"]:
                        stats["vector_stores_deleted"] += 1
                    stats["files_found"] += result["files_found"]
                    stats["files_deleted"] += result["files_deleted"]
                    # Clear vector_store_id from associated threads
                    threads_updated = await self._clear_thread_vector_store_ids(vs_id)
                    stats["threads_updated"] += threads_updated
                    stats["status"] = "checking"
                    yield stats.copy()

            stats["status"] = "completed"
            stats["current_vector_store"] = None
            logger.info("Cleanup completed: %s", stats)
            yield stats.copy()

        except Exception as e:
            stats["status"] = "error"
            stats["error"] = str(e)
            logger.error("Error during file cleanup: %s", e)
            yield stats.copy()
            raise

    async def _check_vector_store_expired(self, vector_store_id: str) -> bool:
        """Check if a vector store has expired or been deleted.

        Args:
            vector_store_id: The OpenAI vector store ID to check.

        Returns:
            True if the vector store is expired/deleted, False otherwise.
        """
        try:
            vector_store = await self._client.vector_stores.retrieve(
                vector_store_id=vector_store_id
            )
            # Check if the vector store has expired status
            if vector_store.status == "expired":
                logger.info(
                    "Vector store %s has expired status",
                    vector_store_id,
                )
                return True
            return False
        except NotFoundError:
            logger.info(
                "Vector store %s not found (deleted)",
                vector_store_id,
            )
            return True

    async def _clear_thread_vector_store_ids(self, vector_store_id: str) -> int:
        """Clear vector_store_id from all threads associated with the store.

        Args:
            vector_store_id: The vector store ID to clear from threads.

        Returns:
            Number of threads updated.
        """
        async with get_asyncdb_session() as session:
            updated_count = await thread_repo.clear_vector_store_id(
                session, vector_store_id
            )
            await session.commit()
            logger.debug(
                "Cleared vector_store_id from %d threads for store %s",
                updated_count,
                vector_store_id,
            )

        return updated_count


def _get_file_upload_config() -> FileUploadConfig:
    """Get file upload configuration."""
    try:
        config: AssistantConfig | None = service_registry().get(AssistantConfig)
        if config:
            return config.file_upload
    except Exception as e:
        logger.warning("Failed to get file upload config: %s", e)
    return FileUploadConfig()


async def _run_cleanup_job() -> None:
    """Scheduled job to run file cleanup."""
    if not _cleanup_service:
        logger.warning("Cleanup service not initialized, skipping cleanup job")
        return

    try:
        logger.info("Starting scheduled file cleanup")
        final_stats: dict[str, Any] = {}
        async for progress in _cleanup_service.cleanup_expired_files():
            final_stats = progress  # Keep updating to get final stats
        logger.info("Scheduled cleanup completed: %s", final_stats)
    except Exception as e:
        logger.error("Scheduled cleanup failed: %s", e)


def start_scheduler() -> None:
    """Start the APScheduler for file cleanup."""
    global _scheduler, _cleanup_service  # noqa: PLW0603

    # Get configuration
    config = _get_file_upload_config()

    # Create OpenAI client via service
    client_service = OpenAIClientService.from_config()
    if not client_service.is_available:
        logger.warning("OpenAI client not available, file cleanup scheduler disabled")
        return

    client = client_service.create_client()
    if not client:
        logger.warning("Failed to create OpenAI client, cleanup scheduler disabled")
        return

    # Create FileUploadService and FileCleanupService
    file_upload_service = FileUploadService(client=client, config=config)
    _cleanup_service = FileCleanupService(
        client=client, file_upload_service=file_upload_service, config=config
    )

    # Create scheduler
    _scheduler = AsyncIOScheduler()

    # Add cleanup job
    _scheduler.add_job(
        _run_cleanup_job,
        trigger=IntervalTrigger(minutes=config.cleanup_interval_minutes),
        id="file_cleanup",
        name="Clean up expired OpenAI files and vector stores",
        replace_existing=True,
    )

    _scheduler.start()
    logger.info(
        "File cleanup scheduler started (interval: %d minutes)",
        config.cleanup_interval_minutes,
    )


def stop_scheduler() -> None:
    """Stop the APScheduler."""
    global _scheduler  # noqa: PLW0603

    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("File cleanup scheduler stopped")


async def run_cleanup() -> AsyncGenerator[dict[str, Any], None]:
    """Manually trigger file cleanup.

    This async generator can be called from Reflex UI (e.g., filemanager) to
    trigger the cleanup process and receive real-time progress updates.

    Yields:
        Dictionary with cleanup progress including:
        - status: 'starting', 'checking', 'deleting', 'completed', or 'error'
        - vector_stores_checked: number checked so far
        - vector_stores_expired: number found expired
        - vector_stores_deleted: number successfully deleted
        - threads_updated: number of threads cleared
        - current_vector_store: ID being processed (or None)
        - total_vector_stores: total count to process
        - error: error message (only if status is 'error')
    """
    global _cleanup_service  # noqa: PLW0603

    if not _cleanup_service:
        # Try to initialize on-demand
        config = _get_file_upload_config()
        client_service = OpenAIClientService.from_config()

        if not client_service.is_available:
            logger.warning("OpenAI client not available for manual cleanup")
            yield {
                "status": "error",
                "error": "OpenAI client not available",
            }
            return

        client = client_service.create_client()
        if not client:
            logger.warning("Failed to create OpenAI client for manual cleanup")
            yield {
                "status": "error",
                "error": "Failed to create OpenAI client",
            }
            return

        file_upload_service = FileUploadService(client=client, config=config)
        _cleanup_service = FileCleanupService(
            client=client, file_upload_service=file_upload_service, config=config
        )

    try:
        logger.info("Starting manual file cleanup")
        async for stats in _cleanup_service.cleanup_expired_files():
            yield stats
        logger.info("Manual cleanup completed")
    except Exception as e:
        logger.error("Manual cleanup failed: %s", e)
        yield {"status": "error", "error": str(e)}
