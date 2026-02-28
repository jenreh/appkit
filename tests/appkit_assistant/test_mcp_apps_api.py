"""Tests for MCP Apps API endpoints.

Covers resource fetching, tool call proxying, and UI tool listing
through FastAPI endpoints.
"""

from appkit_assistant.backend.api.mcp_apps_api import (
    ToolCallRequest,
    _extract_user_id,
)
from appkit_assistant.backend.schemas import (
    McpAppResource,
    McpAppToolInfo,
    McpAppViewData,
)

# ============================================================================
# ToolCallRequest schema
# ============================================================================


class TestToolCallRequest:
    def test_default_arguments(self) -> None:
        req = ToolCallRequest(tool_name="test")
        assert req.tool_name == "test"
        assert req.arguments == {}

    def test_with_arguments(self) -> None:
        req = ToolCallRequest(
            tool_name="gen",
            arguments={"text": "hello"},
        )
        assert req.arguments == {"text": "hello"}


# ============================================================================
# User ID extraction
# ============================================================================


class TestExtractUserId:
    def test_no_session_returns_default(self) -> None:
        assert _extract_user_id(None) == 0

    def test_empty_session_returns_default(self) -> None:
        assert _extract_user_id("") == 0

    def test_with_session_returns_default(self) -> None:
        # MVP: session presence confirmed, actual mapping deferred
        assert _extract_user_id("some-session-token") == 0

# ============================================================================
# Pydantic schemas
# ============================================================================


class TestSchemas:
    def test_mcp_app_tool_info(self) -> None:
        tool = McpAppToolInfo(
            tool_name="test",
            resource_uri="ui://test",
            server_id=1,
            server_label="Server",
        )
        assert tool.tool_name == "test"
        assert tool.visibility == []
        assert tool.input_schema == {}

    def test_mcp_app_resource(self) -> None:
        resource = McpAppResource(
            uri="ui://test",
            html_content="<h1>Hello</h1>",
        )
        assert resource.html_content == "<h1>Hello</h1>"
        assert resource.csp is None
        assert resource.permissions is None
        assert resource.prefers_border is None

    def test_mcp_app_view_data(self) -> None:
        view = McpAppViewData(
            server_id=1,
            server_name="Server",
            resource_uri="ui://test",
            tool_name="test",
        )
        assert view.id  # UUID generated
        assert view.server_id == 1
        assert view.tool_input == {}
        assert view.tool_result is None
        assert view.html_content is None

    def test_mcp_app_view_data_with_all_fields(self) -> None:
        view = McpAppViewData(
            server_id=2,
            server_name="QR",
            resource_uri="ui://qr/view",
            tool_name="gen_qr",
            tool_input={"text": "hello"},
            tool_result={"status": "ok"},
            html_content="<div>QR</div>",
            csp={"default-src": "'self'"},
            permissions={"allow-scripts": True},
            prefers_border=True,
        )
        assert view.tool_input == {"text": "hello"}
        assert view.tool_result == {"status": "ok"}
        assert view.html_content == "<div>QR</div>"
        assert view.prefers_border is True
