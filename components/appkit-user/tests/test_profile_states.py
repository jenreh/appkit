# ruff: noqa: ARG002, SLF001, S105, S106
"""Tests for ProfileState.

Covers password strength calculation, password update flow,
field setters, and validation.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

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
        assert PASSWORD_REGEX.match("StrongPass1!")

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
        state.set_new_password("MyStr0ng!Pass")
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
        state.new_password = "pass123"
        state.set_confirm_password("pass123")
        assert state.password_error == ""

    def test_mismatching_passwords(self) -> None:
        state = _make_state()
        state.new_password = "pass123"
        state.set_confirm_password("different")
        assert state.password_error != ""


# ============================================================================
# set_current_password
# ============================================================================


class TestSetCurrentPassword:
    def test_sets_value(self) -> None:
        state = _make_state()
        state.set_current_password("old_pass")
        assert state.current_password == "old_pass"


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
        state.new_password = "StrongPass1!xx"
        state.confirm_password = "DifferentPass1!"
        result = await state.handle_password_update()
        assert result is not None  # returns toast error

    @pytest.mark.asyncio
    async def test_successful_update(self) -> None:
        state = _make_state()
        state.new_password = "NewStr0ng!Pass"
        state.confirm_password = "NewStr0ng!Pass"
        state.current_password = "OldPassword"

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with (
            patch(f"{_PATCH}.get_asyncdb_session", return_value=mock_session),
            patch(f"{_PATCH}.user_repo") as mock_repo,
        ):
            mock_repo.update_password = AsyncMock()
            await state.handle_password_update()

        assert state.new_password == ""
        assert state.confirm_password == ""
        assert state.current_password == ""
        assert state.strength_value == 0

    @pytest.mark.asyncio
    async def test_incorrect_current_password(self) -> None:
        state = _make_state()
        state.new_password = "NewStr0ng!Pass"
        state.confirm_password = "NewStr0ng!Pass"
        state.current_password = "WrongOld"

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with (
            patch(f"{_PATCH}.get_asyncdb_session", return_value=mock_session),
            patch(f"{_PATCH}.user_repo") as mock_repo,
        ):
            mock_repo.update_password = AsyncMock(side_effect=ValueError("bad"))
            result = await state.handle_password_update()

        assert result is not None  # error toast
