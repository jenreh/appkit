import logging

import reflex as rx

import appkit_mantine as mn
from appkit_user.authentication.components.components import themed_logo
from appkit_user.authentication.states import LoginState
from appkit_user.configuration import OAuthProvider

logger = logging.getLogger(__name__)


def _oauth_button(
    provider: OAuthProvider,
    text: str,
    icon_light: str,
    enabled_var: rx.Var[bool],
    icon_dark: str | None = None,
) -> rx.Component:
    """Helper to render an OAuth login button."""
    if icon_dark:
        icon = themed_logo(icon_light, icon_dark, w=20, h=20)
    else:
        icon = mn.image(src=icon_light, w=20, h=20)

    return rx.cond(
        enabled_var,
        mn.button(
            text,
            left_section=icon,
            right_section=rx.el.span(),
            variant="default",
            size="md",
            fw="300",
            justify="space-between",
            full_width=True,
            loading=LoginState.is_loading,
            on_click=LoginState.login_with_provider(provider),
        ),
    )


def oauth_login_splash(
    provider: OAuthProvider,
    message: str = "Anmeldung mit {provider}...",
    logo: str = "/img/appkit_logo.svg",
    logo_dark: str = "/img/appkit_logo_dark.svg",
) -> rx.Component:
    """Render a splash screen while handling OAuth callback."""
    return mn.center(
        mn.card(
            mn.stack(
                themed_logo(
                    light=logo,
                    dark=logo_dark,
                    w="180px",
                    style={"margin_left": "0px", "object_fit": "contain"},
                ),
                mn.group(
                    mn.text(message.format(provider=provider)),
                    rx.spinner(),
                    gap="lg",
                ),
            ),
            padding="lg",
            radius="md",
            with_border=True,
            w=400,
        ),
        h="100vh",
    )


def login_form(logo: str, logo_dark: str, margin_left: str = "0px") -> rx.Component:
    return mn.center(
        mn.card(
            mn.stack(
                mn.group(
                    themed_logo(
                        light=logo,
                        dark=logo_dark,
                        h=60,
                        w="auto",
                        style={"marginLeft": margin_left, "objectFit": "contain"},
                    ),
                    align="center",
                    justify="flex-start",
                    mb="xs",
                ),
                rx.form(
                    mn.stack(
                        rx.cond(
                            LoginState.error_message,
                            mn.alert(
                                LoginState.error_message,
                                title="Fehler",
                                color="red",
                                icon=rx.icon("triangle_alert"),
                            ),
                        ),
                        mn.text_input(
                            name="username",
                            left_section=rx.icon("user", size=17),
                            placeholder="Deine E-Mail-Adresse",
                            auto_focus=True,
                            required=True,
                            size="md",
                        ),
                        mn.password_input(
                            name="password",
                            left_section=rx.icon("lock", size=17),
                            placeholder="Dein Passwort",
                            required=True,
                            size="md",
                        ),
                        mn.button(
                            "Anmelden",
                            type="submit",
                            size="md",
                            full_width=True,
                            mt="xs",
                            loading=LoginState.is_loading,
                        ),
                        mn.group(
                            rx.link(
                                mn.text(
                                    "Passwort vergessen?",
                                    size="sm",
                                    c="blue",
                                ),
                                href="/password-reset",
                            ),
                            justify="flex-end",
                            w="100%",
                        ),
                        gap="xs",
                    ),
                    on_submit=LoginState.login_with_password,
                    class_name="w-full",
                ),
                mn.divider(label="oder", label_position="center"),
                mn.stack(
                    _oauth_button(
                        OAuthProvider.GITHUB,
                        "Mit Github anmelden",
                        "/icons/GitHub_light.svg",
                        LoginState.enable_github_oauth,
                        icon_dark="/icons/GitHub_dark.svg",
                    ),
                    _oauth_button(
                        OAuthProvider.AZURE,
                        "Mit Microsoft anmelden",
                        "/icons/microsoft.svg",
                        LoginState.enable_azure_oauth,
                    ),
                    gap="xs",
                ),
                mn.group(
                    rx.color_mode.button(style={"opacity": "0.8", "scale": "0.95"}),
                    justify="flex-end",
                ),
                gap="lg",
            ),
            padding="lg",
            radius="md",
            with_border=True,
            w=400,  # min-w-[26em] approx 400px
        ),
    )
