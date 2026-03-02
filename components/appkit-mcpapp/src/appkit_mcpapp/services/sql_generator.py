"""SQL generator service using LLM for dynamic query generation.

Uses OpenAI/Azure OpenAI to generate SQL queries from natural language
questions about the auth_users table.
"""

import logging

from openai import AsyncOpenAI

from appkit_mcpapp.services.sql_validator import (
    ADMIN_ONLY_COLUMNS,
    ALLOWED_COLUMNS,
    SQLValidationError,
    validate_sql,
)

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are a SQL query generator for a PostgreSQL database.
You MUST generate ONLY SELECT queries against the 'auth_users' table.

Available columns in auth_users:
- id (integer, primary key)
- email (varchar, unique)
- name (varchar, nullable)
- is_active (boolean)
- is_admin (boolean)
- is_verified (boolean)
- roles (text[], PostgreSQL array of strings)
- last_login (timestamp with timezone)
- created_at (timestamp with timezone)
- updated_at (timestamp with timezone)

Rules:
1. ONLY generate SELECT statements.
   Never use DROP, DELETE, INSERT, UPDATE, CREATE, ALTER, TRUNCATE.
2. Always query from auth_users table only.
3. Support aggregations (COUNT, SUM, AVG), GROUP BY, ORDER BY, WHERE clauses.
4. For role-based queries, use unnest(roles) to expand the array.
5. Return ONLY the raw SQL query, no explanations or markdown.
6. Use proper PostgreSQL syntax.
7. Limit results to 1000 rows maximum.

{column_restriction}
"""

_ADMIN_COLUMN_NOTE = "The user has admin access. All columns are available."
_USER_COLUMN_NOTE = (
    "The user does NOT have admin access. "
    "Do NOT include 'email' or 'name' columns in the query. "
    "Only return aggregated/statistical data."
)


class SQLGenerationError(Exception):
    """Raised when SQL generation fails."""


async def generate_sql(
    question: str,
    *,
    is_admin: bool = False,
    client: AsyncOpenAI | None = None,
    model: str = "gpt-5-mini",
) -> str:
    """Generate a SQL query from a natural language question.

    Args:
        question: Natural language question about users.
        is_admin: Whether the requesting user has admin privileges.
        client: AsyncOpenAI client instance.
        model: The model to use for generation.

    Returns:
        Generated and validated SQL query string.

    Raises:
        SQLGenerationError: If SQL generation or validation fails.
    """
    if not client:
        raise SQLGenerationError("OpenAI client not available")

    if not question or not question.strip():
        raise SQLGenerationError("Question cannot be empty")

    column_restriction = _ADMIN_COLUMN_NOTE if is_admin else _USER_COLUMN_NOTE
    system_prompt = _SYSTEM_PROMPT.format(column_restriction=column_restriction)

    logger.info(
        "Generating SQL for question: %.200s (admin=%s)",
        question,
        is_admin,
    )

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question},
            ],
        )

        sql = response.choices[0].message.content
        if not sql:
            raise SQLGenerationError("LLM returned empty response")

        # Clean up markdown code blocks if present
        sql = _clean_sql_response(sql)

        logger.debug("Generated SQL: %s", sql)

        # Validate the generated SQL
        return validate_sql(sql, is_admin=is_admin)

    except SQLValidationError as e:
        logger.warning("Generated SQL failed validation: %s", e)
        raise SQLGenerationError(f"Generated query is not safe: {e}") from e
    except SQLGenerationError:
        raise
    except Exception as e:
        logger.error("SQL generation failed: %s", e)
        raise SQLGenerationError(f"Failed to generate SQL: {e}") from e


def _clean_sql_response(sql: str) -> str:
    """Remove markdown code blocks from LLM response.

    Args:
        sql: Raw SQL response from LLM.

    Returns:
        Cleaned SQL string.
    """
    sql = sql.strip()
    if sql.startswith("```sql"):
        sql = sql[6:]
    elif sql.startswith("```"):
        sql = sql[3:]
    if sql.endswith("```"):
        sql = sql[:-3]
    return sql.strip()


def get_safe_columns(is_admin: bool = False) -> list[str]:
    """Get list of columns visible to the role.

    Args:
        is_admin: Whether the user has admin privileges.

    Returns:
        List of column names that can be queried.
    """
    if is_admin:
        return sorted(list(ALLOWED_COLUMNS))

    # Regular users cannot access PII columns
    return sorted(list(ALLOWED_COLUMNS - ADMIN_ONLY_COLUMNS))
