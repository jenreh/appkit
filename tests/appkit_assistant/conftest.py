"""Shared fixtures for appkit_assistant tests."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from appkit_commons.registry import service_registry
from appkit_commons.configuration.configuration import ReflexConfig


def _ensure_reflex_config() -> None:
    reg = service_registry()
    if not reg.has(ReflexConfig):
        reg.register_as(ReflexConfig, ReflexConfig(deploy_url="http://localhost:3000"))


_ensure_reflex_config()

# Import schemas after registry is ready
from appkit_assistant.backend.schemas import AIModel, MCPAuthType  # noqa: E402
from appkit_assistant.backend.database.models import MCPServer  # noqa: E402


@pytest.fixture
def mock_session():
    """Mock async database session."""
    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_result.scalars.return_value.first.return_value = None
    mock_result.scalar_one_or_none.return_value = None
    session.execute.return_value = mock_result
    session.get = AsyncMock(return_value=None)
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.delete = AsyncMock()
    return session


@pytest.fixture
def sample_model() -> AIModel:
    """Return a sample AIModel for testing."""
    return AIModel(
        id="test-model",
        text="Test Model",
        model="gpt-4o",
        stream=True,
        temperature=0.7,
        supports_search=False,
        supports_tools=True,
    )


@pytest.fixture
def sample_models(sample_model) -> dict[str, AIModel]:
    return {sample_model.id: sample_model}


@pytest.fixture
def mcp_server_no_auth() -> MCPServer:
    """MCP server with no authentication."""
    return MCPServer(
        id=1,
        name="test-server",
        url="https://mcp.example.com/sse",
        headers="{}",
        prompt="Use this server for testing.",
        auth_type=MCPAuthType.NONE,
    )


@pytest.fixture
def mcp_server_with_headers() -> MCPServer:
    """MCP server with static Authorization header."""
    return MCPServer(
        id=2,
        name="auth-server",
        url="https://mcp.example.com/auth",
        headers='{"Authorization": "Bearer static-token-123"}',
        prompt="",
        auth_type=MCPAuthType.API_KEY,
    )


@pytest.fixture
def mcp_server_oauth() -> MCPServer:
    """MCP server requiring OAuth."""
    return MCPServer(
        id=3,
        name="oauth-server",
        url="https://mcp.example.com/oauth",
        headers="{}",
        prompt="",
        auth_type=MCPAuthType.OAUTH_DISCOVERY,
        discovery_url="https://mcp.example.com/.well-known/openid-configuration",
        oauth_client_id="client-id",
        oauth_client_secret="client-secret",
        oauth_issuer="https://mcp.example.com",
    )
