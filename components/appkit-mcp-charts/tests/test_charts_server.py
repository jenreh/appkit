"""Tests for MCP Charts server tools."""

import json

import pytest
from fastmcp.client import Client
from fastmcp.exceptions import ToolError


async def test_generate_barchart_tool(charts_client: Client) -> None:
    """Test generating a bar chart via MCP tool call."""
    data = [
        {"category": "A", "value": 10},
        {"category": "B", "value": 20},
    ]
    result = await charts_client.call_tool(
        "generate_barchart",
        arguments={
            "x_axis": "category",
            "y_axes": ["value"],
            "data": data,
            "chart_title": "Test Chart",
        },
    )
    # The tool returns a JSON string with {success, html, error}
    response = json.loads(result.content[0].text)
    assert response["success"] is True
    assert "plotly-graph-div" in response["html"]


async def test_generate_pie_chart_tool(charts_client: Client) -> None:
    """Test generating a pie chart via MCP tool call."""
    data = [
        {"product": "A", "sales": 100},
        {"product": "B", "sales": 50},
    ]
    result = await charts_client.call_tool(
        "generate_pie_chart",
        arguments={
            "labels_column": "product",
            "values_column": "sales",
            "data": data,
            "chart_title": "Sales Distribution",
        },
    )
    response = json.loads(result.content[0].text)
    assert response["success"] is True
    assert "plotly-graph-div" in response["html"]


async def test_generate_barchart_validation_error(charts_client: Client) -> None:
    """Test validation error when data is missing columns sets isError=True."""
    data = [{"category": "A"}]  # Missing "value"
    with pytest.raises(ToolError, match="not found"):
        await charts_client.call_tool(
            "generate_barchart",
            arguments={"x_axis": "category", "y_axes": ["value"], "data": data},
        )
