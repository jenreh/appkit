"""File upload service for managing OpenAI file uploads and vector stores.

Handles uploading files to OpenAI, creating/managing vector stores per thread,
and tracking uploads in the database for cleanup purposes.
"""

import asyncio
import logging
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI
from sqlalchemy import select

from appkit_assistant.backend.database.models import (
    AssistantFileUpload,
    AssistantThread,
)
from appkit_assistant.backend.database.repositories import file_upload_repo
from appkit_assistant.backend.schemas import (
    Chunk,
    ChunkType,
)
from appkit_assistant.backend.services.chunk_factory import ChunkFactory
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
        self._chunk_factory = ChunkFactory("file_upload_service")

    async def _recreate_vector_store(
        self,
        session: Any,
        thread: AssistantThread,
        thread_uuid: str,
    ) -> tuple[str, str]:
        """Recreate a vector store that no longer exists in OpenAI.

        Creates a new vector store and adds all existing files from the thread.

        Args:
            session: Database session.
            thread: The thread whose vector store needs recreation.
            thread_uuid: UUID string of the thread (for naming).

        Returns:
            Tuple of (new_vector_store_id, vector_store_name).

        Raises:
            FileUploadError: If recreation fails.
        """
        old_vector_store_id = thread.vector_store_id

        # Get existing file records for this thread
        existing_files = await file_upload_repo.find_by_thread(session, thread.id)
        openai_file_ids = [f.openai_file_id for f in existing_files]

        logger.info(
            "Recreating vector store for thread %s with %d existing files",
            thread_uuid,
            len(openai_file_ids),
        )

        # Create new vector store
        vector_store = await self._create_vector_store_with_retry(thread_uuid)
        new_vector_store_id = vector_store.id
        vector_store_name = vector_store.name or f"Thread-{thread_uuid}"

        # Add existing files to new vector store
        files_added = 0
        for file_id in openai_file_ids:
            try:
                await self.client.vector_stores.files.create(
                    vector_store_id=new_vector_store_id,
                    file_id=file_id,
                )
                files_added += 1
            except Exception as e:
                logger.warning(
                    "Failed to add file %s to new vector store: %s",
                    file_id,
                    e,
                )

        # Update thread with new vector store ID
        thread.vector_store_id = new_vector_store_id
        session.add(thread)

        # Update all file records with new vector store ID
        for file_record in existing_files:
            file_record.vector_store_id = new_vector_store_id
            file_record.vector_store_name = vector_store_name
            session.add(file_record)

        await session.commit()

        logger.info(
            "Recreated vector store: %s -> %s (%d/%d files migrated)",
            old_vector_store_id,
            new_vector_store_id,
            files_added,
            len(openai_file_ids),
        )

        return new_vector_store_id, vector_store_name

    async def _add_files_to_vector_store(
        self,
        vector_store_id: str,
        vector_store_name: str,
        file_ids: list[str],
        thread_id: int,
        user_id: int,
        filenames: list[str],
        file_sizes: list[int],
    ) -> None:
        """Add uploaded files to a vector store and track in database (private helper).

        Args:
            vector_store_id: The vector store to add files to.
            vector_store_name: The name of the vector store.
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
                    vector_store_name=vector_store_name,
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

    async def _wait_for_processing(  # noqa: PLR0912
        self,
        vector_store_id: str,
        file_ids: list[str],
        filenames: list[str],
        max_wait_seconds: int = 60,
    ) -> AsyncGenerator[Chunk, None]:
        """Wait for files to be processed, yielding progress chunks in real-time.

        Args:
            vector_store_id: The vector store containing the files.
            file_ids: List of file IDs to wait for.
            filenames: List of original filenames for progress display.
            max_wait_seconds: Maximum seconds to wait.

        Yields:
            Chunk objects with processing status updates.
        """
        if not file_ids:
            return

        # Map file IDs to filenames for display
        file_id_to_name = dict(zip(file_ids, filenames, strict=True))
        total_files = len(file_ids)
        completed_count = 0

        # Initial processing chunk
        if total_files == 1:
            initial_text = f"Indiziere: {filenames[0]}"
        else:
            initial_text = f"Indiziere {total_files} Dateien..."
        yield self._chunk_factory.create(
            ChunkType.PROCESSING,
            initial_text,
            {
                "status": "indexing",
                "total_files": total_files,
                "completed_files": 0,
            },
        )

        start_time = asyncio.get_event_loop().time()
        pending_files = set(file_ids)
        success = True

        loop = asyncio.get_event_loop()
        while pending_files and (loop.time() - start_time) < max_wait_seconds:
            vs_files = await self.client.vector_stores.files.list(
                vector_store_id=vector_store_id
            )

            for vs_file in vs_files.data:
                if vs_file.id in pending_files:
                    if vs_file.status == "completed":
                        pending_files.discard(vs_file.id)
                        completed_count += 1
                        filename = file_id_to_name.get(vs_file.id, vs_file.id)
                        logger.debug("File indexed: %s", vs_file.id)

                        # Progress update chunk
                        progress_text = f"Indiziert: {filename}"
                        yield self._chunk_factory.create(
                            ChunkType.PROCESSING,
                            progress_text,
                            {
                                "status": "progress",
                                "total_files": total_files,
                                "completed_files": completed_count,
                                "current_file": filename,
                            },
                        )
                    elif vs_file.status in ("failed", "cancelled"):
                        error_msg = ""
                        if vs_file.last_error:
                            error_msg = vs_file.last_error.message
                        logger.error(
                            "File indexing failed: %s - %s",
                            vs_file.id,
                            error_msg,
                        )
                        failed_name = file_id_to_name.get(vs_file.id, vs_file.id)
                        yield self._chunk_factory.create(
                            ChunkType.PROCESSING,
                            f"Fehler: {failed_name}",
                            {
                                "status": "failed",
                                "total_files": total_files,
                                "completed_files": completed_count,
                                "error": error_msg,
                            },
                        )
                        pending_files.discard(vs_file.id)
                        success = False

            if pending_files:
                await asyncio.sleep(1)

        if pending_files:
            logger.warning("Timeout waiting for files: %s", pending_files)
            yield self._chunk_factory.create(
                ChunkType.PROCESSING,
                f"Zeitüberschreitung ({completed_count}/{total_files})",
                {
                    "status": "timeout",
                    "total_files": total_files,
                    "completed_files": completed_count,
                },
            )
            return

        # Final success chunk
        if success:
            if total_files == 1:
                done_text = f"Bereit: {filenames[0]}"
            else:
                done_text = f"{total_files} Dateien bereit"
            yield self._chunk_factory.create(
                ChunkType.PROCESSING,
                done_text,
                {
                    "status": "completed",
                    "total_files": total_files,
                    "completed_files": total_files,
                },
            )

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

    async def _delete_files_from_vector_stores(
        self, db_files: list[AssistantFileUpload]
    ) -> None:
        """Delete files FROM their vector stores (Level 1)."""
        # Build map of vector_store_id -> file_ids
        vector_store_files: dict[str, list[str]] = {}
        for db_file in db_files:
            if db_file.vector_store_id:
                if db_file.vector_store_id not in vector_store_files:
                    vector_store_files[db_file.vector_store_id] = []
                vector_store_files[db_file.vector_store_id].append(
                    db_file.openai_file_id
                )

        # Delete from each vector store
        for vs_id, vs_file_ids in vector_store_files.items():
            for file_id in vs_file_ids:
                try:
                    await self.client.vector_stores.files.delete(
                        vector_store_id=vs_id,
                        file_id=file_id,
                    )
                    logger.debug("Deleted file %s from vector store %s", file_id, vs_id)
                except Exception as e:
                    logger.warning(
                        "Failed to delete file %s from vector store %s: %s",
                        file_id,
                        vs_id,
                        e,
                    )

    async def _delete_files_from_openai(self, file_ids: list[str]) -> dict[str, bool]:
        """Delete files from OpenAI (Level 2)."""
        results = {}
        for file_id in file_ids:
            try:
                await self.client.files.delete(file_id=file_id)
                logger.debug("Deleted OpenAI file: %s", file_id)
                results[file_id] = True
            except Exception as e:
                logger.warning("Failed to delete OpenAI file %s: %s", file_id, e)
                results[file_id] = False
        return results

    async def _delete_file_db_records(
        self,
        db_files: list[AssistantFileUpload],
        deletion_results: dict[str, bool],
    ) -> None:
        """Delete database records for successfully deleted files (Level 3)."""
        deleted_file_ids = [fid for fid, success in deletion_results.items() if success]
        if not deleted_file_ids:
            return

        async with get_asyncdb_session() as session:
            for db_file in db_files:
                if db_file.openai_file_id in deleted_file_ids:
                    try:
                        await session.delete(db_file)
                        logger.debug(
                            "Deleted DB record for file: %s", db_file.openai_file_id
                        )
                    except Exception as e:
                        logger.warning(
                            "Failed to delete DB record for file %s: %s",
                            db_file.openai_file_id,
                            e,
                        )
            await session.commit()

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

    async def process_files(  # noqa: PLR0912
        self,
        file_paths: list[str],
        thread_db_id: int,
        thread_uuid: str,
        user_id: int,
    ) -> AsyncGenerator[Chunk, None]:
        """Process files for a thread, yielding progress chunks in real-time.

        Uploads files, creates/gets vector store, adds files to it, and waits
        for indexing - yielding progress updates as each step happens.

        Final chunk has metadata with 'vector_store_id' key.

        Args:
            file_paths: List of local file paths to process.
            thread_db_id: Database ID of the thread.
            thread_uuid: UUID string of the thread.
            user_id: ID of the user.

        Yields:
            Chunk objects with real-time progress updates.
            Final chunk contains 'vector_store_id' in metadata.

        Raises:
            FileUploadError: If any step fails (with cleanup of uploaded files).
        """
        if not file_paths:
            return

        uploaded_file_ids: list[str] = []
        filenames: list[str] = []
        file_sizes: list[int] = []
        total_files = len(file_paths)
        vector_store_id: str | None = None

        try:
            # Phase 1: Upload files to OpenAI
            for i, file_path in enumerate(file_paths, 1):
                path = Path(file_path)
                filename = path.name

                yield self._chunk_factory.create(
                    ChunkType.PROCESSING,
                    f"Lade hoch: {filename} ({i}/{total_files})",
                    {
                        "status": "uploading",
                        "current_file": filename,
                        "file_index": i,
                        "total_files": total_files,
                    },
                )

                file_id = await self.upload_file(file_path, thread_db_id, user_id)
                uploaded_file_ids.append(file_id)
                filenames.append(filename)
                file_sizes.append(path.stat().st_size)

            # Phase 2: Get or create vector store
            yield self._chunk_factory.create(
                ChunkType.PROCESSING,
                "Bereite Vector Store vor...",
                {"status": "preparing_store"},
            )

            vector_store_id, vector_store_name = await self.get_vector_store(
                thread_db_id, thread_uuid
            )

            # Phase 3: Add files to vector store
            for i, (file_id, filename) in enumerate(
                zip(uploaded_file_ids, filenames, strict=True), 1
            ):
                yield self._chunk_factory.create(
                    ChunkType.PROCESSING,
                    f"Füge hinzu: {filename} ({i}/{total_files})",
                    {
                        "status": "adding_to_store",
                        "current_file": filename,
                        "file_index": i,
                        "total_files": total_files,
                    },
                )

                await self.client.vector_stores.files.create(
                    vector_store_id=vector_store_id,
                    file_id=file_id,
                )
                logger.debug(
                    "Added file %s to vector store %s", file_id, vector_store_id
                )

            # Track in database
            async with get_asyncdb_session() as session:
                for file_id, filename, size in zip(
                    uploaded_file_ids, filenames, file_sizes, strict=True
                ):
                    upload_record = AssistantFileUpload(
                        filename=filename,
                        openai_file_id=file_id,
                        vector_store_id=vector_store_id,
                        vector_store_name=vector_store_name,
                        thread_id=thread_db_id,
                        user_id=user_id,
                        file_size=size,
                    )
                    session.add(upload_record)
                await session.commit()
                logger.debug("Tracked %d file uploads in database", len(filenames))

            # Phase 4: Wait for indexing with streaming progress
            async for chunk in self._wait_for_processing(
                vector_store_id, uploaded_file_ids, filenames
            ):
                # Add vector_store_id to final chunk metadata
                if chunk.chunk_metadata and chunk.chunk_metadata.get("status") in (
                    "completed",
                    "timeout",
                    "failed",
                ):
                    chunk.chunk_metadata["vector_store_id"] = vector_store_id
                yield chunk

        except Exception:
            # Cleanup uploaded files on failure
            if uploaded_file_ids:
                logger.warning(
                    "Cleaning up %d uploaded files due to error",
                    len(uploaded_file_ids),
                )
                await self.delete_files(uploaded_file_ids)
            raise

    async def get_vector_store(
        self,
        thread_id: int,
        thread_uuid: str,
    ) -> tuple[str, str]:
        """Get existing vector store for thread or create a new one.

        Automatically validates the vector store exists in OpenAI and recreates
        if missing.

        Args:
            thread_id: Database ID of the thread.
            thread_uuid: UUID string of the thread (for naming).

        Returns:
            Tuple of (vector_store_id, vector_store_name).

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

            # Return existing vector store if present and valid
            if thread.vector_store_id:
                logger.debug(
                    "Checking existing vector store: %s",
                    thread.vector_store_id,
                )
                # Validate vector store exists in OpenAI
                try:
                    vs = await self.client.vector_stores.retrieve(
                        thread.vector_store_id
                    )
                    return thread.vector_store_id, vs.name or ""
                except Exception as e:
                    error_msg = str(e).lower()
                    if "not found" in error_msg or "404" in error_msg:
                        logger.warning(
                            "Vector store %s no longer exists, creating new one",
                            thread.vector_store_id,
                        )
                        # Vector store doesn't exist - create new one and migrate files
                        return await self._recreate_vector_store(
                            session, thread, thread_uuid
                        )
                    # Other error - log but try to continue
                    logger.warning(
                        "Error checking vector store %s: %s",
                        thread.vector_store_id,
                        e,
                    )
                    return thread.vector_store_id, f"Thread-{thread_uuid}"

            # Create new vector store with expiration
            vector_store = await self._create_vector_store_with_retry(thread_uuid)
            vector_store_id = vector_store.id
            vector_store_name = vector_store.name or f"Thread-{thread_uuid}"

            # Update thread with vector store ID
            thread.vector_store_id = vector_store_id
            session.add(thread)
            await session.commit()

            logger.info(
                "Created vector store for thread %s: %s",
                thread_uuid,
                vector_store_id,
            )

            return vector_store_id, vector_store_name

    async def delete_files(self, file_ids: list[str]) -> dict[str, bool]:
        """Delete files with proper three-level ordering.

        Order:
        1. Delete files FROM their vector stores (remove association)
        2. Delete files from OpenAI
        3. Delete database records

        Args:
            file_ids: List of OpenAI file IDs to delete.

        Returns:
            Dictionary mapping file_id to deletion success status.
        """
        if not file_ids:
            return {}

        # Get file records from database to know which vector stores they belong to
        async with get_asyncdb_session() as session:
            file_records = await session.execute(
                select(AssistantFileUpload).where(
                    AssistantFileUpload.openai_file_id.in_(file_ids)
                )
            )
            db_files = file_records.scalars().all()

        # LEVEL 1: Delete files FROM their vector stores
        await self._delete_files_from_vector_stores(db_files)

        # LEVEL 2: Delete files from OpenAI
        results = await self._delete_files_from_openai(file_ids)

        # LEVEL 3: Delete database records (only for successfully deleted files)
        await self._delete_file_db_records(db_files, results)

        return results

    async def delete_vector_store(self, vector_store_id: str) -> bool:
        """Delete a vector store with proper ordering.

        Order:
        1. Delete all files in the vector store (via delete_files - 3-level deletion)
        2. Delete the vector store container itself

        Args:
            vector_store_id: The vector store ID to delete.

        Returns:
            True if vector store was successfully deleted, False otherwise.
        """
        if not vector_store_id:
            return False

        logger.info("Deleting vector store: %s", vector_store_id)

        # Step 1: List and delete all files in the vector store
        try:
            vs_files = await self.client.vector_stores.files.list(
                vector_store_id=vector_store_id
            )
            file_ids = [vs_file.id for vs_file in vs_files.data]

            if file_ids:
                logger.info(
                    "Deleting %d files from vector store %s",
                    len(file_ids),
                    vector_store_id,
                )
                deletion_results = await self.delete_files(file_ids)
                successful = sum(1 for success in deletion_results.values() if success)
                logger.info(
                    "Successfully deleted %d/%d files from vector store %s",
                    successful,
                    len(file_ids),
                    vector_store_id,
                )
        except Exception as e:
            logger.warning(
                "Failed to delete files from vector store %s: %s",
                vector_store_id,
                e,
            )

        # Step 2: Delete the vector store container itself
        try:
            await self.client.vector_stores.delete(vector_store_id=vector_store_id)
            logger.info("Deleted vector store: %s", vector_store_id)
            return True
        except Exception as e:
            logger.warning(
                "Failed to delete vector store %s (will auto-expire): %s",
                vector_store_id,
                e,
            )
            return False

    async def cleanup_deleted_thread(
        self,
        thread_db_id: int,
        vector_store_id: str | None,
    ) -> dict[str, Any]:
        """Clean up all resources for a deleted thread.

        Deletion is handled by delete_vector_store which:
        1. Deletes all files (3-level: from VS, from OpenAI, from DB)
        2. Deletes the vector store container

        Args:
            thread_db_id: Database ID of the deleted thread.
            vector_store_id: The vector store ID (if any) associated with the thread.

        Returns:
            Dictionary with cleanup statistics:
            {
                'vector_store_deleted': bool,
                'thread_db_id': int,
                'errors': list[str]
            }
        """
        logger.info("Starting cleanup for deleted thread %d", thread_db_id)

        result = {
            "vector_store_deleted": False,
            "thread_db_id": thread_db_id,
            "errors": [],
        }

        if not vector_store_id:
            logger.debug(
                "No vector store to clean up for thread %d",
                thread_db_id,
            )
            return result

        # Delete vector store (which handles all file deletion internally)
        vs_deleted = await self.delete_vector_store(vector_store_id)
        result["vector_store_deleted"] = vs_deleted

        if not vs_deleted:
            result["errors"].append(f"Failed to delete vector store {vector_store_id}")

        logger.info(
            "Cleanup completed for thread %d: VS=%s, errors=%d",
            thread_db_id,
            result["vector_store_deleted"],
            len(result["errors"]),
        )

        return result
