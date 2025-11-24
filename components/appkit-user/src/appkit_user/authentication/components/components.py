import logging
from collections.abc import Callable

import reflex as rx

from appkit_user.authentication.states import LoginState, UserSession
from appkit_user.configuration import OAuthProvider

logger = logging.getLogger(__name__)
ComponentCallable = Callable[[], rx.Component]

### components ###


def _form_inline_field(
    icon: str,
    **kwargs,
) -> rx.Component:
    if "class_name" not in kwargs:
        kwargs["class_name"] = ""
    kwargs["class_name"] += " w-full"
    if kwargs.get("size") is None:
        kwargs["size"] = "3"

    return rx.form.field(
        rx.input(
            rx.input.slot(rx.icon(icon)),
            **kwargs,
        ),
        class_name="form-group w-full",
    )


def default_fallback(
    message: str = "Du hast nicht die notwendigen Rechte, um diese Inhalte zu sehen!",
) -> rx.Component:
    """Fallback component to show when the user is not authenticated."""
    return rx.center(
        rx.card(
            rx.heading(message, class_name="w-full", size="3"),
            class_name="w-[380px] p-8",
        ),
        class_name="w-full h-[80vh]",
    )


def login_form(
    header: str, logo: str, logo_dark: str, margin_left: str = "0px"
) -> rx.Component:
    icon_class = "absolute left-[30px] top-1/2 -translate-y-1/2 w-5 h-5"

    return rx.center(
        rx.card(
            rx.vstack(
                rx.hstack(
                    rx.color_mode_cond(
                        rx.image(
                            logo,
                            class_name="h-[60px]",
                            style={"marginLeft": margin_left},
                        ),
                        rx.image(
                            logo_dark,
                            class_name="h-[60px]",
                            style={"marginLeft": margin_left},
                        ),
                    ),
                    rx.heading(header, size="8", margin_left="9px", margin_top="24px"),
                    align="center",
                    justify="start",
                    margin_bottom="0.5em",
                ),
                rx.form(
                    rx.vstack(
                        rx.cond(
                            LoginState.error_message,
                            rx.callout(
                                "Fehler: " + LoginState.error_message,
                                icon="triangle_alert",
                                color_scheme="red",
                                role="alert",
                            ),
                        ),
                        _form_inline_field(
                            name="username",
                            icon="user",
                            placeholder="Deine E-Mail-Adresse",
                            auto_focus=True,
                        ),
                        _form_inline_field(
                            name="password",
                            icon="lock",
                            placeholder="Dein Passwort",
                            type="password",
                        ),
                        rx.button(
                            "Anmelden",
                            type="submit",
                            size="3",
                            class_name="w-full mt-3",
                            loading=rx.cond(
                                LoginState.is_loading,
                                True,
                                False,
                            ),
                        ),
                        class_name="justify-start w-full gap-2",
                    ),
                    on_submit=[
                        LoginState.login_with_password,
                    ],
                ),
                rx.hstack(
                    rx.divider(margin="0"),
                    rx.text(
                        "oder",
                        class_name="whitespace-nowrap font-medium",
                    ),
                    rx.divider(margin="0"),
                    class_name="items-center w-full",
                ),
                rx.vstack(
                    rx.cond(
                        LoginState.enable_github_oauth,
                        rx.button(
                            rx.color_mode_cond(
                                rx.image(
                                    "/icons/GitHub_light.svg", class_name=icon_class
                                ),
                                rx.image(
                                    "/icons/GitHub_dark.svg", class_name=icon_class
                                ),
                            ),
                            "Mit Github anmelden",
                            variant="outline",
                            size="3",
                            class_name="relative flex w-full",
                            loading=rx.cond(
                                LoginState.is_loading,
                                True,
                                False,
                            ),
                            on_click=[
                                LoginState.login_with_provider(OAuthProvider.GITHUB),
                            ],
                        ),
                    ),
                    rx.cond(
                        LoginState.enable_azure_oauth,
                        rx.button(
                            rx.image("/icons/microsoft.svg", class_name=icon_class),
                            "Mit Microsoft anmelden",
                            variant="outline",
                            size="3",
                            class_name="relative flex w-full",
                            loading=rx.cond(
                                LoginState.is_loading,
                                True,
                                False,
                            ),
                            on_click=[
                                LoginState.login_with_provider(OAuthProvider.AZURE),
                            ],
                        ),
                    ),
                    class_name="w-full gap-1",
                ),
                rx.hstack(
                    rx.spacer(),
                    rx.color_mode.button(style={"opacity": "0.8", "scale": "0.95"}),
                    class_name="w-full",
                ),
                class_name="w-full gap-5",
            ),
            size="4",
            class_name="min-w-[26em] max-w-[26em] w-full",
            variant="surface",
            appearance="dark",
        ),
    )


def oauth_login_splash(
    provider: OAuthProvider,
    message: str = "Anmeldung mit {provider}...",
    logo: str = "/img/logo.svg",
    logo_dark: str = "/img/logo_dark.svg",
) -> rx.Component:
    """Render a splash screen while handling OAuth callback."""
    return rx.card(
        rx.vstack(
            rx.color_mode_cond(
                rx.image(logo, class_name="w-[70%]"),
                rx.image(logo_dark, class_name="w-[70%]"),
            ),
            rx.hstack(
                rx.text(message.format(provider=provider)),
                rx.spinner(),
                class_name="w-full gap-5",
            ),
        ),
        size="4",
        class_name="min-w-[26em] max-w-[26em] w-full",
        variant="surface",
    )


def requires_authenticated(
    *children,
    fallback: rx.Component | None = None,  # noqa: B008
) -> rx.Component:
    return rx.cond(
        UserSession.is_authenticated,
        rx.fragment(*children),
        fallback,
    )


def requires_role(
    *children,
    role: str,
    fallback: rx.Component | None = None,  # noqa: B008
) -> rx.Component:
    return rx.cond(
        UserSession.user.roles.contains(role),
        rx.fragment(*children),
        fallback,
    )


def requires_admin(
    *children,
    fallback: rx.Component | None = None,  # noqa: B008
) -> rx.Component:
    return rx.cond(
        UserSession.user.is_admin,
        rx.fragment(*children),
        fallback,
    )
