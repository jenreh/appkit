"""Examples demonstrating Mantine Button and ActionIcon usage in Reflex.

This page consolidates examples for Button and ActionIcon components,
demonstrating sizes, variants, loading states, and event handling.
"""

from __future__ import annotations

import reflex as rx

import appkit_mantine as mn
from appkit_user.authentication.templates import navbar_layout

from app.components.examples import example_box
from app.components.navbar import app_navbar


class ButtonExState(rx.State):
    """State for Button and ActionIcon examples."""

    button_clicks: int = 0
    icon_clicks: int = 0

    @rx.event
    def increment_button(self) -> None:
        self.button_clicks += 1

    @rx.event
    def increment_icon(self) -> None:
        self.icon_clicks += 1


@navbar_layout(
    route="/buttons",
    title="Buttons & Icons",
    navbar=app_navbar(),
    with_header=False,
)
def button_examples() -> rx.Component:
    """Page demonstrating Button and ActionIcon usage."""
    return mn.container(
        mn.stack(
            mn.title("Buttons & Action Icons", order=1),
            mn.text(
                "Showcase of Mantine Button and ActionIcon wrappers",
                size="md",
                c="gray",
            ),
            rx.link("← Back to Home", href="/", size="3"),
            # --- BUTTONS SECTION ---
            mn.title("Buttons", order=2, mt="4px"),
            mn.simple_grid(
                example_box(
                    "Basic Button",
                    mn.stack(
                        mn.button(
                            "Click me",
                            on_click=ButtonExState.increment_button,
                            aria_label="Click me",
                        ),
                        mn.text(f"Clicks: {ButtonExState.button_clicks}"),
                        gap="md",
                    ),
                ),
                example_box(
                    "Sizes & Variants",
                    mn.stack(
                        mn.group(
                            mn.button("XS", size="xs"),
                            mn.button("SM", size="sm"),
                            mn.button("MD", size="md"),
                            mn.button("LG", size="lg"),
                            mn.button("XL", size="xl"),
                            wrap="wrap",
                            spacing="3",
                        ),
                        mn.group(
                            mn.button("Filled", variant="filled", color="blue"),
                            mn.button("Outline", variant="outline"),
                            mn.button("Light", variant="light"),
                            mn.button(
                                "Gradient",
                                variant="gradient",
                                gradient={"from": "indigo", "to": "cyan", "deg": 45},
                            ),
                            wrap="wrap",
                            spacing="3",
                        ),
                        gap="md",
                    ),
                ),
                example_box(
                    "Sections & Justify",
                    mn.stack(
                        mn.group(
                            mn.button("Left Icon", left_section=rx.icon("search")),
                            mn.button(
                                "Right Icon", right_section=rx.icon("chevron-right")
                            ),
                            wrap="wrap",
                            gap="sm",
                        ),
                        mn.button(
                            "Space between",
                            left_section=rx.icon("star"),
                            right_section=rx.icon("chevron-right"),
                            justify="space-between",
                            full_width=True,
                        ),
                        gap="md",
                        w="100%",
                    ),
                ),
                example_box(
                    "Loading & Disabled",
                    mn.stack(
                        mn.group(
                            mn.button(
                                "Loading", loading=True, loader_props={"type": "dots"}
                            ),
                            mn.button("Disabled", disabled=True),
                            mn.button("Data-disabled", data_disabled=True),
                            wrap="wrap",
                            gap="sm",
                        ),
                        gap="md",
                    ),
                ),
                cols=2,
                w="100%",
            ),
            # --- ACTION ICONS SECTION ---
            mn.title("Action Icons", order=2, mt="24px"),
            mn.simple_grid(
                example_box(
                    "Basic ActionIcon",
                    mn.stack(
                        mn.action_icon(
                            rx.icon("trash"),
                            on_click=ButtonExState.increment_icon,
                            aria_label="Delete",
                        ),
                        mn.text(f"Clicks: {ButtonExState.icon_clicks}"),
                    ),
                ),
                example_box(
                    "Sizes & Variants",
                    mn.stack(
                        mn.group(
                            mn.action_icon(rx.icon("star"), size="xs"),
                            mn.action_icon(rx.icon("star"), size="sm"),
                            mn.action_icon(rx.icon("star"), size="md"),
                            mn.action_icon(rx.icon("star"), size="lg"),
                            mn.action_icon(rx.icon("star"), size="xl"),
                            wrap="wrap",
                        ),
                        mn.group(
                            mn.action_icon(
                                rx.icon("heart"), variant="filled", color="blue"
                            ),
                            mn.action_icon(
                                rx.icon("heart"), variant="light", color="red"
                            ),
                            mn.action_icon(rx.icon("heart"), variant="subtle"),
                            mn.action_icon(rx.icon("heart"), variant="outline"),
                            mn.action_icon(
                                rx.icon("heart"),
                                variant="gradient",
                                gradient={"from": "blue", "to": "grape", "deg": 90},
                            ),
                            wrap="wrap",
                        ),
                    ),
                ),
                example_box(
                    "States",
                    mn.group(
                        mn.action_icon(rx.icon("ban"), disabled=True),
                        mn.action_icon(rx.icon("check"), disabled=False, color="gray"),
                        mn.action_icon(
                            size="xl",
                            loading=True,
                            loader_props={"type": "dots"},
                            aria_label="Loading",
                        ),
                        wrap="wrap",
                        gap="md",
                    ),
                ),
                example_box(
                    "ActionIcon Group",
                    mn.action_icon.group(
                        mn.action_icon(
                            rx.icon("arrow-left"), size="md", variant="default"
                        ),
                        mn.action_icon(rx.icon("minus"), size="md", variant="default"),
                        mn.action_icon.group_section(
                            rx.text("Grp", size="1"), size="md", variant="default"
                        ),
                        mn.action_icon(
                            rx.icon("arrow-right"), size="md", variant="default"
                        ),
                        orientation="horizontal",
                    ),
                ),
                cols=2,
                spacing="md",
                w="100%",
            ),
            w="100%",
            mb="6rem",
            gap="sm",
        ),
        size="lg",
        w="100%",
    )
