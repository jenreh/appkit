"""Examples for authenticated_page with custom layout templates."""

from __future__ import annotations

import reflex as rx

import appkit_mantine as mn
from appkit_ui.components.header import SIDEBAR_WIDTH
from appkit_user.authentication.templates import authenticated_page

from app.components.navbar import app_navbar


def _header_template(content: rx.Component) -> rx.Component:
    """App shell with a top header bar and the standard navbar."""
    return mn.app_shell(
        mn.app_shell.header(
            mn.group(
                mn.badge(
                    "authenticated_page",
                    color="blue",
                    variant="light",
                ),
                mn.text(
                    "Custom header · AppShell layout",
                    c="dimmed",
                    size="sm",
                ),
                h="100%",
                align="center",
                px="md",
                gap="sm",
            ),
            ml=SIDEBAR_WIDTH,
        ),
        mn.app_shell.navbar(app_navbar()),
        mn.app_shell.main(content),
        header={"height": 48, "breakpoint": "sm"},
        navbar={"width": SIDEBAR_WIDTH, "breakpoint": "sm"},
        padding="md",
    )


def _aside_template(content: rx.Component) -> rx.Component:
    """App shell with the standard navbar and a right-hand aside panel."""
    return mn.app_shell(
        mn.app_shell.navbar(app_navbar()),
        mn.app_shell.aside(
            mn.stack(
                mn.title("Details", order=4, mb="xs"),
                mn.divider(),
                mn.text(
                    "This aside panel is defined directly inside the template callable"
                    " — no extra config required.",
                    size="sm",
                    c="dimmed",
                ),
                p="md",
                gap="sm",
            )
        ),
        mn.app_shell.main(content),
        navbar={"width": SIDEBAR_WIDTH, "breakpoint": "sm"},
        aside={"width": 220, "breakpoint": "sm"},
        padding="md",
    )


@authenticated_page(
    route="/examples/template-header",
    title="Template: Header + Navbar",
    template=_header_template,
)
def page_template_header_example() -> rx.Component:
    return mn.stack(
        mn.title("Header + Navbar template", order=2),
        mn.text(
            "This page uses ",
            mn.code("authenticated_page"),
            " with a custom template that adds a header bar above the standard navbar.",
            size="sm",
        ),
        gap="md",
        p="xl",
    )


@authenticated_page(
    route="/examples/template-aside",
    title="Template: Navbar + Aside",
    template=_aside_template,
)
def page_template_aside_example() -> rx.Component:
    return mn.stack(
        mn.title("Navbar + Aside template", order=2),
        mn.text(
            "This page uses ",
            mn.code("authenticated_page"),
            " with a custom template that adds a right-hand aside panel"
            " alongside the navbar.",
            size="sm",
        ),
        gap="md",
        p="xl",
    )
