"""Examples for Mantine NavLink wrapper.

Mirrors examples from https://mantine.dev/core/nav-link/
"""

from __future__ import annotations

import reflex as rx

import appkit_mantine as mn
from appkit_user.authentication.templates import navbar_layout

from app.components.navbar import app_navbar


@navbar_layout(
    route="/nav-link",
    title="Rich Select Examples",
    navbar=app_navbar(),
    with_header=False,
)
def nav_link_examples() -> rx.Component:
    return rx.container(
        rx.color_mode.button(position="top-right"),
        rx.vstack(
            rx.heading("NavLink Examples", size="8"),
            rx.text("Examples of Mantine NavLink usage."),
            rx.link("← Back to Home", href="/"),
            # Basic NavLink (enhanced to match docs)
            rx.grid(
                mn.card(
                    mn.stack(
                        rx.heading("Basic NavLink", size="4"),
                        # With left icon
                        mn.nav_link(
                            label="With icon",
                            left_section=rx.icon("house"),
                        ),
                        mn.nav_link(
                            mn.nav_link(
                                label="First child link",
                                href="#required-for-focus",
                                left_section=rx.icon("link"),
                            ),
                            mn.nav_link(
                                label="Second child link", href="#required-for-focus"
                            ),
                            mn.nav_link(
                                label="Third child link", href="#required-for-focus"
                            ),
                            label="Nested parent link",
                            left_section=rx.icon("folder"),
                            children_offset=32,
                            href="#required-for-focus",
                        ),
                        # Disabled
                        mn.nav_link(
                            label="Disabled",
                            disabled=True,
                            left_section=rx.icon("circle-slash"),
                        ),
                        # With description + badge on the right
                        mn.nav_link(
                            label="With description",
                            description="Additional information",
                            left_section=rx.badge("3", color="red", variant="outline"),
                        ),
                        # Active variants
                        mn.nav_link(
                            label="Active subtle",
                            active=True,
                            variant="subtle",
                            right_section=rx.icon("chevron-right"),
                        ),
                        mn.nav_link(
                            label="Active light",
                            active=True,
                            right_section=rx.icon("chevron-right"),
                        ),
                        mn.nav_link(
                            label="Active filled",
                            active=True,
                            variant="filled",
                            right_section=rx.icon("chevron-right"),
                        ),
                        spacing="3",
                    ),
                    with_border=True,
                    shadow="sm",
                    padding="lg",
                    radius="md",
                    w="100%",
                ),
                # Right section and nested children
                mn.card(
                    mn.stack(
                        rx.heading("Right section & Nested links", size="4"),
                        mn.nav_link(
                            mn.nav_link(label="Documents"),
                            mn.nav_link(label="Images"),
                            label="Files",
                            right_section=rx.text("12"),
                        ),
                        spacing="3",
                    ),
                    with_border=True,
                    shadow="sm",
                    padding="lg",
                    radius="md",
                    w="100%",
                ),
                columns="2",
                spacing="4",
                width="100%",
            ),
            spacing="6",
            width="100%",
            padding_y="8",
        ),
        size="3",
        width="100%",
    )
