from pydantic import BaseModel


class Role(BaseModel):
    id: int | None = None
    name: str
    label: str
    description: str | None = ""
    group: str = "default"


class User(BaseModel):
    """User model for managing user data and relationships."""

    user_id: int = 0
    name: str = ""
    email: str = ""
    avatar_url: str = ""

    is_verified: bool = False
    is_admin: bool = False
    is_active: bool = True
    needs_password_reset: bool = False
    roles: list[str] = []


class UserCreate(User):
    """Model for creating a new user."""

    password: str = ""
