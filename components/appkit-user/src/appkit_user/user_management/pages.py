from collections.abc import Callable

import reflex as rx

import appkit_mantine as mn
from appkit_ui.components.header import header
from appkit_user.authentication.components import (
    login_form,
)
from appkit_user.authentication.password_reset_states import (
    PasswordResetConfirmState,
    PasswordResetRequestState,
)
from appkit_user.authentication.states import LOGIN_ROUTE, LoginState, UserSession
from appkit_user.authentication.templates import (
    authenticated,
    default_layout,
)
from appkit_user.user_management.components.user_profile import profile_roles
from appkit_user.user_management.states.profile_states import (
    MIN_PASSWORD_LENGTH,
    ProfileState,
)

ROLES = []


def _password_rule(check: bool, message: str) -> rx.Component:
    return rx.hstack(
        rx.cond(
            check,
            rx.icon("circle-check", size=19, color="green", margin_top="2px"),
            rx.icon("circle-x", size=19, color="red", margin_top="2px"),
        ),
        rx.text(message),
        padding_left="18px",
    )


def create_password_reset_request_page(
    route: str = "/password-reset",
    title: str = "Passwort zurücksetzen",
) -> Callable:
    """Create the password reset request page (email entry).

    Args:
        route: The route for the password reset request page.
        title: The title for the password reset request page.

    Returns:
        The password reset request page component.
    """

    @default_layout(route=route, title=title)
    def _password_reset_request_page() -> rx.Component:
        """The password reset request page (email entry).

        Returns:
            The UI for the password reset request page.
        """
        return rx.center(
            rx.card(
                rx.vstack(
                    rx.vstack(
                        rx.heading("Passwort zurücksetzen", size="7"),
                        rx.text(
                            "Geben Sie Ihre E-Mail-Adresse ein, um einen "
                            "Link zum Zurücksetzen Ihres Passworts zu erhalten.",
                            color_scheme="gray",
                        ),
                        class_name="w-full gap-2",
                    ),
                    rx.cond(
                        PasswordResetRequestState.email_error,
                        rx.callout(
                            PasswordResetRequestState.email_error,
                            icon="triangle_alert",
                            color_scheme="red",
                            role="alert",
                        ),
                    ),
                    rx.cond(
                        PasswordResetRequestState.is_submitted,
                        rx.callout(
                            PasswordResetRequestState.success_message,
                            icon="circle_check",
                            color_scheme="green",
                            role="status",
                        ),
                    ),
                    rx.form(
                        rx.vstack(
                            mn.text_input(
                                placeholder="E-Mail-Adresse",
                                value=PasswordResetRequestState.email,
                                on_change=PasswordResetRequestState.set_email,
                                type="email",
                                class_name="w-full",
                            ),
                            rx.button(
                                "Link senden",
                                type="submit",
                                size="3",
                                class_name="w-full",
                                loading=PasswordResetRequestState.is_loading,
                            ),
                            rx.hstack(
                                rx.spacer(),
                                rx.link(
                                    rx.text(
                                        "Zurück zur Anmeldung",
                                        size="2",
                                        color_scheme="blue",
                                    ),
                                    href="/login",
                                ),
                                class_name="w-full",
                            ),
                            class_name="w-full gap-2",
                        ),
                        on_submit=[PasswordResetRequestState.request_password_reset],
                    ),
                    class_name="w-full gap-4",
                ),
                size="4",
                class_name="min-w-[26em] max-w-[26em] w-full",
                variant="surface",
                appearance="dark",
            ),
        )

    return _password_reset_request_page


