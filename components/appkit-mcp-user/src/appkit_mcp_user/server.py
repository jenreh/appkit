"""FastMCP server for user analytics.

Exposes MCP tools:
- query_users: Dynamic SQL generation and execution
"""

import json
import logging
from typing import Any

from fastmcp import FastMCP
from fastmcp.dependencies import CurrentRequest
from starlette.requests import Request

from appkit_commons.ai.openai_client_service import (
    get_openai_client_service,
)
from appkit_commons.registry import service_registry
from appkit_mcp_commons.context import (
    UserContext,
    extract_session_id,
    get_user_context_default,
)
from appkit_mcp_commons.exceptions import AuthenticationError
from appkit_mcp_user.authentication.service import authenticate_user
from appkit_mcp_user.configuration import McpUserConfig
from appkit_mcp_user.tools.query_users import query_users_table

logger = logging.getLogger(__name__)


def create_user_mcp_server(
    *,
    name: str = "appkit-user-analytics",
) -> FastMCP:
    """Create and configure the FastMCP server for user analytics.

    Args:
        name: Server name for MCP registration.

    Returns:
        Configured FastMCP server instance.
    """
    mcp = FastMCP(name)

    @mcp.tool()
    async def query_users(
        question: str,
        request: Request = CurrentRequest(),  # noqa: B008
    ) -> str:
        """Query the Appkit users table with a natural language question.

        Dynamically generates a SQL query from the question,
        validates it for safety, and executes it against the
        auth_users table. Returns structured results.

        Args:
            question: Natural language question about users,
                e.g. "How many active users are there?" or
                "Show me users grouped by role".

        Returns:
            JSON string with query results.
        """
        user_ctx = _get_user_context(request)
        openai_client = _get_openai_client()
        # Ensure config is loaded
        try:
            config = service_registry().get(McpUserConfig)
        except LookupError:
            # Fallback if config not loaded yet, or ensure it is loaded in lifespan
            logger.warning("McpUserConfig not found in registry, using default")
            config = McpUserConfig()

        logger.info(
            "Tool query_users called by user %d: %.200s",
            user_ctx.user_id,
            question,
        )

        result = await query_users_table(
            question,
            user_ctx,
            openai_client=openai_client,
            model=config.openai_model,
        )

        if not result.success:
            raise ValueError(result.error or "Query failed")

        return json.dumps(
            {
                "success": result.success,
                "data": result.data,
                "columns": result.columns,
                "row_count": result.row_count,
                "error": result.error,
            },
            default=str,
        )

    return mcp


def _get_user_context(request: Request) -> UserContext:
    """Extract user context from MCP request context.

    Attempts to authenticate via reflex_session cookie.
    Falls back to a default unauthenticated context if no
    session is available.

    Args:
        request: Starlette request injected via ``CurrentRequest()``.

    Returns:
        UserContext for the authenticated user or default.
    """
    session_id = extract_session_id(request)

    if not session_id:
        logger.debug("No session cookie, using default user context")
        return get_user_context_default()

    try:
        return authenticate_user(session_id)
    except AuthenticationError as e:
        logger.warning("Authentication failed: %s", e)
        return get_user_context_default()


def _get_openai_client() -> Any:
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
