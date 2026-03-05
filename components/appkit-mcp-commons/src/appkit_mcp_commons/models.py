from pydantic import BaseModel, Field


class BaseResult(BaseModel):
    """Base result model for MCP tool responses."""

    success: bool = Field(..., description="Whether the operation was successful")
    error: str | None = Field(default=None, description="Error message if failed")


class ToolResult[T](BaseResult):
    """Generic tool execution result."""

    data: T | None = Field(default=None, description="Tool execution data payload")


class VisualizationResult(BaseResult):
    """Result from a visualization tool."""

    html: str = Field(..., description="HTML content for rendering the visualization")
