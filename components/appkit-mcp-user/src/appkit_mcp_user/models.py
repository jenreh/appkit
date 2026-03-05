from pydantic import Field

from appkit_mcp_commons.models import BaseResult


class QueryResult(BaseResult):
    """Result of a user query execution."""

    data: list[dict[str, object]] = Field(default_factory=list)
    columns: list[str] = Field(default_factory=list)
    row_count: int = 0
