"""Tests for roles module."""

from appkit_commons.roles import NO_ROLE, Role


class TestRole:
    """Test suite for Role model."""

    def test_role_creation_with_all_fields(self) -> None:
        """Role can be created with all fields."""
        # Arrange & Act
        role = Role(
            id=1,
            name="admin",
            label="Administrator",
            description="Full system access",
            group="system",
        )

        # Assert
        assert role.id == 1
        assert role.name == "admin"
        assert role.label == "Administrator"
        assert role.description == "Full system access"
        assert role.group == "system"

    def test_role_creation_with_minimal_fields(self) -> None:
        """Role can be created with only required fields."""
        # Arrange & Act
        role = Role(name="user", label="User")

        # Assert
        assert role.id is None
        assert role.name == "user"
        assert role.label == "User"
        assert role.description == ""
        assert role.group == "default"

    def test_role_with_no_id(self) -> None:
        """Role id field can be None."""
        # Arrange & Act
        role = Role(name="guest", label="Guest User", id=None)

        # Assert
        assert role.id is None
        assert role.name == "guest"

    def test_role_with_custom_description(self) -> None:
        """Role with custom description."""
        # Arrange & Act
        role = Role(
            name="editor",
            label="Editor",
            description="Can edit content but not publish",
        )

        # Assert
        assert role.description == "Can edit content but not publish"

    def test_role_with_custom_group(self) -> None:
        """Role with custom group."""
        # Arrange & Act
        role = Role(
            name="viewer",
            label="Viewer",
            group="content",
        )

        # Assert
        assert role.group == "content"

    def test_no_role_constant(self) -> None:
        """NO_ROLE constant is properly configured."""
        # Assert
        assert NO_ROLE.id is None
        assert NO_ROLE.name == "__none__"
        assert NO_ROLE.label == "Keine Einschränkung"
        assert NO_ROLE.description == "Kein Rollenzwang"
        assert NO_ROLE.group == "default"

    def test_no_role_is_role_instance(self) -> None:
        """NO_ROLE is an instance of Role."""
        # Assert
        assert isinstance(NO_ROLE, Role)

    def test_role_field_types(self) -> None:
        """Role fields have correct types."""
        # Arrange
        role = Role(id=5, name="moderator", label="Moderator")

        # Assert
        assert isinstance(role.id, int)
        assert isinstance(role.name, str)
        assert isinstance(role.label, str)
        assert isinstance(role.description, str)
        assert isinstance(role.group, str)

    def test_role_with_special_characters_in_name(self) -> None:
        """Role can have special characters in name."""
        # Arrange & Act
        role = Role(
            name="role_with_underscore",
            label="Role With Underscore",
        )

        # Assert
        assert role.name == "role_with_underscore"

    def test_role_with_unicode_in_label(self) -> None:
        """Role can have unicode characters in label."""
        # Arrange & Act
        role = Role(
            name="admin_de",
            label="Администратор",
        )

        # Assert
        assert role.label == "Администратор"

    def test_role_model_serialization(self) -> None:
        """Role model can be serialized."""
        # Arrange
        role = Role(id=1, name="test", label="Test Role")

        # Act
        data = role.model_dump()

        # Assert
        assert data["id"] == 1
        assert data["name"] == "test"
        assert data["label"] == "Test Role"
        assert "description" in data
        assert "group" in data
