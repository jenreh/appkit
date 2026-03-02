from appkit_mcp_commons.models import BaseResult, ToolResult, VisualizationResult


def test_base_result_success() -> None:
    """Test BaseResult success case."""
    res = BaseResult(success=True)
    assert res.success
    assert res.error is None


def test_base_result_error() -> None:
    """Test BaseResult error case."""
    res = BaseResult(success=False, error="Something wrong")
    assert not res.success
    assert res.error == "Something wrong"


def test_tool_result_generic() -> None:
    """Test ToolResult with generic data."""
    res = ToolResult[dict](success=True, data={"value": 1})
    assert res.data["value"] == 1


def test_tool_result_empty() -> None:
    """Test ToolResult with no data."""
    res = ToolResult[str](success=True)
    assert res.data is None


def test_visualization_result() -> None:
    """Test VisualizationResult."""
    html = "<div>Plot</div>"
    res = VisualizationResult(success=True, html=html)
    assert res.html == html
