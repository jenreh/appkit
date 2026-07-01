# ruff: noqa: ARG002, SLF001, S105, S106
"""Tests for PasswordResetService.

Covers the request_reset and confirm_reset outcomes, including the
security property (generic acceptance regardless of user existence), the
history/token/session-invalidation side effects on success, and the
hash-once invariant (the same hash lands in both the user entity and the
password-history record).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from appkit_user.authentication.backend.services.password_reset_service import (
    ConfirmResetOutcome,
    PasswordResetService,
    RequestResetOutcome,
    get_password_reset_service,
)

_PATCH = "appkit_user.authentication.backend.services.password_reset_service"


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
# Accessor
# ============================================================================


class TestGetPasswordResetService:
    def test_returns_singleton(self) -> None:
        assert get_password_reset_service() is get_password_reset_service()

    def test_returns_service_instance(self) -> None:
        assert isinstance(get_password_reset_service(), PasswordResetService)


# ============================================================================
# request_reset
# ============================================================================


class TestRequestReset:
    @pytest.mark.asyncio
    async def test_invalid_email(self) -> None:
        svc = PasswordResetService()
        outcome = await svc.request_reset("not-an-email")
        assert outcome == RequestResetOutcome.INVALID_EMAIL

    @pytest.mark.asyncio
    async def test_rate_limited_is_accepted(self) -> None:
        svc = PasswordResetService()
        with (
            patch(f"{_PATCH}.service_registry") as mock_reg,
            patch(f"{_PATCH}.get_asyncdb_session", return_value=_db_context()),
            patch(f"{_PATCH}.password_reset_request_repo") as mock_req_repo,
            patch(f"{_PATCH}.user_repo") as mock_user_repo,
        ):
            mock_reg.return_value.get.return_value = _mock_config(max_requests=3)
            mock_req_repo.count_recent_requests = AsyncMock(return_value=3)
            outcome = await svc.request_reset("user@example.com")
        assert outcome == RequestResetOutcome.ACCEPTED
        mock_user_repo.find_by_email.assert_not_called()

    @pytest.mark.asyncio
    async def test_user_not_found_is_accepted_and_logged(self) -> None:
        svc = PasswordResetService()
        db = AsyncMock()
        db.commit = AsyncMock()
        with (
            patch(f"{_PATCH}.service_registry") as mock_reg,
            patch(f"{_PATCH}.get_asyncdb_session", return_value=_db_context(db)),
            patch(f"{_PATCH}.password_reset_request_repo") as mock_req_repo,
            patch(f"{_PATCH}.user_repo") as mock_user_repo,
            patch(f"{_PATCH}.password_reset_token_repo") as mock_token_repo,
        ):
            mock_reg.return_value.get.return_value = _mock_config()
            mock_req_repo.count_recent_requests = AsyncMock(return_value=0)
            mock_req_repo.log_request = AsyncMock()
            mock_user_repo.find_by_email = AsyncMock(return_value=None)
            outcome = await svc.request_reset("user@example.com")
        assert outcome == RequestResetOutcome.ACCEPTED
        # No token issued for a non-existent user.
        mock_token_repo.create_token.assert_not_called()
        mock_req_repo.log_request.assert_awaited_once()
        db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_success_sends_email_with_raw_token(self) -> None:
        svc = PasswordResetService()
        db = AsyncMock()
        db.commit = AsyncMock()

        user_entity = MagicMock()
        user_entity.id = 42
        user_entity.name = "TestUser"
        user_entity.email = "user@example.com"

        token_entity = MagicMock()
        email_svc = AsyncMock()
        email_svc.send_password_reset_email = AsyncMock(return_value=True)
        email_svc.__class__.__name__ = "RealProvider"

        with (
            patch(f"{_PATCH}.service_registry") as mock_reg,
            patch(f"{_PATCH}.get_asyncdb_session", return_value=_db_context(db)),
            patch(f"{_PATCH}.password_reset_request_repo") as mock_req_repo,
            patch(f"{_PATCH}.user_repo") as mock_user_repo,
            patch(f"{_PATCH}.password_reset_token_repo") as mock_token_repo,
            patch(f"{_PATCH}.get_email_service", return_value=email_svc),
        ):
            mock_reg.return_value.get.return_value = _mock_config()
            mock_req_repo.count_recent_requests = AsyncMock(return_value=0)
            mock_req_repo.log_request = AsyncMock()
            mock_user_repo.find_by_email = AsyncMock(return_value=user_entity)
            mock_token_repo.create_token = AsyncMock(
                return_value=(token_entity, "RAW-TOKEN-123")
            )
            outcome = await svc.request_reset("user@example.com")

        assert outcome == RequestResetOutcome.ACCEPTED
        # The raw token (not its hash) is used in the emailed link.
        _, kwargs = email_svc.send_password_reset_email.call_args
        assert "RAW-TOKEN-123" in kwargs["reset_link"]
        assert kwargs["user_name"] == "TestUser"
        db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_success_when_email_send_fails(self) -> None:
        svc = PasswordResetService()
        db = AsyncMock()
        db.commit = AsyncMock()

        user_entity = MagicMock()
        user_entity.id = 7
        user_entity.name = "X"
        user_entity.email = "user@example.com"

        email_svc = AsyncMock()
        email_svc.send_password_reset_email = AsyncMock(return_value=False)
        email_svc.__class__.__name__ = "RealProvider"

        with (
            patch(f"{_PATCH}.service_registry") as mock_reg,
            patch(f"{_PATCH}.get_asyncdb_session", return_value=_db_context(db)),
            patch(f"{_PATCH}.password_reset_request_repo") as mock_req_repo,
            patch(f"{_PATCH}.user_repo") as mock_user_repo,
            patch(f"{_PATCH}.password_reset_token_repo") as mock_token_repo,
            patch(f"{_PATCH}.get_email_service", return_value=email_svc),
        ):
            mock_reg.return_value.get.return_value = _mock_config()
            mock_req_repo.count_recent_requests = AsyncMock(return_value=0)
            mock_req_repo.log_request = AsyncMock()
            mock_user_repo.find_by_email = AsyncMock(return_value=user_entity)
            mock_token_repo.create_token = AsyncMock(return_value=(MagicMock(), "tok"))
            outcome = await svc.request_reset("user@example.com")
        assert outcome == RequestResetOutcome.ACCEPTED

    @pytest.mark.asyncio
    async def test_no_email_service_still_accepted(self) -> None:
        svc = PasswordResetService()
        db = AsyncMock()
        db.commit = AsyncMock()

        user_entity = MagicMock()
        user_entity.id = 7
        user_entity.name = None
        user_entity.email = "user@example.com"

        with (
            patch(f"{_PATCH}.service_registry") as mock_reg,
            patch(f"{_PATCH}.get_asyncdb_session", return_value=_db_context(db)),
            patch(f"{_PATCH}.password_reset_request_repo") as mock_req_repo,
            patch(f"{_PATCH}.user_repo") as mock_user_repo,
            patch(f"{_PATCH}.password_reset_token_repo") as mock_token_repo,
            patch(f"{_PATCH}.get_email_service", return_value=None),
        ):
            mock_reg.return_value.get.return_value = _mock_config()
            mock_req_repo.count_recent_requests = AsyncMock(return_value=0)
            mock_req_repo.log_request = AsyncMock()
            mock_user_repo.find_by_email = AsyncMock(return_value=user_entity)
            mock_token_repo.create_token = AsyncMock(return_value=(MagicMock(), "tok"))
            outcome = await svc.request_reset("user@example.com")
        assert outcome == RequestResetOutcome.ACCEPTED

    @pytest.mark.asyncio
    async def test_exception_still_accepted(self) -> None:
        svc = PasswordResetService()
        with patch(f"{_PATCH}.service_registry", side_effect=RuntimeError("boom")):
            outcome = await svc.request_reset("user@example.com")
        assert outcome == RequestResetOutcome.ACCEPTED


# ============================================================================
# confirm_reset
# ============================================================================


class TestConfirmReset:
    @pytest.mark.asyncio
    async def test_invalid_password(self) -> None:
        svc = PasswordResetService()
        result = await svc.confirm_reset("tok", "weak", "weak")
        assert result.outcome == ConfirmResetOutcome.INVALID_PASSWORD

    @pytest.mark.asyncio
    async def test_password_mismatch(self) -> None:
        svc = PasswordResetService()
        result = await svc.confirm_reset("tok", "StrongPass1!xx", "Different1!xx")
        assert result.outcome == ConfirmResetOutcome.PASSWORD_MISMATCH

    @pytest.mark.asyncio
    async def test_invalid_token_none(self) -> None:
        svc = PasswordResetService()
        with (
            patch(f"{_PATCH}.get_asyncdb_session", return_value=_db_context()),
            patch(f"{_PATCH}.password_reset_token_repo") as mock_repo,
        ):
            mock_repo.find_by_token = AsyncMock(return_value=None)
            result = await svc.confirm_reset("tok", "StrongPass1!xx", "StrongPass1!xx")
        assert result.outcome == ConfirmResetOutcome.INVALID_TOKEN

    @pytest.mark.asyncio
    async def test_invalid_token_not_valid(self) -> None:
        svc = PasswordResetService()
        token = MagicMock()
        token.is_valid.return_value = False
        with (
            patch(f"{_PATCH}.get_asyncdb_session", return_value=_db_context()),
            patch(f"{_PATCH}.password_reset_token_repo") as mock_repo,
        ):
            mock_repo.find_by_token = AsyncMock(return_value=token)
            result = await svc.confirm_reset("tok", "StrongPass1!xx", "StrongPass1!xx")
        assert result.outcome == ConfirmResetOutcome.INVALID_TOKEN

    @pytest.mark.asyncio
    async def test_password_reused(self) -> None:
        svc = PasswordResetService()
        token = MagicMock()
        token.is_valid.return_value = True
        token.id = 1
        token.user_id = 42
        token.reset_type = "user_initiated"
        with (
            patch(f"{_PATCH}.get_asyncdb_session", return_value=_db_context()),
            patch(f"{_PATCH}.password_reset_token_repo") as mock_token_repo,
            patch(f"{_PATCH}.password_history_repo") as mock_history_repo,
        ):
            mock_token_repo.find_by_token = AsyncMock(return_value=token)
            mock_history_repo.check_password_reuse = AsyncMock(return_value=True)
            result = await svc.confirm_reset("tok", "StrongPass1!xx", "StrongPass1!xx")
        assert result.outcome == ConfirmResetOutcome.PASSWORD_REUSED

    @pytest.mark.asyncio
    async def test_user_not_found(self) -> None:
        svc = PasswordResetService()
        token = MagicMock()
        token.is_valid.return_value = True
        token.id = 1
        token.user_id = 42
        token.reset_type = "user_initiated"
        with (
            patch(f"{_PATCH}.get_asyncdb_session", return_value=_db_context()),
            patch(f"{_PATCH}.password_reset_token_repo") as mock_token_repo,
            patch(f"{_PATCH}.password_history_repo") as mock_history_repo,
            patch(f"{_PATCH}.user_repo") as mock_user_repo,
        ):
            mock_token_repo.find_by_token = AsyncMock(return_value=token)
            mock_history_repo.check_password_reuse = AsyncMock(return_value=False)
            mock_user_repo.find_by_id = AsyncMock(return_value=None)
            result = await svc.confirm_reset("tok", "StrongPass1!xx", "StrongPass1!xx")
        assert result.outcome == ConfirmResetOutcome.USER_NOT_FOUND

    @pytest.mark.asyncio
    async def test_success_full_side_effects_and_hash_once(self) -> None:
        svc = PasswordResetService()
        token = MagicMock()
        token.is_valid.return_value = True
        token.id = 1
        token.user_id = 42
        token.reset_type = "user_initiated"

        user = MagicMock()
        user._password = "old_hash"
        user.needs_password_reset = False

        db = AsyncMock()
        db.commit = AsyncMock()

        with (
            patch(f"{_PATCH}.get_asyncdb_session", return_value=_db_context(db)),
            patch(f"{_PATCH}.password_reset_token_repo") as mock_token_repo,
            patch(f"{_PATCH}.password_history_repo") as mock_history_repo,
            patch(f"{_PATCH}.user_repo") as mock_user_repo,
            patch(f"{_PATCH}.session_repo") as mock_session_repo,
            patch(
                f"{_PATCH}.generate_password_hash", return_value="NEW_HASH"
            ) as mock_hash,
        ):
            mock_token_repo.find_by_token = AsyncMock(return_value=token)
            mock_token_repo.mark_as_used = AsyncMock()
            mock_history_repo.check_password_reuse = AsyncMock(return_value=False)
            mock_history_repo.save_password_to_history = AsyncMock()
            mock_user_repo.find_by_id = AsyncMock(return_value=user)
            mock_session_repo.delete_all_by_user_id = AsyncMock()
            result = await svc.confirm_reset("tok", "StrongPass1!xx", "StrongPass1!xx")

        assert result.outcome == ConfirmResetOutcome.SUCCESS
        # Hash-once invariant: hashed exactly once, and the SAME hash lands in
        # both the user entity and the password-history record.
        mock_hash.assert_called_once_with("StrongPass1!xx")
        assert user._password == "NEW_HASH"
        _, hist_kwargs = mock_history_repo.save_password_to_history.call_args
        assert hist_kwargs["password_hash"] == "NEW_HASH"
        # Token marked used, sessions invalidated, two commits (data + sessions).
        mock_token_repo.mark_as_used.assert_awaited_once_with(db, 1)
        mock_session_repo.delete_all_by_user_id.assert_awaited_once_with(db, 42)
        assert db.commit.await_count == 2

    @pytest.mark.asyncio
    async def test_admin_forced_clears_flag(self) -> None:
        svc = PasswordResetService()
        token = MagicMock()
        token.is_valid.return_value = True
        token.id = 1
        token.user_id = 42

        user = MagicMock()
        user._password = "old_hash"
        user.needs_password_reset = True

        db = AsyncMock()
        db.commit = AsyncMock()

        with (
            patch(f"{_PATCH}.get_asyncdb_session", return_value=_db_context(db)),
            patch(f"{_PATCH}.password_reset_token_repo") as mock_token_repo,
            patch(f"{_PATCH}.password_history_repo") as mock_history_repo,
            patch(f"{_PATCH}.user_repo") as mock_user_repo,
            patch(f"{_PATCH}.session_repo") as mock_session_repo,
            patch(f"{_PATCH}.generate_password_hash", return_value="NEW_HASH"),
            patch(f"{_PATCH}.PasswordResetType") as mock_type,
        ):
            mock_type.ADMIN_FORCED = "admin_forced"
            token.reset_type = "admin_forced"
            mock_token_repo.find_by_token = AsyncMock(return_value=token)
            mock_token_repo.mark_as_used = AsyncMock()
            mock_history_repo.check_password_reuse = AsyncMock(return_value=False)
            mock_history_repo.save_password_to_history = AsyncMock()
            mock_user_repo.find_by_id = AsyncMock(return_value=user)
            mock_session_repo.delete_all_by_user_id = AsyncMock()
            result = await svc.confirm_reset("tok", "StrongPass1!xx", "StrongPass1!xx")

        assert result.outcome == ConfirmResetOutcome.SUCCESS
        assert user.needs_password_reset is False

    @pytest.mark.asyncio
    async def test_exception_returns_error(self) -> None:
        svc = PasswordResetService()
        with patch(f"{_PATCH}.get_asyncdb_session", side_effect=RuntimeError("boom")):
            result = await svc.confirm_reset("tok", "StrongPass1!xx", "StrongPass1!xx")
        assert result.outcome == ConfirmResetOutcome.ERROR
