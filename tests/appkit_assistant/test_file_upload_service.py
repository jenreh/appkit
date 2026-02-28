"""Tests for FileUploadService.

Covers file validation, retry logic, vector store lifecycle,
file deletion cascade, and error handling.
"""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from appkit_assistant.backend.services.file_upload_service import (
    FileUploadError,
    FileUploadService,
)
from appkit_assistant.configuration import FileUploadConfig

_PATCH = "appkit_assistant.backend.services.file_upload_service"


def _db_context(session: AsyncMock | None = None):
    s = session or AsyncMock()
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=s)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


@pytest.fixture
def mock_client() -> MagicMock:
    client = MagicMock()
    client.files = MagicMock()
    client.files.create = AsyncMock()
    client.files.delete = AsyncMock()
    client.vector_stores = MagicMock()
    client.vector_stores.create = AsyncMock()
    client.vector_stores.retrieve = AsyncMock()
    client.vector_stores.delete = AsyncMock()
    client.vector_stores.files = MagicMock()
    client.vector_stores.files.create = AsyncMock()
    client.vector_stores.files.list = AsyncMock()
    client.vector_stores.files.delete = AsyncMock()
    return client


@pytest.fixture
def config() -> FileUploadConfig:
    return FileUploadConfig(
        max_file_size_mb=10,
        max_files_per_thread=5,
        vector_store_expiration_days=7,
    )


@pytest.fixture
def service(mock_client: MagicMock, config: FileUploadConfig) -> FileUploadService:
    return FileUploadService(client=mock_client, config=config)


# ============================================================================
# Initialisation
# ============================================================================


class TestInit:
    def test_default_config(self, mock_client: MagicMock) -> None:
        svc = FileUploadService(client=mock_client)
        assert svc.config is not None
        assert svc.client is mock_client

    def test_custom_config(
        self, mock_client: MagicMock, config: FileUploadConfig
    ) -> None:
        svc = FileUploadService(client=mock_client, config=config)
        assert svc._max_file_size_bytes == 10 * 1024 * 1024  # noqa: SLF001


# ============================================================================
# upload_file — validation
# ============================================================================


class TestUploadFileValidation:
    @pytest.mark.asyncio
    async def test_file_not_found(self, service: FileUploadService) -> None:
        with pytest.raises(FileUploadError, match="nicht gefunden"):
            await service.upload_file("/nonexistent/file.txt", 1, 1)

    @pytest.mark.asyncio
    async def test_file_too_large(
        self, service: FileUploadService, tmp_path: Path
    ) -> None:
        big_file = tmp_path / "big.pdf"
        big_file.write_bytes(b"x" * (11 * 1024 * 1024))  # 11MB > 10MB

        with pytest.raises(FileUploadError, match="maximale Größe"):
            await service.upload_file(str(big_file), 1, 1)

    @pytest.mark.asyncio
    async def test_max_files_exceeded(
        self, service: FileUploadService, tmp_path: Path
    ) -> None:
        small_file = tmp_path / "ok.txt"
        small_file.write_text("content")

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [MagicMock()] * 5

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch(
            "appkit_assistant.backend.services.file_upload_service.get_asyncdb_session"
        ) as mock_ctx:
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            with pytest.raises(FileUploadError, match="Maximum files"):
                await service.upload_file(str(small_file), 1, 1)

    @pytest.mark.asyncio
    async def test_successful_upload(
        self,
        service: FileUploadService,
        mock_client: MagicMock,
        tmp_path: Path,
    ) -> None:
        small_file = tmp_path / "doc.txt"
        small_file.write_text("content")

        mock_client.files.create.return_value = MagicMock(id="file-123")

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch(
            "appkit_assistant.backend.services.file_upload_service.get_asyncdb_session"
        ) as mock_ctx:
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await service.upload_file(str(small_file), 1, 1)
        assert result == "file-123"


# ============================================================================
# _upload_with_retry
# ============================================================================


