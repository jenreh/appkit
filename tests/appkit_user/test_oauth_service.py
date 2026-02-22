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

    def test_generate_pkce_pair_returns_two_strings(self) -> None:
        """generate_pkce_pair returns verifier and challenge strings."""
        # Act
        verifier, challenge = generate_pkce_pair()

        # Assert
        assert isinstance(verifier, str)
        assert isinstance(challenge, str)
        assert len(verifier) > 0
        assert len(challenge) > 0

    def test_generate_pkce_pair_verifier_length(self) -> None:
        """generate_pkce_pair produces verifier of correct length (43 chars)."""
        # Act
        verifier, _ = generate_pkce_pair()

        # Assert - Should be 43 characters (32 bytes base64-encoded, no padding)
        assert len(verifier) == 43

    def test_generate_pkce_pair_challenge_length(self) -> None:
        """generate_pkce_pair produces challenge of correct length (43 chars)."""
        # Act
        _, challenge = generate_pkce_pair()

        # Assert - SHA256 hash is 32 bytes -> 43 chars base64 without padding
        assert len(challenge) == 43

    def test_generate_pkce_pair_different_each_time(self) -> None:
        """generate_pkce_pair generates unique pairs."""
        # Act
        verifier1, challenge1 = generate_pkce_pair()
        verifier2, challenge2 = generate_pkce_pair()

        # Assert
        assert verifier1 != verifier2
        assert challenge1 != challenge2

    def test_generate_pkce_pair_no_padding(self) -> None:
        """generate_pkce_pair removes base64 padding."""
        # Act
        verifier, challenge = generate_pkce_pair()

        # Assert - No '=' padding characters
        assert "=" not in verifier
        assert "=" not in challenge

    def test_generate_pkce_pair_url_safe(self) -> None:
        """generate_pkce_pair produces URL-safe strings."""
        # Act
        verifier, challenge = generate_pkce_pair()

        # Assert - Should not contain + or /
        assert "+" not in verifier
        assert "/" not in verifier
        assert "+" not in challenge
        assert "/" not in challenge


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

    def test_oauth_service_initialization(
        self, oauth_service: OAuthService, auth_config: AuthenticationConfiguration
    ) -> None:
        """OAuthService initializes with config."""
        # Assert
        assert oauth_service.server_url == "http://localhost"
        assert oauth_service.server_port == 3000
        assert oauth_service.github_enabled is True
        assert oauth_service.azure_enabled is True

    def test_oauth_service_github_config_set(self, oauth_service: OAuthService) -> None:
        """OAuthService sets GitHub configuration."""
        # Assert
        assert oauth_service.github_config is not None
        assert oauth_service.github_config.client_id == "test_github_client_id"

    def test_oauth_service_azure_config_set(self, oauth_service: OAuthService) -> None:
        """OAuthService sets Azure configuration."""
        # Assert
        assert oauth_service.azure_config is not None
        assert oauth_service.azure_config.client_id == "test_azure_client_id"

    def test_oauth_service_providers_dict(self, oauth_service: OAuthService) -> None:
        """OAuthService initializes providers dictionary."""
        # Assert
        assert OAuthProvider.GITHUB in oauth_service.providers
        assert OAuthProvider.AZURE in oauth_service.providers

    def test_oauth_service_missing_config_raises(self) -> None:
        """OAuthService raises RuntimeError when config missing."""
        # Arrange
        with patch(
            "appkit_user.authentication.backend.services.oauth_service.service_registry"
        ) as mock_registry:
            mock_registry.return_value.get.return_value = None

            # Act & Assert
            with pytest.raises(RuntimeError, match="not initialized in registry"):
                OAuthService(config=None)

    def test_as_provider_from_string(self, oauth_service: OAuthService) -> None:
        """_as_provider converts string to OAuthProvider enum."""
        # Act
        result = oauth_service._as_provider("github")

        # Assert
        assert result == OAuthProvider.GITHUB

    def test_as_provider_from_enum(self, oauth_service: OAuthService) -> None:
        """_as_provider preserves OAuthProvider enum."""
        # Act
        result = oauth_service._as_provider(OAuthProvider.AZURE)

        # Assert
        assert result == OAuthProvider.AZURE

    def test_get_provider_config_github(self, oauth_service: OAuthService) -> None:
        """_get_provider_config returns GitHub config."""
        # Act
        config = oauth_service._get_provider_config("github")

        # Assert
        assert config.client_id == "test_github_client_id"

    def test_get_provider_config_azure(self, oauth_service: OAuthService) -> None:
        """_get_provider_config returns Azure config."""
        # Act
        config = oauth_service._get_provider_config(OAuthProvider.AZURE)

        # Assert
        assert config.client_id == "test_azure_client_id"

    def test_get_provider_config_unsupported_raises(
        self, oauth_service: OAuthService
    ) -> None:
        """_get_provider_config raises ValueError for unsupported provider."""
        # Act & Assert
        with pytest.raises(ValueError, match="Unsupported OAuth provider"):
            oauth_service._get_provider_config("unsupported_provider")

    def test_normalize_user_data_github(self, oauth_service: OAuthService) -> None:
        """_normalize_user_data formats GitHub user data."""
        # Arrange
        github_data = {
            "id": 12345,
            "email": "User@GitHub.com",
            "name": "Test User",
            "avatar_url": "https://avatar.url",
            "login": "testuser",
        }

        # Act
        normalized = oauth_service._normalize_user_data(
            OAuthProvider.GITHUB, github_data
        )

        # Assert
        assert normalized["id"] == "12345"
        assert normalized["email"] == "user@github.com"  # Lowercased
        assert normalized["name"] == "Test User"
        assert normalized["avatar_url"] == "https://avatar.url"
        assert normalized["username"] == "testuser"

    def test_normalize_user_data_azure(self, oauth_service: OAuthService) -> None:
        """_normalize_user_data formats Azure user data."""
        # Arrange
        azure_data = {
            "id": "azure-user-id",
            "email": "Test@AZURE.com",
            "name": "Azure User",
            "picture": "https://picture.url",
            "preferred_username": "azureuser",
        }

        # Act
        normalized = oauth_service._normalize_user_data(OAuthProvider.AZURE, azure_data)

        # Assert
        assert normalized["id"] == "azure-user-id"
        assert normalized["email"] == "test@azure.com"  # Lowercased
        assert normalized["name"] == "Azure User"
        assert normalized["avatar_url"] == "https://picture.url"
        assert normalized["username"] == "azureuser"

    def test_normalize_user_data_azure_uses_sub_as_id(
        self, oauth_service: OAuthService
    ) -> None:
        """_normalize_user_data uses 'sub' as fallback ID for Azure."""
        # Arrange
        azure_data = {"sub": "subject-id", "email": "test@azure.com"}

        # Act
        normalized = oauth_service._normalize_user_data(OAuthProvider.AZURE, azure_data)

        # Assert
        assert normalized["id"] == "subject-id"

    def test_convert_upn_to_email_external_user(
        self, oauth_service: OAuthService
    ) -> None:
        """_convert_upn_to_email converts Azure #EXT# UPN to email."""
        # Arrange
        upn = "first.last_outlook.com#EXT#@tenant.onmicrosoft.com"

        # Act
        email = oauth_service._convert_upn_to_email(upn)

        # Assert
        assert email == "first.last@outlook.com"

    def test_convert_upn_to_email_no_ext(self, oauth_service: OAuthService) -> None:
        """_convert_upn_to_email preserves UPN without #EXT#."""
        # Arrange
        upn = "user@domain.com"

        # Act
        email = oauth_service._convert_upn_to_email(upn)

        # Assert
        assert email == "user@domain.com"

    def test_convert_upn_to_email_no_underscore(
        self, oauth_service: OAuthService
    ) -> None:
        """_convert_upn_to_email handles #EXT# without underscore."""
        # Arrange
        upn = "invalid#EXT#@tenant.onmicrosoft.com"

        # Act
        email = oauth_service._convert_upn_to_email(upn)

        # Assert
        assert email == "invalid#EXT#@tenant.onmicrosoft.com"  # Unchanged

    @patch("appkit_user.authentication.backend.services.oauth_service.OAuth2Session")
    def test_get_auth_url_github(
        self, mock_oauth_session: Mock, oauth_service: OAuthService
    ) -> None:
        """get_auth_url generates GitHub authorization URL."""
        # Arrange
        mock_session_instance = MagicMock()
        mock_session_instance.authorization_url.return_value = (
            "https://github.com/login/oauth/authorize?client_id=test",
            "state_value",
        )
        mock_oauth_session.return_value = mock_session_instance

        # Act
        auth_url, state, code_verifier = oauth_service.get_auth_url("github")

        # Assert
        assert "https://github.com/login/oauth/authorize" in auth_url
        assert isinstance(state, str)
        assert len(state) > 0
        assert code_verifier is None  # GitHub doesn't use PKCE

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
        # Arrange
        mock_generate_pkce.return_value = ("verifier123", "challenge456")
        mock_session_instance = MagicMock()
        mock_session_instance.authorization_url.return_value = (
            "https://login.microsoftonline.com/authorize?client_id=test",
            "state_value",
        )
        mock_oauth_session.return_value = mock_session_instance

        # Act
        auth_url, state, code_verifier = oauth_service.get_auth_url(OAuthProvider.AZURE)

        # Assert
        assert "https://login.microsoftonline.com" in auth_url
        assert isinstance(state, str)
        assert code_verifier == "verifier123"
        # Verify PKCE was used in authorization_url call
        mock_session_instance.authorization_url.assert_called_once()
        call_kwargs = mock_session_instance.authorization_url.call_args[1]
        assert call_kwargs.get("code_challenge") == "challenge456"
        assert call_kwargs.get("code_challenge_method") == "S256"

    def test_get_redirect_url_github(self, oauth_service: OAuthService) -> None:
        """get_redirect_url returns GitHub redirect URL."""
        # Act
        redirect_url = oauth_service.get_redirect_url("github")

        # Assert
        assert redirect_url == "http://localhost:3000/oauth/github/callback"

    def test_get_redirect_url_azure(self, oauth_service: OAuthService) -> None:
        """get_redirect_url returns Azure redirect URL."""
        # Act
        redirect_url = oauth_service.get_redirect_url(OAuthProvider.AZURE)

        # Assert
        assert redirect_url == "http://localhost:3000/oauth/azure/callback"

    @patch("appkit_user.authentication.backend.services.oauth_service.OAuth2Session")
    def test_exchange_code_for_token_github(
        self, mock_oauth_session: Mock, oauth_service: OAuthService
    ) -> None:
        """exchange_code_for_token fetches token for GitHub."""
        # Arrange
        mock_session_instance = MagicMock()
        mock_session_instance.fetch_token.return_value = {
            "access_token": "github_token",
            "token_type": "bearer",
        }
        mock_oauth_session.return_value = mock_session_instance

        # Act
        token = oauth_service.exchange_code_for_token(
            "github", "auth_code_123", "state_abc"
        )

        # Assert
        assert token["access_token"] == "github_token"
        # Verify client_secret was passed
        call_kwargs = mock_session_instance.fetch_token.call_args[1]
        assert call_kwargs["client_secret"] == "test_github_secret"

    @patch("appkit_user.authentication.backend.services.oauth_service.OAuth2Session")
    def test_exchange_code_for_token_azure_with_pkce(
        self, mock_oauth_session: Mock, oauth_service: OAuthService
    ) -> None:
        """exchange_code_for_token fetches token for Azure with PKCE."""
        # Arrange
        oauth_service.azure_config.is_public_client = False  # Confidential client
        mock_session_instance = MagicMock()
        mock_session_instance.fetch_token.return_value = {
            "access_token": "azure_token",
            "token_type": "bearer",
        }
        mock_oauth_session.return_value = mock_session_instance

        # Act
        token = oauth_service.exchange_code_for_token(
            OAuthProvider.AZURE,
            "auth_code_456",
            "state_xyz",
            code_verifier="verifier789",
        )

        # Assert
        assert token["access_token"] == "azure_token"
        # Verify PKCE code_verifier was passed
        call_kwargs = mock_session_instance.fetch_token.call_args[1]
        assert call_kwargs["code_verifier"] == "verifier789"
        assert call_kwargs["client_secret"] == "test_azure_secret"

    @patch("appkit_user.authentication.backend.services.oauth_service.OAuth2Session")
    def test_exchange_code_for_token_azure_missing_verifier_raises(
        self, mock_oauth_session: Mock, oauth_service: OAuthService
    ) -> None:
        """exchange_code_for_token raises ValueError for Azure without code_verifier."""
        # Act & Assert
        with pytest.raises(ValueError, match="code_verifier required"):
            oauth_service.exchange_code_for_token(
                OAuthProvider.AZURE, "auth_code", "state", code_verifier=None
            )

    @patch("appkit_user.authentication.backend.services.oauth_service.OAuth2Session")
    def test_exchange_code_for_token_azure_public_client(
        self, mock_oauth_session: Mock, oauth_service: OAuthService
    ) -> None:
        """exchange_code_for_token uses include_client_id for Azure public client."""
        # Arrange
        oauth_service.azure_config.is_public_client = True
        mock_session_instance = MagicMock()
        mock_session_instance.fetch_token.return_value = {"access_token": "token"}
        mock_oauth_session.return_value = mock_session_instance

        # Act
        oauth_service.exchange_code_for_token(
            OAuthProvider.AZURE, "code", "state", code_verifier="verifier"
        )

        # Assert
        call_args = mock_session_instance.fetch_token.call_args
        assert call_args[1].get("include_client_id") is True
        assert "client_secret" not in call_args[1]

    @patch("appkit_user.authentication.backend.services.oauth_service.OAuth2Session")
    def test_get_user_info_github(
        self, mock_oauth_session: Mock, oauth_service: OAuthService
    ) -> None:
        """get_user_info fetches GitHub user data."""
        # Arrange
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

        # Act
        user_info = oauth_service.get_user_info("github", token)

        # Assert
        assert user_info["id"] == "123"
        assert user_info["email"] == "user@github.com"  # Lowercased
        assert user_info["username"] == "testuser"

    @patch("appkit_user.authentication.backend.services.oauth_service.OAuth2Session")
    def test_get_user_info_github_fetches_email_from_api(
        self, mock_oauth_session: Mock, oauth_service: OAuthService
    ) -> None:
        """get_user_info fetches email from GitHub emails API if missing."""
        # Arrange
        mock_session_instance = MagicMock()

        # User info without email
        mock_user_response = MagicMock()
        mock_user_response.json.return_value = {
            "id": 123,
            "email": None,
            "name": "Test User",
            "login": "testuser",
        }

        # Email API response
        mock_email_response = MagicMock()
        mock_email_response.json.return_value = [
            {"email": "secondary@example.com", "primary": False},
            {"email": "Primary@EXAMPLE.com", "primary": True},
        ]

        mock_session_instance.get.side_effect = [
            mock_user_response,
            mock_email_response,
        ]
        mock_oauth_session.return_value = mock_session_instance
        token = {"access_token": "github_token"}

        # Act
        user_info = oauth_service.get_user_info("github", token)

        # Assert
        assert user_info["email"] == "primary@example.com"  # Lowercased

    @patch("appkit_user.authentication.backend.services.oauth_service.OAuth2Session")
    def test_get_user_info_azure_with_upn_conversion(
        self, mock_oauth_session: Mock, oauth_service: OAuthService
    ) -> None:
        """get_user_info converts Azure UPN to email."""
        # Arrange
        mock_session_instance = MagicMock()

        # User info without email
        mock_user_response = MagicMock()
        mock_user_response.json.return_value = {
            "id": "azure-id",
            "email": None,
            "name": "Azure User",
        }

        # Profile API with UPN
        mock_profile_response = MagicMock()
        mock_profile_response.json.return_value = {
            "userPrincipalName": "user_outlook.com#EXT#@tenant.onmicrosoft.com",
        }

        mock_session_instance.get.side_effect = [
            mock_user_response,
            mock_profile_response,
        ]
        mock_oauth_session.return_value = mock_session_instance
        token = {"access_token": "azure_token"}

        # Act
        user_info = oauth_service.get_user_info(OAuthProvider.AZURE, token)

        # Assert
        assert user_info["email"] == "user@outlook.com"

    def test_provider_supported_github(self, oauth_service: OAuthService) -> None:
        """provider_supported returns True for GitHub."""
        # Act
        result = oauth_service.provider_supported("github")

        # Assert
        assert result is True

    def test_provider_supported_azure(self, oauth_service: OAuthService) -> None:
        """provider_supported returns True for Azure."""
        # Act
        result = oauth_service.provider_supported(OAuthProvider.AZURE)

        # Assert
        assert result is True

    def test_provider_supported_unsupported(self, oauth_service: OAuthService) -> None:
        """provider_supported returns False for unsupported provider."""
        # Arrange
        oauth_service.providers = {}  # Clear providers

        # Act
        result = oauth_service.provider_supported("github")

        # Assert
        assert result is False
