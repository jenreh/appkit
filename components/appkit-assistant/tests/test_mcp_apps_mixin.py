"""Tests for McpAppsMixin state mixin.

Covers MCP App view management, UI tool registry, and state clearing.
"""

from appkit_assistant.backend.schemas import McpAppToolInfo, McpAppViewData
from appkit_assistant.state.thread.mcp_apps import McpAppsMixin

# ============================================================================
# Helpers
# ============================================================================


def _make_mixin() -> McpAppsMixin:
    """Create a McpAppsMixin with required state vars."""
    mixin = McpAppsMixin()
    mixin.mcp_app_views = []
    mixin._ui_tool_registry = {}
    return mixin


def _make_view_data(
    tool_name: str = "test_tool",
    server_name: str = "TestServer",
    server_id: int = 1,
    resource_uri: str = "ui://test/view",
) -> McpAppViewData:
    return McpAppViewData(
        server_id=server_id,
        server_name=server_name,
        resource_uri=resource_uri,
        tool_name=tool_name,
    )


def _make_tool_info(
    tool_name: str = "test_tool",
    server_id: int = 1,
    server_label: str = "TestServer",
    resource_uri: str = "ui://test/view",
) -> McpAppToolInfo:
    return McpAppToolInfo(
        tool_name=tool_name,
        resource_uri=resource_uri,
        server_id=server_id,
        server_label=server_label,
    )


# ============================================================================
# _handle_mcp_app_view
# ============================================================================


class TestHandleMcpAppView:
    def test_adds_view(self) -> None:
        mixin = _make_mixin()
        view = _make_view_data()
        mixin._handle_mcp_app_view(view)
        assert len(mixin.mcp_app_views) == 1
        assert mixin.mcp_app_views[0].tool_name == "test_tool"

    def test_multiple_views(self) -> None:
        mixin = _make_mixin()
        mixin._handle_mcp_app_view(_make_view_data(tool_name="tool_a"))
        mixin._handle_mcp_app_view(_make_view_data(tool_name="tool_b"))
        assert len(mixin.mcp_app_views) == 2


# ============================================================================
# _update_ui_tool_registry
# ============================================================================


class TestUpdateUiToolRegistry:
    def test_adds_tools(self) -> None:
        mixin = _make_mixin()
        tools = [
            _make_tool_info(tool_name="tool_a"),
            _make_tool_info(tool_name="tool_b"),
        ]
        mixin._update_ui_tool_registry(tools)
        assert "tool_a" in mixin._ui_tool_registry
        assert "tool_b" in mixin._ui_tool_registry

    def test_empty_tools(self) -> None:
        mixin = _make_mixin()
        mixin._update_ui_tool_registry([])
        assert mixin._ui_tool_registry == {}


# ============================================================================
# _get_ui_tool_info
# ============================================================================


class TestGetUiToolInfo:
    def test_found(self) -> None:
        mixin = _make_mixin()
        tool = _make_tool_info(tool_name="my_tool")
        mixin._update_ui_tool_registry([tool])
        result = mixin._get_ui_tool_info("my_tool")
        assert result is not None
        assert result["tool_name"] == "my_tool"

    def test_not_found(self) -> None:
        mixin = _make_mixin()
        result = mixin._get_ui_tool_info("nonexistent")
        assert result is None


# ============================================================================
# _clear_mcp_app_state
# ============================================================================


class TestClearMcpAppState:
    def test_clears_views_and_registry(self) -> None:
        mixin = _make_mixin()
        mixin._handle_mcp_app_view(_make_view_data())
        mixin._update_ui_tool_registry([_make_tool_info()])

        assert len(mixin.mcp_app_views) == 1
        assert len(mixin._ui_tool_registry) == 1

        mixin._clear_mcp_app_state()

        assert mixin.mcp_app_views == []
        assert mixin._ui_tool_registry == {}
