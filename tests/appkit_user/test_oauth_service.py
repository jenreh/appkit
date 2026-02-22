"""Tests for OAuthService."""

from unittest.mock import MagicMock, Mock, patch

import pytest

from appkit_user.authentication.backend.services import (
    OAuthService,
    generate_pkce_pair,
)
from appkit_user.configuration import (
    AuthenticationConfiguration,
    AzureOAuthConfig,
    GithubOAuthConfig,
    OAuthProvider,
)


class TestGeneratePkcePair:
    """Test suite for generate_pkce_pair function."""

    def test_generate_pkce_pair_structure(self) -> None:
        """generate_pkce_pair returns valid verifier and challenge strings."""
        verifier, challenge = generate_pkce_pair()

        # Check types and basic constraints
        assert isinstance(verifier, str)
        assert isinstance(challenge, str)
        assert len(verifier) == 43
        assert len(challenge) == 43

        # Check formatting (URL safe, no padding)
        for s in (verifier, challenge):
            assert len(s) > 0
            assert "=" not in s
            assert "+" not in s
            assert "/" not in s

    def test_generate_pkce_pair_different_each_time(self) -> None:
        """generate_pkce_pair generates unique pairs."""
        verifier1, challenge1 = generate_pkce_pair()
        verifier2, challenge2 = generate_pkce_pair()

        assert verifier1 != verifier2
        assert challenge1 != challenge2


