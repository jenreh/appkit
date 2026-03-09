"""MCP Image Generator component configuration."""

from typing import Literal

from appkit_commons.configuration.base import BaseConfig

ScopeType = Literal["image:generate", "image:edit"]


class MCPToken(BaseConfig):
    """Model representing an MCP token and its associated scopes.

    Attributes:
        client_id: Identifier for the client associated with the token.
        scopes: List of scopes/permissions granted to the token.
    """

    client_id: str
    scopes: list[ScopeType]


class MCPTokenConfig(BaseConfig):
    """Configuration for MCP token authentication.

    Attributes:
        id: Unique identifier for the token configuration.
        token: MCPToken instance containing the token and its scopes.
    """

    id: str
    token: MCPToken


class MCPImageGeneratorConfig(BaseConfig):
    """Configuration for the MCP Image Generator server.

    Attributes:
        default_model: Generator model ID from the imagecreator registry.
        max_file_size_mb: Maximum file size in megabytes for uploads.
        auth_tokens: MCP token authentication configuration.
    """

    default_model: str = ""
    max_file_size_mb: int = 10
    auth_tokens: list[MCPTokenConfig] = []
