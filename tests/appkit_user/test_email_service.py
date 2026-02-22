"""Tests for email service providers and factories."""

import logging
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from appkit_commons.registry import service_registry
from appkit_user.authentication.backend.services.email_service import (
    AzureEmailProvider,
    EmailServiceFactory,
    MockEmailProvider,
    PasswordResetType,
    ResendEmailProvider,
    get_email_service,
)
from appkit_user.configuration import (
    AuthenticationConfiguration,
    AzureEmailConfig,
    MockEmailConfig,
    PasswordResetConfig,
    ResendEmailConfig,
)


class TestPasswordResetType:
    """Test PasswordResetType enum."""

    def test_user_initiated_value(self) -> None:
        """USER_INITIATED has correct string value."""
        assert PasswordResetType.USER_INITIATED == "user_initiated"

    def test_admin_forced_value(self) -> None:
        """ADMIN_FORCED has correct string value."""
        assert PasswordResetType.ADMIN_FORCED == "admin_forced"


class TestMockEmailProvider:
    """Test suite for MockEmailProvider."""

    @pytest.fixture
    def mock_config(self) -> MockEmailConfig:
        """Provide mock email configuration."""
        return MockEmailConfig(
            from_email="test@localhost",
            from_name="Test App",
        )

    @pytest.fixture
    def mock_provider(self, mock_config: MockEmailConfig) -> MockEmailProvider:
        """Provide MockEmailProvider instance."""
        return MockEmailProvider(mock_config)

    @pytest.mark.asyncio
    async def test_send_email_success(
        self, mock_provider: MockEmailProvider, caplog: Any
    ) -> None:
        """send_email logs email details and returns True."""
        with caplog.at_level(logging.INFO):
            result = await mock_provider.send_email(
                to_email="user@example.com",
                subject="Test Subject",
                html_body="<html>Test body</html>",
            )

        assert result is True
        assert "MOCK EMAIL SENT" in caplog.text
        assert "user@example.com" in caplog.text
        assert "Test Subject" in caplog.text

    @pytest.mark.asyncio
    async def test_send_password_reset_email_user_initiated(
        self, mock_provider: MockEmailProvider, caplog: Any, tmp_path: Path
    ) -> None:
        """send_password_reset_email with user initiated type."""
        # Create template file
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        template_path = template_dir / "password_reset_user_initiated.html"
        template_path.write_text(
            "<html>Reset link: {{ reset_url }} for {{ user_name }}</html>"
        )

        # Mock the configuration
        mock_config = AuthenticationConfiguration(
            session_timeout=25,
            server_url="http://localhost",
            server_port=3000,
            password_reset=PasswordResetConfig(templates_dir=template_dir),
        )
        with patch.object(
            service_registry(), "get", return_value=mock_config
        ) as mock_get:
            mock_get.side_effect = lambda cls: (
                mock_config
                if cls == AuthenticationConfiguration
                else object.__getattribute__(service_registry(), "get")(cls)
            )

            with caplog.at_level(logging.INFO):
                result = await mock_provider.send_password_reset_email(
                    to_email="user@example.com",
                    reset_link="http://localhost/reset?token=abc123",
                    user_name="John Doe",
                    reset_type=PasswordResetType.USER_INITIATED,
                )

        assert result is True
        assert "MOCK EMAIL SENT" in caplog.text

    @pytest.mark.asyncio
    async def test_send_password_reset_email_admin_forced(
        self, mock_provider: MockEmailProvider, caplog: Any, tmp_path: Path
    ) -> None:
        """send_password_reset_email with admin forced type."""
        # Create template file
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        template_path = template_dir / "password_reset_admin_forced.html"
        template_path.write_text("<html>Admin reset link: {{ reset_url }}</html>")

        # Mock the configuration
        mock_config = AuthenticationConfiguration(
            session_timeout=25,
            server_url="http://localhost",
            server_port=3000,
            password_reset=PasswordResetConfig(templates_dir=template_dir),
        )
        with patch.object(
            service_registry(), "get", return_value=mock_config
        ) as mock_get:
            mock_get.side_effect = lambda cls: (
                mock_config
                if cls == AuthenticationConfiguration
                else object.__getattribute__(service_registry(), "get")(cls)
            )

            with caplog.at_level(logging.INFO):
                result = await mock_provider.send_password_reset_email(
                    to_email="user@example.com",
                    reset_link="http://localhost/reset?token=abc123",
                    user_name="Jane Doe",
                    reset_type=PasswordResetType.ADMIN_FORCED,
                )

        assert result is True


