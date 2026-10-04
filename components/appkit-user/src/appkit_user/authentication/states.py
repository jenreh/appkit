import asyncio
import functools
import logging
import secrets
import string
from collections.abc import AsyncGenerator, Callable
from datetime import UTC, datetime, timedelta
from typing import Any, Final

import reflex as rx
from reflex.event import EventSpec
from sqlalchemy.ext.asyncio import AsyncSession

from appkit_commons.database.session import get_asyncdb_session
from appkit_commons.public_path import strip_public_prefix
from appkit_commons.registry import service_registry
from appkit_user.authentication.backend.database import (
    OAuthStateEntity,
    UserEntity,
    UserSessionEntity,
    oauth_state_repo,
    session_repo,
    user_repo,
)
from appkit_user.authentication.backend.models import User
from appkit_user.authentication.backend.services import OAuthService
from appkit_user.authentication.session_validation import (
    LOGIN_ROUTE,
    SessionStatus,
    SessionValidationResult,
    SessionValidator,
    safe_redirect_path,
)
from appkit_user.configuration import AuthenticationConfiguration

logger = logging.getLogger(__name__)


@functools.lru_cache(maxsize=1)
def _auth_config() -> AuthenticationConfiguration:
    """Resolve the authentication configuration lazily and cache it."""
    return service_registry().get(AuthenticationConfiguration)


def _session_timeout() -> timedelta:
    """Session lifetime, resolved lazily from configuration."""
    return timedelta(minutes=_auth_config().session_timeout)


def _session_monitor_interval() -> timedelta:
    """How long a validated session may be trusted without re-reading the DB."""
    return timedelta(seconds=_auth_config().session_monitor_interval_seconds)


def _generate_auth_token() -> str:
    """Generate a secure auth token."""
    return "".join(secrets.choice(TOKEN_CHARS) for _ in range(TOKEN_LENGTH))


def storage_key(name: str, prefix: str) -> str:
    """Local storage key of ``name`` for the app with ``prefix``."""
    return f"{prefix}{name}"


def app_storage_key(name: str) -> str:
    """Local storage key of ``name`` with this app's prefix."""
    return storage_key(name, _STORAGE_KEY_PREFIX)


_STORAGE_KEY_PREFIX: Final = _auth_config().effective_storage_key_prefix
_SESSION_VALIDATOR: Final = SessionValidator()

AUTH_TOKEN_REFRESH_DELTA: Final = timedelta(
    minutes=_auth_config().auth_token_refresh_delta
)

SESSION_COOKIE_NAME: Final = _auth_config().effective_session_cookie_name
SESSION_COOKIE_SECURE: Final = _auth_config().session_cookie_secure

AUTH_TOKEN_LOCAL_STORAGE_KEY: Final = app_storage_key("_auth_token")
OAUTH_STATE_LOCAL_STORAGE_KEY: Final = app_storage_key("_oauth_state")
LOGIN_REDIRECT_LOCAL_STORAGE_KEY: Final = app_storage_key("login_redirect_to")

TOKEN_LENGTH: Final = 64
TOKEN_CHARS: Final = string.ascii_letters + string.digits + "!@#$%^&*()-=_+[]{}|;:,.<>?"

LOGOUT_ROUTE: Final = "/login"


