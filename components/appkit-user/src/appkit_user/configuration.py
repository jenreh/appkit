from enum import StrEnum
from pathlib import Path
from typing import Annotated, Final, Literal
from urllib.parse import urlsplit, urlunsplit

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings

from appkit_commons.configuration.base import BaseConfig
from appkit_commons.public_path import (
    app_slug,
    default_session_cookie_name,
    public_url,
)


class OAuthProvider(StrEnum):
    GITHUB = "github"
    AZURE = "azure"
    GOOGLE = "google"
    APPLE = "apple"


class OAuthConfig(BaseConfig):
    provider: OAuthProvider
    client_id: str
    # SecretStr so the value is masked in repr()/model_dump() and cannot leak
    # into logs or tracebacks alongside the rest of the config object.
    client_secret: SecretStr
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


class GoogleOAuthConfig(OAuthConfig):
    provider: Literal[OAuthProvider.GOOGLE] = OAuthProvider.GOOGLE
    scopes: list[str] = ["openid", "profile", "email"]
    auth_url: str = "https://accounts.google.com/o/oauth2/v2/auth"
    token_url: str = "https://oauth2.googleapis.com/token"  # noqa: S105
    user_url: str = "https://www.googleapis.com/oauth2/v3/userinfo"
    redirect_url: str | None = None


class AppleOAuthConfig(OAuthConfig):
    provider: Literal[OAuthProvider.APPLE] = OAuthProvider.APPLE
    scopes: list[str] = ["name", "email"]
    auth_url: str = "https://appleid.apple.com/auth/authorize"
    token_url: str = "https://appleid.apple.com/auth/token"  # noqa: S105
    # Apple serves no userinfo endpoint; identity claims come from the
    # `id_token` in the token response (see OAuthService._apple_user_info).
    user_url: str = ""
    redirect_url: str | None = None


AnyOAuthSetting = Annotated[
    GithubOAuthConfig | AzureOAuthConfig | GoogleOAuthConfig | AppleOAuthConfig,
    Field(discriminator="provider"),
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
    api_key: SecretStr


class AzureEmailConfig(EmailProviderConfig):
    """Configuration for Azure Communication Services email provider."""

    provider: Literal[EmailProvider.AZURE] = EmailProvider.AZURE
    connection_string: SecretStr


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

    token_expiry_minutes: int = 30
    max_requests_per_hour: int = 3
    templates_dir: Path | None = None


_DEFAULT_PORTS: Final = {"http": 80, "https": 443}


class AuthenticationConfiguration(BaseSettings):
    """Configuration for OAuth providers."""

    session_timeout: int = 25  # minutes
    auth_token_refresh_delta: int = 10  # minutes
    session_monitor_interval_seconds: int = 60  # seconds between session checks
    server_url: str
    server_port: int

    # Session filter (servlet-filter style guard) settings
    # Apps on one origin need distinct cookie names and storage keys. ""
    # derives both from the app path prefix: "knai_session" and "knai_" under
    # /knai, "reflex_session" and no prefix at the site root.
    session_cookie_name: str = ""  # mirrors the auth token
    storage_key_prefix: str = Field(default="", pattern=r"^[A-Za-z0-9_]*$")
    # Secure by default: the cookie carries the session token, so it must not
    # be transmittable (or settable) over plaintext HTTP. Browsers exempt
    # localhost, so local HTTP dev still works; set False only for a non-TLS
    # deployment reached by hostname.
    session_cookie_secure: bool = True
    session_filter_enabled: bool = True  # kill switch for the guard
    # fnmatch glob allowlist; everything not matched here is default-deny.
    public_routes: list[str] = [
        "/login",
        "/password-reset",
        "/password-reset/confirm",
        "/oauth/*/callback",
    ]

    oauth_providers: list[AnyOAuthSetting] = []

    # Email provider configuration
    email_provider: AnyEmailProviderConfig | None = None

    # Password reset configuration
    password_reset: PasswordResetConfig = PasswordResetConfig()

    @property
    def public_origin(self) -> str:
        """server_url with server_port, without a port that is 0 or the default.

        A port already in server_url wins over server_port.
        """
        url = self.server_url.rstrip("/")
        parts = urlsplit(url)
        port = self.server_port
        if not port or parts.port or _DEFAULT_PORTS.get(parts.scheme) == port:
            return url
        return urlunsplit(parts._replace(netloc=f"{parts.netloc}:{port}"))

    @property
    def effective_session_cookie_name(self) -> str:
        """session_cookie_name, or the one derived from the app path prefix."""
        return self.session_cookie_name or default_session_cookie_name()

    @property
    def effective_storage_key_prefix(self) -> str:
        """storage_key_prefix, or the one derived from the app path prefix."""
        if self.storage_key_prefix:
            return self.storage_key_prefix
        slug = app_slug()
        return f"{slug}_" if slug else ""

    @property
    def public_base_url(self) -> str:
        """public_origin plus the app path prefix, e.g. ``https://x/knai``.

        Not added twice when server_url already ends with the prefix.
        """
        return public_url(self.public_origin)