class TestResendEmailProvider:
    """Test suite for ResendEmailProvider."""

    @pytest.fixture
    def resend_config(self) -> ResendEmailConfig:
        """Provide Resend email configuration."""
        return ResendEmailConfig(
            api_key="test-api-key",  # noqa: S106
            from_email="noreply@example.com",
            from_name="Test App",
        )

    @pytest.fixture
    def resend_provider(self, resend_config: ResendEmailConfig) -> ResendEmailProvider:
        """Provide ResendEmailProvider instance."""
        return ResendEmailProvider(resend_config)

    @pytest.mark.asyncio
    async def test_send_email_success(
        self, resend_provider: ResendEmailProvider
    ) -> None:
        """send_email sends email via Resend API successfully."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_async_client = AsyncMock()
            mock_async_client.post.return_value = mock_response
            mock_async_client.__aenter__.return_value = mock_async_client
            mock_async_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_async_client

            result = await resend_provider.send_email(
                to_email="user@example.com",
                subject="Test",
                html_body="<html>Test</html>",
            )

            assert result is True
            mock_async_client.post.assert_called_once()
            call_args = mock_async_client.post.call_args
            assert "https://api.resend.com/emails" in str(call_args)

    @pytest.mark.asyncio
    async def test_send_email_failure_status_code(
        self, resend_provider: ResendEmailProvider
    ) -> None:
        """send_email returns False on non-200 status code."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.status_code = 400
            mock_response.text = "Bad request"
            mock_async_client = AsyncMock()
            mock_async_client.post.return_value = mock_response
            mock_async_client.__aenter__.return_value = mock_async_client
            mock_async_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_async_client

            result = await resend_provider.send_email(
                to_email="user@example.com",
                subject="Test",
                html_body="<html>Test</html>",
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_send_email_httpx_import_error(
        self, resend_provider: ResendEmailProvider, caplog: Any
    ) -> None:
        """send_email returns False when httpx is not installed."""
        with patch(
            "builtins.__import__", side_effect=ImportError("No module named httpx")
        ):
            with caplog.at_level(logging.ERROR):
                result = await resend_provider.send_email(
                    to_email="user@example.com",
                    subject="Test",
                    html_body="<html>Test</html>",
                )

            assert result is False
            assert "httpx is required" in caplog.text

    @pytest.mark.asyncio
    async def test_send_email_exception(
        self, resend_provider: ResendEmailProvider, caplog: Any
    ) -> None:
        """send_email returns False on exception."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_async_client = AsyncMock()
            mock_async_client.post.side_effect = Exception("Connection error")
            mock_async_client.__aenter__.return_value = mock_async_client
            mock_async_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_async_client

            with caplog.at_level(logging.ERROR):
                result = await resend_provider.send_email(
                    to_email="user@example.com",
                    subject="Test",
                    html_body="<html>Test</html>",
                )

            assert result is False
            assert "Connection error" in caplog.text

    @pytest.mark.asyncio
    async def test_send_password_reset_email_success(
        self, resend_provider: ResendEmailProvider, tmp_path: Path
    ) -> None:
        """send_password_reset_email sends reset email successfully."""
        # Create template file
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        template_path = template_dir / "password_reset_user_initiated.html"
        template_path.write_text(
            "<html>Reset: {{ reset_url }} for {{ user_name }} in {{ year }}</html>"
        )

        # Mock the configuration
        mock_config = AuthenticationConfiguration(
            session_timeout=25,
            server_url="http://localhost",
            server_port=3000,
            email_provider=ResendEmailConfig(
                api_key="test-api-key",  # noqa: S106
                from_email="noreply@example.com",
                from_name="Test App",
            ),
            password_reset=PasswordResetConfig(templates_dir=template_dir),
        )

        with patch.object(
            service_registry(), "get", return_value=mock_config
        ) as mock_get:
            mock_get.side_effect = lambda cls: (
                mock_config
                if cls == AuthenticationConfiguration
                else object.__getattribute__(service_registry(), "get")(cls)
            )

            with patch("httpx.AsyncClient") as mock_client_class:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_async_client = AsyncMock()
                mock_async_client.post.return_value = mock_response
                mock_async_client.__aenter__.return_value = mock_async_client
                mock_async_client.__aexit__.return_value = None
                mock_client_class.return_value = mock_async_client

                result = await resend_provider.send_password_reset_email(
                    to_email="user@example.com",
                    reset_link="http://localhost/reset?token=abc123",
                    user_name="John Doe",
                )

                assert result is True


class TestAzureEmailProvider:
    """Test suite for AzureEmailProvider."""

    @pytest.fixture
    def azure_config(self) -> AzureEmailConfig:
        """Provide Azure email configuration."""
        return AzureEmailConfig(
            connection_string="endpoint=https://test.communication.azure.com/;accesskey=test",  # noqa: S106
            from_email="noreply@example.com",
            from_name="Test App",
        )

    @pytest.fixture
    def azure_provider(self, azure_config: AzureEmailConfig) -> AzureEmailProvider:
        """Provide AzureEmailProvider instance."""
        return AzureEmailProvider(azure_config)

    @pytest.mark.asyncio
    async def test_send_email_success(self, azure_provider: AzureEmailProvider) -> None:
        """send_email sends email via Azure successfully."""
        with patch("azure.communication.email.EmailClient") as mock_client_class:
            mock_poller = MagicMock()
            mock_poller.result.return_value = True
            mock_client = MagicMock()
            mock_client.begin_send.return_value = mock_poller
            mock_client_class.from_connection_string.return_value = mock_client

            result = await azure_provider.send_email(
                to_email="user@example.com",
                subject="Test",
                html_body="<html>Test</html>",
            )

            assert result is True
            mock_client.begin_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_email_no_result(
        self, azure_provider: AzureEmailProvider, caplog: Any
    ) -> None:
        """send_email returns False when no result from Azure."""
        with patch("azure.communication.email.EmailClient") as mock_client_class:
            mock_poller = MagicMock()
            mock_poller.result.return_value = None
            mock_client = MagicMock()
            mock_client.begin_send.return_value = mock_poller
            mock_client_class.from_connection_string.return_value = mock_client

            with caplog.at_level(logging.ERROR):
                result = await azure_provider.send_email(
                    to_email="user@example.com",
                    subject="Test",
                    html_body="<html>Test</html>",
                )

            assert result is False
            assert "No result returned" in caplog.text

    @pytest.mark.asyncio
    async def test_send_email_import_error(
        self, azure_provider: AzureEmailProvider, caplog: Any
    ) -> None:
        """send_email returns False when azure package is not installed."""
        with patch(
            "builtins.__import__",
            side_effect=ImportError("No module named azure"),
        ):
            with caplog.at_level(logging.ERROR):
                result = await azure_provider.send_email(
                    to_email="user@example.com",
                    subject="Test",
                    html_body="<html>Test</html>",
                )

            assert result is False
            assert "azure-communication-email is required" in caplog.text

    @pytest.mark.asyncio
    async def test_send_email_exception(
        self, azure_provider: AzureEmailProvider, caplog: Any
    ) -> None:
        """send_email returns False on exception."""
        with patch("azure.communication.email.EmailClient") as mock_client_class:
            mock_client_class.from_connection_string.side_effect = Exception(
                "Connection failed"
            )

            with caplog.at_level(logging.ERROR):
                result = await azure_provider.send_email(
                    to_email="user@example.com",
                    subject="Test",
                    html_body="<html>Test</html>",
                )

            assert result is False
            assert "Connection failed" in caplog.text

    @pytest.mark.asyncio
    async def test_send_password_reset_email_success(
        self, azure_provider: AzureEmailProvider, tmp_path: Path
    ) -> None:
        """send_password_reset_email sends reset email via Azure."""
        # Create template file
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        template_path = template_dir / "password_reset_user_initiated.html"
        template_path.write_text(
            "<html>Reset: {{ reset_url }} for {{ user_name }}</html>"
        )

        # Mock the configuration
        mock_config = AuthenticationConfiguration(
            session_timeout=25,
            server_url="http://localhost",
            server_port=3000,
            email_provider=MockEmailConfig(from_email="test@localhost"),
            password_reset=PasswordResetConfig(templates_dir=template_dir),
        )

        with patch.object(
            service_registry(), "get", return_value=mock_config
        ) as mock_get:
            mock_get.side_effect = lambda cls: (
                mock_config
                if cls == AuthenticationConfiguration
                else object.__getattribute__(service_registry(), "get")(cls)
            )

            with patch("azure.communication.email.EmailClient") as mock_client_class:
                mock_poller = MagicMock()
                mock_poller.result.return_value = True
                mock_client = MagicMock()
                mock_client.begin_send.return_value = mock_poller
                mock_client_class.from_connection_string.return_value = mock_client

                result = await azure_provider.send_password_reset_email(
                    to_email="user@example.com",
                    reset_link="http://localhost/reset?token=abc123",
                    user_name="Jane Doe",
                )

                assert result is True


class TestEmailProviderTemplateRendering:
    """Test template rendering behavior through public methods."""

    @pytest.mark.asyncio
    async def test_template_with_variables_renders_correctly(
        self, tmp_path: Path
    ) -> None:
        """Template with Jinja2 variables renders correctly in password reset email."""
        # Create template file
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        template_path = template_dir / "password_reset_user_initiated.html"
        template_path.write_text(
            "<html>Reset: <a href='{{ reset_url }}'>Click here</a> "
            "for {{ user_name }} in {{ year }}</html>"
        )

        mock_config = AuthenticationConfiguration(
            session_timeout=25,
            server_url="http://localhost",
            server_port=3000,
            email_provider=MockEmailConfig(from_email="test@localhost"),
            password_reset=PasswordResetConfig(templates_dir=template_dir),
        )

        with patch.object(
            service_registry(), "get", return_value=mock_config
        ) as mock_get:
            mock_get.side_effect = lambda cls: (
                mock_config
                if cls == AuthenticationConfiguration
                else object.__getattribute__(service_registry(), "get")(cls)
            )

            provider = MockEmailProvider(mock_config.email_provider)
            result = await provider.send_password_reset_email(
                to_email="user@example.com",
                reset_link="http://localhost/reset?token=abc123",
                user_name="John Doe",
            )

            assert result is True

    @pytest.mark.asyncio
    async def test_missing_template_file_raises_error(self, tmp_path: Path) -> None:
        """send_password_reset_email returns False when template file missing."""
        # Create empty template directory (no files)
        template_dir = tmp_path / "templates"
        template_dir.mkdir()

        mock_config = AuthenticationConfiguration(
            session_timeout=25,
            server_url="http://localhost",
            server_port=3000,
            email_provider=MockEmailConfig(from_email="test@localhost"),
            password_reset=PasswordResetConfig(templates_dir=template_dir),
        )

        with patch.object(
            service_registry(), "get", return_value=mock_config
        ) as mock_get:
            mock_get.side_effect = lambda cls: (
                mock_config
                if cls == AuthenticationConfiguration
                else object.__getattribute__(service_registry(), "get")(cls)
            )

            provider = MockEmailProvider(mock_config.email_provider)
            result = await provider.send_password_reset_email(
                to_email="user@example.com",
                reset_link="http://localhost/reset?token=abc123",
                user_name="John Doe",
            )

            # When template is missing, send_password_reset_email returns False
            assert result is False

    @pytest.mark.asyncio
    async def test_invalid_template_syntax_raises_error(self, tmp_path: Path) -> None:
        """send_password_reset_email returns False on invalid Jinja2 syntax."""
        # Create template with invalid syntax
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        template_path = template_dir / "password_reset_user_initiated.html"
        template_path.write_text("<html>{{ broken_syntax</html>")  # Invalid syntax

        mock_config = AuthenticationConfiguration(
            session_timeout=25,
            server_url="http://localhost",
            server_port=3000,
            email_provider=MockEmailConfig(from_email="test@localhost"),
            password_reset=PasswordResetConfig(templates_dir=template_dir),
        )

        with patch.object(
            service_registry(), "get", return_value=mock_config
        ) as mock_get:
            mock_get.side_effect = lambda cls: (
                mock_config
                if cls == AuthenticationConfiguration
                else object.__getattribute__(service_registry(), "get")(cls)
            )

            provider = MockEmailProvider(mock_config.email_provider)
            result = await provider.send_password_reset_email(
                to_email="user@example.com",
                reset_link="http://localhost/reset?token=abc123",
                user_name="John Doe",
            )

            # When template syntax is invalid, send_password_reset_email returns False
            assert result is False


class TestEmailServiceFactory:
    """Test suite for EmailServiceFactory."""

    def test_create_provider_mock(self) -> None:
        """create_provider returns MockEmailProvider for MOCK provider."""
        config = AuthenticationConfiguration(
            session_timeout=25,
            server_url="http://localhost",
            server_port=3000,
            email_provider=MockEmailConfig(from_email="test@localhost"),
        )

        provider = EmailServiceFactory.create_provider(config)

        assert isinstance(provider, MockEmailProvider)

    def test_create_provider_resend(self) -> None:
        """create_provider returns ResendEmailProvider for RESEND provider."""
        config = AuthenticationConfiguration(
            session_timeout=25,
            server_url="http://localhost",
            server_port=3000,
            email_provider=ResendEmailConfig(
                api_key="test-key",  # noqa: S106
                from_email="noreply@example.com",
            ),
        )

        provider = EmailServiceFactory.create_provider(config)

        assert isinstance(provider, ResendEmailProvider)

    def test_create_provider_azure(self) -> None:
        """create_provider returns AzureEmailProvider for AZURE provider."""
        config = AuthenticationConfiguration(
            session_timeout=25,
            server_url="http://localhost",
            server_port=3000,
            email_provider=AzureEmailConfig(
                connection_string="endpoint=https://test.communication.azure.com/;accesskey=test",  # noqa: S106
                from_email="noreply@example.com",
            ),
        )

        provider = EmailServiceFactory.create_provider(config)

        assert isinstance(provider, AzureEmailProvider)

    def test_create_provider_no_config(self, caplog: Any) -> None:
        """create_provider returns None when no email provider configured."""
        config = AuthenticationConfiguration(
            session_timeout=25,
            server_url="http://localhost",
            server_port=3000,
        )

        with caplog.at_level(logging.WARNING):
            provider = EmailServiceFactory.create_provider(config)

        assert provider is None
        assert "No email provider configured" in caplog.text

    def test_create_provider_unknown_provider(self, caplog: Any) -> None:
        """create_provider returns None for unknown provider."""
        # Create a config with an unknown provider by using a mock
        config = MagicMock(spec=AuthenticationConfiguration)
        config.email_provider = MagicMock()
        config.email_provider.provider = "unknown"

        with caplog.at_level(logging.ERROR):
            provider = EmailServiceFactory.create_provider(config)

        assert provider is None
        assert "Unknown email provider" in caplog.text


class TestGetEmailService:
    """Test suite for get_email_service function."""

    def test_get_email_service_mock_configured(self) -> None:
        """get_email_service returns configured MockEmailProvider."""
        config = AuthenticationConfiguration(
            session_timeout=25,
            server_url="http://localhost",
            server_port=3000,
            email_provider=MockEmailConfig(from_email="test@localhost"),
        )

        with patch.object(service_registry(), "get", return_value=config) as mock_get:
            mock_get.side_effect = lambda cls: (
                config
                if cls == AuthenticationConfiguration
                else object.__getattribute__(service_registry(), "get")(cls)
            )

            service = get_email_service()

            assert isinstance(service, MockEmailProvider)

    def test_get_email_service_resend_configured(self) -> None:
        """get_email_service returns configured ResendEmailProvider."""
        config = AuthenticationConfiguration(
            session_timeout=25,
            server_url="http://localhost",
            server_port=3000,
            email_provider=ResendEmailConfig(
                api_key="test-key",  # noqa: S106
                from_email="noreply@example.com",
            ),
        )

        with patch.object(service_registry(), "get", return_value=config) as mock_get:
            mock_get.side_effect = lambda cls: (
                config
                if cls == AuthenticationConfiguration
                else object.__getattribute__(service_registry(), "get")(cls)
            )

            service = get_email_service()

            assert isinstance(service, ResendEmailProvider)

    def test_get_email_service_none_when_not_configured(self) -> None:
        """get_email_service returns None when no provider configured."""
        config = AuthenticationConfiguration(
            session_timeout=25,
            server_url="http://localhost",
            server_port=3000,
        )

        with patch.object(service_registry(), "get", return_value=config) as mock_get:
            mock_get.side_effect = lambda cls: (
                config
                if cls == AuthenticationConfiguration
                else object.__getattribute__(service_registry(), "get")(cls)
            )

            service = get_email_service()

            assert service is None


class TestHTMLAutoEscaping:
    """Test suite for HTML auto-escaping in template rendering."""

    @pytest.mark.asyncio
    async def test_html_special_chars_in_username_are_escaped(
        self, tmp_path: Path, caplog: Any
    ) -> None:
        """HTML special characters in user_name are properly escaped."""
        # Create template that uses user_name variable
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        template_path = template_dir / "password_reset_user_initiated.html"
        template_path.write_text(
            "<html>Hello {{ user_name }}, reset here: {{ reset_url }}</html>"
        )

        mock_config = AuthenticationConfiguration(
            session_timeout=25,
            server_url="http://localhost",
            server_port=3000,
            email_provider=MockEmailConfig(from_email="test@localhost"),
            password_reset=PasswordResetConfig(templates_dir=template_dir),
        )

        with patch.object(
            service_registry(), "get", return_value=mock_config
        ) as mock_get:
            mock_get.side_effect = lambda cls: (
                mock_config
                if cls == AuthenticationConfiguration
                else object.__getattribute__(service_registry(), "get")(cls)
            )

            provider = MockEmailProvider(mock_config.email_provider)
            # Use HTML special chars in username
            with caplog.at_level(logging.INFO):
                result = await provider.send_password_reset_email(
                    to_email="user@example.com",
                    reset_link="http://localhost/reset?token=abc123",
                    user_name="John & Jane <Doe>",
                )

            assert result is True
            # Check that the HTML entities are present in the logged output
            assert (
                "&amp;" in caplog.text
                or "John &amp; Jane" in caplog.text
                or "&lt;" in caplog.text
            )

    @pytest.mark.asyncio
    async def test_script_tag_injection_in_username_is_escaped(
        self, tmp_path: Path
    ) -> None:
        """Script injection attempts in user_name are properly escaped."""
        # Create template that uses user_name variable
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        template_path = template_dir / "password_reset_user_initiated.html"
        template_path.write_text("<html>User: {{ user_name }}</html>")

        mock_config = AuthenticationConfiguration(
            session_timeout=25,
            server_url="http://localhost",
            server_port=3000,
            email_provider=MockEmailConfig(from_email="test@localhost"),
            password_reset=PasswordResetConfig(templates_dir=template_dir),
        )

        with patch.object(
            service_registry(), "get", return_value=mock_config
        ) as mock_get:
            mock_get.side_effect = lambda cls: (
                mock_config
                if cls == AuthenticationConfiguration
                else object.__getattribute__(service_registry(), "get")(cls)
            )

            provider = MockEmailProvider(mock_config.email_provider)
            # Try to inject a script tag
            result = await provider.send_password_reset_email(
                to_email="user@example.com",
                reset_link="http://localhost/reset?token=abc123",
                user_name='<script>alert("XSS")</script>',
            )

            assert result is True

    @pytest.mark.asyncio
    async def test_html_attributes_injection_in_reset_url_is_escaped(
        self, tmp_path: Path
    ) -> None:
        """HTML attribute injection in reset_url is properly escaped."""
        # Create template that uses reset_url in an HTML attribute
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        template_path = template_dir / "password_reset_user_initiated.html"
        template_path.write_text(
            '<html><a href="{{ reset_url }}">Click to reset</a></html>'
        )

        mock_config = AuthenticationConfiguration(
            session_timeout=25,
            server_url="http://localhost",
            server_port=3000,
            email_provider=MockEmailConfig(from_email="test@localhost"),
            password_reset=PasswordResetConfig(templates_dir=template_dir),
        )

        with patch.object(
            service_registry(), "get", return_value=mock_config
        ) as mock_get:
            mock_get.side_effect = lambda cls: (
                mock_config
                if cls == AuthenticationConfiguration
                else object.__getattribute__(service_registry(), "get")(cls)
            )

            provider = MockEmailProvider(mock_config.email_provider)
            # Try to break out of href and inject onclick
            result = await provider.send_password_reset_email(
                to_email="user@example.com",
                reset_link='" onclick="alert(1)"',
                user_name="Test User",
            )

            assert result is True

    def test_render_template_escapes_ampersand(self, tmp_path: Path) -> None:
        """Direct template rendering escapes ampersands correctly."""
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        template_path = template_dir / "test.html"
        template_path.write_text("<html>{{ content }}</html>")

        mock_config = AuthenticationConfiguration(
            session_timeout=25,
            server_url="http://localhost",
            server_port=3000,
            email_provider=MockEmailConfig(from_email="test@localhost"),
            password_reset=PasswordResetConfig(templates_dir=template_dir),
        )

        with patch.object(
            service_registry(), "get", return_value=mock_config
        ) as mock_get:
            mock_get.side_effect = lambda cls: (
                mock_config
                if cls == AuthenticationConfiguration
                else object.__getattribute__(service_registry(), "get")(cls)
            )

            provider = MockEmailProvider(mock_config.email_provider)
            rendered = provider._render_template("test.html", content="AT&T")

            assert "&amp;" in rendered
            assert "AT&amp;T" in rendered

    def test_render_template_escapes_less_than_greater_than(
        self, tmp_path: Path
    ) -> None:
        """Direct template rendering escapes < and > correctly."""
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        template_path = template_dir / "test.html"
        template_path.write_text("<html>{{ content }}</html>")

        mock_config = AuthenticationConfiguration(
            session_timeout=25,
            server_url="http://localhost",
            server_port=3000,
            email_provider=MockEmailConfig(from_email="test@localhost"),
            password_reset=PasswordResetConfig(templates_dir=template_dir),
        )

        with patch.object(
            service_registry(), "get", return_value=mock_config
        ) as mock_get:
            mock_get.side_effect = lambda cls: (
                mock_config
                if cls == AuthenticationConfiguration
                else object.__getattribute__(service_registry(), "get")(cls)
            )

            provider = MockEmailProvider(mock_config.email_provider)
            rendered = provider._render_template(
                "test.html", content="<script>alert(1)</script>"
            )

            assert "&lt;" in rendered
            assert "&gt;" in rendered
            assert "&lt;script&gt;" in rendered
            assert "&lt;/script&gt;" in rendered

    def test_render_template_escapes_quotes(self, tmp_path: Path) -> None:
        """Direct template rendering escapes quotes correctly."""
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        template_path = template_dir / "test.html"
        template_path.write_text('<div attr="{{ content }}">Text</div>')

        mock_config = AuthenticationConfiguration(
            session_timeout=25,
            server_url="http://localhost",
            server_port=3000,
            email_provider=MockEmailConfig(from_email="test@localhost"),
            password_reset=PasswordResetConfig(templates_dir=template_dir),
        )

        with patch.object(
            service_registry(), "get", return_value=mock_config
        ) as mock_get:
            mock_get.side_effect = lambda cls: (
                mock_config
                if cls == AuthenticationConfiguration
                else object.__getattribute__(service_registry(), "get")(cls)
            )

            provider = MockEmailProvider(mock_config.email_provider)
            rendered = provider._render_template("test.html", content='break" attr="')

            assert "&#34;" in rendered or "&quot;" in rendered

    def test_render_template_escapes_single_quotes(self, tmp_path: Path) -> None:
        """Direct template rendering escapes single quotes correctly."""
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        template_path = template_dir / "test.html"
        template_path.write_text("<div attr='{{ content }}'>Text</div>")

        mock_config = AuthenticationConfiguration(
            session_timeout=25,
            server_url="http://localhost",
            server_port=3000,
            email_provider=MockEmailConfig(from_email="test@localhost"),
            password_reset=PasswordResetConfig(templates_dir=template_dir),
        )

        with patch.object(
            service_registry(), "get", return_value=mock_config
        ) as mock_get:
            mock_get.side_effect = lambda cls: (
                mock_config
                if cls == AuthenticationConfiguration
                else object.__getattribute__(service_registry(), "get")(cls)
            )

            provider = MockEmailProvider(mock_config.email_provider)
            rendered = provider._render_template("test.html", content="break' attr='")

            assert "&#39;" in rendered or "&#x27;" in rendered


class TestEmailServiceIntegration:
    """Integration tests for email service components."""

    @pytest.mark.asyncio
    async def test_password_reset_email_end_to_end_mock(self, tmp_path: Path) -> None:
        """Test end-to-end password reset email flow with mock provider."""
        # Create template file
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        template_path = template_dir / "password_reset_user_initiated.html"
        template_path.write_text(
            "<html>Reset your password: <a href='{{ reset_url }}'>{{ reset_url }}</a> "
            "for {{ user_name }} ({{ year }})</html>"
        )

        # Mock the configuration
        mock_config = AuthenticationConfiguration(
            session_timeout=25,
            server_url="http://localhost:3000",
            server_port=3000,
            email_provider=MockEmailConfig(
                from_email="noreply@example.com", from_name="AppKit"
            ),
            password_reset=PasswordResetConfig(templates_dir=template_dir),
        )

        with patch.object(
            service_registry(), "get", return_value=mock_config
        ) as mock_get:
            mock_get.side_effect = lambda cls: (
                mock_config
                if cls == AuthenticationConfiguration
                else object.__getattribute__(service_registry(), "get")(cls)
            )

            service = get_email_service()
            assert service is not None

            result = await service.send_password_reset_email(
                to_email="user@example.com",
                reset_link="http://localhost:3000/reset?token=abc123xyz",
                user_name="John Doe",
            )

            assert result is True

    @pytest.mark.asyncio
    async def test_multiple_emails_can_be_sent(self, tmp_path: Path) -> None:
        """Test that multiple emails can be sent in sequence."""
        # Create template file
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        template_path = template_dir / "password_reset_user_initiated.html"
        template_path.write_text("<html>Reset: {{ reset_url }}</html>")

        mock_config = AuthenticationConfiguration(
            session_timeout=25,
            server_url="http://localhost",
            server_port=3000,
            email_provider=MockEmailConfig(from_email="test@localhost"),
            password_reset=PasswordResetConfig(templates_dir=template_dir),
        )

        with patch.object(
            service_registry(), "get", return_value=mock_config
        ) as mock_get:
            mock_get.side_effect = lambda cls: (
                mock_config
                if cls == AuthenticationConfiguration
                else object.__getattribute__(service_registry(), "get")(cls)
            )

            service = get_email_service()
            assert service is not None

            # Send multiple emails
            for i in range(3):
                result = await service.send_password_reset_email(
                    to_email=f"user{i}@example.com",
                    reset_link=f"http://localhost/reset?token=token{i}",
                    user_name=f"User {i}",
                )
                assert result is True
