import logging
import secrets
import string
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from typing import Final

import reflex as rx
from reflex.event import EventSpec
from sqlalchemy.ext.asyncio import AsyncSession

from appkit_commons.database.session import get_asyncdb_session
from appkit_commons.registry import service_registry
from appkit_user.authentication.backend.entities import OAuthStateEntity, UserEntity
from appkit_user.authentication.backend.models import User
from appkit_user.authentication.backend.oauth_service import OAuthService
from appkit_user.authentication.backend.oauthstate_repository import oauth_state_repo
from appkit_user.authentication.backend.user_repository import user_repo
from appkit_user.authentication.backend.user_session_repository import session_repo
from appkit_user.configuration import AuthenticationConfiguration

logger = logging.getLogger(__name__)

config: AuthenticationConfiguration = service_registry().get(
    AuthenticationConfiguration
)

SESSION_TIMEOUT: Final = timedelta(minutes=config.session_timeout)
AUTH_TOKEN_REFRESH_DELTA: Final = timedelta(minutes=config.auth_token_refresh_delta)
SESSION_MONITOR_INTERVAL: Final = timedelta(
    seconds=config.session_monitor_interval_seconds
)
AUTH_TOKEN_LOCAL_STORAGE_KEY: Final = "_auth_token"  # noqa: S105

TOKEN_LENGTH: Final = 64
TOKEN_CHARS: Final = string.ascii_letters + string.digits + "!@#$%^&*()-=_+[]{}|;:,.<>?"

LOGIN_ROUTE: Final = "/login"
LOGOUT_ROUTE: Final = "/login"


def _generate_auth_token() -> str:
    """Generate a secure auth token."""
    return "".join(secrets.choice(TOKEN_CHARS) for _ in range(TOKEN_LENGTH))


class UserSession(rx.State):
    """Enhanced session state with client-side storage integration."""

    auth_token: str = rx.LocalStorage(name=AUTH_TOKEN_LOCAL_STORAGE_KEY)
    user_id: int = 0
    user: User | None = None

    async def _find_valid_session(self, db: AsyncSession):
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
        await session_repo.save(
            db,
            user_entity.id,
            self.auth_token,
            datetime.now(UTC) + SESSION_TIMEOUT,
        )
        self.user_id = user_entity.id
        self.user = User(**user_entity.to_dict())

    @rx.var(cache=True, interval=AUTH_TOKEN_REFRESH_DELTA)
    async def authenticated_user(self) -> User | None:
        """The currently authenticated user, or None if not authenticated.

        This is a read-only check that does NOT prolong the session.

        Returns:
            The User instance if authenticated, None otherwise.
        """
        async with get_asyncdb_session() as db:
            user_session = await self._find_valid_session(db)

            if user_session is None or user_session.is_expired():
                return None

            if user_session.user:
                self.user = User(**user_session.user.to_dict())
                self.user_id = self.user.user_id

        return self.user

    @rx.var(cache=True, interval=AUTH_TOKEN_REFRESH_DELTA)
    async def is_authenticated(self) -> bool:
        """Whether the current user is authenticated.

        Returns:
            True if the authenticated user has a positive user ID, False otherwise.
        """
        user = await self.authenticated_user
        return user is not None

    @rx.event
    async def terminate_session(self) -> None:
        """Terminate the current session and clear storage."""
        logger.debug("Terminating session for user_id=%s", self.user_id)
        async with get_asyncdb_session() as session:
            await session_repo.delete_by_user_and_session_id(
                session, self.user_id, self.auth_token
            )

        self.reset()
        return rx.clear_session_storage()

    @rx.event
    async def prolong_session(self) -> None:
        """Prolong the current session by resetting the expiration time.

        Call this method ONLY on explicit user activity (form submissions,
        button clicks, etc.) to keep the session alive.

        **IMPORTANT**: This should NEVER be called from check_auth(),
        authenticated_user, is_authenticated, or any automatic mechanism.
        """
        if self.user_id <= 0 or not self.auth_token:
            return

        async with get_asyncdb_session() as session:
            user_session = await session_repo.find_by_user_and_session_id(
                session, self.user_id, self.auth_token
            )
            if user_session and not user_session.is_expired():
                new_expires_at = datetime.now(UTC) + SESSION_TIMEOUT
                user_session.expires_at = new_expires_at
                await session.commit()
                logger.debug(
                    "Session prolonged for user_id=%s, new expiry=%s",
                    self.user_id,
                    new_expires_at,
                )

    @rx.event
    async def clear_session_storage_token(self) -> EventSpec:
        """Clear the 'token' from browser session storage."""
        return rx.call_script("sessionStorage.removeItem('token')")


