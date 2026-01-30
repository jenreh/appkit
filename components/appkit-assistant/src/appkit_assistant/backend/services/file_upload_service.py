"""File upload service for managing OpenAI file uploads and vector stores.

Handles uploading files to OpenAI, creating/managing vector stores per thread,
and tracking uploads in the database for cleanup purposes.
"""

import asyncio
import logging
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI
from sqlalchemy import select

from appkit_assistant.backend.models import AssistantFileUpload, AssistantThread
from appkit_assistant.configuration import FileUploadConfig
from appkit_commons.database.session import get_asyncdb_session

logger = logging.getLogger(__name__)


class FileUploadError(Exception):
    """Raised when file upload operations fail."""


class FileUploadService:
    """Service for managing file uploads to OpenAI and vector store lifecycle.

    Handles:
    - Uploading files to OpenAI with size/count validation
    - Creating vector stores per thread with configurable expiration
    - Adding files to existing vector stores
    - Tracking uploads in database for cleanup
    - Retry logic with cleanup on failure
    """

    def __init__(
        self,
        client: AsyncOpenAI,
        config: FileUploadConfig | None = None,
    ) -> None:
        """Initialize the file upload service.

        Args:
            client: AsyncOpenAI client instance (shared from processor).
            config: File upload configuration. Uses defaults if not provided.
        """
        self.client = client
        self.config = config or FileUploadConfig()
        self._max_file_size_bytes = self.config.max_file_size_mb * 1024 * 1024

    async def upload_file(
        self,
        file_path: str,
        thread_id: int,
        user_id: int,  # noqa: ARG002
    ) -> str:
        """Upload a file to OpenAI for assistants/file_search.

        Args:
            file_path: Local path to the file to upload.
            thread_id: Database ID of the thread this file belongs to.
            user_id: ID of the user uploading the file.

        Returns:
            The OpenAI file ID.

        Raises:
            FileUploadError: If validation fails or upload errors occur.
        """
        path = Path(file_path)

        # Validate file exists
        if not path.exists():
            raise FileUploadError(f"File not found: {file_path}")

        # Validate file size
        file_size = path.stat().st_size
        if file_size > self._max_file_size_bytes:
            raise FileUploadError(
                f"File exceeds maximum size of {self.config.max_file_size_mb}MB"
            )

        # Validate file count for thread
        await self._validate_file_count(thread_id)

        # Upload to OpenAI with retry
        openai_file_id = await self._upload_with_retry(path)

        logger.info(
            "Uploaded file to OpenAI: %s -> %s",
            path.name,
            openai_file_id,
        )

        return openai_file_id

    async def get_or_create_vector_store(
        self,
        thread_id: int,
        thread_uuid: str,
    ) -> str:
        """Get existing vector store for thread or create a new one.

        Args:
            thread_id: Database ID of the thread.
            thread_uuid: UUID string of the thread (for naming).

        Returns:
            The vector store ID.

        Raises:
            FileUploadError: If vector store creation fails.
        """
        async with get_asyncdb_session() as session:
            result = await session.execute(
                select(AssistantThread).where(AssistantThread.id == thread_id)
            )
            thread = result.scalar_one_or_none()

            if not thread:
                raise FileUploadError(f"Thread not found: {thread_id}")

            # Return existing vector store if present
            if thread.vector_store_id:
                logger.debug(
                    "Using existing vector store: %s",
                    thread.vector_store_id,
                )
                return thread.vector_store_id

            # Create new vector store with expiration
            vector_store = await self._create_vector_store_with_retry(thread_uuid)
            vector_store_id = vector_store.id

            # Update thread with vector store ID
            thread.vector_store_id = vector_store_id
            session.add(thread)
            await session.commit()

            logger.info(
                "Created vector store for thread %s: %s",
                thread_uuid,
                vector_store_id,
            )

            return vector_store_id

    async def add_files_to_vector_store(
        self,
        vector_store_id: str,
        file_ids: list[str],
        thread_id: int,
        user_id: int,
        filenames: list[str],
        file_sizes: list[int],
    ) -> None:
        """Add uploaded files to a vector store and track in database.

        Args:
            vector_store_id: The vector store to add files to.
            file_ids: List of OpenAI file IDs to add.
            thread_id: Database ID of the thread.
            user_id: ID of the user who uploaded the files.
            filenames: Original filenames for each file.
            file_sizes: Size in bytes for each file.

        Raises:
            FileUploadError: If adding files fails.
        """
        if not file_ids:
            return

        # Add files to vector store
        for file_id in file_ids:
            try:
                await self.client.vector_stores.files.create(
                    vector_store_id=vector_store_id,
                    file_id=file_id,
                )
                logger.debug(
                    "Added file %s to vector store %s",
                    file_id,
                    vector_store_id,
                )
            except Exception as e:
                logger.error(
                    "Failed to add file %s to vector store: %s",
                    file_id,
                    e,
                )
                raise FileUploadError(f"Failed to add file to vector store: {e}") from e

        # Track in database
        async with get_asyncdb_session() as session:
            for file_id, filename, size in zip(
                file_ids, filenames, file_sizes, strict=True
            ):
                upload_record = AssistantFileUpload(
                    filename=filename,
                    openai_file_id=file_id,
                    vector_store_id=vector_store_id,
                    thread_id=thread_id,
                    user_id=user_id,
                    file_size=size,
                )
                session.add(upload_record)

            await session.commit()
            logger.debug(
                "Tracked %d file uploads in database",
                len(file_ids),
            )

    async def wait_for_processing(
        self,
        vector_store_id: str,
        file_ids: list[str],
        max_wait_seconds: int = 60,
    ) -> bool:
        """Wait for files to be processed in the vector store.

        Args:
            vector_store_id: The vector store containing the files.
            file_ids: List of file IDs to wait for.
            max_wait_seconds: Maximum seconds to wait.

        Returns:
            True if all files processed successfully, False otherwise.
        """
        if not file_ids:
            return True

        start_time = asyncio.get_event_loop().time()
        pending_files = set(file_ids)

        loop = asyncio.get_event_loop()
        while pending_files and (loop.time() - start_time) < max_wait_seconds:
            vs_files = await self.client.vector_stores.files.list(
                vector_store_id=vector_store_id
            )

            for vs_file in vs_files.data:
                if vs_file.id in pending_files:
                    if vs_file.status == "completed":
                        pending_files.discard(vs_file.id)
                        logger.debug("File processed: %s", vs_file.id)
                    elif vs_file.status in ("failed", "cancelled"):
                        error_msg = ""
                        if vs_file.last_error:
                            error_msg = vs_file.last_error.message
                        logger.error(
                            "File processing failed: %s - %s",
                            vs_file.id,
                            error_msg,
                        )
                        return False

            if pending_files:
                await asyncio.sleep(1)

        if pending_files:
            logger.warning(
                "Timeout waiting for files: %s",
                pending_files,
            )
            return False

        return True

    async def cleanup_files(self, file_ids: list[str]) -> None:
        """Delete files from OpenAI.

        Args:
            file_ids: List of OpenAI file IDs to delete.
        """
        for file_id in file_ids:
            try:
                await self.client.files.delete(file_id=file_id)
                logger.debug("Deleted OpenAI file: %s", file_id)
            except Exception as e:
                logger.warning("Failed to delete file %s: %s", file_id, e)

    async def _validate_file_count(self, thread_id: int) -> None:
        """Validate that adding another file won't exceed the limit."""
        async with get_asyncdb_session() as session:
            result = await session.execute(
                select(AssistantFileUpload).where(
                    AssistantFileUpload.thread_id == thread_id
                )
            )
            existing_count = len(result.scalars().all())

            if existing_count >= self.config.max_files_per_thread:
                raise FileUploadError(
                    f"Maximum files per thread ({self.config.max_files_per_thread}) "
                    "reached"
                )

    async def _upload_with_retry(self, path: Path, max_retries: int = 2) -> str:
        """Upload file to OpenAI with retry logic.

        Args:
            path: Path to the file.
            max_retries: Maximum number of attempts.

        Returns:
            The OpenAI file ID.

        Raises:
            FileUploadError: If all retries fail.
        """
        last_error: Exception | None = None

        for attempt in range(max_retries):
            try:
                file_content = path.read_bytes()
                vs_file = await self.client.files.create(
                    file=(path.name, file_content),
                    purpose="assistants",
                )
                return vs_file.id
            except Exception as e:
                last_error = e
                logger.warning(
                    "File upload attempt %d failed: %s",
                    attempt + 1,
                    e,
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)

        msg = f"Failed to upload file after {max_retries} attempts"
        raise FileUploadError(msg) from last_error

    async def _create_vector_store_with_retry(
        self,
        thread_uuid: str,
        max_retries: int = 2,
    ) -> Any:
        """Create vector store with retry logic.

        Args:
            thread_uuid: Thread UUID for naming the store.
            max_retries: Maximum number of attempts.

        Returns:
            The created vector store object.

        Raises:
            FileUploadError: If all retries fail.
        """
        last_error: Exception | None = None

        for attempt in range(max_retries):
            try:
                return await self.client.vector_stores.create(
                    name=f"Thread-{thread_uuid}",
                    expires_after={
                        "anchor": "last_active_at",
                        "days": self.config.vector_store_expiration_days,
                    },
                )
            except Exception as e:
                last_error = e
                logger.warning(
                    "Vector store creation attempt %d failed: %s",
                    attempt + 1,
                    e,
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)

        raise FileUploadError(
            f"Failed to create vector store after {max_retries} attempts"
        ) from last_error

    async def process_files_for_thread(
        self,
        file_paths: list[str],
        thread_db_id: int,
        thread_uuid: str,
        user_id: int,
    ) -> str | None:
        """Process multiple files for a thread.

        Uploads files, creates/gets vector store, and adds files to it.
        1. Uploads all files to OpenAI
        2. Gets or creates a vector store for the thread
        3. Adds all files to the vector store
        4. Waits for processing to complete

        Args:
            file_paths: List of local file paths to process.
            thread_db_id: Database ID of the thread.
            thread_uuid: UUID string of the thread.
            user_id: ID of the user.

        Returns:
            The vector store ID if files were processed, None if no files.

        Raises:
            FileUploadError: If any step fails (with cleanup of uploaded files).
        """
        if not file_paths:
            return None

        uploaded_file_ids: list[str] = []
        filenames: list[str] = []
        file_sizes: list[int] = []

        try:
            # Upload all files
            for file_path in file_paths:
                path = Path(file_path)
                file_id = await self.upload_file(file_path, thread_db_id, user_id)
                uploaded_file_ids.append(file_id)
                filenames.append(path.name)
                file_sizes.append(path.stat().st_size)

            # Get or create vector store
            vector_store_id = await self.get_or_create_vector_store(
                thread_db_id, thread_uuid
            )

            # Add files to vector store
            await self.add_files_to_vector_store(
                vector_store_id=vector_store_id,
                file_ids=uploaded_file_ids,
                thread_id=thread_db_id,
                user_id=user_id,
                filenames=filenames,
                file_sizes=file_sizes,
            )

            # Wait for processing
            success = await self.wait_for_processing(vector_store_id, uploaded_file_ids)

            if not success:
                logger.warning("Some files failed to process in vector store")

            return vector_store_id

        except Exception:
            # Cleanup uploaded files on failure
            if uploaded_file_ids:
                logger.warning(
                    "Cleaning up %d uploaded files due to error",
                    len(uploaded_file_ids),
                )
                await self.cleanup_files(uploaded_file_ids)
            raise
