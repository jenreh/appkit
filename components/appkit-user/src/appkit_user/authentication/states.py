import logging
import secrets
import string
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from typing import Final

import reflex as rx
from reflex.event import EventSpec

from appkit_commons.database.session import get_asyncdb_session
from appkit_commons.registry import service_registry
from appkit_user.authentication.backend.entities import OAuthStateEntity
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
AUTH_TOKEN_LOCAL_STORAGE_KEY: Final = "_auth_token"  # noqa: S105

TOKEN_LENGTH: Final = 64
TOKEN_CHARS: Final = string.ascii_letters + string.digits + "!@#$%^&*()-=_+[]{}|;:,.<>?"

LOGIN_ROUTE: Final = "/login"
LOGOUT_ROUTE: Final = "/login"


class UserSession(rx.State):
    """Enhanced session state with client-side storage integration."""

    auth_token: str = rx.LocalStorage(name=AUTH_TOKEN_LOCAL_STORAGE_KEY)
    user_id: int = 0
    user: User | None = None

    def _generate_auth_token(self) -> str:
        """Generate a simple auth token with a length of 64 chars."""
        return "".join(secrets.choice(TOKEN_CHARS) for _ in range(TOKEN_LENGTH))

    @rx.var(cache=True, interval=AUTH_TOKEN_REFRESH_DELTA)
    async def authenticated_user(self) -> User | None:
        """The currently authenticated user, or a dummy user if not authenticated.

        Returns:
            A LocalUser instance with id=-1 if not authenticated, or the LocalUser
            instance corresponding to the currently authenticated user.
        """
        async with get_asyncdb_session() as session:
            user_session = await session_repo.find_by_user_and_session_id(
                session, self.user_id, self.auth_token
            )

            if user_session is None or user_session.is_expired():
                return None

            user_session.expires_at = datetime.now(UTC) + SESSION_TIMEOUT
            await session.flush()  # Ensure the session is updated in the database

            if user_session and user_session.user:
                # Convert UserEntity to User model by extracting attributes
                user_entity = user_session.user
                user = User(**user_entity.to_dict())
                self.user = user

            await session.commit()

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
        async with get_asyncdb_session() as session:
            await session_repo.delete_by_user_and_session_id(
                session, self.user_id, self.auth_token
            )

        self.reset()
        return rx.clear_session_storage()

    @rx.event
    async def clear_session_storage_token(self) -> EventSpec:
        """Clear the 'token' from browser session storage."""
        return rx.call_script("sessionStorage.removeItem('token')")