def create_password_reset_confirm_page(
    route: str = "/password-reset/confirm",
    title: str = "Passwort bestätigen",
) -> Callable:
    """Create the password reset confirmation page (new password entry).

    Args:
        route: The route for the password reset confirmation page.
        title: The title for the password reset confirmation page.

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
        return rx.center(
            rx.card(
                rx.vstack(
                    rx.vstack(
                        rx.heading("Passwort zurücksetzen", size="7"),
                        rx.text(
                            rx.text(
                                "Für: ",
                                as_="span",
                                font_weight="500",
                            ),
                            PasswordResetConfirmState.user_email,
                            color_scheme="gray",
                        ),
                        rx.text(
                            "Geben Sie Ihr neues Passwort ein.",
                            color_scheme="gray",
                            size="2",
                        ),
                        class_name="w-full gap-1",
                    ),
                    rx.cond(
                        PasswordResetConfirmState.token_error,
                        rx.callout(
                            PasswordResetConfirmState.token_error,
                            icon="triangle_alert",
                            color_scheme="red",
                            role="alert",
                        ),
                    ),
                    rx.cond(
                        PasswordResetConfirmState.password_error,
                        rx.callout(
                            PasswordResetConfirmState.password_error,
                            icon="triangle_alert",
                            color_scheme="red",
                            role="alert",
                        ),
                    ),
                    rx.cond(
                        PasswordResetConfirmState.password_history_error,
                        rx.callout(
                            PasswordResetConfirmState.password_history_error,
                            icon="triangle_alert",
                            color_scheme="red",
                            role="alert",
                        ),
                    ),
                    rx.form(
                        rx.vstack(
                            mn.password_input(
                                placeholder="Neues Passwort",
                                value=PasswordResetConfirmState.new_password,
                                on_change=PasswordResetConfirmState.set_new_password,
                                class_name="w-full",
                            ),
                            mn.password_input(
                                placeholder="Passwort bestätigen",
                                value=PasswordResetConfirmState.confirm_password,
                                on_change=PasswordResetConfirmState.set_confirm_password,
                                class_name="w-full",
                            ),
                            rx.vstack(
                                rx.vstack(
                                    _password_rule(
                                        PasswordResetConfirmState.has_length,
                                        f"Mindestens {MIN_PASSWORD_LENGTH} Zeichen",
                                    ),
                                    _password_rule(
                                        PasswordResetConfirmState.has_upper,
                                        "Ein Großbuchstabe",
                                    ),
                                    _password_rule(
                                        PasswordResetConfirmState.has_lower,
                                        "Ein Kleinbuchstabe",
                                    ),
                                    _password_rule(
                                        PasswordResetConfirmState.has_digit,
                                        "Eine Ziffer",
                                    ),
                                    _password_rule(
                                        PasswordResetConfirmState.has_special,
                                        "Ein Sonderzeichen",
                                    ),
                                    class_name="w-full gap-2 text-sm",
                                ),
                                class_name="w-full",
                            ),
                            rx.button(
                                "Passwort zurücksetzen",
                                type="submit",
                                size="3",
                                class_name="w-full",
                                loading=PasswordResetConfirmState.is_loading,
                            ),
                            rx.hstack(
                                rx.spacer(),
                                rx.link(
                                    rx.text(
                                        "Zurück zur Anmeldung",
                                        size="2",
                                        color_scheme="blue",
                                    ),
                                    href="/login",
                                ),
                                class_name="w-full",
                            ),
                            class_name="w-full gap-2",
                        ),
                        on_submit=[PasswordResetConfirmState.confirm_password_reset],
                    ),
                    class_name="w-full gap-4",
                ),
                size="4",
                class_name="min-w-[26em] max-w-[26em] w-full",
                variant="surface",
                appearance="dark",
            ),
        )

    return _password_reset_confirm_page


# @default_layout(route=LOGIN_ROUTE, title="Login")
# def login_page(
#     header: str = "AppKit",
#     logo: str = "/img/logo.svg",
#     logo_dark: str = "/img/logo_dark.svg",
#     margin_left: str = "0px",
# ) -> rx.Component:
#     return login_form(
#         header=header, logo=logo, logo_dark=logo_dark, margin_left=margin_left
#     )


def create_login_page(
    header: str = "",
    logo: str = "/img/logo.svg",
    logo_dark: str = "/img/logo_dark.svg",
    margin_left: str = "0px",
    route: str = LOGIN_ROUTE,
    title: str = "Login",
) -> Callable:
    """Create the login page.

    Args:
        header: The header text to display on the login page.
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
            header=header,
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
        return rx.vstack(
            header("Profil"),
            rx.flex(
                rx.vstack(
                    rx.hstack(
                        rx.icon("square-user-round", class_name="w-4 h-4"),
                        rx.heading("Persönliche Informationen", size="5"),
                        class_name="items-center",
                    ),
                    rx.text("Aktualisiere deine persönlichen Informationen.", size="3"),
                    class_name="w-full",
                ),
                rx.form.root(
                    rx.vstack(
                        rx.vstack(
                            rx.cond(
                                UserSession.user.avatar_url,
                                rx.avatar(
                                    src=UserSession.user.avatar_url,
                                    class_name="w-14 h-14 mb-[6px]",
                                ),
                            ),
                            rx.hstack(
                                rx.icon("user", class_name="w-4 h-4", stroke_width=1.5),
                                rx.text("Name"),
                                class_name="w-full items-center gap-2",
                            ),
                            mn.form.input(
                                placeholder="dein Name",
                                type="text",
                                class_name="w-full",
                                name="lastname",
                                default_value=rx.cond(
                                    UserSession.user.name, UserSession.user.name, ""
                                ),
                                read_only=True,
                                pointer=True,
                            ),
                            class_name="flex-col gap-1 w-full",
                        ),
                        rx.vstack(
                            rx.hstack(
                                rx.icon(
                                    "at-sign", class_name="w-4 h-4", stroke_width=1.5
                                ),
                                rx.text("E-Mail / Benutzername"),
                                class_name="w-full items-center gap-2",
                            ),
                            mn.form.input(
                                placeholder="deine E-Mail-Adresse",
                                type="email",
                                default_value=UserSession.user.email,
                                class_name="w-full",
                                name="mail",
                                read_only=True,
                                pointer=True,
                            ),
                            class_name="flex-col gap-1 w-full",
                        ),
                        rx.cond(
                            UserSession.user,
                            profile_roles(
                                is_admin=UserSession.user.is_admin,
                                is_active=UserSession.user.is_active,
                                is_verified=UserSession.user.is_verified,
                            ),
                            profile_roles(
                                is_admin=False,
                                is_active=False,
                                is_verified=False,
                            ),
                        ),
                        class_name="w-full gap-5",
                    ),
                    class_name="w-full max-w-[325px]",
                ),
                class_name="w-full gap-4 flex-col md:flex-row",
            ),
            rx.divider(),
            rx.flex(
                rx.vstack(
                    rx.hstack(
                        rx.icon("key-round", class_name="w-4 h-4"),
                        rx.heading("Passwort ändern", size="5"),
                        class_name="items-center",
                    ),
                    rx.text(
                        "Aktualisiere dein Passwort. Ein neues Passwort muss der ",
                        "Passwort-Richtlinie entsprechen:",
                        size="3",
                    ),
                    _password_rule(
                        ProfileState.has_length,
                        f"Mindestens {MIN_PASSWORD_LENGTH} Zeichen",
                    ),
                    _password_rule(
                        ProfileState.has_upper, "Mindestens ein Großbuchstabe"
                    ),
                    _password_rule(
                        ProfileState.has_lower, "Mindestens ein Kleinbuchstabe"
                    ),
                    _password_rule(ProfileState.has_digit, "Mindestens eine Zahl"),
                    _password_rule(
                        ProfileState.has_special, "Mindestens ein Sonderzeichen"
                    ),
                    class_name="w-full",
                ),
                rx.form.root(
                    rx.vstack(
                        rx.vstack(
                            rx.hstack(
                                rx.icon("lock", class_name="w-4 h-4", stroke_width=1.5),
                                rx.text("Aktuelles Passwort"),
                                class_name="w-full items-center gap-2",
                            ),
                            mn.form.input(
                                placeholder="dein aktuelles Passwort",
                                type="password",
                                default_value="",
                                class_name="w-full",
                                name="current_password",
                                value=ProfileState.current_password,
                                on_change=ProfileState.set_current_password,
                            ),
                            class_name="flex-col gap-1 w-full",
                        ),
                        rx.vstack(
                            rx.hstack(
                                rx.icon(
                                    "lock-keyhole-open",
                                    class_name="w-4 h-4",
                                    stroke_width=1.5,
                                ),
                                rx.text("Neues Passwort"),
                                class_name="w-full items-center gap-2",
                            ),
                            mn.password_input(
                                placeholder="Dein neues Passwort...",
                                class_name="w-full",
                                value=ProfileState.new_password,
                                on_change=ProfileState.set_new_password,
                            ),
                            rx.progress(
                                value=ProfileState.strength_value,
                                width="100%",
                            ),
                            class_name="flex-col gap-1 w-full",
                        ),
                        rx.vstack(
                            rx.hstack(
                                rx.icon(
                                    "lock-keyhole",
                                    class_name="w-4 h-4",
                                    stroke_width=1.5,
                                ),
                                rx.text("Passwort bestätigen"),
                                class_name="w-full items-center gap-2",
                            ),
                            mn.password_input(
                                placeholder="bestätige dein neues Passwort",
                                type="password",
                                default_value="",
                                error=ProfileState.password_error,
                                class_name="w-full",
                                name="confirm_password",
                                value=ProfileState.confirm_password,
                                on_change=ProfileState.set_confirm_password,
                            ),
                            class_name="flex-col gap-1 w-full",
                        ),
                        rx.button(
                            "Passwort aktualisieren", type="submit", class_name="w-full"
                        ),
                        class_name="w-full gap-5",
                    ),
                    class_name="w-full max-w-[325px]",
                    on_submit=ProfileState.handle_password_update,
                    reset_on_submit=True,
                ),
                class_name="w-full gap-4 flex-col md:flex-row",
            ),
            **kwargs,
        )

    return _profile_page
