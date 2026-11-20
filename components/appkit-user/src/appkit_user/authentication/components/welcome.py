"""Default welcome page content for users awaiting admin approval."""

import reflex as rx

import appkit_mantine as mn
from appkit_commons.public_path import public_path
from appkit_user.authentication.components.components import themed_logo
from appkit_user.authentication.states import LoginState, UserSession

DEFAULT_WELCOME_MESSAGE = (
    "Ihr Konto wurde angelegt. Ein Administrator muss es noch freigeben, "
    "bevor Sie die Anwendung nutzen können. Sie erhalten Zugriff, sobald "
    "die Freigabe erfolgt ist."
)


def logout_button(label: str = "Abmelden", **kwargs: object) -> rx.Component:
    """Button that ends the session, for use on a custom welcome page."""
    return mn.button(
        label,
        left_section=rx.icon("log-out", size=16),
        on_click=LoginState.logout,
        **kwargs,
    )


def welcome_pending(
    message: str = DEFAULT_WELCOME_MESSAGE,
    logo: str = "/img/appkit_logo.svg",
    logo_dark: str = "/img/appkit_logo_dark.svg",
) -> rx.Component:
    """Greet a new user and explain that access awaits admin approval.

    Args:
        message: Explanation shown below the greeting.
        logo: Logo for light mode.
        logo_dark: Logo for dark mode.

    Returns:
        The welcome card, centred on the page.
    """
    name = UserSession.user.name
    return mn.center(
        mn.card(
            mn.stack(
                mn.group(
                    themed_logo(
                        light=public_path(logo),
                        dark=public_path(logo_dark),
                        h=60,
                        w="auto",
                        style={"objectFit": "contain"},
                    ),
                    align="center",
                    justify="flex-start",
                    mb="xs",
                ),
                mn.title(
                    rx.cond(name, "Willkommen, " + name + "!", "Willkommen!"),
                    order=3,
                ),
                mn.text(message, c="dimmed"),
                mn.alert(
                    "Freigabe ausstehend",
                    icon=rx.icon("hourglass", size=18),
                    color="orange",
                    variant="light",
                    radius="sm",
                ),
                mn.group(logout_button(variant="default"), justify="flex-end"),
                gap="md",
            ),
            padding="lg",
            radius="md",
            with_border=True,
            w=440,
            maw="100%",
        ),
        h="100vh",
        px="md",
    )
