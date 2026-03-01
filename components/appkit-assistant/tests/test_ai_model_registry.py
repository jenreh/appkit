# ruff: noqa: ARG002, SLF001, S105, S106
"""Tests for AIModelRegistry and helper functions.

Covers _create_processor, _register_openai_client_service,
AIModelRegistry.initialize / reload, and processor decoration.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.exc import OperationalError

from appkit_assistant.backend.ai_model_registry import (
    AIModelRegistry,
    _create_processor,
    _register_openai_client_service,
)
from appkit_assistant.backend.processors import (
    LoremIpsumProcessor,
)

_PATCH = "appkit_assistant.backend.ai_model_registry"


def _model(
    model_id: str = "gpt-4",
    processor_type: str = "openai",
    api_key: str = "sk-test",
    base_url: str | None = None,
    on_azure: bool = False,
    enable_tracking: bool = False,
    active: bool = True,
):
    m = MagicMock()
    m.model_id = model_id
    m.processor_type = processor_type
    m.api_key = api_key
    m.base_url = base_url
    m.on_azure = on_azure
    m.enable_tracking = enable_tracking
    m.active = active
    m.to_ai_model.return_value = MagicMock()
    return m


def _db_context(session: AsyncMock | None = None):
    s = session or AsyncMock()
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=s)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


# ================================================================
# _create_processor
# ================================================================


class TestCreateProcessor:
    def test_lorem_ipsum(self) -> None:
        m = _model(processor_type="lorem_ipsum", api_key="")
        p = _create_processor(m)
        assert p is not None

    def test_openai(self) -> None:
        m = _model(processor_type="openai")
        p = _create_processor(m)
        assert p is not None

    def test_claude(self) -> None:
        m = _model(processor_type="claude")
        p = _create_processor(m)
        assert p is not None

    def test_perplexity(self) -> None:
        m = _model(processor_type="perplexity")
        p = _create_processor(m)
        assert p is not None

    def test_gemini(self) -> None:
        m = _model(processor_type="gemini")
        p = _create_processor(m)
        assert p is not None

    def test_unknown_type(self) -> None:
        m = _model(processor_type="unknown_type")
        p = _create_processor(m)
        assert p is None

    def test_no_api_key_non_lorem(self) -> None:
        m = _model(processor_type="openai", api_key="")
        p = _create_processor(m)
        assert p is None

    def test_openai_with_base_url(self) -> None:
        m = _model(
            processor_type="openai",
            base_url="https://custom.api",
        )
        p = _create_processor(m)
        assert p is not None

    def test_openai_on_azure(self) -> None:
        m = _model(
            processor_type="openai",
            on_azure=True,
        )
        p = _create_processor(m)
        assert p is not None

    def test_claude_on_azure(self) -> None:
        m = _model(
            processor_type="claude",
            on_azure=True,
            base_url="https://azure.endpoint",
        )
        p = _create_processor(m)
        assert p is not None


# ================================================================
# _register_openai_client_service
# ================================================================


class TestRegisterOpenAIClientService:
    def test_registers_first_openai(self) -> None:
        m = _model(processor_type="openai")
        with patch(f"{_PATCH}.service_registry") as sr:
            _register_openai_client_service([m])
            sr.return_value.register_as.assert_called_once()

    def test_no_openai_model(self) -> None:
        m = _model(processor_type="claude", api_key="sk-test")
        with patch(f"{_PATCH}.service_registry") as sr:
            _register_openai_client_service([m])
            sr.return_value.register_as.assert_not_called()

    def test_openai_without_key(self) -> None:
        m = _model(processor_type="openai", api_key="")
        with patch(f"{_PATCH}.service_registry") as sr:
            _register_openai_client_service([m])
            sr.return_value.register_as.assert_not_called()


# ================================================================
# AIModelRegistry
# ================================================================


class TestAIModelRegistry:
    def test_init(self) -> None:
        r = AIModelRegistry()
        assert r._loaded is False
        assert len(r._registered_model_ids) == 0

    def test_set_processor_decorator(self) -> None:
        r = AIModelRegistry()
        dec = MagicMock()
        r.set_processor_decorator(dec)
        assert r._processor_decorator is dec

    @pytest.mark.asyncio
    async def test_initialize_calls_reload(self) -> None:
        r = AIModelRegistry()
        r._loaded = False
        with patch.object(r, "reload", new_callable=AsyncMock):
            await r.initialize()
        assert r._loaded is True

    @pytest.mark.asyncio
    async def test_initialize_noop_if_loaded(self) -> None:
        r = AIModelRegistry()
        r._loaded = True
        with patch.object(r, "reload", new_callable=AsyncMock) as m:
            await r.initialize()
        m.assert_not_called()

    @pytest.mark.asyncio
    async def test_reload_success(self) -> None:
        r = AIModelRegistry()
        m = _model(processor_type="lorem_ipsum", api_key="")
        session = AsyncMock()
        session.expunge_all = MagicMock()
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(session),
            ),
            patch(f"{_PATCH}.ai_model_repo") as repo,
            patch(f"{_PATCH}.ModelManager") as mm_cls,
            patch(f"{_PATCH}._register_openai_client_service"),
        ):
            repo.find_all_active_ordered_by_text = AsyncMock(return_value=[m])
            mm = mm_cls.return_value
            mm.get_all_models.return_value = []
            await r.reload()
        assert "lorem_ipsum" not in r._registered_model_ids
        # lorem_ipsum has no api_key but still registers

    @pytest.mark.asyncio
    async def test_reload_with_decorator(self) -> None:
        r = AIModelRegistry()
        m = _model(enable_tracking=True)
        dec = MagicMock(side_effect=lambda p, _n: p)
        r.set_processor_decorator(dec)
        session = AsyncMock()
        session.expunge_all = MagicMock()
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(session),
            ),
            patch(f"{_PATCH}.ai_model_repo") as repo,
            patch(f"{_PATCH}.ModelManager") as mm_cls,
            patch(f"{_PATCH}._register_openai_client_service"),
        ):
            repo.find_all_active_ordered_by_text = AsyncMock(return_value=[m])
            mm = mm_cls.return_value
            mm.get_all_models.return_value = []
            await r.reload()
        dec.assert_called_once()

    @pytest.mark.asyncio
    async def test_reload_unregisters_old(self) -> None:
        r = AIModelRegistry()
        r._registered_model_ids = {"old-model"}
        session = AsyncMock()
        session.expunge_all = MagicMock()
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(session),
            ),
            patch(f"{_PATCH}.ai_model_repo") as repo,
            patch(f"{_PATCH}.ModelManager") as mm_cls,
            patch(f"{_PATCH}._register_openai_client_service"),
        ):
            repo.find_all_active_ordered_by_text = AsyncMock(return_value=[])
            mm = mm_cls.return_value
            mm.unregister_processors = MagicMock()
            mm.get_all_models.return_value = []
            await r.reload()
        mm.unregister_processors.assert_called_once_with({"old-model"})

    @pytest.mark.asyncio
    async def test_reload_sets_default_model(self) -> None:
        r = AIModelRegistry()
        m = _model(processor_type="openai")
        session = AsyncMock()
        session.expunge_all = MagicMock()

        model_info = MagicMock()
        model_info.id = "gpt-4"

        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(session),
            ),
            patch(f"{_PATCH}.ai_model_repo") as repo,
            patch(f"{_PATCH}.ModelManager") as mm_cls,
            patch(f"{_PATCH}._register_openai_client_service"),
        ):
            repo.find_all_active_ordered_by_text = AsyncMock(return_value=[m])
            mm = mm_cls.return_value
            mm.get_all_models.return_value = [model_info]
            mm.get_processor_for_model.return_value = MagicMock()
            await r.reload()
        mm.set_default_model.assert_called()

    @pytest.mark.asyncio
    async def test_reload_db_error_returns(self) -> None:
        r = AIModelRegistry()
        with patch(
            f"{_PATCH}.get_asyncdb_session",
            side_effect=RuntimeError("db down"),
        ):
            await r.reload()
        # Should gracefully handle without raising

    @pytest.mark.asyncio
    async def test_reload_operational_error_retry(
        self,
    ) -> None:
        r = AIModelRegistry()
        session = AsyncMock()
        session.expunge_all = MagicMock()

        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
            ) as gdb,
            patch(f"{_PATCH}.ai_model_repo") as repo,
            patch(f"{_PATCH}.ModelManager") as mm_cls,
            patch(f"{_PATCH}._register_openai_client_service"),
            patch(f"{_PATCH}.asyncio") as aio,
        ):
            # First 2 calls raise, 3rd succeeds
            db1 = _db_context(session)
            err = OperationalError("", [], Exception())
            gdb.side_effect = [err, err, db1]
            aio.sleep = AsyncMock()
            repo.find_all_active_ordered_by_text = AsyncMock(return_value=[])
            mm = mm_cls.return_value
            mm.get_all_models.return_value = []
            await r.reload()

    @pytest.mark.asyncio
    async def test_reload_all_retries_fail(self) -> None:
        r = AIModelRegistry()
        err = OperationalError("", [], Exception())
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                side_effect=err,
            ),
            patch(f"{_PATCH}.asyncio") as aio,
        ):
            aio.sleep = AsyncMock()
            await r.reload()
        # Should not raise, graceful failure

    @pytest.mark.asyncio
    async def test_reload_fallback_default(self) -> None:
        """When all models are lorem_ipsum, use first."""
        r = AIModelRegistry()
        m = _model(processor_type="lorem_ipsum", api_key="")
        session = AsyncMock()
        session.expunge_all = MagicMock()

        model_info = MagicMock()
        model_info.id = "lorem"

        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                return_value=_db_context(session),
            ),
            patch(f"{_PATCH}.ai_model_repo") as repo,
            patch(f"{_PATCH}.ModelManager") as mm_cls,
            patch(f"{_PATCH}._register_openai_client_service"),
        ):
            repo.find_all_active_ordered_by_text = AsyncMock(return_value=[m])
            mm = mm_cls.return_value
            mm.get_all_models.return_value = [model_info]
            mm.get_processor_for_model.return_value = LoremIpsumProcessor()
            await r.reload()
        # Falls through first branch, hits second elif
        mm.set_default_model.assert_called()