class LoginState(UserSession):
    """Simple authentication state."""

    redirect_to: str = "/"
    homepage: str = "/"
    login_route: str = LOGIN_ROUTE
    logout_route: str = LOGOUT_ROUTE
    is_loading: bool = False

    error_message: str = ""
    _oauth_service: OAuthService = OAuthService()

    @rx.var
    def enable_azure_oauth(self) -> bool:
        """Whether Azure OAuth is enabled."""
        return self._oauth_service.azure_enabled

    @rx.var
    def enable_github_oauth(self) -> bool:
        """Whether GitHub OAuth is enabled."""
        return self._oauth_service.github_enabled

    @rx.event
    async def login_with_password(self, form_data: dict) -> AsyncGenerator:
        """
        Login with username and password. Expects form_data to contain
        - 'username'
        - 'password'
        """
        self.is_loading = True
        self.error_message = ""
        await self.terminate_session()

        username = form_data["username"]
        password = form_data["password"]

        try:
            async with get_asyncdb_session() as db:
                (
                    user_entity,
                    status,
                ) = await user_repo.get_login_status_by_credentials(
                    db, username, password
                )

                if status != "success":
                    error_msg = ""
                    if status == "invalid_credentials":
                        error_msg = "Ungültiger Benutzername oder Passwort."
                    elif status == "inactive":
                        error_msg = (
                            "Ihr Konto wurde deaktiviert. "
                            "Bitte wenden Sie sich an einen Administrator."
                        )
                    elif status == "not_verified":
                        error_msg = (
                            "Ihr Konto wurde noch nicht verifiziert. "
                            "Bitte wenden Sie sich an einen Administrator."
                        )

                    self.error_message = error_msg
                    yield rx.toast.error(error_msg, position="top-right")
                    return

                self.auth_token = self._generate_auth_token()
                await session_repo.save(
                    db,
                    user_entity.id,
                    self.auth_token,
                    datetime.now(UTC) + SESSION_TIMEOUT,
                )

                self.user_id = user_entity.id
                self.user = User(**user_entity.to_dict())

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

            await self.terminate_session()

            # Normalize provider to string value (handles Enum inputs)
            provider_str = (
                provider_name.value
                if hasattr(provider_name, "value")
                else str(provider_name)
            )

            if not self._oauth_service.provider_supported(provider_str):
                self.error_message = f"Unknown provider: {provider_name}"
                return rx.toast.info(
                    f"Der Anbieter {provider_name} wird nicht unterstützt.",
                    position="top-right",
                )

            auth_url, state, code_verifier = self._oauth_service.get_auth_url(
                provider_str
            )
            session_id = self.router.session.client_token
            async with get_asyncdb_session() as db:
                await oauth_state_repo.delete_expired(db)
                await oauth_state_repo.delete_by_session_id(db, session_id=session_id)

                expires_at = datetime.now(UTC) + SESSION_TIMEOUT
                oauth_state = OAuthStateEntity(
                    session_id=session_id,
                    state=state,
                    provider=provider_str,
                    code_verifier=code_verifier,
                    expires_at=expires_at,
                )
                await oauth_state_repo.create(db, oauth_state)

            return rx.redirect(auth_url)

        except Exception as e:
            logger.exception("Login with provider failed")
            self.error_message = f"Login failed: {e}"
            self.is_loading = False

    @rx.event
    async def handle_oauth_callback(self, provider: str) -> AsyncGenerator:
        """Generic OAuth callback handler."""
        try:
            params = self.router.url.query_parameters

            logger.debug(
                "Handling OAuth callback for provider: %s - params: %s",
                provider,
                params,
            )

            code = params.get("code")
            state = params.get("state")
            error = params.get("error")

            if error:
                self.error_message = error
                logger.debug("OAuth error: %s", error)
                yield rx.toast.error(error, position="top-right")
                return

            if not code:
                yield rx.toast.error("No code provided", position="top-right")
                return

            if not state:
                yield rx.toast.error("No state provided", position="top-right")
                return

            # Verify state (CSRF protection)
            async with get_asyncdb_session() as db:
                await oauth_state_repo.delete_expired(db)

                oauth_state = await oauth_state_repo.find_valid_by_state_and_provider(
                    db, state=state, provider=provider
                )

                if not oauth_state:
                    yield rx.toast.error("Invalid or expired state")

                token = self._oauth_service.exchange_code_for_token(
                    provider, code, state, oauth_state.code_verifier
                )
                user_info = self._oauth_service.get_user_info(provider, token)

                try:
                    user_entity = await user_repo.get_or_create_oauth_user(
                        db, user_info, provider, token
                    )
                except ValueError as e:
                    # Handle cases where user is inactive or not verified
                    yield rx.toast.error(str(e), position="top-right")
                    return

                self.auth_token = self._generate_auth_token()
                await session_repo.save(
                    db,
                    user_entity.id,
                    self.auth_token,
                    datetime.now(UTC) + SESSION_TIMEOUT,
                )

                self.user_id = user_entity.id
                self.user = User(**user_entity.to_dict())

                await oauth_state_repo.delete(db, oauth_state)

            yield LoginState.redir()

        except Exception as e:
            logger.exception("OAuth callback failed")
            yield rx.toast.error(f"OAuth callback failed: {e!s}")
        finally:
            self.is_loading = False

    @rx.event
    async def logout(self) -> EventSpec:
        """Logout user and terminate session."""
        return rx.redirect(LOGOUT_ROUTE)

    @rx.event
    async def redir(self) -> EventSpec:
        """Redirect to the redirect_to route if logged in, or to the login page."""
        if not self.is_hydrated:
            # Re-trigger the event handler after hydration.
            return LoginState.redir()  # type: ignore[return]

        current_page_path = self.router.url.path
        is_auth = await self.is_authenticated

        # 1. If not authenticated and not on the login page, redirect to login.
        #    Store the intended destination to redirect back after successful login.
        if not is_auth and current_page_path != self.login_route:
            self.redirect_to = self.router.url.path
            return rx.redirect(self.login_route)

        # 2. If a `redirect_to` path is set (e.g., after login), navigate there.
        #    Clear `redirect_to` after using it.
        if self.redirect_to:
            redirect_url = self.redirect_to
            self.redirect_to = ""  # Clear the stored redirect path
            return rx.redirect(redirect_url or self.homepage)

        # 3. Handle cases for authenticated users:
        if is_auth:
            # If authenticated and on the login page, redirect to the homepage.
            if current_page_path == self.login_route:
                return rx.redirect(self.homepage)
            # If authenticated and on an OAuth callback page (and not handled by
            # redirect to the homepage.
            if current_page_path.startswith("/oauth/") and current_page_path.endswith(
                "/callback"
            ):
                return rx.redirect(self.homepage)

        # 4. Default action:
        #    - Authenticated user on a regular page: stay on the current page.
        #    - Unauthenticated user on the login page: stay on the login page.
        #    rx.redirect to the current page effectively refreshes or ensures the URL.
        return rx.redirect(current_page_path)
