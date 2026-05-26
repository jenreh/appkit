"""Simplified OAuth2 configuration and utilities."""

import base64
import hashlib
import logging
import secrets
from typing import Any

from requests_oauthlib import OAuth2Session

from appkit_commons.registry import service_registry
from appkit_user.configuration import (
    AppleOAuthConfig,
    AuthenticationConfiguration,
    AzureOAuthConfig,
    GithubOAuthConfig,
    GoogleOAuthConfig,
    OAuthConfig,
    OAuthProvider,
)

logger = logging.getLogger(__name__)


def generate_pkce_pair() -> tuple[str, str]:
    """Generate PKCE code verifier and challenge (S256)."""
    # Generate code verifier (43-128 characters)
    code_verifier = (
        base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("utf-8").rstrip("=")
    )

    # Generate code challenge (SHA256 hash of verifier)
    code_challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode("utf-8")).digest())
        .decode("utf-8")
        .rstrip("=")
    )

    return code_verifier, code_challenge


class OAuthService:
    """Service class for OAuth2 operations."""

    providers: dict[str, OAuthConfig]
    github_config: GithubOAuthConfig
    azure_config: AzureOAuthConfig
    google_config: GoogleOAuthConfig
    apple_config: AppleOAuthConfig
    azure_enabled: bool = False
    github_enabled: bool = False
    google_enabled: bool = False
    apple_enabled: bool = False

    def __init__(self, config: AuthenticationConfiguration | None = None) -> None:
        """Initialize OAuth service with configuration."""
        if config is None:
            config = service_registry().get(AuthenticationConfiguration)

        if config is None:
            raise RuntimeError(
                "UserManagementConfiguration not initialized in registry"
            )

        self.server_url = config.server_url
        self.server_port = config.server_port
        self.github_config = None  # type: ignore[assignment]
        self.azure_config = None  # type: ignore[assignment]
        self.google_config = None  # type: ignore[assignment]
        self.apple_config = None  # type: ignore[assignment]

        self._initialize_providers(config.oauth_providers)

    def _initialize_providers(self, oauth_providers: list[OAuthConfig]) -> None:
        """Initialize provider configurations from configured entries."""
        self.providers = {}

        for provider_config in oauth_providers:
            normalized_config = self._apply_provider_defaults(provider_config)
            provider_key = self._provider_key(normalized_config.provider)
            self.providers[provider_key] = normalized_config

            if provider_key == OAuthProvider.GITHUB.value:
                self.github_config = normalized_config
                self.github_enabled = True
            elif provider_key == OAuthProvider.AZURE.value:
                self.azure_config = normalized_config
                self.azure_enabled = True
            elif provider_key == OAuthProvider.GOOGLE.value:
                self.google_config = normalized_config
                self.google_enabled = True
            elif provider_key == OAuthProvider.APPLE.value:
                self.apple_config = normalized_config
                self.apple_enabled = True

    def _apply_provider_defaults(self, provider_config: OAuthConfig) -> OAuthConfig:
        """Apply provider-specific defaults and normalization."""
        provider_key = self._provider_key(provider_config.provider)

        if provider_config.redirect_url is None:
            provider_config.redirect_url = (
                f"{self.server_url}:{self.server_port}/oauth/{provider_key}/callback"
            )

        if provider_key == OAuthProvider.AZURE.value and isinstance(
            provider_config, AzureOAuthConfig
        ):
            provider_config.auth_url = provider_config.auth_url.format(
                tenant=provider_config.tenant_id
            )
            provider_config.token_url = provider_config.token_url.format(
                tenant=provider_config.tenant_id
            )

        return provider_config

    def _as_provider(self, provider: OAuthProvider | str) -> OAuthProvider | str:
        if isinstance(provider, OAuthProvider):
            return provider

        provider_key = self._provider_key(provider)
        if provider_key in self.providers:
            return provider_key

        try:
            return OAuthProvider(provider)
        except ValueError as e:
            raise ValueError(f"Unsupported OAuth provider: {provider}") from e

    @staticmethod
    def _provider_key(provider: OAuthProvider | str) -> str:
        if isinstance(provider, OAuthProvider):
            return provider.value
        return str(provider).strip().lower()

    def _get_provider_config(self, provider: OAuthProvider | str) -> OAuthConfig:
        """Get provider configuration with tenant URL formatting."""
        prov = self._as_provider(provider)
        config = self.providers.get(self._provider_key(prov))
        if config is None:
            raise ValueError(f"Unsupported OAuth provider: {provider}")
        return config

    def _normalize_user_data(
        self, provider: OAuthProvider | str, user_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Normalize user data from different providers."""
        provider_key = self._provider_key(provider)

        if provider_key == OAuthProvider.GITHUB.value:
            user_data = {
                "id": str(user_data.get("id", "")),
                "email": user_data.get("email") or "",
                "name": user_data.get("name") or "",
                "avatar_url": user_data.get("avatar_url", ""),
                "username": user_data.get("login", ""),
            }

        if provider_key == OAuthProvider.AZURE.value:
            user_data = {
                "id": user_data.get("id") or user_data.get("sub") or "",
                "email": self._convert_upn_to_email(user_data.get("email"))
                or user_data.get("mail")
                or "",
                "name": user_data.get("name") or user_data.get("displayName") or "",
                "avatar_url": user_data.get("picture") or "",
                "username": user_data.get("preferred_username", ""),
            }

        user_data["email"] = user_data["email"].lower()
        return user_data

    def _convert_upn_to_email(self, user_principal_name: str) -> str:
        """
        Convert Azure UPN with #EXT# format to valid email address

        Example:
        'first.lastname_outlook.com#EXT#@tenant.onmicrosoft.com'
        -> 'first.lastname@outlook.com'
        """
        if "#EXT#" not in user_principal_name:
            return user_principal_name

        user_part = user_principal_name.split("#EXT#", maxsplit=1)[0]
        last_underscore_index = user_part.rfind("_")

        if last_underscore_index == -1:
            return user_principal_name

        username = user_part[:last_underscore_index]
        domain_part = user_part[last_underscore_index + 1 :]
        domain = domain_part.replace("_", ".")
        return f"{username}@{domain}"

    def get_auth_url(
        self, provider: OAuthProvider | str
    ) -> tuple[str, str, str | None]:
        """Get OAuth authorization URL with state and optional PKCE code_verifier.

        Returns (auth_url, state, code_verifier_or_none)
        """
        prov = self._as_provider(provider)
        config: OAuthConfig = self._get_provider_config(prov)

        # Generate state for CSRF protection
        state = secrets.token_urlsafe(32)
        oauth = OAuth2Session(
            client_id=config.client_id,
            scope=config.scopes,
            redirect_uri=config.redirect_url,
            state=state,
        )

        code_verifier: str | None = None
        # For Azure, enforce PKCE (S256)
        if self._provider_key(prov) == OAuthProvider.AZURE.value:
            code_verifier, code_challenge = generate_pkce_pair()
            auth_url, _ = oauth.authorization_url(
                config.auth_url,
                code_challenge=code_challenge,
                code_challenge_method="S256",
            )
        else:
            auth_url, _ = oauth.authorization_url(config.auth_url)

        return auth_url, state, code_verifier

    def get_redirect_url(self, provider: OAuthProvider | str) -> str:
        """Get redirect URL for OAuth provider."""
        config: OAuthConfig = self._get_provider_config(provider)
        provider_value = (
            provider.value if isinstance(provider, OAuthProvider) else str(provider)
        )
        return (
            config.redirect_url
            or f"{self.server_url}:{self.server_port}/oauth/{provider_value}/callback"
        )

    def exchange_code_for_token(
        self,
        provider: OAuthProvider | str,
        code: str,
        state: str,
        code_verifier: str | None = None,
    ) -> dict[str, Any]:
        """Exchange authorization code for access token."""
        prov = self._as_provider(provider)
        config: OAuthConfig = self._get_provider_config(prov)

        oauth = OAuth2Session(
            client_id=config.client_id,
            redirect_uri=config.redirect_url,
            state=state,
        )

        token_kwargs: dict[str, Any] = {"code": code}
        include_client_id: bool = False

        # Include PKCE code_verifier for Azure
        if self._provider_key(prov) == OAuthProvider.AZURE.value:
            if not code_verifier:
                raise ValueError(
                    "code_verifier required for Azure OAuth token exchange"
                )
            token_kwargs["code_verifier"] = code_verifier
            # For public clients, do not send client_secret
            az_cfg: AzureOAuthConfig = self.azure_config
            # Azure public clients: client_id should be included by fetch_token
            # (via include_client_id), redirect_uri is already bound to session.
            if az_cfg.is_public_client:
                include_client_id = True
            else:
                # Confidential client: use Basic auth with client_secret
                token_kwargs["client_secret"] = config.client_secret
                include_client_id = False
        else:
            # Non-Azure providers keep sending client_secret (GitHub)
            token_kwargs["client_secret"] = config.client_secret

        return oauth.fetch_token(
            config.token_url,
            include_client_id=include_client_id,
            **token_kwargs,
        )

    def get_user_info(
        self, provider: OAuthProvider | str, token: dict[str, Any]
    ) -> dict[str, Any]:
        """Get user information from OAuth provider."""
        prov = self._as_provider(provider)
        config: OAuthConfig = self._get_provider_config(prov)

        oauth = OAuth2Session(config.client_id, token=token)
        response = oauth.get(config.user_url)
        response.raise_for_status()
        user_data = response.json()

        provider_key = self._provider_key(prov)

        if (
            user_data.get("email") is None
            and provider_key == OAuthProvider.GITHUB.value
        ):
            email_response = oauth.get(self.github_config.user_email_url)
            email_response.raise_for_status()
            emails = email_response.json()
            user_data["email"] = next(
                (email["email"] for email in emails if email["primary"]), ""
            )

        if user_data.get("email") is None and provider_key == OAuthProvider.AZURE.value:
            email_response = oauth.get(self.azure_config.user_url)
            email_response.raise_for_status()
            profile_data = email_response.json()

            # Try multiple email fields in order of preference
            user_data["email"] = (
                profile_data.get("mail")
                or self._convert_upn_to_email(profile_data.get("userPrincipalName"))
                or (profile_data.get("otherMails") or [None])[0]
                or ""
            )

        return self._normalize_user_data(provider_key, user_data)

    def provider_supported(self, provider: OAuthProvider | str) -> bool:
        prov = self._as_provider(provider)
        return self._provider_key(prov) in self.providers
