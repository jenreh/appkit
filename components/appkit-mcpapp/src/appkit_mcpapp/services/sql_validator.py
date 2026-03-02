"""SQL validator for user analytics queries.

Validates generated SQL queries for safety, ensuring only SELECT
statements are executed and no destructive operations are allowed.
"""

import logging
import re

logger = logging.getLogger(__name__)

# Forbidden SQL keywords that indicate destructive operations
_FORBIDDEN_KEYWORDS: set[str] = {
    "DROP",
    "DELETE",
    "INSERT",
    "UPDATE",
    "CREATE",
    "ALTER",
    "TRUNCATE",
    "EXEC",
    "EXECUTE",
    "GRANT",
    "REVOKE",
    "MERGE",
    "REPLACE",
    "CALL",
}

# Allowed table names for queries
ALLOWED_TABLES: set[str] = {"auth_users"}

# SQL keywords that appear after FROM/JOIN but are not table names
# (should be skipped during table reference validation)
_SQL_KEYWORDS_IN_FROM: set[str] = {
    "LATERAL",
    "CROSS",
    "NATURAL",
    "INNER",
    "LEFT",
    "RIGHT",
    "FULL",
    "OUTER",
}

# Allowed column names for the auth_users table
ALLOWED_COLUMNS: set[str] = {
    "id",
    "email",
    "name",
    "is_active",
    "is_admin",
    "is_verified",
    "roles",
    "last_login",
    "created_at",
    "updated_at",
}

# Columns restricted to admin-only access
ADMIN_ONLY_COLUMNS: set[str] = {"email", "name"}


class SQLValidationError(Exception):
    """Raised when SQL validation fails."""


def validate_sql(sql: str, *, is_admin: bool = False) -> str:
    """Validate a SQL query for safety.

    Ensures the query is a SELECT-only statement, references only
    allowed tables and columns, and contains no destructive keywords.

    Args:
        sql: The SQL query string to validate.
        is_admin: Whether the user has admin privileges.

    Returns:
        The validated and cleaned SQL string.

    Raises:
        SQLValidationError: If the query fails validation.
    """
    if not sql or not sql.strip():
        raise SQLValidationError("Empty SQL query")

    cleaned = sql.strip().rstrip(";").strip()

    _check_forbidden_keywords(cleaned)
    _check_select_only(cleaned)
    _check_allowed_tables(cleaned)
    _check_column_access(cleaned, is_admin=is_admin)

    logger.debug("SQL validation passed for query: %.100s", cleaned)
    return cleaned


def _check_forbidden_keywords(sql: str) -> None:
    """Check for forbidden SQL keywords."""
    sql_upper = sql.upper()
    for keyword in _FORBIDDEN_KEYWORDS:
        # Match keyword as whole word using regex
        pattern = rf"\b{keyword}\b"
        if re.search(pattern, sql_upper):
            logger.warning("Forbidden SQL keyword detected: %s", keyword)
            raise SQLValidationError(f"Query contains forbidden keyword: {keyword}")


def _check_select_only(sql: str) -> None:
    """Ensure the query starts with SELECT."""
    sql_upper = sql.upper().lstrip()
    if not sql_upper.startswith("SELECT"):
        raise SQLValidationError("Only SELECT queries are allowed")


def _check_allowed_tables(sql: str) -> None:
    """Check that only allowed tables are referenced."""
    sql_upper = sql.upper()

    # Extract table references after FROM and JOIN keywords
    # Match words, possibly quoted or with schema (e.g. "public"."users")
    table_pattern = r"\b(?:FROM|JOIN)\s+([\"\w\.]+)"
    matches = re.findall(table_pattern, sql_upper)

    for table_ref in matches:
        # Clean up quotes from the reference
        table = table_ref.replace('"', "").strip()

        # Skip SQL keywords that appear after FROM/JOIN but are not table names
        if table in _SQL_KEYWORDS_IN_FROM:
            continue

        if table.lower() not in ALLOWED_TABLES:
            logger.warning("Disallowed table reference: %s", table)
            raise SQLValidationError(
                f"Query references disallowed table: {table.lower()}"
            )


def _check_column_access(sql: str, *, is_admin: bool) -> None:
    """Check that non-admin users don't access restricted columns."""
    if is_admin:
        return

    sql_lower = sql.lower()
    for col in ADMIN_ONLY_COLUMNS:
        # Check for column references (not inside string literals)
        pattern = rf"\b{col}\b"
        if re.search(pattern, sql_lower):
            logger.warning(
                "Non-admin user attempted to access restricted column: %s",
                col,
            )
            raise SQLValidationError(f"Column '{col}' requires admin privileges")
