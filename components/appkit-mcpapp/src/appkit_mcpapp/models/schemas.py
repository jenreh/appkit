"""Pydantic schemas for the MCP user analytics server."""

from __future__ import annotations

from pydantic import BaseModel, Field


class UserContext(BaseModel):
    """Authenticated user context extracted from session."""

    user_id: int
    is_admin: bool = False
    roles: list[str] = Field(default_factory=list)


class QueryResult(BaseModel):
    """Result of a user query execution."""

    success: bool
    data: list[dict[str, object]] = Field(default_factory=list)
    columns: list[str] = Field(default_factory=list)
    row_count: int = 0
    error: str | None = None


class ChartConfig(BaseModel):
    """Configuration for a barchart visualization."""

    chart_id: str
    data: list[dict[str, object]] = Field(default_factory=list)
    x_axis: str
    y_axes: list[str] = Field(default_factory=list)
    bar_mode: str = "group"
    chart_title: str = "User Analytics"


class VisualizationResult(BaseModel):
    """Result of a visualization generation."""

    success: bool
    chart_id: str = ""
    html: str = ""
    preview_url: str = ""
    error: str | None = None