class TestUploadWithRetry:
    @pytest.mark.asyncio
    async def test_success_first_attempt(
        self,
        service: FileUploadService,
        mock_client: MagicMock,
        tmp_path: Path,
    ) -> None:
        f = tmp_path / "test.txt"
        f.write_text("data")
        mock_client.files.create.return_value = MagicMock(id="file-ok")

        result = await service._upload_with_retry(f)  # noqa: SLF001
        assert result == "file-ok"

    @pytest.mark.asyncio
    async def test_retry_on_failure(
        self,
        service: FileUploadService,
        mock_client: MagicMock,
        tmp_path: Path,
    ) -> None:
        f = tmp_path / "test.txt"
        f.write_text("data")
        mock_client.files.create.side_effect = [
            Exception("timeout"),
            MagicMock(id="file-ok"),
        ]

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await service._upload_with_retry(f)  # noqa: SLF001
        assert result == "file-ok"

    @pytest.mark.asyncio
    async def test_all_retries_fail(
        self,
        service: FileUploadService,
        mock_client: MagicMock,
        tmp_path: Path,
    ) -> None:
        f = tmp_path / "test.txt"
        f.write_text("data")
        mock_client.files.create.side_effect = Exception("always fails")

        with (
            patch("asyncio.sleep", new_callable=AsyncMock),
            pytest.raises(FileUploadError, match="Failed to upload"),
        ):
            await service._upload_with_retry(f)  # noqa: SLF001


# ============================================================================
# _create_vector_store_with_retry
# ============================================================================


class TestCreateVectorStoreRetry:
    @pytest.mark.asyncio
    async def test_success(
        self,
        service: FileUploadService,
        mock_client: MagicMock,
    ) -> None:
        mock_client.vector_stores.create.return_value = MagicMock(
            id="vs-123", name="Thread-abc"
        )

        result = await service._create_vector_store_with_retry("abc")  # noqa: SLF001
        assert result.id == "vs-123"

    @pytest.mark.asyncio
    async def test_all_retries_fail(
        self,
        service: FileUploadService,
        mock_client: MagicMock,
    ) -> None:
        mock_client.vector_stores.create.side_effect = Exception("fail")

        with (
            patch("asyncio.sleep", new_callable=AsyncMock),
            pytest.raises(FileUploadError, match="Failed to create vector store"),
        ):
            await service._create_vector_store_with_retry("abc")  # noqa: SLF001


# ============================================================================
# get_vector_store
# ============================================================================


class TestGetVectorStore:
    @pytest.mark.asyncio
    async def test_creates_new_when_no_existing(
        self,
        service: FileUploadService,
        mock_client: MagicMock,
    ) -> None:
        mock_thread = MagicMock(vector_store_id=None)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_thread
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_client.vector_stores.create.return_value = SimpleNamespace(
            id="vs-new", name="Thread-uuid1"
        )

        with patch(
            "appkit_assistant.backend.services.file_upload_service.get_asyncdb_session"
        ) as mock_ctx:
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            vs_id, vs_name = await service.get_vector_store(1, "uuid1")

        assert vs_id == "vs-new"
        assert "uuid1" in vs_name

    @pytest.mark.asyncio
    async def test_returns_existing_valid(
        self,
        service: FileUploadService,
        mock_client: MagicMock,
    ) -> None:
        mock_thread = MagicMock(vector_store_id="vs-existing")
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_thread
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_client.vector_stores.retrieve.return_value = MagicMock(name="Thread-uuid1")

        with patch(
            "appkit_assistant.backend.services.file_upload_service.get_asyncdb_session"
        ) as mock_ctx:
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            vs_id, _vs_name = await service.get_vector_store(1, "uuid1")

        assert vs_id == "vs-existing"

    @pytest.mark.asyncio
    async def test_thread_not_found_raises(self, service: FileUploadService) -> None:
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch(
            "appkit_assistant.backend.services.file_upload_service.get_asyncdb_session"
        ) as mock_ctx:
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            with pytest.raises(FileUploadError, match="Thread not found"):
                await service.get_vector_store(999, "uuid1")


# ============================================================================
# delete_files — three-level cascade
# ============================================================================


class TestDeleteFiles:
    @pytest.mark.asyncio
    async def test_empty_list(self, service: FileUploadService) -> None:
        result = await service.delete_files([])
        assert result == {}

    @pytest.mark.asyncio
    async def test_full_cascade(
        self,
        service: FileUploadService,
        mock_client: MagicMock,
    ) -> None:
        db_file = MagicMock(openai_file_id="file-1", vector_store_id="vs-1")
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [db_file]
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch(
            "appkit_assistant.backend.services.file_upload_service.get_asyncdb_session"
        ) as mock_ctx:
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await service.delete_files(["file-1"])

        assert result["file-1"] is True
        # Vector store file delete was called
        mock_client.vector_stores.files.delete.assert_awaited()
        # OpenAI file delete was called
        mock_client.files.delete.assert_awaited()


