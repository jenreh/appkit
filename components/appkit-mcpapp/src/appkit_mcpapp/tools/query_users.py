"""MCP tool: query_users_table.

Accepts a natural language question, generates SQL using an LLM,
executes it against the auth_users table, and returns tabular results.
"""

import logging
from typing import Any

from sqlalchemy import text

from appkit_commons.database.session import get_session_manager
from appkit_mcpapp.models.schemas import QueryResult, UserContext
from appkit_mcpapp.services.sql_generator import (
    SQLGenerationError,
    generate_sql,
)

logger = logging.getLogger(__name__)

# Query execution timeout in seconds
QUERY_TIMEOUT = 10


async def query_users_table(
    question: str,
    user_ctx: UserContext,
    *,
    openai_client: Any = None,
    model: str = "gpt-5-mini",
) -> QueryResult:
    """Query the users table based on a natural language question.

    Generates SQL dynamically using an LLM, validates it for safety,
    executes it against the database, and returns structured results.

    Args:
        question: Natural language question about users.
        user_ctx: Authenticated user context.
        openai_client: AsyncOpenAI client for SQL generation.
        model: LLM model name for SQL generation.

    Returns:
        QueryResult with data rows and metadata.
    """
    logger.info(
        "User %d querying users table: %.200s",
        user_ctx.user_id,
        question,
    )

    try:
        sql = await generate_sql(
            question,
            is_admin=user_ctx.is_admin,
            client=openai_client,
            model=model,
        )
    except SQLGenerationError as e:
        logger.warning(
            "SQL generation failed for user %d: %s",
            user_ctx.user_id,
            e,
        )
        return QueryResult(
            success=False,
            error=f"Could not generate query: {e}",
        )

    logger.info(
        "Generated SQL for user %d: %s",
        user_ctx.user_id,
        sql,
    )

    return _execute_query(sql, user_ctx)


def _execute_query(sql: str, user_ctx: UserContext) -> QueryResult:
    """Execute a validated SQL query and return results.

    Args:
        sql: Validated SQL query.
        user_ctx: Authenticated user context.

    Returns:
        QueryResult with query results or error.
    """
    try:
        with get_session_manager().session() as session:
            result = session.execute(
                text(sql).execution_options(
                    timeout=QUERY_TIMEOUT * 1000,
                )
            )
            rows = result.fetchall()

            # Get column names - try multiple approaches for compatibility
            columns = list(result.keys()) if hasattr(result, "keys") else []
            if not columns and rows and result.cursor and result.cursor.description:
                columns = [desc[0] for desc in result.cursor.description]

            logger.debug(
                "SQL execution returned %d rows, columns: %s",
                len(rows),
                columns,
            )

            data = [dict(zip(columns, row, strict=False)) for row in rows]

            # Note: No need to filter columns here. The SQL query was already
            # validated for safety during generation, so derived columns from
            # aggregations (COUNT, SUM, etc.) are safe to return.

            logger.info(
                "Query returned %d rows with %d columns for user %d",
                len(data),
                len(columns),
                user_ctx.user_id,
            )

            return QueryResult(
                success=True,
                data=data,
                columns=columns,
                row_count=len(data),
            )

    except Exception as e:
        logger.error(
            "Query execution failed for user %d: %s",
            user_ctx.user_id,
            e,
        )
        return QueryResult(
            success=False,
            error="Query execution failed. Please try a different question.",
        )
