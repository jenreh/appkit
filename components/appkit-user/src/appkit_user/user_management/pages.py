from collections.abc import Callable

import reflex as rx

import appkit_mantine as mn
from appkit_ui.components.header import header
from appkit_user.authentication.components import (
    login_form,
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
