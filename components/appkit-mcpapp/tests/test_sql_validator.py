"""Tests for SQL validator."""

import pytest

from appkit_mcpapp.services.sql_validator import (
    ADMIN_ONLY_COLUMNS,
    ALLOWED_COLUMNS,
    ALLOWED_TABLES,
    SQLValidationError,
    validate_sql,
)


class TestValidateSql:
    """Tests for validate_sql function."""

    def test_valid_select_query(self) -> None:
        result = validate_sql("SELECT COUNT(*) FROM auth_users", is_admin=True)
        assert result == "SELECT COUNT(*) FROM auth_users"

    def test_valid_select_with_where(self) -> None:
        result = validate_sql(
            "SELECT id, is_active FROM auth_users WHERE is_active = true",
            is_admin=False,
        )
        assert "SELECT" in result
        assert "auth_users" in result

    def test_trailing_semicolon_stripped(self) -> None:
        result = validate_sql(
            "SELECT COUNT(*) FROM auth_users;",
            is_admin=True,
        )
        assert not result.endswith(";")

    def test_empty_query_raises(self) -> None:
        with pytest.raises(SQLValidationError, match="Empty SQL"):
            validate_sql("")

    def test_whitespace_only_raises(self) -> None:
        with pytest.raises(SQLValidationError, match="Empty SQL"):
            validate_sql("   ")

    def test_drop_keyword_raises(self) -> None:
        with pytest.raises(SQLValidationError, match="DROP"):
            validate_sql("DROP TABLE auth_users", is_admin=True)

    def test_delete_keyword_raises(self) -> None:
        with pytest.raises(SQLValidationError, match="DELETE"):
            validate_sql(
                "DELETE FROM auth_users WHERE id = 1",
                is_admin=True,
            )

    def test_insert_keyword_raises(self) -> None:
        with pytest.raises(SQLValidationError, match="INSERT"):
            validate_sql(
                "INSERT INTO auth_users (name) VALUES ('test')",
                is_admin=True,
            )

    def test_update_keyword_raises(self) -> None:
        with pytest.raises(SQLValidationError, match="UPDATE"):
            validate_sql(
                "UPDATE auth_users SET name = 'x' WHERE id = 1",
                is_admin=True,
            )

    def test_create_keyword_raises(self) -> None:
        with pytest.raises(SQLValidationError, match="CREATE"):
            validate_sql("CREATE TABLE test (id INT)", is_admin=True)

    def test_alter_keyword_raises(self) -> None:
        with pytest.raises(SQLValidationError, match="ALTER"):
            validate_sql(
                "ALTER TABLE auth_users ADD col TEXT",
                is_admin=True,
            )

    def test_truncate_keyword_raises(self) -> None:
        with pytest.raises(SQLValidationError, match="TRUNCATE"):
            validate_sql("TRUNCATE auth_users", is_admin=True)

    def test_non_select_query_raises(self) -> None:
        with pytest.raises(SQLValidationError, match="SELECT queries"):
            validate_sql("SHOW TABLES", is_admin=True)

    def test_disallowed_table_raises(self) -> None:
        with pytest.raises(SQLValidationError, match="disallowed table"):
            validate_sql(
                "SELECT * FROM secret_table",
                is_admin=True,
            )

    def test_join_disallowed_table_raises(self) -> None:
        with pytest.raises(SQLValidationError, match="disallowed table"):
            validate_sql(
                "SELECT * FROM auth_users JOIN other_table ON 1=1",
                is_admin=True,
            )

    def test_non_admin_email_column_raises(self) -> None:
        with pytest.raises(SQLValidationError, match="requires admin"):
            validate_sql(
                "SELECT email FROM auth_users",
                is_admin=False,
            )

    def test_non_admin_name_column_raises(self) -> None:
        with pytest.raises(SQLValidationError, match="requires admin"):
            validate_sql(
                "SELECT name FROM auth_users",
                is_admin=False,
            )

    def test_admin_can_access_email(self) -> None:
        result = validate_sql(
            "SELECT email FROM auth_users",
            is_admin=True,
        )
        assert "email" in result

    def test_admin_can_access_name(self) -> None:
        result = validate_sql(
            "SELECT name FROM auth_users",
            is_admin=True,
        )
        assert "name" in result

    def test_aggregation_query_allowed(self) -> None:
        sql = "SELECT is_active, COUNT(*) as cnt FROM auth_users GROUP BY is_active"
        result = validate_sql(sql, is_admin=False)
        assert "COUNT" in result

    def test_lateral_keyword_allowed(self) -> None:
        """Test that LATERAL keyword in FROM clause is allowed (PostgreSQL feature)."""
        sql = (
            "SELECT r.*, u.id FROM auth_users u "
            "JOIN LATERAL (SELECT * FROM auth_users WHERE id = u.id) r ON true"
        )
        result = validate_sql(sql, is_admin=False)
        assert "LATERAL" in result

    def test_other_sql_keywords_in_from_allowed(self) -> None:
        """Test that other SQL keywords after FROM/JOIN are allowed."""
        # Test CROSS
        sql = "SELECT * FROM auth_users CROSS JOIN LATERAL ..."
        # This would normally fail due to incomplete query, but we're testing
        # the keyword parsing logic
        try:
            validate_sql(
                "SELECT * FROM auth_users CROSS JOIN auth_users a2", is_admin=False
            )
        except SQLValidationError as e:
            # Should not complain about CROSS being disallowed
            assert "CROSS" not in str(e)


class TestConstants:
    """Tests for module-level constants."""

    def test_allowed_tables_contains_auth_users(self) -> None:
        assert "auth_users" in ALLOWED_TABLES

    def test_allowed_columns_contains_expected(self) -> None:
        expected = {"id", "is_active", "is_admin", "roles", "last_login"}
        assert expected.issubset(ALLOWED_COLUMNS)

    def test_admin_only_columns(self) -> None:
        assert "email" in ADMIN_ONLY_COLUMNS
        assert "name" in ADMIN_ONLY_COLUMNS
