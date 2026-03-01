# ruff: noqa: ARG002, SLF001, S105, S106
"""Tests for user_prompt_service - validate_handle & is_owner."""

from __future__ import annotations

import pytest

from appkit_assistant.backend.services.user_prompt_service import (
    is_owner,
    validate_handle,
)


class TestValidateHandle:
    def test_valid_simple(self) -> None:
        ok, err = validate_handle("my-prompt")
        assert ok is True
        assert err == ""

    def test_valid_alphanumeric(self) -> None:
        ok, _ = validate_handle("Test123")
        assert ok is True

    def test_empty(self) -> None:
        ok, err = validate_handle("")
        assert ok is False
        assert "leer" in err

    def test_whitespace_only(self) -> None:
        ok, err = validate_handle("   ")
        assert ok is False
        assert "leer" in err

    def test_too_short(self) -> None:
        ok, err = validate_handle("ab")
        assert ok is False
        assert "3" in err

    def test_exactly_three(self) -> None:
        ok, _ = validate_handle("abc")
        assert ok is True

    def test_too_long(self) -> None:
        ok, err = validate_handle("a" * 51)
        assert ok is False
        assert "50" in err

    def test_exactly_fifty(self) -> None:
        ok, _ = validate_handle("a" * 50)
        assert ok is True

    def test_invalid_characters_underscore(self) -> None:
        ok, err = validate_handle("bad_handle")
        assert ok is False
        assert "Buchstaben" in err

    def test_invalid_characters_space(self) -> None:
        ok, _err = validate_handle("bad handle")
        assert ok is False

    def test_invalid_characters_special(self) -> None:
        ok, _err = validate_handle("bad@handle!")
        assert ok is False

    def test_case_insensitive(self) -> None:
        ok, _ = validate_handle("MyHandle")
        assert ok is True

    @pytest.mark.parametrize(
        "handle",
        ["valid", "a-b-c", "123", "test-handle-1"],
    )
    def test_valid_variants(self, handle: str) -> None:
        ok, err = validate_handle(handle)
        assert ok is True
        assert err == ""


class TestIsOwner:
    def test_same_user(self) -> None:
        assert is_owner(1, 1) is True

    def test_different_user(self) -> None:
        assert is_owner(1, 2) is False