class TestOAuthService:
    """Test suite for OAuthService class."""

    @pytest.fixture
    def github_config(self) -> GithubOAuthConfig:
        """Provide GitHub OAuth configuration."""
        return GithubOAuthConfig(
            client_id="test_github_client_id",
            client_secret="test_github_secret",
            redirect_url="http://localhost:3000/oauth/github/callback",
        )

    @pytest.fixture
    def azure_config(self) -> AzureOAuthConfig:
        """Provide Azure OAuth configuration."""
        return AzureOAuthConfig(
            client_id="test_azure_client_id",
            client_secret="test_azure_secret",
            tenant_id="test-tenant-id",
            redirect_url="http://localhost:3000/oauth/azure/callback",
        )

    @pytest.fixture
    def auth_config(
        self, github_config: GithubOAuthConfig, azure_config: AzureOAuthConfig
    ) -> AuthenticationConfiguration:
        """Provide complete authentication configuration."""
        return AuthenticationConfiguration(
            server_url="http://localhost",
            server_port=3000,
            oauth_providers=[github_config, azure_config],
        )

    @pytest.fixture
    def oauth_service(self, auth_config: AuthenticationConfiguration) -> OAuthService:
        """Provide OAuth service instance."""
        with patch(
            "appkit_user.authentication.backend.services.oauth_service.service_registry"
        ) as mock_registry:
            mock_registry.return_value.get.return_value = auth_config
            return OAuthService(config=auth_config)

    def test_oauth_service_initialization(self, oauth_service: OAuthService) -> None:
        """OAuthService initializes correctly with config and providers."""
        assert oauth_service.server_url == "http://localhost"
        assert oauth_service.server_port == 3000
        assert oauth_service.github_enabled is True
        assert oauth_service.azure_enabled is True

        # Check configs are set
        assert oauth_service.github_config is not None
        assert oauth_service.github_config.client_id == "test_github_client_id"
        assert oauth_service.azure_config is not None
        assert oauth_service.azure_config.client_id == "test_azure_client_id"

        # Check providers dict
        assert OAuthProvider.GITHUB in oauth_service.providers
        assert OAuthProvider.AZURE in oauth_service.providers

    def test_oauth_service_missing_config_raises(self) -> None:
        """OAuthService raises RuntimeError when config missing."""
        with patch(
            "appkit_user.authentication.backend.services.oauth_service.service_registry"
        ) as mock_registry:
            mock_registry.return_value.get.return_value = None

            with pytest.raises(RuntimeError, match="not initialized in registry"):
                OAuthService(config=None)

    @pytest.mark.parametrize(
        ("provider_input", "expected"),
        [
            ("github", OAuthProvider.GITHUB),
            (OAuthProvider.AZURE, OAuthProvider.AZURE),
        ],
    )
    def test_as_provider(
        self,
        oauth_service: OAuthService,
        provider_input: str | OAuthProvider,
        expected: OAuthProvider,
    ) -> None:
        """_as_provider resolves strings and enums correctly."""
        assert oauth_service._as_provider(provider_input) == expected

    @pytest.mark.parametrize(
        ("provider", "expected_client_id"),
        [
            ("github", "test_github_client_id"),
            (OAuthProvider.AZURE, "test_azure_client_id"),
        ],
    )
    def test_get_provider_config(
        self,
        oauth_service: OAuthService,
        provider: str | OAuthProvider,
        expected_client_id: str,
    ) -> None:
        """_get_provider_config returns correct configuration."""
        config = oauth_service._get_provider_config(provider)
        assert config.client_id == expected_client_id

    def test_get_provider_config_unsupported_raises(
        self, oauth_service: OAuthService
    ) -> None:
        """_get_provider_config raises ValueError for unsupported provider."""
        with pytest.raises(ValueError, match="Unsupported OAuth provider"):
            oauth_service._get_provider_config("unsupported_provider")

    @pytest.mark.parametrize(
        ("provider", "raw_data", "expected"),
        [
            (
                OAuthProvider.GITHUB,
                {
                    "id": 12345,
                    "email": "User@GitHub.com",
                    "name": "Test User",
                    "avatar_url": "https://avatar.url",
                    "login": "testuser",
                },
                {
                    "id": "12345",
                    "email": "user@github.com",
                    "name": "Test User",
                    "avatar_url": "https://avatar.url",
                    "username": "testuser",
                },
            ),
            (
                OAuthProvider.AZURE,
                {
                    "id": "azure-user-id",
                    "email": "Test@AZURE.com",
                    "name": "Azure User",
                    "picture": "https://picture.url",
                    "preferred_username": "azureuser",
                },
                {
                    "id": "azure-user-id",
                    "email": "test@azure.com",
                    "name": "Azure User",
                    "avatar_url": "https://picture.url",
                    "username": "azureuser",
                },
            ),
            (
                OAuthProvider.AZURE,
                {"sub": "subject-id", "email": "test@azure.com"},
                {"id": "subject-id"},  # Minimal check for 'sub' fallback
            ),
        ],
    )
    def test_normalize_user_data(
        self,
        oauth_service: OAuthService,
        provider: OAuthProvider,
        raw_data: dict,
        expected: dict,
    ) -> None:
        """_normalize_user_data formats provider data correctly."""
        normalized = oauth_service._normalize_user_data(provider, raw_data)

        for key, value in expected.items():
            assert normalized[key] == value

    @pytest.mark.parametrize(
        ("upn", "expected_email"),
        [
            (
                "first.last_outlook.com#EXT#@tenant.onmicrosoft.com",
                "first.last@outlook.com",
            ),
            ("user@domain.com", "user@domain.com"),
            (
                "invalid#EXT#@tenant.onmicrosoft.com",
                "invalid#EXT#@tenant.onmicrosoft.com",
            ),
        ],
    )
    def test_convert_upn_to_email(
        self, oauth_service: OAuthService, upn: str, expected_email: str
    ) -> None:
        """_convert_upn_to_email handles various UPN formats."""
        assert oauth_service._convert_upn_to_email(upn) == expected_email

    @patch("appkit_user.authentication.backend.services.oauth_service.OAuth2Session")
    def test_get_auth_url_github(
        self, mock_oauth_session: Mock, oauth_service: OAuthService
    ) -> None:
        """get_auth_url generates GitHub authorization URL."""
        mock_session_instance = MagicMock()
        mock_session_instance.authorization_url.return_value = (
            "https://github.com/login/oauth/authorize?client_id=test",
            "state_value",
        )
        mock_oauth_session.return_value = mock_session_instance

        auth_url, state, code_verifier = oauth_service.get_auth_url("github")

        assert "https://github.com/login/oauth/authorize" in auth_url
        assert isinstance(state, str)
        assert len(state) > 0
        assert code_verifier is None

    @patch("appkit_user.authentication.backend.services.oauth_service.OAuth2Session")
    @patch(
        "appkit_user.authentication.backend.services.oauth_service.generate_pkce_pair"
    )
    def test_get_auth_url_azure_with_pkce(
        self,
        mock_generate_pkce: Mock,
        mock_oauth_session: Mock,
        oauth_service: OAuthService,
    ) -> None:
        """get_auth_url generates Azure authorization URL with PKCE."""
        mock_generate_pkce.return_value = ("verifier123", "challenge456")
        mock_session_instance = MagicMock()
        mock_session_instance.authorization_url.return_value = (
            "https://login.microsoftonline.com/authorize?client_id=test",
            "state_value",
        )
        mock_oauth_session.return_value = mock_session_instance

        auth_url, state, code_verifier = oauth_service.get_auth_url(OAuthProvider.AZURE)

        assert "https://login.microsoftonline.com" in auth_url
        assert isinstance(state, str)
        assert code_verifier == "verifier123"

        mock_session_instance.authorization_url.assert_called_once()
        call_kwargs = mock_session_instance.authorization_url.call_args[1]
        assert call_kwargs.get("code_challenge") == "challenge456"
        assert call_kwargs.get("code_challenge_method") == "S256"

    @pytest.mark.parametrize(
        ("provider", "expected_url"),
        [
            ("github", "http://localhost:3000/oauth/github/callback"),
            (OAuthProvider.AZURE, "http://localhost:3000/oauth/azure/callback"),
        ],
    )
    def test_get_redirect_url(
        self,
        oauth_service: OAuthService,
        provider: str | OAuthProvider,
        expected_url: str,
    ) -> None:
        """get_redirect_url returns correct redirect URL."""
        assert oauth_service.get_redirect_url(provider) == expected_url

    @patch("appkit_user.authentication.backend.services.oauth_service.OAuth2Session")
    def test_exchange_code_for_token_github(
        self, mock_oauth_session: Mock, oauth_service: OAuthService
    ) -> None:
        """exchange_code_for_token fetches token for GitHub."""
        mock_session_instance = MagicMock()
        mock_session_instance.fetch_token.return_value = {
            "access_token": "github_token",
            "token_type": "bearer",
        }
        mock_oauth_session.return_value = mock_session_instance

        token = oauth_service.exchange_code_for_token(
            "github", "auth_code_123", "state_abc"
        )

        assert token["access_token"] == "github_token"
        assert (
            mock_session_instance.fetch_token.call_args[1]["client_secret"]
            == "test_github_secret"
        )

    @patch("appkit_user.authentication.backend.services.oauth_service.OAuth2Session")
    def test_exchange_code_for_token_azure_with_pkce(
        self, mock_oauth_session: Mock, oauth_service: OAuthService
    ) -> None:
        """exchange_code_for_token fetches token for Azure with PKCE."""
        oauth_service.azure_config.is_public_client = False
        mock_session_instance = MagicMock()
        mock_session_instance.fetch_token.return_value = {
            "access_token": "azure_token",
            "token_type": "bearer",
        }
        mock_oauth_session.return_value = mock_session_instance

        token = oauth_service.exchange_code_for_token(
            OAuthProvider.AZURE,
            "auth_code_456",
            "state_xyz",
            code_verifier="verifier789",
        )

        assert token["access_token"] == "azure_token"
        call_kwargs = mock_session_instance.fetch_token.call_args[1]
        assert call_kwargs["code_verifier"] == "verifier789"
        assert call_kwargs["client_secret"] == "test_azure_secret"

    @patch("appkit_user.authentication.backend.services.oauth_service.OAuth2Session")
    def test_exchange_code_for_token_azure_missing_verifier_raises(
        self, mock_oauth_session: Mock, oauth_service: OAuthService
    ) -> None:
        """exchange_code_for_token raises ValueError for Azure without code_verifier."""
        with pytest.raises(ValueError, match="code_verifier required"):
            oauth_service.exchange_code_for_token(
                OAuthProvider.AZURE, "auth_code", "state", code_verifier=None
            )

    @patch("appkit_user.authentication.backend.services.oauth_service.OAuth2Session")
    def test_exchange_code_for_token_azure_public_client(
        self, mock_oauth_session: Mock, oauth_service: OAuthService
    ) -> None:
        """exchange_code_for_token uses include_client_id for Azure public client."""
        oauth_service.azure_config.is_public_client = True
        mock_session_instance = MagicMock()
        mock_session_instance.fetch_token.return_value = {"access_token": "token"}
        mock_oauth_session.return_value = mock_session_instance

        oauth_service.exchange_code_for_token(
            OAuthProvider.AZURE, "code", "state", code_verifier="verifier"
        )

        call_args = mock_session_instance.fetch_token.call_args
        assert call_args[1].get("include_client_id") is True
        assert "client_secret" not in call_args[1]

    @patch("appkit_user.authentication.backend.services.oauth_service.OAuth2Session")
    def test_get_user_info_github(
        self, mock_oauth_session: Mock, oauth_service: OAuthService
    ) -> None:
        """get_user_info fetches GitHub user data."""
        mock_session_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": 123,
            "email": "user@GITHUB.com",
            "name": "Test User",
            "login": "testuser",
            "avatar_url": "https://avatar.url",
        }
        mock_session_instance.get.return_value = mock_response
        mock_oauth_session.return_value = mock_session_instance
        token = {"access_token": "github_token"}

        user_info = oauth_service.get_user_info("github", token)

        assert user_info["id"] == "123"
        assert user_info["email"] == "user@github.com"
        assert user_info["username"] == "testuser"

    @patch("appkit_user.authentication.backend.services.oauth_service.OAuth2Session")
    def test_get_user_info_github_fetches_email_from_api(
        self, mock_oauth_session: Mock, oauth_service: OAuthService
    ) -> None:
        """get_user_info fetches email from GitHub emails API if missing."""
        mock_session_instance = MagicMock()
        mock_session_instance.get.side_effect = [
            MagicMock(
                json=lambda: {
                    "id": 123,
                    "email": None,
                    "name": "Test User",
                    "login": "testuser",
                }
            ),
            MagicMock(
                json=lambda: [
                    {"email": "secondary@example.com", "primary": False},
                    {"email": "Primary@EXAMPLE.com", "primary": True},
                ]
            ),
        ]
        mock_oauth_session.return_value = mock_session_instance
        token = {"access_token": "github_token"}

        user_info = oauth_service.get_user_info("github", token)

        assert user_info["email"] == "primary@example.com"

    @patch("appkit_user.authentication.backend.services.oauth_service.OAuth2Session")
    def test_get_user_info_azure_with_upn_conversion(
        self, mock_oauth_session: Mock, oauth_service: OAuthService
    ) -> None:
        """get_user_info converts Azure UPN to email."""
        mock_session_instance = MagicMock()
        mock_session_instance.get.side_effect = [
            MagicMock(
                json=lambda: {
                    "id": "azure-id",
                    "email": None,
                    "name": "Azure User",
                }
            ),
            MagicMock(
                json=lambda: {
                    "userPrincipalName": "user_outlook.com#EXT#@tenant.onmicrosoft.com",
                }
            ),
        ]
        mock_oauth_session.return_value = mock_session_instance
        token = {"access_token": "azure_token"}

        user_info = oauth_service.get_user_info(OAuthProvider.AZURE, token)

        assert user_info["email"] == "user@outlook.com"

    def test_provider_supported_true(self, oauth_service: OAuthService) -> None:
        """provider_supported returns True for configured provider."""
        # Assuming github is in default mock providers
        assert oauth_service.provider_supported("github") is True

    def test_provider_supported_false(self, oauth_service: OAuthService) -> None:
        """provider_supported returns False for unconfigured provider."""
        # Simulate empty providers
        oauth_service.providers = {}
        # 'github' is valid enum but not configured
        assert oauth_service.provider_supported("github") is False

    def test_provider_supported_invalid_raises(
        self, oauth_service: OAuthService
    ) -> None:
        """provider_supported raises ValueError for invalid provider string."""
        with pytest.raises(ValueError, match="Unsupported OAuth provider"):
            oauth_service.provider_supported("invalid_provider")