# ============================================================================
# _delete_files_from_openai
# ============================================================================


class TestDeleteFilesFromOpenai:
    @pytest.mark.asyncio
    async def test_success(
        self,
        service: FileUploadService,
    ) -> None:
        result = await service._delete_files_from_openai(["f1", "f2"])  # noqa: SLF001
        assert result == {"f1": True, "f2": True}

    @pytest.mark.asyncio
    async def test_partial_failure(
        self,
        service: FileUploadService,
    ) -> None:
        service.client.files.delete.side_effect = [None, Exception("fail")]
        result = await service._delete_files_from_openai(["f1", "f2"])  # noqa: SLF001
        assert result["f1"] is True
        assert result["f2"] is False


# ============================================================================
# _wait_for_processing — progress chunks
# ============================================================================


class TestWaitForProcessing:
    @pytest.mark.asyncio
    async def test_all_completed(
        self,
        service: FileUploadService,
        mock_client: MagicMock,
    ) -> None:
        vs_file = MagicMock(id="f1", status="completed")
        mock_client.vector_stores.files.list.return_value = MagicMock(data=[vs_file])

        chunks = [
            chunk
            async for chunk in service._wait_for_processing(  # noqa: SLF001
                "vs-1", ["f1"], ["doc.pdf"]
            )
        ]

        statuses = [c.chunk_metadata.get("status") for c in chunks]
        assert "indexing" in statuses
        assert "completed" in statuses

    @pytest.mark.asyncio
    async def test_file_failed(
        self,
        service: FileUploadService,
        mock_client: MagicMock,
    ) -> None:
        vs_file = MagicMock(
            id="f1", status="failed", last_error=MagicMock(message="bad format")
        )
        mock_client.vector_stores.files.list.return_value = MagicMock(data=[vs_file])

        chunks = [
            chunk
            async for chunk in service._wait_for_processing(  # noqa: SLF001
                "vs-1", ["f1"], ["doc.pdf"]
            )
        ]

        statuses = [c.chunk_metadata.get("status") for c in chunks]
        assert "failed" in statuses

    @pytest.mark.asyncio
    async def test_empty_file_ids(self, service: FileUploadService) -> None:
        chunks = [
            chunk
            async for chunk in service._wait_for_processing(  # noqa: SLF001
                "vs-1", [], []
            )
        ]
        assert chunks == []


# ============================================================================
# delete_vector_store
# ============================================================================


class TestDeleteVectorStore:
    @pytest.mark.asyncio
    async def test_empty_id(self, service: FileUploadService) -> None:
        result = await service.delete_vector_store("")
        assert result["deleted"] is False

    @pytest.mark.asyncio
    async def test_successful_deletion(
        self,
        service: FileUploadService,
        mock_client: MagicMock,
    ) -> None:
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_client.vector_stores.files.list.return_value = MagicMock(data=[])

        with (
            patch(
                "appkit_assistant.backend.services.file_upload_service."
                "get_asyncdb_session"
            ) as mock_ctx,
            patch(
                "appkit_assistant.backend.services.file_upload_service.file_upload_repo"
            ) as mock_repo,
        ):
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_repo.find_by_vector_store = AsyncMock(return_value=[])

            result = await service.delete_vector_store("vs-1")

        assert result["deleted"] is True
        mock_client.vector_stores.delete.assert_awaited_once()


# ============================================================================
# cleanup_deleted_thread
# ============================================================================


class TestCleanupDeletedThread:
    @pytest.mark.asyncio
    async def test_no_vector_store(self, service: FileUploadService) -> None:
        result = await service.cleanup_deleted_thread(1, None)
        assert result["vector_store_deleted"] is False
        assert result["errors"] == []

    @pytest.mark.asyncio
    async def test_with_vector_store(self, service: FileUploadService) -> None:
        with patch.object(
            service,
            "delete_vector_store",
            new_callable=AsyncMock,
            return_value={"deleted": True, "files_found": 2, "files_deleted": 2},
        ):
            result = await service.cleanup_deleted_thread(1, "vs-1")
        assert result["vector_store_deleted"] is True

    @pytest.mark.asyncio
    async def test_vector_store_deletion_failure(
        self, service: FileUploadService
    ) -> None:
        with patch.object(
            service,
            "delete_vector_store",
            new_callable=AsyncMock,
            return_value={"deleted": False, "files_found": 0, "files_deleted": 0},
        ):
            result = await service.cleanup_deleted_thread(1, "vs-1")
        assert result["vector_store_deleted"] is False
        assert len(result["errors"]) == 1


