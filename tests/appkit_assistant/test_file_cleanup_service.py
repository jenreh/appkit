# ruff: noqa: ARG002, SLF001, S105, S106
"""Tests for FileCleanupService and run_cleanup helper.

Covers scheduled cleanup, per-subscription iteration, expired-store
detection, thread vector_store_id clearing, and the manual trigger.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from openai import NotFoundError

from appkit_assistant.backend.services.file_cleanup_service import (
    FileCleanupService,
    get_file_upload_config,
    run_cleanup,
)

_PATCH = "appkit_assistant.backend.services.file_cleanup_service"


def _db_context(session: AsyncMock | None = None):
    s = session or AsyncMock()
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=s)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


def _config(interval: int = 60):
    cfg = MagicMock()
    cfg.cleanup_interval_minutes = interval
    cfg.max_file_size_mb = 20
    cfg.max_files_per_thread = 10
    cfg.vector_store_expiration_days = 7
    return cfg


# ================================================================
# get_file_upload_config
# ================================================================


class TestGetFileUploadConfig:
    def test_from_registry(self) -> None:
        mock_cfg = MagicMock()
        mock_cfg.file_upload = MagicMock()
        with patch(f"{_PATCH}.service_registry") as sr:
            sr.return_value.get.return_value = mock_cfg
            result = get_file_upload_config()
        assert result is mock_cfg.file_upload

    def test_fallback_on_error(self) -> None:
        with patch(f"{_PATCH}.service_registry") as sr:
            sr.return_value.get.side_effect = RuntimeError("x")
            result = get_file_upload_config()
        from appkit_assistant.configuration import FileUploadConfig

        assert isinstance(result, FileUploadConfig)

    def test_none_config(self) -> None:
        with patch(f"{_PATCH}.service_registry") as sr:
            sr.return_value.get.return_value = None
            result = get_file_upload_config()
        from appkit_assistant.configuration import FileUploadConfig

        assert isinstance(result, FileUploadConfig)


# ================================================================
# FileCleanupService init & properties
# ================================================================


class TestFileCleanupServiceInit:
    def test_defaults(self) -> None:
        with patch(
            f"{_PATCH}.get_file_upload_config",
            return_value=_config(),
        ):
            svc = FileCleanupService()
        assert svc.job_id == "file_cleanup"
        assert svc.name == "Clean up expired OpenAI files and vector stores"

    def test_trigger(self) -> None:
        svc = FileCleanupService(config=_config(30))
        t = svc.trigger
        assert t.to_cron() is not None

    def test_trigger_min_one_minute(self) -> None:
        svc = FileCleanupService(config=_config(0))
        t = svc.trigger
        # Still creates a valid trigger (min 1 minute)
        assert t is not None


# ================================================================
# _check_vector_store_expired
# ================================================================


class TestCheckVectorStoreExpired:
    @pytest.mark.asyncio
    async def test_expired_status(self) -> None:
        svc = FileCleanupService(config=_config())
        client = AsyncMock()
        vs = MagicMock()
        vs.status = "expired"
        client.vector_stores.retrieve = AsyncMock(return_value=vs)
        assert await svc._check_vector_store_expired(client, "vs-1")

    @pytest.mark.asyncio
    async def test_active_status(self) -> None:
        svc = FileCleanupService(config=_config())
        client = AsyncMock()
        vs = MagicMock()
        vs.status = "active"
        client.vector_stores.retrieve = AsyncMock(return_value=vs)
        assert not await svc._check_vector_store_expired(client, "vs-1")

    @pytest.mark.asyncio
    async def test_not_found(self) -> None:
        svc = FileCleanupService(config=_config())
        client = AsyncMock()
        resp = MagicMock()
        resp.status_code = 404
        client.vector_stores.retrieve = AsyncMock(
            side_effect=NotFoundError(
                "not found",
                response=resp,
                body=None,
            )
        )
        assert await svc._check_vector_store_expired(client, "vs-1")


# ================================================================
# _clear_thread_vector_store_ids
# ================================================================


class TestClearThreadVectorStoreIds:
    @pytest.mark.asyncio
    async def test_clears_threads(self) -> None:
        svc = FileCleanupService(config=_config())
        db = AsyncMock()
        db.commit = AsyncMock()
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(db),
            ),
            patch(f"{_PATCH}.thread_repo") as tr,
        ):
            tr.clear_vector_store_id = AsyncMock(return_value=3)
            result = await svc._clear_thread_vector_store_ids("vs-1")
        assert result == 3


# ================================================================
# execute
# ================================================================


class TestExecute:
    @pytest.mark.asyncio
    async def test_disabled_interval(self) -> None:
        svc = FileCleanupService(config=_config(0))
        await svc.execute()
        # Should not raise, just return

    @pytest.mark.asyncio
    async def test_success(self) -> None:
        svc = FileCleanupService(config=_config(60))

        async def _gen():
            yield {"status": "completed"}

        with patch.object(svc, "cleanup_all_subscriptions", side_effect=_gen):
            await svc.execute()

    @pytest.mark.asyncio
    async def test_error(self) -> None:
        svc = FileCleanupService(config=_config(60))

        async def _gen():
            raise RuntimeError("fail")
            yield  # noqa: B027

        with patch.object(
            svc,
            "cleanup_all_subscriptions",
            side_effect=_gen,
        ):
            await svc.execute()


# ================================================================
# cleanup_all_subscriptions
# ================================================================


class TestCleanupAllSubscriptions:
    @pytest.mark.asyncio
    async def test_no_models(self) -> None:
        svc = FileCleanupService(config=_config())
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.file_upload_repo") as fu,
        ):
            fu.find_distinct_ai_models = AsyncMock(return_value=[])
            results = [r async for r in svc.cleanup_all_subscriptions()]
        assert results[-1]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_skips_model_without_client(self) -> None:
        svc = FileCleanupService(config=_config())
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.file_upload_repo") as fu,
            patch(f"{_PATCH}.OpenAIClientService") as oai,
        ):
            fu.find_distinct_ai_models = AsyncMock(return_value=["model-x"])
            oai.create_client_for_model = AsyncMock(return_value=None)
            results = [r async for r in svc.cleanup_all_subscriptions()]
        assert results[-1]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_processes_model(self) -> None:
        svc = FileCleanupService(config=_config())

        async def _cleanup(*args, **kwargs):
            yield {
                "vector_stores_checked": 1,
                "vector_stores_expired": 0,
                "vector_stores_deleted": 0,
                "files_found": 0,
                "files_deleted": 0,
                "threads_updated": 0,
                "status": "completed",
                "current_vector_store": None,
                "total_vector_stores": 1,
            }

        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.file_upload_repo") as fu,
            patch(f"{_PATCH}.OpenAIClientService") as oai,
            patch(f"{_PATCH}.FileUploadService"),
            patch.object(
                svc,
                "cleanup_expired_files",
                side_effect=_cleanup,
            ),
        ):
            fu.find_distinct_ai_models = AsyncMock(return_value=["gpt-4"])
            oai.create_client_for_model = AsyncMock(return_value=AsyncMock())
            results = [r async for r in svc.cleanup_all_subscriptions()]
        assert results[-1]["status"] == "completed"
        assert results[-1]["vector_stores_checked"] >= 1


# ================================================================
# cleanup_expired_files
# ================================================================


class TestCleanupExpiredFiles:
    @pytest.mark.asyncio
    async def test_no_stores(self) -> None:
        svc = FileCleanupService(config=_config())
        client = AsyncMock()
        fus = AsyncMock()
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.file_upload_repo") as fu,
            patch(f"{_PATCH}.thread_repo") as tr,
        ):
            fu.find_unique_vector_stores = AsyncMock(return_value=[])
            tr.find_unique_vector_store_ids = AsyncMock(return_value=[])
            results = [r async for r in svc.cleanup_expired_files(client, fus)]
        assert results[-1]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_expired_store_deleted(self) -> None:
        svc = FileCleanupService(config=_config())
        client = AsyncMock()
        fus = AsyncMock()
        fus.delete_vector_store = AsyncMock(
            return_value={
                "deleted": True,
                "files_found": 2,
                "files_deleted": 2,
            }
        )
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.file_upload_repo") as fu,
            patch(f"{_PATCH}.thread_repo") as tr,
            patch.object(
                svc,
                "_check_vector_store_expired",
                return_value=True,
            ),
            patch.object(
                svc,
                "_clear_thread_vector_store_ids",
                return_value=1,
            ),
        ):
            fu.find_unique_vector_stores_by_ai_model = AsyncMock(
                return_value=[("vs-1", "S1")]
            )
            tr.find_unique_vector_store_ids = AsyncMock(return_value=[])
            results = [
                r
                async for r in svc.cleanup_expired_files(client, fus, ai_model="gpt-4")
            ]
        final = results[-1]
        assert final["status"] == "completed"
        assert final["vector_stores_expired"] == 1
        assert final["vector_stores_deleted"] == 1

    @pytest.mark.asyncio
    async def test_not_expired(self) -> None:
        svc = FileCleanupService(config=_config())
        client = AsyncMock()
        fus = AsyncMock()
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.file_upload_repo") as fu,
            patch(f"{_PATCH}.thread_repo") as tr,
            patch.object(
                svc,
                "_check_vector_store_expired",
                return_value=False,
            ),
        ):
            fu.find_unique_vector_stores = AsyncMock(return_value=[("vs-1", "S1")])
            tr.find_unique_vector_store_ids = AsyncMock(return_value=[])
            results = [r async for r in svc.cleanup_expired_files(client, fus)]
        assert results[-1]["vector_stores_expired"] == 0

    @pytest.mark.asyncio
    async def test_error_propagates(self) -> None:
        svc = FileCleanupService(config=_config())
        client = AsyncMock()
        fus = AsyncMock()
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(),
            ),
            patch(f"{_PATCH}.file_upload_repo") as fu,
            patch(f"{_PATCH}.thread_repo") as tr,
        ):
            fu.find_unique_vector_stores = AsyncMock(side_effect=RuntimeError("db"))
            tr.find_unique_vector_store_ids = AsyncMock(return_value=[])
            results: list[dict] = []
            with pytest.raises(RuntimeError, match="db"):
                async for r in svc.cleanup_expired_files(client, fus):
                    results.append(r)
        assert results[-1]["status"] == "error"


# ================================================================
# run_cleanup
# ================================================================


class TestRunCleanup:
    @pytest.mark.asyncio
    async def test_with_model(self) -> None:
        async def _gen(*a, **kw):
            yield {"status": "completed"}

        with (
            patch(
                f"{_PATCH}.get_file_upload_config",
                return_value=_config(),
            ),
            patch(f"{_PATCH}.OpenAIClientService") as oai,
            patch(
                f"{_PATCH}.FileUploadService",
            ),
            patch(f"{_PATCH}.FileCleanupService") as cls,
        ):
            oai.create_client_for_model = AsyncMock(return_value=AsyncMock())
            inst = cls.return_value
            inst.cleanup_expired_files = _gen
            results = [r async for r in run_cleanup(ai_model="gpt-4")]
        assert results[-1]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_no_client(self) -> None:
        with (
            patch(
                f"{_PATCH}.get_file_upload_config",
                return_value=_config(),
            ),
            patch(f"{_PATCH}.OpenAIClientService") as oai,
        ):
            oai.create_client_for_model = AsyncMock(return_value=None)
            results = [r async for r in run_cleanup(ai_model="x")]
        assert results[-1]["status"] == "error"

    @pytest.mark.asyncio
    async def test_all_subscriptions(self) -> None:
        async def _gen():
            yield {"status": "completed"}

        with (
            patch(
                f"{_PATCH}.get_file_upload_config",
                return_value=_config(),
            ),
            patch(f"{_PATCH}.FileCleanupService") as cls,
        ):
            inst = cls.return_value
            inst.cleanup_all_subscriptions = _gen
            results = [r async for r in run_cleanup()]
        assert results[-1]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_exception(self) -> None:
        async def _gen():
            raise RuntimeError("fail")
            yield  # noqa: B027

        with (
            patch(
                f"{_PATCH}.get_file_upload_config",
                return_value=_config(),
            ),
            patch(f"{_PATCH}.FileCleanupService") as cls,
        ):
            inst = cls.return_value
            inst.cleanup_all_subscriptions = _gen
            results = [r async for r in run_cleanup()]
        assert results[-1]["status"] == "error"
