"""Email service for sending password reset emails."""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path

from jinja2 import Template

from appkit_commons.registry import service_registry
from appkit_user.configuration import (
    AuthenticationConfiguration,
    AzureEmailConfig,
    EmailProvider,
    MockEmailConfig,
    ResendEmailConfig,
)

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


class EmailProviderBase(ABC):
    """Abstract base class for email providers."""

    def __init__(self, config: ResendEmailConfig | AzureEmailConfig | MockEmailConfig):
        """Initialize email provider with configuration.

        Args:
            config: Email provider configuration
        """
        self.config = config

    @abstractmethod
    async def send_email(self, to_email: str, subject: str, html_body: str) -> bool:
        """Send an email.

        Args:
            to_email: Recipient email address
            subject: Email subject
            html_body: HTML content of the email

        Returns:
            True if email was sent successfully, False otherwise
        """

    async def send_password_reset_email(
        self,
        to_email: str,
        reset_link: str,
        user_name: str,
        reset_type: str = "user_initiated",
    ) -> bool:
        """Send a password reset email.

        Args:
            to_email: Recipient email address
            reset_link: Password reset URL
            user_name: User's name
            reset_type: Type of reset ("user_initiated" or "admin_forced")

        Returns:
            True if email was sent successfully, False otherwise
        """
        # Select appropriate template based on reset type
        if reset_type == "admin_forced":
            template_file = "password_reset_admin_forced.html"
        else:
            template_file = "password_reset_user_initiated.html"

        template_path = TEMPLATES_DIR / template_file

        # Load and render template
        try:
            with open(template_path, encoding="utf-8") as f:
                template = Template(f.read())

            html_body = template.render(
                reset_url=reset_link,
                user_name=user_name,
                year=datetime.now().year,
            )

            subject = "Passwort zurücksetzen | AppKit"

            return await self.send_email(to_email, subject, html_body)

        except Exception as e:
            logger.exception("Failed to render email template: %s", e)
            return False


class ResendEmailProvider(EmailProviderBase):
    """Email provider using Resend API."""

    def __init__(self, config: ResendEmailConfig):
        """Initialize Resend email provider.

        Args:
            config: Resend configuration
        """
        super().__init__(config)
        self.config: ResendEmailConfig = config

    async def send_email(self, to_email: str, subject: str, html_body: str) -> bool:
        """Send email using Resend API.

        Args:
            to_email: Recipient email address
            subject: Email subject
            html_body: HTML content

        Returns:
            True if sent successfully
        """
        try:
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.resend.com/emails",
                    headers={
                        "Authorization": f"Bearer {self.config.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "from": f"{self.config.from_name} <{self.config.from_email}>",
                        "to": [to_email],
                        "subject": subject,
                        "html": html_body,
                    },
                    timeout=30.0,
                )

                if response.status_code == 200:
                    logger.info("Email sent successfully via Resend to %s", to_email)
                    return True

                logger.error(
                    "Failed to send email via Resend: %s %s",
                    response.status_code,
                    response.text,
                )
                return False

        except Exception as e:
            logger.exception("Error sending email via Resend: %s", e)
            return False


class AzureEmailProvider(EmailProviderBase):
    """Email provider using Azure Communication Services."""

    def __init__(self, config: AzureEmailConfig):
        """Initialize Azure email provider.

        Args:
            config: Azure email configuration
        """
        super().__init__(config)
        self.config: AzureEmailConfig = config

    async def send_email(self, to_email: str, subject: str, html_body: str) -> bool:
        """Send email using Azure Communication Services.

        Args:
            to_email: Recipient email address
            subject: Email subject
            html_body: HTML content

        Returns:
            True if sent successfully
        """
        try:
            from azure.communication.email import EmailClient

            client = EmailClient.from_connection_string(self.config.connection_string)

            message = {
                "senderAddress": self.config.from_email,
                "recipients": {
                    "to": [{"address": to_email}],
                },
                "content": {
                    "subject": subject,
                    "html": html_body,
                },
            }

            poller = client.begin_send(message)
            result = poller.result()

            if result:
                logger.info("Email sent successfully via Azure to %s", to_email)
                return True

            logger.error("Failed to send email via Azure")
            return False

        except Exception as e:
            logger.exception("Error sending email via Azure: %s", e)
            return False


class MockEmailProvider(EmailProviderBase):
    """Mock email provider for development/testing."""

    def __init__(self, config: MockEmailConfig):
        """Initialize mock email provider.

        Args:
            config: Mock email configuration
        """
        super().__init__(config)
        self.config: MockEmailConfig = config

    async def send_email(self, to_email: str, subject: str, html_body: str) -> bool:
        """Mock email sending by logging to console.

        Args:
            to_email: Recipient email address
            subject: Email subject
            html_body: HTML content

        Returns:
            Always True
        """
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
        """Create an email provider based on configuration.

        Args:
            config: Authentication configuration

        Returns:
            EmailProviderBase instance or None if not configured
        """
        if not config.email_provider:
            logger.warning("No email provider configured")
            return None

        provider_config = config.email_provider

        if provider_config.provider == EmailProvider.RESEND:
            logger.info("Initializing Resend email provider")
            return ResendEmailProvider(provider_config)

        if provider_config.provider == EmailProvider.AZURE:
            logger.info("Initializing Azure email provider")
            return AzureEmailProvider(provider_config)

        if provider_config.provider == EmailProvider.MOCK:
            logger.info("Initializing Mock email provider")
            return MockEmailProvider(provider_config)

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