# ============================================================================
# Supplementary tests for uncovered code paths
# ============================================================================


class TestRecreateVectorStore:
    @pytest.mark.asyncio
    async def test_recreate_migrates_files(
        self,
        service: FileUploadService,
        mock_client: MagicMock,
    ) -> None:
        """_recreate_vector_store creates new VS and migrates files."""
        session = AsyncMock()
        thread = MagicMock()
        thread.vector_store_id = "old-vs"

        file1 = MagicMock()
        file1.openai_file_id = "file-1"
        file2 = MagicMock()
        file2.openai_file_id = "file-2"

        new_vs = MagicMock()
        new_vs.id = "new-vs"
        new_vs.name = "Thread-uuid"

        with patch(f"{_PATCH}.file_upload_repo") as fr:
            fr.find_by_thread = AsyncMock(return_value=[file1, file2])
            mock_client.vector_stores.create = AsyncMock(return_value=new_vs)
            mock_client.vector_stores.files.create = AsyncMock()

            vs_id, _vs_name = await service._recreate_vector_store(
                session, thread, "uuid"
            )

        assert vs_id == "new-vs"
        assert thread.vector_store_id == "new-vs"
        assert mock_client.vector_stores.files.create.call_count == 2
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_recreate_handles_file_add_failure(
        self,
        service: FileUploadService,
        mock_client: MagicMock,
    ) -> None:
        """_recreate_vector_store continues when one file fails to add."""
        session = AsyncMock()
        thread = MagicMock()
        thread.vector_store_id = "old-vs"

        file1 = MagicMock()
        file1.openai_file_id = "file-ok"
        file2 = MagicMock()
        file2.openai_file_id = "file-fail"

        new_vs = MagicMock()
        new_vs.id = "new-vs"
        new_vs.name = "Thread-uuid"

        with patch(f"{_PATCH}.file_upload_repo") as fr:
            fr.find_by_thread = AsyncMock(return_value=[file1, file2])
            mock_client.vector_stores.create = AsyncMock(return_value=new_vs)
            mock_client.vector_stores.files.create = AsyncMock(
                side_effect=[None, RuntimeError("api error")]
            )

            vs_id, _ = await service._recreate_vector_store(session, thread, "uuid")

        assert vs_id == "new-vs"


class TestAddFilesToVectorStore:
    @pytest.mark.asyncio
    async def test_add_files_success(
        self,
        service: FileUploadService,
        mock_client: MagicMock,
    ) -> None:
        """_add_files_to_vector_store adds files and writes DB records."""
        mock_client.vector_stores.files.create = AsyncMock()
        session = AsyncMock()

        with patch(
            f"{_PATCH}.get_asyncdb_session",
            return_value=_db_context(session),
        ):
            await service._add_files_to_vector_store(
                vector_store_id="vs-1",
                vector_store_name="test",
                file_ids=["f1", "f2"],
                thread_id=1,
                user_id=1,
                filenames=["a.txt", "b.txt"],
                file_sizes=[100, 200],
                ai_model="gpt-4",
            )

        assert mock_client.vector_stores.files.create.call_count == 2
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_add_files_empty(
        self,
        service: FileUploadService,
    ) -> None:
        """_add_files_to_vector_store returns early for empty list."""
        await service._add_files_to_vector_store(
            vector_store_id="vs-1",
            vector_store_name="test",
            file_ids=[],
            thread_id=1,
            user_id=1,
            filenames=[],
            file_sizes=[],
        )

    @pytest.mark.asyncio
    async def test_add_files_api_error(
        self,
        service: FileUploadService,
        mock_client: MagicMock,
    ) -> None:
        """_add_files_to_vector_store raises FileUploadError on API failure."""
        mock_client.vector_stores.files.create = AsyncMock(
            side_effect=RuntimeError("api")
        )
        with pytest.raises(FileUploadError, match="Failed to add file"):
            await service._add_files_to_vector_store(
                vector_store_id="vs-1",
                vector_store_name="test",
                file_ids=["f1"],
                thread_id=1,
                user_id=1,
                filenames=["a.txt"],
                file_sizes=[100],
            )


