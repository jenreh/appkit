"""Shared test fixtures for appkit-mcpapp tests."""

import pytest

from appkit_mcpapp.models.schemas import UserContext


@pytest.fixture
def admin_user() -> UserContext:
    """Admin user context fixture."""
    return UserContext(user_id=1, is_admin=True, roles=["admin"])


@pytest.fixture
def regular_user() -> UserContext:
    """Regular (non-admin) user context fixture."""
    return UserContext(user_id=2, is_admin=False, roles=["user"])


@pytest.fixture
def sample_data() -> list[dict[str, object]]:
    """Sample tabular data for chart tests."""
    return [
        {"role": "admin", "count": 5},
        {"role": "user", "count": 15},
        {"role": "editor", "count": 8},
    ]
