import logging

from fastmcp.server.auth.providers.jwt import StaticTokenVerifier

from appkit_commons.registry import service_registry
from appkit_mcp_image.configuration import MCPImageGeneratorConfig

logger = logging.getLogger(__name__)

config = service_registry().get(MCPImageGeneratorConfig)


def _load_tokens() -> dict:
    """Load token configuration from configuration."""
    tokens = config.auth_tokens
    if not tokens:
        return {}

    # Convert list of MCPTokenConfig to dict format expected by StaticTokenVerifier
    # Format: {token_id: {"client_id": "...", "scopes": [...]}}
    token_dict = {}
    for token_config in tokens:
        token_dict[token_config.id] = {
            "client_id": token_config.token.client_id,
            "scopes": token_config.token.scopes,
        }

    return token_dict


verifier = StaticTokenVerifier(
    tokens=_load_tokens(),
    required_scopes=["image:generate", "image:edit"],
)