class TestProcessFiles:
    @pytest.mark.asyncio
    async def test_empty_file_paths(
        self,
        service: FileUploadService,
    ) -> None:
        """process_files returns immediately for empty list."""
        chunks = [c async for c in service.process_files([], 1, "u", 1)]
        assert chunks == []

    @pytest.mark.asyncio
    async def test_full_flow(
        self,
        service: FileUploadService,
        mock_client: MagicMock,
        tmp_path: Path,
    ) -> None:
        """process_files uploads, creates VS, adds, tracks, and waits."""
        f = tmp_path / "test.txt"
        f.write_text("hello")

        mock_client.vector_stores.files.create = AsyncMock()

        vs_file = SimpleNamespace(id="file-1", status="completed", last_error=None)
        mock_client.vector_stores.files.list = AsyncMock(
            return_value=SimpleNamespace(data=[vs_file])
        )

        session = AsyncMock()
        session.add = MagicMock()

        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(session),
            ),
            patch.object(
                service,
                "upload_file",
                new_callable=AsyncMock,
                return_value="file-1",
            ),
            patch.object(
                service,
                "get_vector_store",
                new_callable=AsyncMock,
                return_value=("vs-new", "Thread-u"),
            ),
        ):
            chunks = [
                c async for c in service.process_files([str(f)], 1, "u", 1, "gpt-4")
            ]

        assert len(chunks) >= 3
        statuses = [c.chunk_metadata.get("status") for c in chunks if c.chunk_metadata]
        assert "uploading" in statuses

    @pytest.mark.asyncio
    async def test_cleanup_on_failure(
        self,
        service: FileUploadService,
        mock_client: MagicMock,
        tmp_path: Path,
    ) -> None:
        """process_files cleans up uploaded files on failure."""
        f = tmp_path / "test.txt"
        f.write_text("hello")

        mock_client.files.create = AsyncMock(return_value=SimpleNamespace(id="file-1"))

        session = AsyncMock()
        session.add = MagicMock()
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(session),
            ),
            patch.object(
                service,
                "upload_file",
                new_callable=AsyncMock,
                return_value="file-1",
            ),
            patch.object(
                service,
                "get_vector_store",
                new_callable=AsyncMock,
                side_effect=RuntimeError("vs fail"),
            ),
            patch.object(
                service,
                "delete_files",
                new_callable=AsyncMock,
            ) as mock_del,
        ):
            with pytest.raises(RuntimeError, match="vs fail"):
                async for _ in service.process_files([str(f)], 1, "u", 1):
                    pass
            mock_del.assert_awaited_once()


class TestGetVectorStoreRecreate:
    @staticmethod
    def _mock_session_with_thread(thread: MagicMock) -> AsyncMock:
        session = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = thread
        session.execute = AsyncMock(return_value=result)
        return session

    @pytest.mark.asyncio
    async def test_existing_vs_not_found_triggers_recreate(
        self,
        service: FileUploadService,
        mock_client: MagicMock,
    ) -> None:
        """get_vector_store recreates VS when 404 from OpenAI."""
        thread = MagicMock()
        thread.vector_store_id = "old-vs"

        session = self._mock_session_with_thread(thread)
        mock_client.vector_stores.retrieve = AsyncMock(
            side_effect=Exception("not found 404")
        )

        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(session),
            ),
            patch.object(
                service,
                "_recreate_vector_store",
                new_callable=AsyncMock,
                return_value=("new-vs", "Thread-u"),
            ) as recreate,
        ):
            vs_id, _vs_name = await service.get_vector_store(1, "u")

        recreate.assert_awaited_once()
        assert vs_id == "new-vs"

    @pytest.mark.asyncio
    async def test_existing_vs_other_error(
        self,
        service: FileUploadService,
        mock_client: MagicMock,
    ) -> None:
        """get_vector_store returns existing VS ID on non-404 error."""
        thread = MagicMock()
        thread.vector_store_id = "old-vs"

        session = self._mock_session_with_thread(thread)
        mock_client.vector_stores.retrieve = AsyncMock(
            side_effect=Exception("server error")
        )

        with patch(
            f"{_PATCH}.get_asyncdb_session",
            return_value=_db_context(session),
        ):
            vs_id, vs_name = await service.get_vector_store(1, "u")

        assert vs_id == "old-vs"
        assert "Thread-u" in vs_name
