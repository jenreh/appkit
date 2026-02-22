from collections.abc import Callable

import reflex as rx

from appkit_user.authentication.components import (
    login_form,
    password_reset_confirm_form,
    password_reset_request_form,
)
from appkit_user.authentication.password_reset_states import (
    PasswordResetConfirmState,
)
from appkit_user.authentication.states import LOGIN_ROUTE, LoginState
from appkit_user.authentication.templates import (
    authenticated,
    default_layout,
)
from appkit_user.user_management.components.user_profile import user_profile_view

ROLES = []


def create_password_reset_request_page(
    route: str = "/password-reset",
    title: str = "Passwort zurücksetzen",
    logo: str = "/img/appkit_logo.svg",
    logo_dark: str = "/img/appkit_logo_dark.svg",
) -> Callable:
    """Create the password reset request page (email entry).

    Args:
        route: The route for the password reset request page.
        title: The title for the password reset request page.
        logo: The logo for light mode.
        logo_dark: The logo for dark mode.

    Returns:
        The password reset request page component.
    """

    @default_layout(route=route, title=title)
    def _password_reset_request_page() -> rx.Component:
        """The password reset request page (email entry).

        Returns:
            The UI for the password reset request page.
        """
        return password_reset_request_form(logo=logo, logo_dark=logo_dark)

    return _password_reset_request_page


def create_password_reset_confirm_page(
    route: str = "/password-reset/confirm",
    title: str = "Passwort bestätigen",
    logo: str = "/img/appkit_logo.svg",
    logo_dark: str = "/img/appkit_logo_dark.svg",
) -> Callable:
    """Create the password reset confirmation page (new password entry).

    Args:
        route: The route for the password reset confirmation page.
        title: The title for the password reset confirmation page.
        logo: The logo for light mode.
        logo_dark: The logo for dark mode.

    Returns:
        The password reset confirmation page component.
    """

    @default_layout(
        route=route,
        title=title,
        on_load=PasswordResetConfirmState.validate_token,
    )
    def _password_reset_confirm_page() -> rx.Component:
        """The password reset confirmation page (new password entry).

        Returns:
            The UI for the password reset confirmation page.
        """
        return password_reset_confirm_form(logo=logo, logo_dark=logo_dark)

    return _password_reset_confirm_page


def create_login_page(
    logo: str = "/img/appkit_logo.svg",
    logo_dark: str = "/img/appkit_logo_dark.svg",
    margin_left: str = "0px",
    route: str = LOGIN_ROUTE,
    title: str = "Login",
) -> Callable:
    """Create the login page.

    Args:
        logo: The logo image URL for light mode.
        logo_dark: The logo image URL for dark mode.
        margin_left: The left margin for the login form.
        route: The route for the login page.
        title: The title for the login page.

    Returns:
        The login page component.
    """

    @default_layout(
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
            logo=logo,
            logo_dark=logo_dark,
            margin_left=margin_left,
        )

    return _login_page


def create_profile_page(
    navbar: rx.Component,
    route: str = "/profile",
    title: str = "Profil",
    **kwargs,
) -> Callable:
    """Create the profile page with authentication.

    Args:
        navbar: The navigation bar to use in the page.

    Returns:
        The profile page component.
    """

    @authenticated(
        route=route,
        title=title,
        navbar=navbar,
    )
    def _profile_page() -> rx.Component:
        """The profile page.

        Returns:
            The UI for the profile page.
        """
        return user_profile_view(**kwargs)

    return _profile_page
