"""FastAPI router for file cleanup with APScheduler integration.

Provides scheduled cleanup of expired OpenAI vector stores and associated files.
The scheduler runs as part of the FastAPI app lifecycle.
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from fastapi import APIRouter, HTTPException
from openai import AsyncOpenAI
from sqlalchemy import select

from appkit_assistant.backend.models import AssistantFileUpload, AssistantThread
from appkit_assistant.configuration import AssistantConfig, FileUploadConfig
from appkit_commons.database.session import get_asyncdb_session
from appkit_commons.registry import service_registry

logger = logging.getLogger(__name__)

# Global scheduler instance
_scheduler: AsyncIOScheduler | None = None
_cleanup_service: "FileCleanupService | None" = None


class FileCleanupService:
    """Service for cleaning up expired files and vector stores."""

    def __init__(
        self,
        client: AsyncOpenAI,
        config: FileUploadConfig,
    ) -> None:
        """Initialize the cleanup service.

        Args:
            client: AsyncOpenAI client for API calls.
            config: File upload configuration.
        """
        self.client = client
        self.config = config

    async def cleanup_expired_files(self) -> dict[str, int]:
        """Clean up expired vector stores and their associated files.

        This method:
        1. Gets all unique vector store IDs from the database
        2. Checks if each vector store still exists in OpenAI
        3. For expired/deleted stores: deletes OpenAI files and DB records
        4. Clears vector_store_id from threads with expired stores

        Returns:
            Statistics about the cleanup operation.
        """
        stats = {
            "vector_stores_checked": 0,
            "vector_stores_expired": 0,
            "files_deleted": 0,
            "db_records_deleted": 0,
            "threads_updated": 0,
        }

        try:
            # Get all unique vector store IDs from file uploads
            async with get_asyncdb_session() as session:
                result = await session.execute(
                    select(AssistantFileUpload.vector_store_id).distinct()
                )
                vector_store_ids = [row[0] for row in result.all()]

            logger.info(
                "Checking %d vector stores for expiration",
                len(vector_store_ids),
            )
            stats["vector_stores_checked"] = len(vector_store_ids)

            for vs_id in vector_store_ids:
                is_expired = await self._check_vector_store_expired(vs_id)

                if is_expired:
                    stats["vector_stores_expired"] += 1
                    cleanup_stats = await self._cleanup_vector_store(vs_id)
                    stats["files_deleted"] += cleanup_stats["files_deleted"]
                    stats["db_records_deleted"] += cleanup_stats["db_records_deleted"]
                    stats["threads_updated"] += cleanup_stats["threads_updated"]

            logger.info("Cleanup completed: %s", stats)
            return stats

        except Exception as e:
            logger.error("Error during file cleanup: %s", e)
            raise

    async def _check_vector_store_expired(self, vector_store_id: str) -> bool:
        """Check if a vector store has expired or been deleted.

        Args:
            vector_store_id: The OpenAI vector store ID to check.

        Returns:
            True if the vector store is expired/deleted, False otherwise.
        """
        try:
            vs = await self.client.vector_stores.retrieve(
                vector_store_id=vector_store_id
            )
            # Check if expired
            if vs.status == "expired":
                logger.debug("Vector store %s has expired", vector_store_id)
                return True
            return False
        except Exception as e:
            # If we can't retrieve it, assume it's been deleted
            error_str = str(e).lower()
            if "not found" in error_str or "404" in error_str:
                logger.debug(
                    "Vector store %s not found, treating as expired",
                    vector_store_id,
                )
                return True
            # Log other errors but don't treat as expired
            logger.warning(
                "Error checking vector store %s: %s",
                vector_store_id,
                e,
            )
            return False

    async def _cleanup_vector_store(self, vector_store_id: str) -> dict[str, int]:
        """Clean up all resources associated with an expired vector store.

        Args:
            vector_store_id: The expired vector store ID.

        Returns:
            Statistics about the cleanup.
        """
        stats = {
            "files_deleted": 0,
            "db_records_deleted": 0,
            "threads_updated": 0,
        }

        async with get_asyncdb_session() as session:
            # Get all file uploads for this vector store
            result = await session.execute(
                select(AssistantFileUpload).where(
                    AssistantFileUpload.vector_store_id == vector_store_id
                )
            )
            file_uploads = list(result.scalars().all())

            # Delete files from OpenAI
            for upload in file_uploads:
                try:
                    await self.client.files.delete(file_id=upload.openai_file_id)
                    stats["files_deleted"] += 1
                    logger.debug("Deleted OpenAI file: %s", upload.openai_file_id)
                except Exception as e:
                    logger.warning(
                        "Failed to delete file %s: %s",
                        upload.openai_file_id,
                        e,
                    )

            # Delete database records
            for upload in file_uploads:
                await session.delete(upload)
                stats["db_records_deleted"] += 1

            # Clear vector_store_id from associated threads
            thread_result = await session.execute(
                select(AssistantThread).where(
                    AssistantThread.vector_store_id == vector_store_id
                )
            )
            threads = list(thread_result.scalars().all())

            for thread in threads:
                thread.vector_store_id = None
                session.add(thread)
                stats["threads_updated"] += 1
                logger.debug(
                    "Cleared vector_store_id from thread %s",
                    thread.thread_id,
                )

            await session.commit()

        logger.info(
            "Cleaned up vector store %s: %s",
            vector_store_id,
            stats,
        )
        return stats


def _get_openai_client() -> AsyncOpenAI | None:
    """Get an OpenAI client from configuration."""
    try:
        config: AssistantConfig | None = service_registry().get(AssistantConfig)
        if not config:
            logger.warning("AssistantConfig not found in service registry")
            return None

        api_key = (
            config.openai_api_key.get_secret_value() if config.openai_api_key else None
        )
        base_url = config.openai_base_url

        if not api_key:
            logger.warning("OpenAI API key not configured")
            return None

        # Check if Azure
        if base_url and "azure" in base_url.lower():
            return AsyncOpenAI(
                api_key=api_key,
                base_url=f"{base_url}/openai/v1",
                default_query={"api-version": "preview"},
            )
        if base_url:
            return AsyncOpenAI(api_key=api_key, base_url=base_url)
        return AsyncOpenAI(api_key=api_key)

    except Exception as e:
        logger.error("Failed to create OpenAI client: %s", e)
        return None


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
        stats = await _cleanup_service.cleanup_expired_files()
        logger.info("Scheduled cleanup completed: %s", stats)
    except Exception as e:
        logger.error("Scheduled cleanup failed: %s", e)


def start_scheduler() -> None:
    """Start the APScheduler for file cleanup."""
    global _scheduler, _cleanup_service  # noqa: PLW0603

    # Get configuration
    config = _get_file_upload_config()
    client = _get_openai_client()

    if not client:
        logger.warning("OpenAI client not available, file cleanup scheduler disabled")
        return

    _cleanup_service = FileCleanupService(client=client, config=config)

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


@asynccontextmanager
async def file_cleanup_lifespan(_app: Any) -> AsyncGenerator[None, None]:
    """FastAPI lifespan context manager for file cleanup scheduler.

    Usage:
        from appkit_assistant.api.file_cleanup_api import file_cleanup_lifespan

        app = FastAPI(lifespan=file_cleanup_lifespan)
    """
    start_scheduler()
    yield
    stop_scheduler()


# Create router
router = APIRouter(prefix="/assistant/files", tags=["assistant-files"])


@router.post("/cleanup")
async def trigger_cleanup() -> dict[str, Any]:
    """Manually trigger file cleanup.

    This endpoint allows administrators to trigger the cleanup process
    without waiting for the scheduled job.

    Returns:
        Cleanup statistics.
    """
    global _cleanup_service  # noqa: PLW0603

    if not _cleanup_service:
        # Try to initialize on-demand
        client = _get_openai_client()
        config = _get_file_upload_config()

        if not client:
            raise HTTPException(
                status_code=503,
                detail="OpenAI client not available",
            )

        _cleanup_service = FileCleanupService(client=client, config=config)

    try:
        stats = await _cleanup_service.cleanup_expired_files()
        return {"status": "success", "stats": stats}
    except Exception as e:
        logger.error("Manual cleanup failed: %s", e)
        raise HTTPException(
            status_code=500,
            detail=f"Cleanup failed: {e}",
        ) from e


@router.get("/status")
async def get_scheduler_status() -> dict[str, Any]:
    """Get the status of the file cleanup scheduler.

    Returns:
        Scheduler status information.
    """
    if not _scheduler:
        return {
            "running": False,
            "message": "Scheduler not initialized",
        }

    job = _scheduler.get_job("file_cleanup")
    if not job:
        return {
            "running": True,
            "message": "Scheduler running but cleanup job not found",
        }

    return {
        "running": _scheduler.running,
        "next_run": str(job.next_run_time) if job.next_run_time else None,
        "job_id": job.id,
        "job_name": job.name,
    }