class UserSession(rx.State):
    """Enhanced session state with client-side storage integration."""

    auth_token: str = rx.LocalStorage(name=AUTH_TOKEN_LOCAL_STORAGE_KEY)
    # MIRRORS auth_token rather than replacing it, so existing local-storage
    # sessions keep working and the cookie simply appears on the next login.
    # It carries the token on plain HTTP requests (page loads, REST/MCP) where
    # local storage is not readable. No max_age on purpose: this is a browser
    # session cookie, the DB `expires_at` is the real gate.
    session_cookie: str = rx.Cookie(
        name=SESSION_COOKIE_NAME,
        path="/",
        same_site="lax",
        secure=SESSION_COOKIE_SECURE or None,
    )
    user_id: int = 0
    user: User | None = None

    # How long a validated session may be trusted without re-reading the DB.
    # NOT the session's own expiry: caching until then would mean a revoked
    # session (admin force-logout, logout elsewhere, account deactivated) stayed
    # usable on an open socket for the whole session lifetime. Capping the cache
    # at the monitor interval keeps revocation latency at what the old clock
    # throttle gave (60 s) while still enforcing the timeout at the exact expiry
    # instant, because the DB stays authoritative once the cache lapses.
    _session_expires_at: datetime | None = None

    def _has_unexpired_cache(self) -> bool:
        """Whether a previously validated session is still known to be valid."""
        return (
            self._session_expires_at is not None
            and datetime.now(UTC) < self._session_expires_at
        )

    def _trust_session_until(self, expires_at: datetime | None) -> None:
        """Cache the session as valid, capped at the monitor interval.

        Args:
            expires_at: The session's own expiry, or None when unknown.
        """
        trust_until = datetime.now(UTC) + _session_monitor_interval()
        self._session_expires_at = (
            min(expires_at, trust_until) if expires_at is not None else trust_until
        )

    def _cache_session(self, result: SessionValidationResult) -> None:
        """Adopt a VALID validation result into this state."""
        if not result.is_valid or result.user is None:
            return
        self.user = result.user
        self.user_id = result.user.user_id
        self._trust_session_until(result.expires_at)
        # Backfill the mirror for sessions created before the cookie existed.
        # Without this, everyone logged in at deploy time keeps a working
        # WebSocket session but gets 401s from every REST route and a 302 from
        # the page guard, because those transports can only read the cookie.
        if not self.session_cookie and self.auth_token:
            self.session_cookie = self.auth_token

    async def _execute_db_operation(
        self, operation: Callable[[AsyncSession], Any]
    ) -> Any:
        """Execute a database operation with retry logic for transient errors.

        Args:
            operation: An async function that takes a DB session and returns a result.

        Returns:
            The result of the operation.

        Raises:
            Exception: If the operation fails after all retries.
        """
        max_retries = 3
        retry_delay = 0.5
        last_exception = None

        for attempt in range(max_retries):
            try:
                async with get_asyncdb_session() as session:
                    return await operation(session)
            except Exception as e:
                last_exception = e
                # Only retry on operational errors (like connection closed),
                # but simpler to retry on any error for now given we see "SSL closed".
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2**attempt)
                    logger.warning(
                        "Database op failed for user=%s (%d/%d): %s. Retry in %.1fs...",
                        self.user_id,
                        attempt + 1,
                        max_retries,
                        str(e),
                        wait_time,
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        "Database op failed for user=%s after %d attempts: %s",
                        self.user_id,
                        max_retries,
                        str(e),
                    )

        if last_exception:
            raise last_exception

        return None

    async def _find_valid_session(self, db: AsyncSession) -> UserSessionEntity | None:
        """Find valid session by user_id+token or token alone (fallback)."""
        if self.user_id > 0:
            return await session_repo.find_by_user_and_session_id(
                db, self.user_id, self.auth_token
            )
        if self.auth_token:
            return await session_repo.find_by_session_id(db, self.auth_token)
        return None

    async def _create_session(self, db: AsyncSession, user_entity: UserEntity) -> None:
        """Create a new authenticated session for the user."""
        self.auth_token = _generate_auth_token()
        expires_at = datetime.now(UTC) + _session_timeout()
        await session_repo.save(
            db,
            user_entity.id,
            self.auth_token,
            expires_at.replace(tzinfo=None),
        )
        self.session_cookie = self.auth_token
        self._trust_session_until(expires_at)
        self.user_id = user_entity.id
        self.user = User.model_validate(user_entity)

    @rx.var(cache=True, interval=AUTH_TOKEN_REFRESH_DELTA)
    async def authenticated_user(self) -> User | None:
        """The currently authenticated user, or None if not authenticated.

        This is a read-only check that does NOT prolong the session.

        Returns:
            The User instance if authenticated, None otherwise.
        """

        async def _check(db: AsyncSession) -> User | None:
            user_session = await self._find_valid_session(db)

            if user_session is None or user_session.is_expired():
                return None

            if user_session.user:
                return User.model_validate(user_session.user)
            return None

        try:
            user: User | None = await self._execute_db_operation(_check)
            if user:
                self.user = user
                self.user_id = user.user_id
            return user
        except Exception:
            return None

    @rx.var(cache=True, interval=AUTH_TOKEN_REFRESH_DELTA)
    async def is_authenticated(self) -> bool:
        """Whether the current user is authenticated.

        Returns:
            True if the authenticated user has a positive user ID, False otherwise.
        """
        user = await self.authenticated_user
        return user is not None

    @rx.event
    async def terminate_session(self) -> EventSpec | None:
        """Terminate the current session and clear storage.

        Includes retry logic to handle transient database connection errors
        that may occur due to stale SSL connections in the pool.
        """
        logger.debug("Terminating session for user_id=%s", self.user_id)

        async def _terminate(session: AsyncSession) -> None:
            await session_repo.delete_by_user_and_session_id(
                session, self.user_id, self.auth_token
            )

        try:
            await self._execute_db_operation(_terminate)
        except Exception as e:
            # Continue cleanup even if DB delete fails
            logger.debug("Ignored error during session termination: %s", e)

        # Cleared explicitly *before* reset(): terminate_session is also invoked
        # on LoginState, and reset() skips vars inherited from a parent state —
        # so reset() alone would leave the cookie and the expiry cache behind.
        self.session_cookie = ""
        self._session_expires_at = None

        self.reset()
        return rx.clear_session_storage()

    @rx.event
    async def prolong_session(self) -> None:
        """Prolong the current session by resetting the expiration time.

        Call this method ONLY on explicit user activity (form submissions,
        button clicks, etc.) to keep the session alive.

        **IMPORTANT**: This should NEVER be called from check_auth(),
        authenticated_user, is_authenticated, or any automatic mechanism.

        Includes error handling for transient database connection issues.
        """
        if self.user_id <= 0 or not self.auth_token:
            return

        async def _prolong(session: AsyncSession) -> None:
            user_session = await session_repo.find_by_user_and_session_id(
                session, self.user_id, self.auth_token
            )
            if user_session and not user_session.is_expired():
                new_expires_at = datetime.now(UTC) + _session_timeout()
                # Store naive UTC to fix DB timezone mismatch on TIMESTAMP columns
                user_session.expires_at = new_expires_at.replace(tzinfo=None)
                await session.commit()
                self._trust_session_until(new_expires_at)
                logger.debug(
                    "Session prolonged for user_id=%s, new expiry=%s",
                    self.user_id,
                    new_expires_at,
                )

        try:
            await self._execute_db_operation(_prolong)
        except Exception as e:
            logger.debug("Failed to prolong session (already logged): %s", e)

    @rx.event
    async def clear_session_storage_token(self) -> EventSpec:
        """Clear the 'token' from browser session storage."""
        return rx.call_script("sessionStorage.removeItem('token')")


