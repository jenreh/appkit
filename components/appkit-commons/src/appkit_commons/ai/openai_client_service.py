"""OpenAI client service for creating and managing AsyncOpenAI clients."""

import logging
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import httpx
from openai import AsyncOpenAI

from appkit_commons.registry import service_registry

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AiModelCredentials:
    """Credentials needed to build an OpenAI client for a specific model."""

    api_key: str | None
    base_url: str | None = None
    on_azure: bool = False


@runtime_checkable
class AiModelResolver(Protocol):
    """Resolves a model id to its client credentials.

    Implemented by the owning higher-level package (e.g. appkit-assistant) and
    registered in the service registry, so appkit-commons does not import it.
    This inverts the previous appkit-commons -> appkit-assistant dependency.
    """

    async def resolve_model_credentials(
        self, model_id: str
    ) -> "AiModelCredentials | None": ...


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

    @staticmethod
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
        # Extended timeout for long LLM operations like BPMN generation (60+ seconds).
        # OpenAI SDK accepts timeout directly via httpx.Timeout object.
        # - connect: 10s (TCP connection establishment)
        # - read: 600s (full request/response for complex LLM operations)
        # - write: 60s (request body upload)
        # - pool: 10s (connection pool timeout)
        timeout = httpx.Timeout(
            timeout=600.0,  # Overall timeout fallback
            connect=10.0,  # TCP connection
            read=600.0,  # Receiving response
            write=60.0,  # Sending request
            pool=10.0,  # Connection pool
        )

        if base_url and on_azure:
            logger.debug("Creating Azure OpenAI client with extended timeout")
            logger.debug(
                "Timeout: connect=10s, read=600s, write=60s, pool=10s, total=600s"
            )
            return AsyncOpenAI(
                api_key=api_key,
                base_url=f"{base_url}/openai/v1",
                default_query={"api-version": "preview"},
                timeout=timeout,
            )
        if base_url:
            logger.debug(
                "Creating OpenAI client with custom base URL and extended timeout"
            )
            logger.debug(
                "Timeout: connect=10s, read=600s, write=60s, pool=10s, total=600s"
            )
            return AsyncOpenAI(
                api_key=api_key,
                base_url=base_url,
                timeout=timeout,
            )
        logger.debug("Creating standard OpenAI client with extended timeout")
        logger.debug("Timeout: connect=10s, read=600s, write=60s, pool=10s, total=600s")
        return AsyncOpenAI(api_key=api_key, timeout=timeout)

    @classmethod
    def from_config(cls) -> "OpenAIClientService":
        """Deprecated: use the service registry instance set by AIModelRegistry."""
        return cls()

    @property
    def is_available(self) -> bool:
        """Check if the service is properly configured with an API key."""
        return self._api_key is not None

    @staticmethod
    async def create_client_for_model(
        ai_model: str,
    ) -> AsyncOpenAI | None:
        """Create an AsyncOpenAI client using credentials for a DB model.

        Resolves the model's credentials via the :class:`AiModelResolver`
        registered in the service registry (provided by the owning package,
        e.g. appkit-assistant) and builds a client with them.

        Args:
            ai_model: The ``model_id`` string (e.g. ``"gpt-4o"``).

        Returns:
            Configured AsyncOpenAI client, or *None* if no resolver is
            registered, the model cannot be found, or it has no API key.
        """
        try:
            # AiModelResolver is a Protocol used as a registry key (runtime-safe).
            resolver = service_registry().get(AiModelResolver)  # type: ignore[type-abstract]
        except KeyError:
            logger.warning(
                "No AiModelResolver registered; cannot create client for model %s",
                ai_model,
            )
            return None

        try:
            credentials = await resolver.resolve_model_credentials(ai_model)
            if not credentials or not credentials.api_key:
                logger.warning("No API key for model %s", ai_model)
                return None
            return OpenAIClientService._build_client(
                credentials.api_key, credentials.base_url, credentials.on_azure
            )
        except Exception as e:
            logger.error(
                "Failed to create client for model %s: %s",
                ai_model,
                e,
            )
            return None

    def create_client(self) -> AsyncOpenAI | None:
        """Create an AsyncOpenAI client with the configured settings.

        Returns:
            Configured AsyncOpenAI client, or None if API key is not available.
        """
        if not self._api_key:
            logger.warning("OpenAI API key not configured")
            return None

        return OpenAIClientService._build_client(
            self._api_key, self._base_url, self._on_azure
        )


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
