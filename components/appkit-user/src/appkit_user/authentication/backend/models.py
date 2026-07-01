from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class User(BaseModel):
    """User model for managing user data and relationships."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    user_id: int = Field(default=0, validation_alias="id")
    name: str = ""
    email: str = ""
    avatar_url: str = ""

    is_verified: bool = False
    is_admin: bool = False
    is_active: bool = True
    needs_password_reset: bool = False
    roles: list[str] = []

    @field_validator("name", "avatar_url", mode="before")
    @classmethod
    def coerce_none_to_empty(cls, v: Any) -> Any:
        """Tolerate NULL DB columns: nullable ``name``/``avatar_url`` -> ""."""
        return "" if v is None else v

    @field_validator("roles", mode="before")
    @classmethod
    def extract_roles(cls, v: Any) -> list[str]:
        if not v:
            return []
        return [str(r.name) if hasattr(r, "name") else str(r) for r in v]


class UserCreate(User):
    """Model for creating a new user."""

    password: str = ""
