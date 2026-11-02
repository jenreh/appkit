# ruff: noqa: ARG002, SLF001, S105, S106
"""Tests for ProfileState.

Covers password strength calculation, password update flow,
field setters, and validation.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from appkit_commons.testing import TEST_PASSWORD
from appkit_user.authentication.backend.services import ChangePasswordOutcome
from appkit_user.user_management.states.profile_states import (
    MIN_PASSWORD_LENGTH,
    PASSWORD_REGEX,
    ProfileState,
)

_PATCH = "appkit_user.user_management.states.profile_states"

# Access computed-var descriptors via __dict__.
_CV = ProfileState.__dict__


def _unwrap(name: str):
    """Get the raw function from an EventHandler in __dict__."""
    entry = ProfileState.__dict__[name]
    return entry.fn if hasattr(entry, "fn") else entry


class _StubProfileState:
    """Plain stub for ProfileState without rx.State."""

    def __init__(self) -> None:
        self.new_password: str = ""
        self.confirm_password: str = ""
        self.current_password: str = ""
        self.password_error: str = ""
        self.name: str = ""
        self.strength_value: int = 0
        self.has_length: bool = False
        self.has_upper: bool = False
        self.has_lower: bool = False
        self.has_digit: bool = False
        self.has_special: bool = False

    async def get_state(self, cls: type) -> MagicMock:
        mock = MagicMock()
        mock.user_id = 42
        return mock

    # Bind unwrapped methods
    set_new_password = _unwrap("set_new_password")
    set_name = _unwrap("set_name")
    set_confirm_password = _unwrap("set_confirm_password")
    set_current_password = _unwrap("set_current_password")
    handle_password_update = _unwrap("handle_password_update")


def _make_state() -> _StubProfileState:
    return _StubProfileState()


# ============================================================================
# Constants / regex
# ============================================================================


class TestConstants:
    def test_min_password_length(self) -> None:
        assert MIN_PASSWORD_LENGTH == 12

    def test_password_regex_strong(self) -> None:
        assert PASSWORD_REGEX.match(TEST_PASSWORD)

    def test_password_regex_no_upper(self) -> None:
        assert not PASSWORD_REGEX.match("weakpassword1!")

    def test_password_regex_no_digit(self) -> None:
        assert not PASSWORD_REGEX.match("WeakPassword!!")

    def test_password_regex_too_short(self) -> None:
        assert not PASSWORD_REGEX.match("Sh0rt!")

    def test_password_regex_no_special(self) -> None:
        assert not PASSWORD_REGEX.match("NoSpecialChar1A")


# ============================================================================
# set_new_password — strength meter
# ============================================================================


class TestSetNewPassword:
    def test_empty_password(self) -> None:
        state = _make_state()
        state.set_new_password("")
        assert state.strength_value == 0
        assert not state.has_length
        assert not state.has_upper

    def test_only_length(self) -> None:
        state = _make_state()
        state.set_new_password("a" * 13)  # only lowercase + length
        assert state.has_length is True
        assert state.has_lower is True
        assert state.has_upper is False
        assert state.strength_value == 40  # 2 criteria: length + lower

    def test_strong_password(self) -> None:
        state = _make_state()
        state.set_new_password(TEST_PASSWORD)
        assert state.has_length is True
        assert state.has_upper is True
        assert state.has_lower is True
        assert state.has_digit is True
        assert state.has_special is True
        assert state.strength_value == 100

    def test_three_criteria(self) -> None:
        state = _make_state()
        # length + upper + lower = 3 criteria
        state.set_new_password("A" * 6 + "b" * 7)
        assert state.strength_value == 60

    def test_four_criteria(self) -> None:
        state = _make_state()
        # length + upper + lower + digit = 4 criteria
        state.set_new_password("Abcdefghijk1")
        assert state.strength_value == 80

    def test_one_criterion_only(self) -> None:
        state = _make_state()
        state.set_new_password("aaa")  # only lowercase, not enough length
        assert state.has_lower is True
        assert state.strength_value == 20


# ============================================================================
# set_name
# ============================================================================


class TestSetName:
    def test_sets_name(self) -> None:
        state = _make_state()
        state.set_name("Alice")
        assert state.name == "Alice"


# ============================================================================
# set_confirm_password
# ============================================================================


class TestSetConfirmPassword:
    def test_matching_passwords(self) -> None:
        state = _make_state()
        state.new_password = TEST_PASSWORD
        state.set_confirm_password(TEST_PASSWORD)
        assert state.password_error == ""

    def test_mismatching_passwords(self) -> None:
        state = _make_state()
        state.new_password = TEST_PASSWORD
        state.set_confirm_password(f"{TEST_PASSWORD}-other")
        assert state.password_error != ""


# ============================================================================
# set_current_password
# ============================================================================


class TestSetCurrentPassword:
    def test_sets_value(self) -> None:
        state = _make_state()
        state.set_current_password(TEST_PASSWORD)
        assert state.current_password == TEST_PASSWORD


# ============================================================================
# handle_password_update
# ============================================================================


class TestHandlePasswordUpdate:
    @pytest.mark.asyncio
    async def test_invalid_password_format(self) -> None:
        state = _make_state()
        state.new_password = "weak"
        state.confirm_password = "weak"
        result = await state.handle_password_update()
        assert result is not None  # returns toast error

    @pytest.mark.asyncio
    async def test_passwords_dont_match(self) -> None:
        state = _make_state()
        state.new_password = TEST_PASSWORD
        state.confirm_password = f"{TEST_PASSWORD}-other"
        result = await state.handle_password_update()
        assert result is not None  # returns toast error

    @pytest.mark.asyncio
    async def test_successful_update(self) -> None:
        state = _make_state()
        state.new_password = f"{TEST_PASSWORD}-new"
        state.confirm_password = f"{TEST_PASSWORD}-new"
        state.current_password = TEST_PASSWORD

        service = MagicMock()
        service.change_password = AsyncMock(return_value=ChangePasswordOutcome.SUCCESS)

        with patch(f"{_PATCH}.get_password_reset_service", return_value=service):
            await state.handle_password_update()

        # Delegated to the service so the reuse/history/session-revocation
        # policy is enforced, rather than writing the password directly.
        service.change_password.assert_awaited_once()
        assert state.new_password == ""
        assert state.confirm_password == ""
        assert state.current_password == ""
        assert state.strength_value == 0

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "outcome",
        [
            ChangePasswordOutcome.INCORRECT_CURRENT_PASSWORD,
            ChangePasswordOutcome.PASSWORD_REUSED,
            ChangePasswordOutcome.USER_NOT_FOUND,
            ChangePasswordOutcome.ERROR,
        ],
    )
    async def test_failed_update_reports_error_and_keeps_fields(
        self, outcome: ChangePasswordOutcome
    ) -> None:
        """Any non-success outcome must surface an error, not a success toast.

        Regression guard: the old code ignored the repository's ``None``
        return and reported success even when nothing had changed.
        """
        state = _make_state()
        state.new_password = f"{TEST_PASSWORD}-new"
        state.confirm_password = f"{TEST_PASSWORD}-new"
        state.current_password = f"{TEST_PASSWORD}-wrong"

        service = MagicMock()
        service.change_password = AsyncMock(return_value=outcome)

        with patch(f"{_PATCH}.get_password_reset_service", return_value=service):
            result = await state.handle_password_update()

        assert result is not None  # error toast
        # Fields are not cleared, so the user can correct and retry.
        assert state.current_password == f"{TEST_PASSWORD}-wrong"