class LoginState(UserSession):
    """Simple authentication state."""

    redirect_to: str = rx.LocalStorage(name=LOGIN_REDIRECT_LOCAL_STORAGE_KEY)
    oauth_state: str = rx.LocalStorage(name=OAUTH_STATE_LOCAL_STORAGE_KEY)
    homepage: str = "/"
    login_route: str = LOGIN_ROUTE
    logout_route: str = LOGOUT_ROUTE
    is_loading: bool = False
    error_message: str = ""

    _oauth_service: OAuthService = OAuthService()

    # Error messages for login status
    _LOGIN_ERROR_MESSAGES: dict[str, str] = {
        "invalid_credentials": "Ungültiger Benutzername oder Passwort.",
        "inactive": (
            "Ihr Konto wurde deaktiviert. Bitte wenden Sie sich an einen Administrator."
        ),
        "not_verified": (
            "Ihr Konto wurde noch nicht verifiziert. "
            "Bitte wenden Sie sich an einen Administrator."
        ),
    }

    @rx.var
    def enable_azure_oauth(self) -> bool:
        """Whether Azure OAuth is enabled."""
        return self._oauth_service.azure_enabled

    @rx.var
    def enable_github_oauth(self) -> bool:
        """Whether GitHub OAuth is enabled."""
        return self._oauth_service.github_enabled

    @rx.var
    def enable_google_oauth(self) -> bool:
        """Whether Google OAuth is enabled."""
        return self._oauth_service.google_enabled

    @rx.var
    def enable_apple_oauth(self) -> bool:
        """Whether Apple OAuth is enabled."""
        return self._oauth_service.apple_enabled

    async def _prepare_login(self) -> str:
        """Prepare for login: save redirect, terminate old session. Returns redirect."""
        redirect_target = self.redirect_to
        # The clear-session-storage spec is dropped on purpose here: Reflex
        # keeps its client token in session storage, and wiping it mid-flow
        # would break the OAuth state lookup on the callback. A fresh session
        # is created moments later anyway.
        await self.terminate_session()  # type: ignore[operator]  # rx.event handler invoked directly
        if redirect_target and redirect_target != "/":
            self.redirect_to = redirect_target
        return redirect_target

    @rx.event
    async def login_with_password(
        self, form_data: dict
    ) -> AsyncGenerator[EventSpec, None]:
        """Login with username and password."""
        self.is_loading = True
        self.error_message = ""

        await self._prepare_login()

        try:
            async with get_asyncdb_session() as db:
                user_entity, status = await user_repo.get_login_status_by_credentials(
                    db, form_data["username"], form_data["password"]
                )

                if status != "success" or user_entity is None:
                    self.error_message = self._LOGIN_ERROR_MESSAGES.get(status, "")
                    if self.error_message:
                        yield rx.toast.error(self.error_message, position="top-right")
                    return

                await self._create_session(db, user_entity)

            yield LoginState.redir()  # type: ignore[operator]

        except Exception:
            logger.exception("Login failed")
            self.error_message = "Login fehlgeschlagen. Bitte versuchen Sie es erneut."
            yield rx.toast.error(self.error_message, position="top-right")
        finally:
            self.is_loading = False

    @rx.event
    async def login_with_provider(self, provider_name: str) -> EventSpec | None:
        """Start OAuth login flow."""
        try:
            self.is_loading = True
            self.error_message = ""

            await self._prepare_login()

            provider_str = getattr(provider_name, "value", str(provider_name))

            if not self._oauth_service.provider_supported(provider_str):
                self.error_message = f"Unknown provider: {provider_name}"
                return rx.toast.info(  # type: ignore[no-any-return]
                    f"Der Anbieter {provider_name} wird nicht unterstützt.",
                    position="top-right",
                )

            auth_url, state, code_verifier = self._oauth_service.get_auth_url(
                provider_str
            )

            async with get_asyncdb_session() as db:
                await self._store_oauth_state(db, state, provider_str, code_verifier)

            # Bind the state to this browser: the callback only accepts a state
            # that matches the value this user agent stored before redirecting.
            self.oauth_state = state

            return rx.redirect(auth_url)

        except Exception:
            logger.exception("Login with provider failed")
            self.error_message = "Login fehlgeschlagen. Bitte versuchen Sie es erneut."
            self.is_loading = False
            return None

    async def _store_oauth_state(
        self, db: AsyncSession, state: str, provider: str, code_verifier: str | None
    ) -> None:
        """Store OAuth state for CSRF protection."""
        session_id = self.router.session.client_token

        await oauth_state_repo.delete_expired(db)
        await oauth_state_repo.delete_by_session_id(db, session_id=session_id)

        oauth_state = OAuthStateEntity(
            session_id=session_id,
            state=state,
            provider=provider,
            code_verifier=code_verifier,
            expires_at=datetime.now(UTC) + _session_timeout(),
        )
        await oauth_state_repo.create(db, oauth_state)

    @rx.event
    async def handle_oauth_callback(
        self, provider: str
    ) -> AsyncGenerator[EventSpec, None]:
        """Generic OAuth callback handler."""
        try:
            params = self.router.url.query_parameters
            logger.debug("OAuth callback for %s: %s", provider, params)

            error = params.get("error")
            if error:
                self.error_message = error
                yield rx.toast.error(error, position="top-right")
                return

            code, state = params.get("code"), params.get("state")
            if not code or not state:
                yield rx.toast.error(
                    "Missing code or state parameter", position="top-right"
                )
                return

            # CSRF / login-fixation guard: the state must match the one this
            # browser stored when it started the flow. Without this an attacker
            # can replay their own (code, state) pair into a victim's browser
            # and silently log the victim into the attacker's account.
            expected_state = self.oauth_state
            self.oauth_state = ""
            if not expected_state or not secrets.compare_digest(expected_state, state):
                logger.warning(
                    "OAuth callback state mismatch for provider=%s", provider
                )
                yield rx.toast.error("Invalid or expired state", position="top-right")
                return

            async with get_asyncdb_session() as db:
                await oauth_state_repo.delete_expired(db)

                oauth_state = await oauth_state_repo.find_valid_by_state_and_provider(
                    db, state=state, provider=provider
                )
                if not oauth_state:
                    yield rx.toast.error("Invalid or expired state")
                    return

                try:
                    user_entity = await self._exchange_oauth_and_get_user(
                        db, provider, code, state, oauth_state.code_verifier
                    )
                except ValueError as e:
                    yield rx.toast.error(str(e), position="top-right")
                    return

                await self._create_session(db, user_entity)
                await oauth_state_repo.delete(db, oauth_state)

            yield LoginState.redir()  # type: ignore[operator]

        except Exception:
            logger.exception("OAuth callback failed")
            yield rx.toast.error(
                "Anmeldung fehlgeschlagen. Bitte versuchen Sie es erneut.",
                position="top-right",
            )
        finally:
            self.is_loading = False

    async def _exchange_oauth_and_get_user(
        self,
        db: AsyncSession,
        provider: str,
        code: str,
        state: str,
        code_verifier: str | None,
    ) -> UserEntity:
        """Exchange OAuth code for token and get/create user.

        ``OAuthService`` talks to the provider through ``requests_oauthlib``,
        which is blocking. Running it inline would stall the whole event loop —
        and therefore every other connected user — for two HTTP round-trips, so
        both calls are pushed onto a worker thread.
        """
        token = await asyncio.to_thread(
            self._oauth_service.exchange_code_for_token,
            provider,
            code,
            state,
            code_verifier,
        )
        user_info = await asyncio.to_thread(
            self._oauth_service.get_user_info, provider, token
        )
        return await user_repo.get_or_create_oauth_user(db, user_info, provider, token)

    @rx.event
    async def logout(self) -> list[EventSpec]:
        """Logout user and terminate session."""
        clear_storage = await self.terminate_session()  # type: ignore[operator]  # rx.event handler invoked directly

        # terminate_session() clears the browser's session storage; forward it
        # instead of dropping it, so the tab starts from a clean slate.
        events = [clear_storage] if clear_storage is not None else []
        events.append(rx.redirect(LOGOUT_ROUTE))
        return events

    @rx.event
    async def redir(self) -> EventSpec | None:
        """Redirect based on authentication status."""
        if not self.is_hydrated:
            return LoginState.redir()  # type: ignore[operator, no-any-return]

        path = strip_public_prefix(self.router.url.path)
        is_auth = await self.is_authenticated

        logger.debug("Redir check: auth=%s, path=%s", is_auth, path)

        if not is_auth:
            if path == self.login_route:
                return None

            self.redirect_to = safe_redirect_path(path)
            return rx.redirect(self.login_route)

        if self.redirect_to:
            # Sanitised again at the point of use: the stored value may predate
            # this check, or have been pushed back from the browser's own
            # local storage, which the user controls.
            target = safe_redirect_path(self.redirect_to)
            self.redirect_to = ""
            if target:
                return rx.redirect(target)

        if path == self.login_route or self._is_oauth_callback_path(path):
            return rx.redirect(self.homepage)

        return None

    @staticmethod
    def _is_oauth_callback_path(path: str) -> bool:
        """Check if path is an OAuth callback route."""
        normalized = path.rstrip("/")
        return normalized.startswith("/oauth/") and normalized.endswith("/callback")

    @rx.event
    async def check_auth(self) -> list[EventSpec] | None:
        """Page guard: redirect to login if session is invalid or expired.

        Still driven by ``session_monitor()``, which clicks the hidden trigger
        every ``session_monitor_interval_seconds`` to kick idle tabs.

        Returns:
            Events to run on denial, or None when the session is valid.
        """
        # A cached expiry that has not been reached yet is authoritative: no DB
        # round trip until the exact expiry instant.
        if self._has_unexpired_cache():
            return None

        logger.debug("Auth check for user_id=%s", self.user_id)
        result = await _SESSION_VALIDATOR.validate(self.auth_token, self.user_id)

        if result.is_valid:
            self._cache_session(result)

            # Sync with parent state
            user_session_state = await self.get_state(UserSession)
            user_session_state.user_id = self.user_id
            user_session_state.user = self.user
            return None

        if result.status is SessionStatus.ERROR:
            # Fail closed: the session could not be validated, and rendering the
            # page anyway would let a database outage become an authorization
            # bypass. The session itself is left intact so the next monitor tick
            # can succeed.
            logger.error(
                "Auth check failed, denying access for user_id=%s", self.user_id
            )
            return [rx.redirect(self.login_route)]

        logger.debug("Session %s for user_id=%s", result.status.value, self.user_id)
        clear_storage = await self.terminate_session()  # type: ignore[operator]  # rx.event handler invoked directly
        redirect = await self.redir()  # type: ignore[operator]
        return [e for e in (clear_storage, redirect) if e is not None]
