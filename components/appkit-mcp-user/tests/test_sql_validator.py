"""Tests for SQL validator service."""

import pytest

from appkit_mcp_user.services.sql_validator import (
    ADMIN_ONLY_COLUMNS,
    ALLOWED_COLUMNS,
    ALLOWED_TABLES,
    SQLValidationError,
    _check_allowed_tables,
    _check_column_access,
    _check_forbidden_keywords,
    _check_select_only,
    validate_sql,
)


class TestValidateSql:
    """End-to-end validation tests."""

    def test_valid_select(self) -> None:
        result = validate_sql("SELECT count(*) FROM auth_users", is_admin=True)
        assert result == "SELECT count(*) FROM auth_users"

    def test_strips_trailing_semicolon(self) -> None:
        result = validate_sql("SELECT id FROM auth_users;", is_admin=True)
        assert not result.endswith(";")

    def test_strips_whitespace(self) -> None:
        result = validate_sql("  SELECT id FROM auth_users  ", is_admin=True)
        assert result == "SELECT id FROM auth_users"

    def test_empty_query_raises(self) -> None:
        with pytest.raises(SQLValidationError, match="Empty SQL query"):
            validate_sql("")

    def test_whitespace_only_raises(self) -> None:
        with pytest.raises(SQLValidationError, match="Empty SQL query"):
            validate_sql("   ")

    def test_forbidden_keyword_raises(self) -> None:
        with pytest.raises(SQLValidationError, match="forbidden keyword"):
            validate_sql("DROP TABLE auth_users")

    def test_non_select_raises(self) -> None:
        with pytest.raises(SQLValidationError, match="Only SELECT"):
            validate_sql("WITH cte AS (SELECT 1) SELECT * FROM cte")

    def test_disallowed_table_raises(self) -> None:
        with pytest.raises(SQLValidationError, match="disallowed table"):
            validate_sql("SELECT * FROM secret_table", is_admin=True)

    def test_admin_can_access_email(self) -> None:
        result = validate_sql("SELECT email FROM auth_users", is_admin=True)
        assert "email" in result

    def test_non_admin_cannot_access_email(self) -> None:
        with pytest.raises(SQLValidationError, match="requires admin"):
            validate_sql("SELECT email FROM auth_users", is_admin=False)

    def test_non_admin_cannot_access_name(self) -> None:
        with pytest.raises(SQLValidationError, match="requires admin"):
            validate_sql("SELECT name FROM auth_users", is_admin=False)

    def test_non_admin_can_access_id(self) -> None:
        result = validate_sql("SELECT id FROM auth_users", is_admin=False)
        assert "id" in result


class TestCheckForbiddenKeywords:
    """Tests for _check_forbidden_keywords."""

    @pytest.mark.parametrize(
        "keyword",
        [
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
        ],
    )
    def test_each_forbidden_keyword(self, keyword: str) -> None:
        with pytest.raises(SQLValidationError, match=keyword):
            _check_forbidden_keywords(f"{keyword} TABLE auth_users")

    def test_keyword_as_substring_allowed(self) -> None:
        # "CREATED_AT" contains CREATE but should not match whole word
        _check_forbidden_keywords("SELECT created_at FROM auth_users")

    def test_clean_query_passes(self) -> None:
        _check_forbidden_keywords(
            "SELECT count(*) FROM auth_users WHERE is_active = true"
        )


class TestCheckSelectOnly:
    """Tests for _check_select_only."""

    def test_select_passes(self) -> None:
        _check_select_only("SELECT * FROM auth_users")

    def test_select_with_leading_whitespace(self) -> None:
        _check_select_only("   SELECT * FROM auth_users")

    def test_update_fails(self) -> None:
        with pytest.raises(SQLValidationError, match="Only SELECT"):
            _check_select_only("UPDATE auth_users SET is_active = false")

    def test_insert_fails(self) -> None:
        with pytest.raises(SQLValidationError, match="Only SELECT"):
            _check_select_only("INSERT INTO auth_users VALUES (1)")


class TestCheckAllowedTables:
    """Tests for _check_allowed_tables."""

    def test_allowed_table_passes(self) -> None:
        _check_allowed_tables("SELECT * FROM auth_users")

    def test_disallowed_table_raises(self) -> None:
        with pytest.raises(SQLValidationError, match="disallowed table"):
            _check_allowed_tables("SELECT * FROM passwords")

    def test_join_with_disallowed_table_raises(self) -> None:
        with pytest.raises(SQLValidationError, match="disallowed table"):
            _check_allowed_tables(
                "SELECT * FROM auth_users JOIN sessions"
                " ON auth_users.id = sessions.user_id"
            )

    def test_sql_keywords_after_from_skipped(self) -> None:
        # LATERAL, CROSS, etc. should be skipped (not treated as table names)
        _check_allowed_tables("SELECT * FROM LATERAL (SELECT 1) AS auth_users")


class TestCheckColumnAccess:
    """Tests for _check_column_access."""

    def test_admin_can_access_any_column(self) -> None:
        _check_column_access("SELECT email, name FROM auth_users", is_admin=True)

    def test_non_admin_blocked_from_email(self) -> None:
        with pytest.raises(SQLValidationError, match="email"):
            _check_column_access("SELECT email FROM auth_users", is_admin=False)

    def test_non_admin_blocked_from_name(self) -> None:
        with pytest.raises(SQLValidationError, match="name"):
            _check_column_access("SELECT name FROM auth_users", is_admin=False)

    def test_non_admin_can_access_id(self) -> None:
        _check_column_access("SELECT id FROM auth_users", is_admin=False)


class TestConstants:
    """Test module-level constants."""

    def test_allowed_tables_contains_auth_users(self) -> None:
        assert "auth_users" in ALLOWED_TABLES

    def test_admin_only_columns_subset_of_allowed(self) -> None:
        assert ADMIN_ONLY_COLUMNS.issubset(ALLOWED_COLUMNS)

    def test_email_is_admin_only(self) -> None:
        assert "email" in ADMIN_ONLY_COLUMNS

    def test_name_is_admin_only(self) -> None:
        assert "name" in ADMIN_ONLY_COLUMNS
