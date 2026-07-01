"""Tests for OpenAIClientService.

Covers client creation, availability checks, Azure config, and the
module-level helper functions.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from appkit_commons.ai.openai_client_service import (
    AiModelCredentials,
    AiModelResolver,
    OpenAIClientService,
    get_openai_client_service,
)
from appkit_commons.registry import service_registry

# ============================================================================
# _build_client (standalone)
# ============================================================================


class TestBuildClient:
    def test_standard_client(self) -> None:
        client = OpenAIClientService._build_client("sk-test", None, False)
        assert client is not None

    def test_custom_base_url(self) -> None:
        client = OpenAIClientService._build_client(
            "sk-test", "https://custom.api.com", False
        )
        assert client is not None

    def test_azure_client(self) -> None:
        client = OpenAIClientService._build_client(
            "key", "https://myazure.openai.azure.com", True
        )
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
    @staticmethod
    def _register_resolver(
        credentials: AiModelCredentials | None,
        side_effect: Exception | None = None,
    ) -> None:
        """Register a mock AiModelResolver in the service registry."""
        resolver = MagicMock()
        if side_effect is not None:
            resolver.resolve_model_credentials = AsyncMock(side_effect=side_effect)
        else:
            resolver.resolve_model_credentials = AsyncMock(return_value=credentials)
        service_registry().register_as(AiModelResolver, resolver)

    @pytest.mark.asyncio
    async def test_no_resolver_registered_returns_none(self) -> None:
        service_registry().unregister(AiModelResolver)
        result = await OpenAIClientService.create_client_for_model("gpt-4o")
        assert result is None

    @pytest.mark.asyncio
    async def test_no_model_found_returns_none(self) -> None:
        self._register_resolver(None)
        try:
            result = await OpenAIClientService.create_client_for_model("gpt-4o")
            assert result is None
        finally:
            service_registry().unregister(AiModelResolver)

    @pytest.mark.asyncio
    async def test_model_without_api_key_returns_none(self) -> None:
        self._register_resolver(AiModelCredentials(api_key=None))
        try:
            result = await OpenAIClientService.create_client_for_model("gpt-4o")
            assert result is None
        finally:
            service_registry().unregister(AiModelResolver)

    @pytest.mark.asyncio
    async def test_model_with_key_returns_client(self) -> None:
        self._register_resolver(
            AiModelCredentials(api_key="sk-test", base_url=None, on_azure=False)
        )
        try:
            result = await OpenAIClientService.create_client_for_model("gpt-4o")
            assert result is not None
        finally:
            service_registry().unregister(AiModelResolver)

    @pytest.mark.asyncio
    async def test_exception_returns_none(self) -> None:
        self._register_resolver(None, side_effect=RuntimeError("db down"))
        try:
            result = await OpenAIClientService.create_client_for_model("x")
            assert result is None
        finally:
            service_registry().unregister(AiModelResolver)


# ============================================================================
# get_openai_client_service
# ============================================================================


class TestGetOpenaiClientService:
    def test_returns_service_from_registry(self) -> None:
        svc = OpenAIClientService(api_key="sk-test")
        with patch(
            "appkit_commons.ai.openai_client_service.service_registry"
        ) as mock_reg:
            mock_reg.return_value.get.return_value = svc
            result = get_openai_client_service()
            assert result is svc

    def test_returns_default_when_not_registered(self) -> None:
        with patch(
            "appkit_commons.ai.openai_client_service.service_registry"
        ) as mock_reg:
            mock_reg.return_value.get.side_effect = KeyError
            result = get_openai_client_service()
            assert isinstance(result, OpenAIClientService)
            assert result.is_available is False
