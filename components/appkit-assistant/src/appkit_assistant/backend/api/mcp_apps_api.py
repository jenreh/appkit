"""FastAPI endpoints for MCP Apps resource proxying and tool calls.

These endpoints are called by the McpAppBridge frontend component to:
- Fetch HTML resources from MCP servers (proxied through backend)
- Forward tool calls from MCP App iframes to MCP servers
- List UI-enabled tools for a given server
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from appkit_assistant.backend.database.models import MCPServer
from appkit_assistant.backend.database.repositories import mcp_server_repo
from appkit_assistant.backend.services.mcp_apps_service import (
    McpAppsService,
)
from appkit_commons.database.session import get_asyncdb_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/mcp-apps", tags=["mcp-apps"])

# Shared service instance
_mcp_apps_service = McpAppsService()


class ToolCallRequest(BaseModel):
    """Request body for proxying a tool call."""

    tool_name: str
    arguments: dict[str, Any] = {}


async def _get_server(server_id: int) -> MCPServer:
    """Retrieve an MCP server by ID or raise 404.

    Args:
        server_id: The MCP server ID

    Returns:
        The MCPServer instance

    Raises:
        HTTPException: If server is not found
    """
    async with get_asyncdb_session() as session:
        server = await mcp_server_repo.find_by_id(session, server_id)
        if not server:
            raise HTTPException(
                status_code=404,
                detail="MCP server not found",
            )
        return MCPServer(**server.model_dump())


@router.get("/{server_id}/resource")
async def get_resource(
    server_id: int,
    uri: str = Query(..., description="The ui:// resource URI"),
    user_id: int = Query(0, description="User ID for auth"),
) -> dict[str, Any]:
    """Fetch an MCP App resource (HTML content) from a server.

    The frontend iframe src points to this endpoint to load
    the MCP App HTML content.
    """
    server = await _get_server(server_id)

    resource = await _mcp_apps_service.fetch_resource(
        server, user_id, uri
    )
    if not resource:
        raise HTTPException(
            status_code=502,
            detail="Failed to fetch resource from MCP server",
        )

    return {
        "uri": resource.uri,
        "html_content": resource.html_content,
        "csp": resource.csp,
        "permissions": resource.permissions,
        "prefers_border": resource.prefers_border,
    }


@router.post("/{server_id}/tools/call")
async def call_tool(
    server_id: int,
    request: ToolCallRequest,
    user_id: int = Query(0, description="User ID for auth"),
) -> dict[str, Any]:
    """Proxy a tool call from an MCP App iframe to the MCP server.

    This is the endpoint that McpAppBridge.jsx calls when the
    iframe requests a tool call.
    """
    server = await _get_server(server_id)

    result = await _mcp_apps_service.proxy_tool_call(
        server, user_id, request.tool_name, request.arguments
    )
    return result


@router.get("/{server_id}/tools")
async def list_ui_tools(
    server_id: int,
    user_id: int = Query(0, description="User ID for auth"),
) -> list[dict[str, Any]]:
    """List UI-enabled tools for an MCP server.

    Returns the list of tools that have MCP App views,
    used by the frontend to know which tools can render iframes.
    """
    server = await _get_server(server_id)

    tools = await _mcp_apps_service.discover_ui_tools(
        server, user_id
    )
    return [tool.model_dump() for tool in tools]
