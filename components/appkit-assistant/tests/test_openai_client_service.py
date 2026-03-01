"""Tests for OpenAIClientService.

Covers client creation, availability checks, Azure config, and the
module-level helper functions.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from appkit_assistant.backend.services.openai_client_service import (
    OpenAIClientService,
    _build_client,
    get_openai_client_service,
)

# ============================================================================
# _build_client (standalone)
# ============================================================================


class TestBuildClient:
    def test_standard_client(self) -> None:
        client = _build_client("sk-test", None, False)
        assert client is not None

    def test_custom_base_url(self) -> None:
        client = _build_client("sk-test", "https://custom.api.com", False)
        assert client is not None

    def test_azure_client(self) -> None:
        client = _build_client("key", "https://myazure.openai.azure.com", True)
        assert client is not None


# ============================================================================
# OpenAIClientService
# ============================================================================


class TestOpenAIClientService:
    def test_is_available_with_key(self) -> None:
        svc = OpenAIClientService(api_key="sk-test")
        assert svc.is_available is True

    def test_is_available_without_key(self) -> None:
        svc = OpenAIClientService()
        assert svc.is_available is False

    def test_create_client_returns_none_without_key(self) -> None:
        svc = OpenAIClientService()
        assert svc.create_client() is None

    def test_create_client_returns_client_with_key(self) -> None:
        svc = OpenAIClientService(api_key="sk-test")
        client = svc.create_client()
        assert client is not None

    def test_create_client_with_base_url(self) -> None:
        svc = OpenAIClientService(
            api_key="sk-test",
            base_url="https://custom.com",
        )
        client = svc.create_client()
        assert client is not None

    def test_create_client_azure(self) -> None:
        svc = OpenAIClientService(
            api_key="key",
            base_url="https://myazure.openai.azure.com",
            on_azure=True,
        )
        client = svc.create_client()
        assert client is not None

    def test_from_config_returns_instance(self) -> None:
        svc = OpenAIClientService.from_config()
        assert isinstance(svc, OpenAIClientService)


# ============================================================================
# create_client_for_model (static async)
# ============================================================================


class TestCreateClientForModel:
    @pytest.mark.asyncio
    async def test_no_model_found_returns_none(self) -> None:
        mock_repo = MagicMock()
        mock_repo.find_by_model_id = AsyncMock(return_value=None)
        mock_session = AsyncMock()

        with (
            patch(
                "appkit_commons.database.session.get_asyncdb_session"
            ) as mock_session_ctx,
            patch(
                "appkit_assistant.backend.database.repositories.ai_model_repo",
                mock_repo,
            ),
        ):
            mock_session_ctx.return_value.__aenter__ = AsyncMock(
                return_value=mock_session
            )
            mock_session_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await OpenAIClientService.create_client_for_model("gpt-4o")
            assert result is None

    @pytest.mark.asyncio
    async def test_model_without_api_key_returns_none(self) -> None:
        model = MagicMock()
        model.api_key = None
        mock_repo = MagicMock()
        mock_repo.find_by_model_id = AsyncMock(return_value=model)
        mock_session = AsyncMock()

        with (
            patch(
                "appkit_commons.database.session.get_asyncdb_session"
            ) as mock_session_ctx,
            patch(
                "appkit_assistant.backend.database.repositories.ai_model_repo",
                mock_repo,
            ),
        ):
            mock_session_ctx.return_value.__aenter__ = AsyncMock(
                return_value=mock_session
            )
            mock_session_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await OpenAIClientService.create_client_for_model("gpt-4o")
            assert result is None

    @pytest.mark.asyncio
    async def test_model_with_key_returns_client(self) -> None:
        model = MagicMock()
        model.api_key = "sk-test"
        model.base_url = None
        model.on_azure = False
        mock_repo = MagicMock()
        mock_repo.find_by_model_id = AsyncMock(return_value=model)
        mock_session = AsyncMock()

        with (
            patch(
                "appkit_commons.database.session.get_asyncdb_session"
            ) as mock_session_ctx,
            patch(
                "appkit_assistant.backend.database.repositories.ai_model_repo",
                mock_repo,
            ),
        ):
            mock_session_ctx.return_value.__aenter__ = AsyncMock(
                return_value=mock_session
            )
            mock_session_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await OpenAIClientService.create_client_for_model("gpt-4o")
            assert result is not None

    @pytest.mark.asyncio
    async def test_exception_returns_none(self) -> None:
        with patch(
            "appkit_commons.database.session.get_asyncdb_session",
            side_effect=RuntimeError("db down"),
        ):
            result = await OpenAIClientService.create_client_for_model("x")
            assert result is None


# ============================================================================
# get_openai_client_service
# ============================================================================


class TestGetOpenaiClientService:
    def test_returns_service_from_registry(self) -> None:
        svc = OpenAIClientService(api_key="sk-test")
        with patch(
            "appkit_assistant.backend.services.openai_client_service.service_registry"
        ) as mock_reg:
            mock_reg.return_value.get.return_value = svc
            result = get_openai_client_service()
            assert result is svc

    def test_returns_default_when_not_registered(self) -> None:
        with patch(
            "appkit_assistant.backend.services.openai_client_service.service_registry"
        ) as mock_reg:
            mock_reg.return_value.get.side_effect = KeyError
            result = get_openai_client_service()
            assert isinstance(result, OpenAIClientService)
            assert result.is_available is False
