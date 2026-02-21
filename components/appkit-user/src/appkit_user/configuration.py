from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field
from pydantic_settings import BaseSettings

from appkit_commons.configuration.base import BaseConfig


class OAuthProvider(StrEnum):
    GITHUB = "github"
    AZURE = "azure"


class OAuthConfig(BaseConfig):
    provider: OAuthProvider
    client_id: str
    client_secret: str
    scopes: list[str] = []
    auth_url: str = ""
    token_url: str = ""
    user_url: str = ""
    redirect_url: str | None = None


class GithubOAuthConfig(OAuthConfig):
    provider: Literal[OAuthProvider.GITHUB] = OAuthProvider.GITHUB
    scopes: list[str] = ["user", "user:email"]
    auth_url: str = "https://github.com/login/oauth/authorize"
    token_url: str = "https://github.com/login/oauth/access_token"  # noqa: S105
    user_url: str = "https://api.github.com/user"
    redirect_url: str | None = None

    user_email_url: str = "https://api.github.com/user/emails"


class AzureOAuthConfig(OAuthConfig):
    provider: Literal[OAuthProvider.AZURE] = OAuthProvider.AZURE
    scopes: list[str] = ["openid", "profile", "email", "User.Read"]
    auth_url: str = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize"
    token_url: str = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"  # noqa: S105
    user_url: str = "https://graph.microsoft.com/v1.0/me"
    redirect_url: str | None = None

    tenant_id: str = "common"  # Default to common tenant
    # If True, treat the Azure app as a public client (PKCE only, no client_secret)
    is_public_client: bool = False


AnyOAuthSetting = Annotated[
    GithubOAuthConfig | AzureOAuthConfig, Field(discriminator="provider")
]


class EmailProvider(StrEnum):
    RESEND = "resend"
    AZURE = "azure"
    MOCK = "mock"


class EmailProviderConfig(BaseConfig):
    """Base configuration for email providers."""

    provider: EmailProvider
    from_email: str
    from_name: str = "AppKit"


class ResendEmailConfig(EmailProviderConfig):
    """Configuration for Resend email provider."""

    provider: Literal[EmailProvider.RESEND] = EmailProvider.RESEND
    api_key: str


class AzureEmailConfig(EmailProviderConfig):
    """Configuration for Azure Communication Services email provider."""

    provider: Literal[EmailProvider.AZURE] = EmailProvider.AZURE
    connection_string: str


class MockEmailConfig(EmailProviderConfig):
    """Configuration for Mock email provider (development/testing)."""

    provider: Literal[EmailProvider.MOCK] = EmailProvider.MOCK
    from_email: str = "noreply@localhost"


AnyEmailProviderConfig = Annotated[
    ResendEmailConfig | AzureEmailConfig | MockEmailConfig,
    Field(discriminator="provider"),
]


class PasswordResetConfig(BaseConfig):
    """Configuration for password reset feature."""

    token_expiry_minutes: int = 60
    max_requests_per_hour: int = 3


class AuthenticationConfiguration(BaseSettings):
    """Configuration for OAuth providers."""

    session_timeout: int = 25  # minutes
    auth_token_refresh_delta: int = 10  # minutes
    session_monitor_interval_seconds: int = 60  # seconds between session checks
    server_url: str
    server_port: int

    oauth_providers: list[AnyOAuthSetting] = []

    # Email provider configuration
    email_provider: AnyEmailProviderConfig | None = None

    # Password reset configuration
    password_reset: PasswordResetConfig = PasswordResetConfig()
