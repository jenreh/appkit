"""Authentication backend types and enums."""

from enum import StrEnum


class PasswordResetType(StrEnum):
    """Type of password reset process."""

    USER_INITIATED = "user_initiated"
    ADMIN_FORCED = "admin_forced"
