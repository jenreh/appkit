"""Simplified OAuth2 configuration and utilities."""

import base64
import hashlib
import json
import logging
import secrets
from collections.abc import Sequence
from typing import Any, cast

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


def _as_bool(value: Any) -> bool:
    """Coerce an OIDC claim to bool.

    ``email_verified`` is specified as a boolean but Apple (and some Google
    responses) serialise it as the string ``"true"``/``"false"``, which is
    truthy either way when tested directly.
    """
    if isinstance(value, str):
        return value.strip().lower() == "true"
    return bool(value)


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
        self.public_base_url = config.public_base_url
        self.github_config = None  # type: ignore[assignment]
        self.azure_config = None  # type: ignore[assignment]
        self.google_config = None  # type: ignore[assignment]
        self.apple_config = None  # type: ignore[assignment]

        self._initialize_providers(config.oauth_providers)

    def _initialize_providers(self, oauth_providers: Sequence[OAuthConfig]) -> None:
        """Initialize provider configurations from configured entries."""
        self.providers = {}

        for provider_config in oauth_providers:
            normalized_config = self._apply_provider_defaults(provider_config)
            provider_key = self._provider_key(normalized_config.provider)
            self.providers[provider_key] = normalized_config

            if provider_key == OAuthProvider.GITHUB.value:
                self.github_config = cast("GithubOAuthConfig", normalized_config)
                self.github_enabled = True
            elif provider_key == OAuthProvider.AZURE.value:
                self.azure_config = cast("AzureOAuthConfig", normalized_config)
                self.azure_enabled = True
            elif provider_key == OAuthProvider.GOOGLE.value:
                self.google_config = cast("GoogleOAuthConfig", normalized_config)
                self.google_enabled = True
            elif provider_key == OAuthProvider.APPLE.value:
                self.apple_config = cast("AppleOAuthConfig", normalized_config)
                self.apple_enabled = True

    def _apply_provider_defaults(self, provider_config: OAuthConfig) -> OAuthConfig:
        """Apply provider-specific defaults and normalization."""
        provider_key = self._provider_key(provider_config.provider)

        if provider_config.redirect_url is None:
            provider_config.redirect_url = (
                f"{self.public_base_url}/oauth/{provider_key}/callback"
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
                "email_verified": bool(user_data.get("email_verified")),
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
                # Entra ID only returns addresses it owns/has validated for the
                # tenant, so a present address counts as verified.
                "email_verified": bool(
                    self._convert_upn_to_email(user_data.get("email"))
                    or user_data.get("mail")
                ),
                "avatar_url": user_data.get("picture") or "",
                "username": user_data.get("preferred_username", ""),
            }

        if provider_key in (OAuthProvider.GOOGLE.value, OAuthProvider.APPLE.value):
            # Google/Apple are OIDC: the subject is under "sub", not "id", and
            # Apple frequently omits "email" on subsequent logins.
            user_data = {
                "id": user_data.get("id") or user_data.get("sub") or "",
                "email": user_data.get("email") or "",
                "email_verified": _as_bool(user_data.get("email_verified")),
                "name": user_data.get("name") or user_data.get("given_name") or "",
                "avatar_url": user_data.get("picture")
                or user_data.get("avatar_url")
                or "",
                "username": user_data.get("email") or "",
            }

        user_data["email"] = (user_data.get("email") or "").lower()
        user_data["email_verified"] = bool(user_data.get("email_verified"))
        return user_data

    def _convert_upn_to_email(self, user_principal_name: str | None) -> str:
        """
        Convert Azure UPN with #EXT# format to valid email address

        Example:
        'first.lastname_outlook.com#EXT#@tenant.onmicrosoft.com'
        -> 'first.lastname@outlook.com'
        """
        if not user_principal_name:
            return ""

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
            or f"{self.public_base_url}/oauth/{provider_value}/callback"
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
                token_kwargs["client_secret"] = config.client_secret.get_secret_value()
                include_client_id = False
        else:
            # Non-Azure providers keep sending client_secret (GitHub)
            token_kwargs["client_secret"] = config.client_secret.get_secret_value()

        return cast(
            "dict[str, Any]",
            oauth.fetch_token(
                config.token_url,
                include_client_id=include_client_id,
                **token_kwargs,
            ),
        )

    def _apple_user_info(self, token: dict[str, Any]) -> dict[str, Any]:
        """Read Sign in with Apple claims out of the ``id_token``.

        Apple serves no userinfo endpoint — identity claims are only ever
        delivered in the ``id_token`` returned by the token endpoint. That
        token arrives over a direct, TLS-protected server-to-server call whose
        response we requested ourselves, which is the case OpenID Connect Core
        3.1.3.7 allows signature verification to be skipped for.
        """
        id_token = token.get("id_token")
        if not id_token:
            raise ValueError("Apple token response did not include an id_token.")

        try:
            payload_segment = id_token.split(".")[1]
            padding = "=" * (-len(payload_segment) % 4)
            claims = json.loads(
                base64.urlsafe_b64decode(payload_segment + padding).decode("utf-8")
            )
        except (IndexError, ValueError, UnicodeDecodeError) as exc:
            raise ValueError("Apple id_token could not be decoded.") from exc

        return self._normalize_user_data(OAuthProvider.APPLE.value, claims)

    def get_user_info(
        self, provider: OAuthProvider | str, token: dict[str, Any]
    ) -> dict[str, Any]:
        """Get user information from OAuth provider.

        The returned dict always carries an ``email_verified`` flag. Callers
        must not treat an address as an identity assertion unless it is set —
        an unverified provider address is attacker-controlled text.
        """
        prov = self._as_provider(provider)
        config: OAuthConfig = self._get_provider_config(prov)

        if self._provider_key(prov) == OAuthProvider.APPLE.value:
            return self._apple_user_info(token)

        oauth = OAuth2Session(config.client_id, token=token)
        response = oauth.get(config.user_url)
        response.raise_for_status()
        user_data = response.json()

        provider_key = self._provider_key(prov)

        if provider_key == OAuthProvider.GITHUB.value:
            # /user only exposes the *public* profile email and never says
            # whether it was confirmed, so always resolve the primary address
            # through /user/emails, which carries the `verified` flag.
            email_response = oauth.get(self.github_config.user_email_url)
            email_response.raise_for_status()
            emails = email_response.json()
            primary = next(
                (email for email in emails if email.get("primary")),
                None,
            )
            if primary:
                user_data["email"] = primary.get("email") or ""
                user_data["email_verified"] = bool(primary.get("verified"))
            else:
                user_data.setdefault("email", "")
                user_data["email_verified"] = False

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
