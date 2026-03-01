"""FastAPI endpoints for MCP Apps resource proxying and tool calls.

These endpoints are called by the McpAppBridge frontend component to:
- Fetch HTML resources from MCP servers (proxied through backend)
- Forward tool calls from MCP App iframes to MCP servers
- List UI-enabled tools for a given server

Authentication: These endpoints rely on the Reflex session cookie
(automatically sent with same-origin requests from the frontend).
The user_id is extracted from the session server-side.
"""

import json as _json
import logging
from typing import Annotated, Any

from fastapi import APIRouter, Cookie, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from appkit_assistant.backend.database.models import MCPServer
from appkit_assistant.backend.database.repositories import mcp_server_repo
from appkit_assistant.backend.services.mcp_apps_service import (
    McpAppsService,
)
from appkit_assistant.backend.services.mcp_auth_service import MCPAuthService
from appkit_assistant.backend.services.mcp_token_service import (
    MCPTokenService,
)
from appkit_commons.database.session import get_asyncdb_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/mcp-apps", tags=["mcp-apps"])

# Lazily initialized service instances
_mcp_apps_service: McpAppsService | None = None

# Default user ID when session token is not available
_DEFAULT_USER_ID = 0


def _get_mcp_apps_service() -> McpAppsService:
    """Get or create the shared McpAppsService instance.

    Lazily initializes the service with its dependencies
    to avoid import-time instantiation issues.
    """
    global _mcp_apps_service  # noqa: PLW0603
    if _mcp_apps_service is None:
        auth_service = MCPAuthService(redirect_uri="")
        token_service = MCPTokenService(mcp_auth_service=auth_service)
        _mcp_apps_service = McpAppsService(token_service=token_service)
    return _mcp_apps_service


class ToolCallRequest(BaseModel):
    """Request body for proxying a tool call."""

    tool_name: str
    arguments: dict[str, Any] = {}


def _extract_user_id(reflex_session: str | None) -> int:
    """Extract user ID from the Reflex session token.

    MVP implementation: session presence is not enforced here because
    same-origin API calls from the McpAppBridge iframe sandbox may not
    always carry the session cookie (sandboxed iframes have limited
    cookie access).  Full auth integration will map the token to a
    real user ID in a future iteration.

    Args:
        reflex_session: The Reflex session cookie value (may be None)

    Returns:
        The user ID (defaults to 0 when no session is present)
    """
    if reflex_session:
        logger.debug("MCP Apps API: session cookie present")
    else:
        logger.debug("MCP Apps API: no session cookie, using default user_id=0")
    return _DEFAULT_USER_ID


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
    uri: str,
    reflex_session: Annotated[str | None, Cookie()] = None,
) -> HTMLResponse:
    """Fetch an MCP App resource (HTML content) from a server.

    Returns the HTML content with text/html content type.
    Resource metadata (CSP, prefersBorder) is forwarded as X-MCP-* headers
    so the McpAppBridge frontend can apply security policies and visual
    preferences without parsing the HTML body.
    """
    user_id = _extract_user_id(reflex_session)
    server = await _get_server(server_id)

    resource = await _get_mcp_apps_service().fetch_resource(server, user_id, uri)
    if not resource:
        raise HTTPException(
            status_code=502,
            detail="Failed to fetch resource from MCP server",
        )

    extra_headers: dict[str, str] = {
        "X-MCP-Resource-URI": resource.uri,
    }
    if resource.csp is not None:
        extra_headers["X-MCP-CSP"] = _json.dumps(resource.csp)
    if resource.permissions is not None:
        extra_headers["X-MCP-Permissions"] = _json.dumps(resource.permissions)
    if resource.prefers_border is not None:
        extra_headers["X-MCP-Prefers-Border"] = str(resource.prefers_border).lower()

    return HTMLResponse(
        content=resource.html_content,
        headers=extra_headers,
    )


@router.post("/{server_id}/tools/call")
async def call_tool(
    server_id: int,
    request: ToolCallRequest,
    reflex_session: Annotated[str | None, Cookie()] = None,
) -> dict[str, Any]:
    """Proxy a tool call from an MCP App iframe to the MCP server.

    This is the endpoint that McpAppBridge.jsx calls when the
    iframe requests a tool call.
    """
    user_id = _extract_user_id(reflex_session)
    server = await _get_server(server_id)

    return await _get_mcp_apps_service().proxy_tool_call(
        server, user_id, request.tool_name, request.arguments
    )


@router.get("/{server_id}/tools")
async def list_ui_tools(
    server_id: int,
    reflex_session: Annotated[str | None, Cookie()] = None,
) -> list[dict[str, Any]]:
    """List UI-enabled tools for an MCP server.

    Returns the list of tools that have MCP App views,
    used by the frontend to know which tools can render iframes.
    """
    user_id = _extract_user_id(reflex_session)
    server = await _get_server(server_id)

    tools = await _get_mcp_apps_service().discover_ui_tools(server, user_id)
    return [tool.model_dump() for tool in tools]
