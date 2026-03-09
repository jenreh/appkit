"""Common utility functions for MCP servers."""

import logging
from typing import Any

from appkit_commons.ai.openai_client_service import get_openai_client_service

logger = logging.getLogger(__name__)


def get_openai_client() -> Any:
    """Get the OpenAI client from the service registry.

    Returns:
        AsyncOpenAI client instance or None.
    """
    try:
        service = get_openai_client_service()
        return service.create_client()
    except Exception as e:
        logger.warning("Failed to get OpenAI client: %s", e)
        return None