class LoginState(UserSession):
    """Simple authentication state."""

    redirect_to: str = rx.LocalStorage(name="login_redirect_to")
    homepage: str = "/"
    login_route: str = LOGIN_ROUTE
    logout_route: str = LOGOUT_ROUTE
    is_loading: bool = False
    error_message: str = ""

    _oauth_service: OAuthService = OAuthService()
    _last_auth_check: datetime | None = None

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

    async def _prepare_login(self) -> str:
        """Prepare for login: save redirect, terminate old session. Returns redirect."""
        redirect_target = self.redirect_to
        await self.terminate_session()
        if redirect_target and redirect_target != "/":
            self.redirect_to = redirect_target
        return redirect_target

    @rx.event
    async def login_with_password(self, form_data: dict) -> AsyncGenerator:
        """Login with username and password."""
        self.is_loading = True
        self.error_message = ""

        await self._prepare_login()

        try:
            async with get_asyncdb_session() as db:
                user_entity, status = await user_repo.get_login_status_by_credentials(
                    db, form_data["username"], form_data["password"]
                )

                if status != "success":
                    self.error_message = self._LOGIN_ERROR_MESSAGES.get(status, "")
                    if self.error_message:
                        yield rx.toast.error(self.error_message, position="top-right")
                    return

                await self._create_session(db, user_entity)

            yield LoginState.redir()

        except Exception as e:
            logger.exception("Login failed")
            self.error_message = f"Login failed: {e}"
            yield rx.toast.error(f"Login fehlgeschlagen: {e}", position="top-right")
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
                return rx.toast.info(
                    f"Der Anbieter {provider_name} wird nicht unterstützt.",
                    position="top-right",
                )

            auth_url, state, code_verifier = self._oauth_service.get_auth_url(
                provider_str
            )

            async with get_asyncdb_session() as db:
                await self._store_oauth_state(db, state, provider_str, code_verifier)

            return rx.redirect(auth_url)

        except Exception as e:
            logger.exception("Login with provider failed")
            self.error_message = f"Login failed: {e}"
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
            expires_at=datetime.now(UTC) + SESSION_TIMEOUT,
        )
        await oauth_state_repo.create(db, oauth_state)

    @rx.event
    async def handle_oauth_callback(self, provider: str) -> AsyncGenerator:
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

            yield LoginState.redir()

        except Exception as e:
            logger.exception("OAuth callback failed")
            yield rx.toast.error(f"OAuth callback failed: {e!s}")
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
        """Exchange OAuth code for token and get/create user."""
        token = self._oauth_service.exchange_code_for_token(
            provider, code, state, code_verifier
        )
        user_info = self._oauth_service.get_user_info(provider, token)
        return await user_repo.get_or_create_oauth_user(db, user_info, provider, token)

    @rx.event
    async def logout(self) -> EventSpec:
        """Logout user and terminate session."""
        await self.terminate_session()

        return rx.redirect(LOGOUT_ROUTE)

    @rx.event
    async def redir(self) -> EventSpec | None:
        """Redirect based on authentication status."""
        if not self.is_hydrated:
            return LoginState.redir()  # type: ignore[return]

        path = self.router.url.path
        is_auth = await self.is_authenticated

        logger.debug("Redir check: auth=%s, path=%s", is_auth, path)

        if not is_auth:
            if path == self.login_route:
                return None

            self.redirect_to = path
            return rx.redirect(self.login_route)

        if self.redirect_to:
            target = self.redirect_to
            self.redirect_to = ""
            return rx.redirect(target)

        if path == self.login_route or self._is_oauth_callback_path(path):
            return rx.redirect(self.homepage)

        return None

    @staticmethod
    def _is_oauth_callback_path(path: str) -> bool:
        """Check if path is an OAuth callback route."""
        return path.startswith("/oauth/") and path.endswith("/callback")

    @rx.event
    async def check_auth(self) -> EventSpec | None:
        """Page guard: redirect to login if session is invalid or expired."""
        if self._should_skip_auth_check():
            return None

        self._last_auth_check = datetime.now(UTC)
        logger.debug("Auth check for user_id=%s", self.user_id)

        async with get_asyncdb_session() as db:
            user_session = await self._find_valid_session(db)

            if user_session is None or user_session.is_expired():
                logger.debug("Session expired for user_id=%s", self.user_id)
                self._last_auth_check = None
                await self.terminate_session()
                return await self.redir()

            if user_session.user:
                self.user = User(**user_session.user.to_dict())
                self.user_id = self.user.user_id

        # Sync with parent state
        user_session_state = await self.get_state(UserSession)
        user_session_state.user_id = self.user_id
        user_session_state.user = self.user

        return None

    def _should_skip_auth_check(self) -> bool:
        """Check if auth check should be skipped based on time interval."""
        if self._last_auth_check is None:
            return False

        elapsed = datetime.now(UTC) - self._last_auth_check
        if elapsed < SESSION_MONITOR_INTERVAL:
            logger.debug("Skipping auth check, last check %s ago", elapsed)
            return True
        return False
