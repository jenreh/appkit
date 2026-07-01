# ruff: noqa: ARG002, SLF001, S105, S106
"""Tests for PasswordResetRequestState and PasswordResetConfirmState.

Covers email validation, rate limiting, token generation, password strength,
password history checks, and the full reset flow.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from appkit_user.authentication.backend.services import (
    ConfirmResetOutcome,
    ConfirmResetResult,
    RequestResetOutcome,
)
from appkit_user.authentication.password_reset_states import (
    EMAIL_REGEX,
    MIN_PASSWORD_LENGTH,
    PASSWORD_REGEX,
    PasswordResetConfirmState,
    PasswordResetRequestState,
)

_PATCH = "appkit_user.authentication.password_reset_states"


def _unwrap(name: str, cls: type):
    entry = cls.__dict__[name]
    return entry.fn if hasattr(entry, "fn") else entry


def _db_context(session: AsyncMock | None = None):
    s = session or AsyncMock()
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=s)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


def _mock_config(
    max_requests: int = 3, token_expiry: int = 60, server_url: str = "http://localhost"
):
    cfg = MagicMock()
    cfg.password_reset.max_requests_per_hour = max_requests
    cfg.password_reset.token_expiry_minutes = token_expiry
    cfg.server_url = server_url
    return cfg


# ============================================================================
# Regex / constants
# ============================================================================


class TestConstants:
    def test_min_password_length(self) -> None:
        assert MIN_PASSWORD_LENGTH == 12

    def test_email_regex_valid(self) -> None:
        assert EMAIL_REGEX.match("user@example.com")

    def test_email_regex_invalid(self) -> None:
        assert not EMAIL_REGEX.match("not-an-email")
        assert not EMAIL_REGEX.match("@missing.com")

    def test_password_regex_strong(self) -> None:
        assert PASSWORD_REGEX.match("StrongPass1!")

    def test_password_regex_weak(self) -> None:
        assert not PASSWORD_REGEX.match("weak")


# ============================================================================
# PasswordResetRequestState
# ============================================================================


class _StubRequestState:
    def __init__(self) -> None:
        self.email: str = ""
        self.email_error: str = ""
        self.is_loading: bool = False
        self.is_submitted: bool = False
        self.success_message: str = ""

    set_email = _unwrap("set_email", PasswordResetRequestState)
    request_password_reset = _unwrap(
        "request_password_reset", PasswordResetRequestState
    )


class TestSetEmail:
    def test_sets_and_strips(self) -> None:
        state = _StubRequestState()
        state.set_email("  Alice@Test.COM  ")
        assert state.email == "alice@test.com"
        assert state.email_error == ""


def _service_mock(request_outcome=None, confirm_result=None):
    """Build a mock PasswordResetService with the given canned results."""
    svc = MagicMock()
    if request_outcome is not None:
        svc.request_reset = AsyncMock(return_value=request_outcome)
    if confirm_result is not None:
        svc.confirm_reset = AsyncMock(return_value=confirm_result)
    return svc


class TestRequestPasswordReset:
    @pytest.mark.asyncio
    async def test_invalid_email(self) -> None:
        state = _StubRequestState()
        state.email = "not-valid"
        svc = _service_mock(request_outcome=RequestResetOutcome.INVALID_EMAIL)
        with patch(f"{_PATCH}.get_password_reset_service", return_value=svc):
            _ = [c async for c in state.request_password_reset()]
        assert state.email_error != ""
        assert state.is_submitted is False

    @pytest.mark.asyncio
    async def test_accepted_shows_success(self) -> None:
        state = _StubRequestState()
        state.email = "user@example.com"
        svc = _service_mock(request_outcome=RequestResetOutcome.ACCEPTED)
        with patch(f"{_PATCH}.get_password_reset_service", return_value=svc):
            _ = [c async for c in state.request_password_reset()]
        assert state.is_submitted is True
        assert state.is_loading is False
        svc.request_reset.assert_awaited_once_with("user@example.com")


# ============================================================================
# PasswordResetConfirmState
# ============================================================================

_CV_CONFIRM = PasswordResetConfirmState.__dict__


class _StubConfirmState:
    def __init__(self) -> None:
        self.token: str = ""
        self.token_error: str = ""
        self.user_email: str = ""
        self.user_name: str = ""
        self.user_id: int = 0
        self.new_password: str = ""
        self.confirm_password: str = ""
        self.password_error: str = ""
        self.password_history_error: str = ""
        self.is_loading: bool = False
        self.strength_value: int = 0
        self.has_length: bool = False
        self.has_upper: bool = False
        self.has_lower: bool = False
        self.has_digit: bool = False
        self.has_special: bool = False

        # Mock router
        self.router = MagicMock()
        self.router.page.params = {}

    set_new_password = _unwrap("set_new_password", PasswordResetConfirmState)
    set_confirm_password = _unwrap("set_confirm_password", PasswordResetConfirmState)
    validate_token = _unwrap("validate_token", PasswordResetConfirmState)
    confirm_password_reset = _unwrap(
        "confirm_password_reset", PasswordResetConfirmState
    )


class TestSetNewPasswordConfirm:
    def test_strong_password(self) -> None:
        state = _StubConfirmState()
        state.set_new_password("MyStr0ng!Pass")
        assert state.strength_value == 100
        assert state.has_length is True
        assert state.has_upper is True
        assert state.has_lower is True
        assert state.has_digit is True
        assert state.has_special is True
        assert state.password_error == ""

    def test_empty_password(self) -> None:
        state = _StubConfirmState()
        state.set_new_password("")
        assert state.strength_value == 0

    def test_one_criterion(self) -> None:
        state = _StubConfirmState()
        state.set_new_password("aaa")
        assert state.strength_value == 20

    def test_two_criteria(self) -> None:
        state = _StubConfirmState()
        # lower + length
        state.set_new_password("a" * 13)
        assert state.strength_value == 40

    def test_three_criteria(self) -> None:
        state = _StubConfirmState()
        state.set_new_password("A" * 6 + "b" * 7)
        assert state.strength_value == 60

    def test_four_criteria(self) -> None:
        state = _StubConfirmState()
        state.set_new_password("Abcdefghijk1")
        assert state.strength_value == 80


class TestSetConfirmPasswordConfirm:
    def test_matching(self) -> None:
        state = _StubConfirmState()
        state.new_password = "pw123"
        state.set_confirm_password("pw123")
        assert state.password_error == ""

    def test_mismatch(self) -> None:
        state = _StubConfirmState()
        state.new_password = "pw123"
        state.set_confirm_password("different")
        assert state.password_error != ""


class TestValidateToken:
    @pytest.mark.asyncio
    async def test_no_token(self) -> None:
        state = _StubConfirmState()
        state.router.page.params = {}
        _ = [c async for c in state.validate_token()]
        assert state.token_error != ""

    @pytest.mark.asyncio
    async def test_invalid_token(self) -> None:
        state = _StubConfirmState()
        state.router.page.params = {"token": "bad"}
        with (
            patch(f"{_PATCH}.get_asyncdb_session", return_value=_db_context()),
            patch(f"{_PATCH}.password_reset_token_repo") as mock_repo,
        ):
            mock_repo.find_by_token = AsyncMock(return_value=None)
            _ = [c async for c in state.validate_token()]
        assert state.token_error != ""

    @pytest.mark.asyncio
    async def test_used_token(self) -> None:
        state = _StubConfirmState()
        state.router.page.params = {"token": "used"}
        token = MagicMock()
        token.is_valid.return_value = False
        token.is_used = True
        with (
            patch(f"{_PATCH}.get_asyncdb_session", return_value=_db_context()),
            patch(f"{_PATCH}.password_reset_token_repo") as mock_repo,
        ):
            mock_repo.find_by_token = AsyncMock(return_value=token)
            _ = [c async for c in state.validate_token()]
        assert "bereits" in state.token_error

    @pytest.mark.asyncio
    async def test_expired_token(self) -> None:
        state = _StubConfirmState()
        state.router.page.params = {"token": "exp"}
        token = MagicMock()
        token.is_valid.return_value = False
        token.is_used = False
        token.is_expired.return_value = True
        with (
            patch(f"{_PATCH}.get_asyncdb_session", return_value=_db_context()),
            patch(f"{_PATCH}.password_reset_token_repo") as mock_repo,
        ):
            mock_repo.find_by_token = AsyncMock(return_value=token)
            _ = [c async for c in state.validate_token()]
        assert "abgelaufen" in state.token_error

    @pytest.mark.asyncio
    async def test_valid_token(self) -> None:
        state = _StubConfirmState()
        state.router.page.params = {"token": "valid"}
        token = MagicMock()
        token.is_valid.return_value = True
        token.user_id = 42

        user = MagicMock()
        user.email = "user@test.com"
        user.name = "Test"
        user.id = 42

        with (
            patch(f"{_PATCH}.get_asyncdb_session", return_value=_db_context()),
            patch(f"{_PATCH}.password_reset_token_repo") as mock_token_repo,
            patch(f"{_PATCH}.user_repo") as mock_user_repo,
        ):
            mock_token_repo.find_by_token = AsyncMock(return_value=token)
            mock_user_repo.find_by_id = AsyncMock(return_value=user)
            _ = [c async for c in state.validate_token()]

        assert state.user_email == "user@test.com"
        assert state.user_id == 42

    @pytest.mark.asyncio
    async def test_user_not_found(self) -> None:
        state = _StubConfirmState()
        state.router.page.params = {"token": "valid"}
        token = MagicMock()
        token.is_valid.return_value = True
        token.user_id = 42
        with (
            patch(f"{_PATCH}.get_asyncdb_session", return_value=_db_context()),
            patch(f"{_PATCH}.password_reset_token_repo") as mock_token_repo,
            patch(f"{_PATCH}.user_repo") as mock_user_repo,
        ):
            mock_token_repo.find_by_token = AsyncMock(return_value=token)
            mock_user_repo.find_by_id = AsyncMock(return_value=None)
            _ = [c async for c in state.validate_token()]
        assert state.token_error != ""

    @pytest.mark.asyncio
    async def test_exception(self) -> None:
        state = _StubConfirmState()
        state.router.page.params = {"token": "err"}
        with (
            patch(
                f"{_PATCH}.get_asyncdb_session",
                side_effect=RuntimeError("boom"),
            ),
        ):
            _ = [c async for c in state.validate_token()]
        assert state.token_error != ""


def _confirm_service(outcome: ConfirmResetOutcome):
    svc = MagicMock()
    svc.confirm_reset = AsyncMock(return_value=ConfirmResetResult(outcome))
    return svc


class TestConfirmPasswordReset:
    @pytest.mark.asyncio
    async def test_invalid_password(self) -> None:
        state = _StubConfirmState()
        state.new_password = "StrongPass1!xx"
        state.confirm_password = "StrongPass1!xx"
        svc = _confirm_service(ConfirmResetOutcome.INVALID_PASSWORD)
        with patch(f"{_PATCH}.get_password_reset_service", return_value=svc):
            _ = [c async for c in state.confirm_password_reset()]
        assert state.password_error != ""
        assert state.is_loading is False

    @pytest.mark.asyncio
    async def test_passwords_dont_match(self) -> None:
        state = _StubConfirmState()
        state.new_password = "StrongPass1!xx"
        state.confirm_password = "Different1!xx"
        svc = _confirm_service(ConfirmResetOutcome.PASSWORD_MISMATCH)
        with patch(f"{_PATCH}.get_password_reset_service", return_value=svc):
            _ = [c async for c in state.confirm_password_reset()]
        assert state.password_error != ""

    @pytest.mark.asyncio
    async def test_invalid_token_on_confirm(self) -> None:
        state = _StubConfirmState()
        state.new_password = "StrongPass1!xx"
        state.confirm_password = "StrongPass1!xx"
        state.token = "tok"
        svc = _confirm_service(ConfirmResetOutcome.INVALID_TOKEN)
        with patch(f"{_PATCH}.get_password_reset_service", return_value=svc):
            _ = [c async for c in state.confirm_password_reset()]
        assert state.is_loading is False

    @pytest.mark.asyncio
    async def test_password_reuse(self) -> None:
        state = _StubConfirmState()
        state.new_password = "StrongPass1!xx"
        state.confirm_password = "StrongPass1!xx"
        state.token = "tok"
        svc = _confirm_service(ConfirmResetOutcome.PASSWORD_REUSED)
        with patch(f"{_PATCH}.get_password_reset_service", return_value=svc):
            _ = [c async for c in state.confirm_password_reset()]
        assert state.password_history_error != ""

    @pytest.mark.asyncio
    async def test_successful_reset(self) -> None:
        state = _StubConfirmState()
        state.new_password = "StrongPass1!xx"
        state.confirm_password = "StrongPass1!xx"
        state.token = "tok"
        svc = _confirm_service(ConfirmResetOutcome.SUCCESS)
        with patch(f"{_PATCH}.get_password_reset_service", return_value=svc):
            _ = [c async for c in state.confirm_password_reset()]
        assert state.is_loading is False
        svc.confirm_reset.assert_awaited_once_with(
            "tok", "StrongPass1!xx", "StrongPass1!xx"
        )

    @pytest.mark.asyncio
    async def test_user_not_found_on_confirm(self) -> None:
        state = _StubConfirmState()
        state.new_password = "StrongPass1!xx"
        state.confirm_password = "StrongPass1!xx"
        state.token = "tok"
        svc = _confirm_service(ConfirmResetOutcome.USER_NOT_FOUND)
        with patch(f"{_PATCH}.get_password_reset_service", return_value=svc):
            _ = [c async for c in state.confirm_password_reset()]
        assert state.is_loading is False

    @pytest.mark.asyncio
    async def test_error_outcome_on_confirm(self) -> None:
        state = _StubConfirmState()
        state.new_password = "StrongPass1!xx"
        state.confirm_password = "StrongPass1!xx"
        state.token = "tok"
        svc = _confirm_service(ConfirmResetOutcome.ERROR)
        with patch(f"{_PATCH}.get_password_reset_service", return_value=svc):
            _ = [c async for c in state.confirm_password_reset()]
        assert state.is_loading is False
