"""Overlay component examples."""

from __future__ import annotations

import reflex as rx

import appkit_mantine as mn
from appkit_user.authentication.templates import navbar_layout

from app.components.navbar import app_navbar


@navbar_layout(
    route="/overlay",
    title="Overlay Examples",
    navbar=app_navbar(),
    with_header=False,
)
def overlay_examples() -> rx.Component:
    return mn.container(
        mn.stack(
            rx.heading("Hover Card", size="8"),
            rx.text("Show content on hover", size="3", color="gray"),
            mn.card(
                mn.group(
                    mn.hover_card(
                        mn.hover_card.target(mn.button("Hover me")),
                        mn.hover_card.dropdown(
                            rx.text("Dropdown content"),
                        ),
                        shadow="md",
                    ),
                    mn.hover_card(
                        mn.hover_card.target(
                            mn.avatar(
                                radius="xl",
                                src="https://avatars.githubusercontent.com/u/10353856?s=200&v=4",
                            )
                        ),
                        mn.hover_card.dropdown(
                            mn.stack(
                                mn.group(
                                    mn.avatar(
                                        radius="xl",
                                        src="https://avatars.githubusercontent.com/u/10353856?s=200&v=4",
                                    ),
                                    rx.text("Mantine", weight="bold"),
                                ),
                                rx.text(
                                    "Mantine is a React components library",
                                    size="2",
                                ),
                            ),
                            w="280px",
                        ),
                        shadow="md",
                        open_delay=200,
                    ),
                    spacing="xl",
                    justify="center",
                ),
                with_border=True,
                shadow="sm",
                p="lg",
                r="md",
                h="200px",
                w="100%",
            ),
            w="100%",
            p="12px",
        ),
        mn.stack(
            rx.heading("Tooltip", size="8"),
            rx.text("Show info on hover", size="3", color="gray"),
            mn.card(
                mn.group(
                    mn.tooltip(
                        mn.button("Hover me", variant="outline"),
                        label="Tooltip content",
                    ),
                    mn.tooltip(
                        mn.button("Different Color", variant="outline", color="orange"),
                        label="Orange tooltip",
                        color="orange",
                        position="bottom",
                    ),
                    mn.tooltip(
                        mn.button("With Arrow", variant="outline", color="cyan"),
                        label="With arrow",
                        with_arrow=True,
                    ),
                    mn.tooltip(
                        mn.button("Multiline", variant="outline", color="grape"),
                        label=(
                            "This is a really long tooltip that will span "
                            "multiple lines because `multiline` is true"
                        ),
                        multiline=True,
                        w="200px",
                    ),
                    spacing="lg",
                    justify="center",
                ),
                with_border=True,
                shadow="sm",
                padding="lg",
                radius="md",
                h="150px",
                w="100%",
            ),
            w="100%",
            p="12px",
        ),
    )
