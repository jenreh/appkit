"""OpenAI client service for creating and managing AsyncOpenAI clients."""

import logging

from openai import AsyncOpenAI

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

        # Create a client for a specific AI model (subscription)
        client = await OpenAIClientService.create_client_for_model("gpt-4o")
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
        """Deprecated: use the service registry instance set by AIModelRegistry."""
        return cls()

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

        return _build_client(self._api_key, self._base_url, self._on_azure)

    @staticmethod
    async def create_client_for_model(
        ai_model: str,
    ) -> AsyncOpenAI | None:
        """Create an AsyncOpenAI client using credentials from a DB model.

        Looks up the :class:`AssistantAIModel` by its ``model_id`` string
        and builds a client with the model's own API key / base URL.

        Args:
            ai_model: The ``model_id`` string (e.g. ``"gpt-4o"``).

        Returns:
            Configured AsyncOpenAI client, or *None* if the model has
            no API key or cannot be found.
        """
        # Import here to avoid circular imports at module level
        from appkit_assistant.backend.database.repositories import (  # noqa: PLC0415
            ai_model_repo,
        )
        from appkit_commons.database.session import get_asyncdb_session  # noqa: PLC0415

        try:
            async with get_asyncdb_session() as session:
                model = await ai_model_repo.find_by_model_id(session, ai_model)
                if not model or not model.api_key:
                    logger.warning("No API key for model %s", ai_model)
                    return None
                return _build_client(model.api_key, model.base_url, model.on_azure)
        except Exception as e:
            logger.error(
                "Failed to create client for model %s: %s",
                ai_model,
                e,
            )
            return None


def _build_client(
    api_key: str,
    base_url: str | None,
    on_azure: bool,
) -> AsyncOpenAI:
    """Build an AsyncOpenAI client from explicit credentials.

    Args:
        api_key: API key (required).
        base_url: Optional base URL override.
        on_azure: Whether to use Azure OpenAI endpoint conventions.

    Returns:
        Configured AsyncOpenAI client.
    """
    if base_url and on_azure:
        logger.debug("Creating Azure OpenAI client")
        return AsyncOpenAI(
            api_key=api_key,
            base_url=f"{base_url}/openai/v1",
            default_query={"api-version": "preview"},
        )
    if base_url:
        logger.debug("Creating OpenAI client with custom base URL")
        return AsyncOpenAI(api_key=api_key, base_url=base_url)
    logger.debug("Creating standard OpenAI client")
    return AsyncOpenAI(api_key=api_key)


def get_openai_client_service() -> OpenAIClientService:
    """Return the OpenAIClientService registered by AIModelRegistry at startup.

    Returns an unavailable (no-key) instance if the registry has not been
    populated yet (e.g. no openai/openai_skills model in the DB).
    """
    try:
        return service_registry().get(OpenAIClientService)
    except KeyError:
        logger.warning(
            "OpenAIClientService not registered - no openai DB model available"
        )
        return OpenAIClientService()
