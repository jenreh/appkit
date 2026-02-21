"""Tests for AuthErrorDetector."""

import pytest

from appkit_assistant.backend.services.auth_error_detector import (
    AuthErrorDetector,
    get_auth_error_detector,
)


class TestAuthErrorDetector:
    """Test suite for AuthErrorDetector."""

    def test_is_auth_error_detects_401_status(self) -> None:
        """is_auth_error detects 401 in error message."""
        detector = AuthErrorDetector()

        assert detector.is_auth_error("Error 401: Unauthorized") is True
        assert detector.is_auth_error("HTTP 401") is True

    def test_is_auth_error_detects_403_status(self) -> None:
        """is_auth_error detects 403 in error message."""
        detector = AuthErrorDetector()

        assert detector.is_auth_error("Error 403: Forbidden") is True
        assert detector.is_auth_error("HTTP 403") is True

    def test_is_auth_error_detects_unauthorized_keyword(self) -> None:
        """is_auth_error detects 'unauthorized' keyword."""
        detector = AuthErrorDetector()

        assert detector.is_auth_error("Request unauthorized") is True
        assert detector.is_auth_error("Unauthorized access") is True
        assert detector.is_auth_error("UNAUTHORIZED") is True

    def test_is_auth_error_detects_forbidden_keyword(self) -> None:
        """is_auth_error detects 'forbidden' keyword."""
        detector = AuthErrorDetector()

        assert detector.is_auth_error("Access forbidden") is True
        assert detector.is_auth_error("Forbidden resource") is True

    def test_is_auth_error_detects_token_errors(self) -> None:
        """is_auth_error detects token-related errors."""
        detector = AuthErrorDetector()

        assert detector.is_auth_error("Invalid token provided") is True
        assert detector.is_auth_error("Token expired") is True
        assert detector.is_auth_error("authentication required") is True

    def test_is_auth_error_detects_access_denied(self) -> None:
        """is_auth_error detects 'access denied'."""
        detector = AuthErrorDetector()

        assert detector.is_auth_error("Access denied") is True
        assert detector.is_auth_error("access DENIED") is True

    def test_is_auth_error_detects_not_authenticated(self) -> None:
        """is_auth_error detects 'not authenticated'."""
        detector = AuthErrorDetector()

        assert detector.is_auth_error("User not authenticated") is True
        assert detector.is_auth_error("NOT AUTHENTICATED") is True

    def test_is_auth_error_detects_auth_required(self) -> None:
        """is_auth_error detects 'auth_required'."""
        detector = AuthErrorDetector()

        assert detector.is_auth_error("auth_required") is True
        assert detector.is_auth_error("AUTH_REQUIRED") is True

    def test_is_auth_error_returns_false_for_other_errors(self) -> None:
        """is_auth_error returns False for non-auth errors."""
        detector = AuthErrorDetector()

        assert detector.is_auth_error("Network timeout") is False
        assert detector.is_auth_error("500 Internal Server Error") is False
        assert detector.is_auth_error("Invalid request") is False
        assert detector.is_auth_error("Not found") is False

    def test_is_auth_error_case_insensitive(self) -> None:
        """is_auth_error is case-insensitive."""
        detector = AuthErrorDetector()

        assert detector.is_auth_error("UNAUTHORIZED") is True
        assert detector.is_auth_error("Unauthorized") is True
        assert detector.is_auth_error("unauthorized") is True

    def test_extract_error_text_from_dict(self) -> None:
        """extract_error_text extracts 'message' from dict."""
        detector = AuthErrorDetector()

        error = {"message": "Auth failed", "code": 401}
        text = detector.extract_error_text(error)

        assert text == "Auth failed"

    def test_extract_error_text_from_dict_fallback(self) -> None:
        """extract_error_text uses str() when no 'message' key."""
        detector = AuthErrorDetector()

        error = {"code": 401, "status": "error"}
        text = detector.extract_error_text(error)

        assert "401" in text

    def test_extract_error_text_from_object_with_message(self) -> None:
        """extract_error_text extracts 'message' attribute from object."""

        class MockError:
            message = "Authentication error"

        detector = AuthErrorDetector()
        text = detector.extract_error_text(MockError())

        assert text == "Authentication error"

    def test_extract_error_text_from_string(self) -> None:
        """extract_error_text returns string as-is."""
        detector = AuthErrorDetector()

        text = detector.extract_error_text("Simple error message")

        assert text == "Simple error message"

    def test_extract_error_text_from_exception(self) -> None:
        """extract_error_text converts Exception to string."""
        detector = AuthErrorDetector()

        error = ValueError("Invalid value")
        text = detector.extract_error_text(error)

        assert "Invalid value" in text

    def test_extract_error_text_from_none(self) -> None:
        """extract_error_text returns empty string for None."""
        detector = AuthErrorDetector()

        text = detector.extract_error_text(None)

        assert text == ""

    def test_find_matching_server_in_error_finds_server(self) -> None:
        """find_matching_server_in_error finds server by name in error."""

        class MockServer:
            def __init__(self, name: str):
                self.name = name

        detector = AuthErrorDetector()
        servers = [MockServer("GitHub"), MockServer("GitLab"), MockServer("Bitbucket")]

        matched = detector.find_matching_server_in_error(
            "Authentication failed for GitHub", servers
        )

        assert matched is not None
        assert matched.name == "GitHub"

    def test_find_matching_server_in_error_case_insensitive(self) -> None:
        """find_matching_server_in_error is case-insensitive."""

        class MockServer:
            def __init__(self, name: str):
                self.name = name

        detector = AuthErrorDetector()
        servers = [MockServer("GitHub")]

        matched = detector.find_matching_server_in_error("github auth error", servers)

        assert matched is not None
        assert matched.name == "GitHub"

    def test_find_matching_server_in_error_returns_none_when_not_found(self) -> None:
        """find_matching_server_in_error returns None when no match."""

        class MockServer:
            def __init__(self, name: str):
                self.name = name

        detector = AuthErrorDetector()
        servers = [MockServer("GitHub")]

        matched = detector.find_matching_server_in_error(
            "Authentication failed for AWS", servers
        )

        assert matched is None

    def test_find_matching_server_in_error_handles_empty_list(self) -> None:
        """find_matching_server_in_error handles empty server list."""
        detector = AuthErrorDetector()

        matched = detector.find_matching_server_in_error("Some error", [])

        assert matched is None

    def test_find_matching_server_in_error_returns_first_match(self) -> None:
        """find_matching_server_in_error returns first matching server."""

        class MockServer:
            def __init__(self, name: str):
                self.name = name

        detector = AuthErrorDetector()
        servers = [MockServer("Server A"), MockServer("Server B"), MockServer("Server A Clone")]

        matched = detector.find_matching_server_in_error(
            "Error with Server A", servers
        )

        assert matched.name == "Server A"


class TestAuthErrorDetectorSingleton:
    """Test suite for singleton pattern."""

    def test_get_auth_error_detector_returns_instance(self) -> None:
        """get_auth_error_detector returns AuthErrorDetector."""
        detector = get_auth_error_detector()

        assert isinstance(detector, AuthErrorDetector)

    def test_get_auth_error_detector_returns_same_instance(self) -> None:
        """get_auth_error_detector returns singleton."""
        detector1 = get_auth_error_detector()
        detector2 = get_auth_error_detector()

        assert detector1 is detector2
