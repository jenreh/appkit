"""Tests for common utility functions."""

from unittest.mock import MagicMock, patch

from appkit_mcp_commons.utils import get_openai_client


class TestGetOpenaiClient:
    def test_success(self) -> None:
        """Returns client when service is available."""
        mock_client = MagicMock()
        mock_service = MagicMock()
        mock_service.create_client.return_value = mock_client

        with patch(
            "appkit_mcp_commons.utils.get_openai_client_service",
            return_value=mock_service,
        ):
            result = get_openai_client()
        assert result is mock_client

    def test_failure(self) -> None:
        """Returns None when service is unavailable."""
        with patch(
            "appkit_mcp_commons.utils.get_openai_client_service",
            side_effect=RuntimeError("not registered"),
        ):
            result = get_openai_client()
        assert result is None
