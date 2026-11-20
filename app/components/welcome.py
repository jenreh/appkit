"""App-specific welcome page for users awaiting admin approval."""

import reflex as rx

import appkit_mantine as mn
from appkit_commons.public_path import public_path
from appkit_user.authentication.components import logout_button, themed_logo
from appkit_user.authentication.states import UserSession


def _step(icon: str, text: str) -> rx.Component:
    return mn.group(
        mn.theme_icon(rx.icon(icon, size=16), variant="light", radius="xl"),
        mn.text(text, size="sm"),
        gap="sm",
        wrap="nowrap",
    )


def app_welcome() -> rx.Component:
    """Welcome card shown to new users until an admin grants access."""
    name = UserSession.user.name  # ty: ignore[missing-union-attribute]
    return mn.card(
        mn.stack(
            # In a group, like the login form: a direct stack child is
            # stretched to the card width and the logo scales up with it.
            mn.group(
                themed_logo(
                    light=public_path("/img/appkit_logo.svg"),
                    dark=public_path("/img/appkit_logo_dark.svg"),
                    h=60,
                    w="auto",
                    style={"objectFit": "contain"},
                ),
                align="center",
                justify="flex-start",
                mb="xs",
            ),
            mn.title(
                rx.cond(
                    name,
                    "Willkommen bei AppKit, " + name + "!",
                    "Willkommen bei AppKit!",
                ),
                order=3,
            ),
            mn.text(
                "Schön, dass Sie da sind. Ihr Konto ist angelegt, "
                "der Zugriff wird gerade geprüft.",
                c="dimmed",
            ),
            _step("user-check", "Ein Administrator gibt Ihr Konto frei."),
            _step("log-in", "Danach melden Sie sich einfach erneut an."),
            mn.group(logout_button(variant="default"), justify="flex-end"),
            gap="md",
        ),
        padding="lg",
        radius="md",
        with_border=True,
        w=460,
        maw="100%",
    )
