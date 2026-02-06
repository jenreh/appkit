"""Service for user prompt validation and business logic."""

import re

HANDLE_REGEX = re.compile(r"^[A-Za-z0-9-]+$")


def validate_handle(handle: str) -> tuple[bool, str]:
    """Validate user prompt handle format.

    Args:
        handle: The handle string to validate.

    Returns:
        (is_valid, error_message) tuple
    """
    handle = handle.lower().strip()
    if not handle:
        return False, "Handle darf nicht leer sein."

    if len(handle) < 3:  # noqa: PLR2004
        return False, "Handle muss mindestens 3 Zeichen lang sein."

    if len(handle) > 50:  # noqa: PLR2004
        return False, "Handle darf maximal 50 Zeichen lang sein."

    if not HANDLE_REGEX.match(handle):
        return (
            False,
            "Handle darf nur Buchstaben (A-Za-z), Zahlen (0-9) und Bindestriche (-) enthalten.",  # noqa: E501
        )

    return True, ""


def is_owner(prompt_user_id: int, current_user_id: int) -> bool:
    """Check if the current user is the owner of the prompt."""
    return prompt_user_id == current_user_id
