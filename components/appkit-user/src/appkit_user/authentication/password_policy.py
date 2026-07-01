"""Centralized password policy: length, complexity regex, and strength scoring.

Single source of truth shared by the password-reset and profile flows so the
rules cannot drift apart.
"""

import re
from dataclasses import dataclass
from typing import Final

MIN_PASSWORD_LENGTH: Final[int] = 12

# Enforces: at least MIN_PASSWORD_LENGTH characters and at least one uppercase
# letter, one lowercase letter, one digit, and one special character.
PASSWORD_REGEX: Final = re.compile(
    r"^(?=.{"
    + str(MIN_PASSWORD_LENGTH)
    + r",})(?=.*[A-Z])(?=.*[a-z])(?=.*[0-9])(?=.*[^A-Za-z0-9]).*$"
)

PASSWORD_MISMATCH_MESSAGE: Final = "Passwörter stimmen nicht überein."  # noqa: S105


@dataclass(frozen=True)
class PasswordStrength:
    """Per-criterion flags and a 0-100 strength score for a candidate password."""

    has_length: bool
    has_upper: bool
    has_lower: bool
    has_digit: bool
    has_special: bool
    strength: int


def calculate_password_strength(value: str) -> PasswordStrength:
    """Compute password-strength flags and a 0-100 score.

    The score is 20 points per satisfied criterion (length, upper, lower, digit,
    special), i.e. 0 for none and 100 for all five.
    """
    has_length = len(value) >= MIN_PASSWORD_LENGTH
    has_upper = any(c.isupper() for c in value)
    has_lower = any(c.islower() for c in value)
    has_digit = any(c.isdigit() for c in value)
    has_special = any(not c.isalnum() for c in value)
    criteria_met = sum([has_length, has_upper, has_lower, has_digit, has_special])
    return PasswordStrength(
        has_length=has_length,
        has_upper=has_upper,
        has_lower=has_lower,
        has_digit=has_digit,
        has_special=has_special,
        strength=criteria_met * 20,
    )
