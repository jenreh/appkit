"""Auth Error Detector for detecting authentication failures.

Provides unified error detection utilities shared across all AI processors.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class AuthErrorDetector:
    """Utility class for detecting authentication errors."""

    # Common authentication error indicators
    AUTH_INDICATORS: tuple[str, ...] = (
        "401",
        "403",
        "unauthorized",
        "forbidden",
        "authentication required",
        "access denied",
        "invalid token",
        "token expired",
        "not authenticated",
        "auth_required",
    )

    def is_auth_error(self, error: Any) -> bool:
        """Check if an error indicates authentication failure (401/403).

        Args:
            error: The error object or message

        Returns:
            True if the error appears to be authentication-related
        """
        error_str = str(error).lower()
        return any(indicator in error_str for indicator in self.AUTH_INDICATORS)

    def extract_error_text(self, error: Any) -> str:
        """Extract readable error text from an error object.

        Handles various error formats:
        - dict with 'message' key
        - objects with 'message' attribute
        - plain strings or other objects

        Args:
            error: The error object

        Returns:
            Human-readable error string
        """
        if error is None:
            return ""

        if isinstance(error, dict):
            return error.get("message", str(error))

        if hasattr(error, "message"):
            return getattr(error, "message", str(error))

        return str(error)

    def find_matching_server_in_error(
        self,
        error_str: str,
        servers: list[Any],
    ) -> Any | None:
        """Find a server whose name appears in the error message.

        Args:
            error_str: The error message string (should be lowercase)
            servers: List of server objects with 'name' attribute

        Returns:
            The matching server or None
        """
        for server in servers:
            if hasattr(server, "name") and server.name.lower() in error_str.lower():
                return server
        return None


# Singleton instance for convenience
_auth_error_detector: AuthErrorDetector | None = None


def get_auth_error_detector() -> AuthErrorDetector:
    """Get or create the auth error detector singleton.

    Returns:
        The AuthErrorDetector instance
    """
    global _auth_error_detector  # noqa: PLW0603
    if _auth_error_detector is None:
        _auth_error_detector = AuthErrorDetector()
    return _auth_error_detector
