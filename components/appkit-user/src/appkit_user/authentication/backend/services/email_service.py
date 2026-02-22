"""Email service for sending password reset emails."""

import logging
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from pathlib import Path

from jinja2 import Environment, select_autoescape

from appkit_commons.registry import service_registry
from appkit_user.authentication.backend.types import PasswordResetType
from appkit_user.configuration import (
    AuthenticationConfiguration,
    AzureEmailConfig,
    EmailProvider,
    MockEmailConfig,
    ResendEmailConfig,
)

logger = logging.getLogger(__name__)


type EmailConfigType = ResendEmailConfig | AzureEmailConfig | MockEmailConfig


class EmailProviderBase(ABC):
    """Abstract base class for email providers."""

    def __init__(self, config: EmailConfigType):
        self.config = config

    @abstractmethod
    async def send_email(self, to_email: str, subject: str, html_body: str) -> bool:
        """Send an email to the specified recipient."""

    def _get_template_path(self, filename: str) -> Path:
        """Resolve template path from configuration or default location."""
        config: AuthenticationConfiguration = service_registry().get(
            AuthenticationConfiguration
        )
        base_dir = (
            config.password_reset.templates_dir
            if config.password_reset.templates_dir
            else Path(__file__).parent.parent.parent / "templates"
        )
        return base_dir / filename

    def _render_template(self, template_file: str, **context) -> str:
        """Load and render a Jinja2 template."""
        try:
            template_path = self._get_template_path(template_file)
            template_content = template_path.read_text(encoding="utf-8")
            env = Environment(autoescape=select_autoescape(["html", "xml"]))
            template = env.from_string(template_content)
            return template.render(**context)
        except Exception as e:
            logger.error("Failed to render template '%s': %s", template_file, e)
            raise

    async def send_password_reset_email(
        self,
        to_email: str,
        reset_link: str,
        user_name: str,
        reset_type: PasswordResetType = PasswordResetType.USER_INITIATED,
    ) -> bool:
        """Send a password reset email."""
        template_file = (
            "password_reset_admin_forced.html"
            if reset_type == PasswordResetType.ADMIN_FORCED
            else "password_reset_user_initiated.html"
        )

        try:
            config: AuthenticationConfiguration = service_registry().get(
                AuthenticationConfiguration
            )
            html_body = self._render_template(
                template_file,
                reset_url=reset_link,
                user_name=user_name,
                year=datetime.now(UTC).year,
                logo_url=f"{config.server_url}/img/appkit_logo.svg",
            )

            subject = "Passwort zurücksetzen | AppKit"
            return await self.send_email(to_email, subject, html_body)

        except Exception as e:
            logger.exception("Failed to send password reset email: %s", e)
            return False


class ResendEmailProvider(EmailProviderBase):
    """Email provider using Resend API."""

    def __init__(self, config: ResendEmailConfig):
        super().__init__(config)
        self.config: ResendEmailConfig = config

    async def send_email(self, to_email: str, subject: str, html_body: str) -> bool:
        try:
            import httpx  # noqa: PLC0415

            url = "https://api.resend.com/emails"
            headers = {
                "Authorization": f"Bearer {self.config.api_key.get_secret_value()}",
                "Content-Type": "application/json",
            }
            payload = {
                "from": f"{self.config.from_name} <{self.config.from_email}>",
                "to": [to_email],
                "subject": subject,
                "html": html_body,
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url, headers=headers, json=payload, timeout=30.0
                )

                if response.status_code == 200:  # noqa: PLR2004
                    logger.info("Email sent successfully via Resend to %s", to_email)
                    return True

                logger.error(
                    "Failed to send email via Resend: %s %s",
                    response.status_code,
                    response.text,
                )
                return False

        except ImportError:
            logger.error("httpx is required for Resend provider but not installed.")
            return False
        except Exception as e:
            logger.exception("Error sending email via Resend: %s", e)
            return False


class AzureEmailProvider(EmailProviderBase):
    """Email provider using Azure Communication Services."""

    def __init__(self, config: AzureEmailConfig):
        super().__init__(config)
        self.config: AzureEmailConfig = config

    async def send_email(self, to_email: str, subject: str, html_body: str) -> bool:
        """Send email using Azure Communication Services."""
        try:
            from azure.communication.email import EmailClient  # noqa: PLC0415

            client = EmailClient.from_connection_string(
                self.config.connection_string.get_secret_value()
            )
            message = {
                "senderAddress": self.config.from_email,
                "recipients": {"to": [{"address": to_email}]},
                "content": {"subject": subject, "html": html_body},
            }

            poller = client.begin_send(message)
            result = poller.result()

            if result:
                logger.info("Email sent successfully via Azure to %s", to_email)
                return True

            logger.error("Failed to send email via Azure: No result returned")
            return False

        except ImportError:
            logger.error("azure-communication-email is required for Azure provider.")
            return False
        except Exception as e:
            logger.exception("Error sending email via Azure: %s", e)
            return False


class MockEmailProvider(EmailProviderBase):
    """Mock email provider for development/testing."""

    def __init__(self, config: MockEmailConfig):
        super().__init__(config)
        self.config: MockEmailConfig = config

    async def send_email(self, to_email: str, subject: str, html_body: str) -> bool:
        """Mock email sending by logging to console."""
        logger.info("=" * 80)
        logger.info("MOCK EMAIL SENT")
        logger.info("To: %s", to_email)
        logger.info("From: %s <%s>", self.config.from_name, self.config.from_email)
        logger.info("Subject: %s", subject)
        logger.info("-" * 80)
        logger.info("Body (first 200 chars):")
        logger.info("%s...", html_body[:200])
        logger.info("=" * 80)
        return True


class EmailServiceFactory:
    """Factory for creating email provider instances."""

    @staticmethod
    def create_provider(
        config: AuthenticationConfiguration,
    ) -> EmailProviderBase | None:
        """Create an email provider based on configuration."""
        if not config.email_provider:
            logger.warning("No email provider configured")
            return None

        provider_config = config.email_provider

        match provider_config.provider:
            case EmailProvider.RESEND:
                logger.info("Initializing Resend email provider")
                return ResendEmailProvider(provider_config)
            case EmailProvider.AZURE:
                logger.info("Initializing Azure email provider")
                return AzureEmailProvider(provider_config)
            case EmailProvider.MOCK:
                logger.info("Initializing Mock email provider")
                return MockEmailProvider(provider_config)
            case _:
                logger.error("Unknown email provider: %s", provider_config.provider)
                return None


def get_email_service() -> EmailProviderBase | None:
    """Get the configured email service instance.

    Returns:
        EmailProviderBase instance or None if not configured
    """
    config: AuthenticationConfiguration = service_registry().get(
        AuthenticationConfiguration
    )
    return EmailServiceFactory.create_provider(config)
