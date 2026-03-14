"""FastMCP server for user analytics.

Exposes MCP tools:
- query_users: Dynamic SQL generation and execution
"""

import json
import logging

from fastmcp import FastMCP
from fastmcp.dependencies import CurrentRequest
from starlette.requests import Request

from appkit_commons.registry import service_registry
from appkit_mcp_commons.context import extract_user_id
from appkit_mcp_commons.utils import get_openai_client
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
        user_id = extract_user_id(request)
        openai_client = get_openai_client()
        # Ensure config is loaded
        try:
            config = service_registry().get(McpUserConfig)
        except LookupError:
            # Fallback if config not loaded yet, or ensure it is loaded in lifespan
            logger.warning("McpUserConfig not found in registry, using default")
            config = McpUserConfig()

        logger.info(
            "Tool query_users called by user %d: %.200s",
            user_id,
            question,
        )

        result = await query_users_table(
            question,
            user_id,
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
