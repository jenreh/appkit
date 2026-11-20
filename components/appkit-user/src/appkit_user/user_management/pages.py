from collections.abc import Callable
from typing import Protocol

import reflex as rx

from appkit_commons.public_path import public_path
from appkit_user.authentication.components import (
    login_form,
    password_reset_confirm_form,
    password_reset_request_form,
    session_monitor,
    welcome_pending,
)
from appkit_user.authentication.password_reset_states import (
    PasswordResetConfirmState,
)
from appkit_user.authentication.session_validation import welcome_route
from appkit_user.authentication.states import LOGIN_ROUTE, LoginState

ROLES: list[str] = []


class PageLayout(Protocol):
    """Page decorator factory supplied by the app, e.g. its ``default_layout``."""

    def __call__(
        self,
        *,
        route: str | None = None,
        title: str | None = None,
        on_load: rx.EventHandler | list[rx.EventHandler] | None = None,
    ) -> Callable[[Callable[[], rx.Component]], rx.Component]: ...


def create_password_reset_request_page(
    layout: PageLayout,
    route: str = "/password-reset",
    title: str = "Passwort zurücksetzen",
    logo: str = "/img/appkit_logo.svg",
    logo_dark: str = "/img/appkit_logo_dark.svg",
) -> rx.Component:
    """Create the password reset request page (email entry).

    Args:
        layout: Page decorator factory supplied by the app.
        route: The route for the password reset request page.
        title: The title for the password reset request page.
        logo: The logo for light mode.
        logo_dark: The logo for dark mode.

    Returns:
        The password reset request page component.
    """

    @layout(route=route, title=title)
    def _password_reset_request_page() -> rx.Component:
        """The password reset request page (email entry).

        Returns:
            The UI for the password reset request page.
        """
        return password_reset_request_form(
            logo=public_path(logo), logo_dark=public_path(logo_dark)
        )

    return _password_reset_request_page


def create_password_reset_confirm_page(
    layout: PageLayout,
    route: str = "/password-reset/confirm",
    title: str = "Passwort bestätigen",
    logo: str = "/img/appkit_logo.svg",
    logo_dark: str = "/img/appkit_logo_dark.svg",
) -> rx.Component:
    """Create the password reset confirmation page (new password entry).

    Args:
        layout: Page decorator factory supplied by the app.
        route: The route for the password reset confirmation page.
        title: The title for the password reset confirmation page.
        logo: The logo for light mode.
        logo_dark: The logo for dark mode.

    Returns:
        The password reset confirmation page component.
    """

    @layout(
        route=route,
        title=title,
        on_load=PasswordResetConfirmState.validate_token,
    )
    def _password_reset_confirm_page() -> rx.Component:
        """The password reset confirmation page (new password entry).

        Returns:
            The UI for the password reset confirmation page.
        """
        return password_reset_confirm_form(
            logo=public_path(logo), logo_dark=public_path(logo_dark)
        )

    return _password_reset_confirm_page


def create_login_page(
    layout: PageLayout,
    logo: str = "/img/appkit_logo.svg",
    logo_dark: str = "/img/appkit_logo_dark.svg",
    margin_left: str = "0px",
    route: str = LOGIN_ROUTE,
    title: str = "Login",
) -> rx.Component:
    """Create the login page.

    Args:
        layout: Page decorator factory supplied by the app.
        logo: The logo image URL for light mode.
        logo_dark: The logo image URL for dark mode.
        margin_left: The left margin for the login form.
        route: The route for the login page.
        title: The title for the login page.

    Returns:
        The login page component.
    """

    @layout(
        route=route,
        title=title,
        on_load=LoginState.clear_session_storage_token,
    )
    def _login_page() -> rx.Component:
        """The login page.

        Returns:
            The UI for the login page.
        """
        return login_form(
            logo=public_path(logo),
            logo_dark=public_path(logo_dark),
            margin_left=margin_left,
        )

    return _login_page


def create_welcome_page(
    layout: PageLayout,
    content: Callable[[], rx.Component] | None = None,
    route: str | None = None,
    title: str = "Willkommen",
) -> rx.Component:
    """Create the page users awaiting admin approval are fenced to.

    Register it once in the app. The route must match
    ``AuthenticationConfiguration.welcome_route``, which is the default.
    Approved users who open the page are sent on to the homepage.

    Args:
        layout: Page decorator factory supplied by the app.
        content: Builds the page body; defaults to ``welcome_pending``.
            Use ``logout_button`` to let the user sign out.
        route: The route; defaults to the configured welcome route.
        title: The page title.

    Returns:
        The welcome page component.
    """
    build_content = content if content is not None else welcome_pending

    @layout(
        route=route or welcome_route(),
        title=title,
        on_load=LoginState.leave_welcome_if_approved,
    )
    def _welcome_page() -> rx.Component:
        """The welcome page for users awaiting approval.

        Returns:
            The UI for the welcome page.
        """
        return rx.fragment(session_monitor(), build_content())

    return _welcome_page
