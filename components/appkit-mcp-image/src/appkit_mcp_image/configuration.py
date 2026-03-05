"""BPMN component configuration."""

from typing import Literal

from pydantic import SecretStr

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
        backend_server: URL of the backend server.
        max_file_size_mb: Maximum file size in megabytes.
        max_images_to_keep: Maximum number of images to keep in storage.
        generator: Default image generator to use ("azure" or "google").
        azure_prompt_optimizer: LLM model name for Azure prompt optimization.
        azure_image_model: LLM model name for Azure image generation.
        azure_api_key: Azure API key for accessing Azure services.
        azure_base_url: Azure base URL for accessing Azure services.
        google_prompt_optimizer: LLM model name for Google prompt optimization.
        google_image_model: LLM model name for Google image generation.
        google_api_key: Google API key for accessing Google services.
        google_api_key: Google API key for accessing Google services.
        google_prompt_optimizer: LLM model name for Google prompt optimization.
        google_image_model: LLM model name for Google image generation.
    """

    backend_server: str = "http://localhost:8000"
    max_file_size_mb: int = 10
    max_images_to_keep: int = 50

    generator: Literal["azure", "google"] = "azure"

    azure_api_key: SecretStr | None = None
    azure_base_url: SecretStr | None = None
    azure_prompt_optimizer: str = "gpt-5-mini"
    azure_image_model: str = "FLUX.1-Kontext-pro"

    google_api_key: SecretStr | None = None
    google_prompt_optimizer: str = "gemini-2.0-flash-001"
    google_image_model: str = "imagen-4.0-generate-preview-06-06"

    auth_tokens: list[MCPTokenConfig] = []
