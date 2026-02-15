"""OpenAI client service for creating and managing AsyncOpenAI clients."""

import logging

from openai import AsyncOpenAI

from appkit_assistant.configuration import AssistantConfig
from appkit_commons.registry import service_registry

logger = logging.getLogger(__name__)


class OpenAIClientService:
    """Service for creating AsyncOpenAI clients with proper configuration.

    This service handles the complexity of creating OpenAI clients for both
    standard OpenAI API and Azure OpenAI endpoints. It reads configuration
    from the AssistantConfig and provides a consistent interface for client
    creation throughout the application.

    Usage:
        # Get service from registry
        service = service_registry().get(OpenAIClientService)

        # Create a client
        client = service.create_client()
        if client:
            response = await client.files.list()

        # Check if service is available
        if service.is_available:
            ...
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        on_azure: bool = False,
    ) -> None:
        """Initialize the OpenAI client service.

        Args:
            api_key: API key for OpenAI or Azure OpenAI.
            base_url: Base URL for the API (optional).
            on_azure: Whether to use Azure OpenAI client configuration.
        """
        self._api_key = api_key
        self._base_url = base_url
        self._on_azure = on_azure

    @classmethod
    def from_config(cls) -> "OpenAIClientService":
        """Create an OpenAIClientService from the AssistantConfig.

        Returns:
            Configured OpenAIClientService instance.
        """
        config = service_registry().get(AssistantConfig)
        api_key = (
            config.openai_api_key.get_secret_value() if config.openai_api_key else None
        )
        return cls(
            api_key=api_key,
            base_url=config.openai_base_url,
            on_azure=config.uses_azure,
        )

    @property
    def is_available(self) -> bool:
        """Check if the service is properly configured with an API key."""
        return self._api_key is not None

    def create_client(self) -> AsyncOpenAI | None:
        """Create an AsyncOpenAI client with the configured settings.

        Returns:
            Configured AsyncOpenAI client, or None if API key is not available.
        """
        if not self._api_key:
            logger.warning("OpenAI API key not configured")
            return None

        if self._api_key and self._base_url and self._on_azure:
            logger.debug("Creating Azure OpenAI client")
            return AsyncOpenAI(
                api_key=self._api_key,
                base_url=f"{self._base_url}/openai/v1",
                default_query={"api-version": "preview"},
            )
        if self._api_key and self._base_url:
            logger.debug("Creating OpenAI client with custom base URL")
            return AsyncOpenAI(api_key=self._api_key, base_url=self._base_url)
        if self._api_key:
            logger.debug("Creating standard OpenAI client")
            return AsyncOpenAI(api_key=self._api_key)

        return None


def get_openai_client_service() -> OpenAIClientService:
    """Get or create the OpenAI client service from the registry.

    This function ensures the service is registered and returns it.

    Returns:
        The configured OpenAIClientService.
    """
    registry = service_registry()

    # Check if already registered
    try:
        return registry.get(OpenAIClientService)
    except KeyError:
        pass

    # Create and register the service
    service = OpenAIClientService.from_config()
    registry.register_as(OpenAIClientService, service)
    return service
