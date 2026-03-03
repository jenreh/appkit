"""FastMCP server for image processing.

Exposes MCP tools for image-related operations.
"""

import logging

from fastmcp import FastMCP

logger = logging.getLogger(__name__)


def create_image_mcp_server(
    *,
    name: str = "appkit-image",
) -> FastMCP:
    """Create and configure the FastMCP server for image processing.

    Args:
        name: Server name for MCP registration.

    Returns:
        Configured FastMCP server instance.
    """
    mcp = FastMCP(name)

    return mcp  # noqa: RET504
