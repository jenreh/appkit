"""EmptyState component examples (Mantine 9.4, ``@mantine/core``)."""

from __future__ import annotations

import reflex as rx

import appkit_mantine as mn
from appkit_user.authentication.templates import navbar_layout

from app.components.examples import example_box
from app.components.navbar import app_navbar


@navbar_layout(
    route="/empty-state",
    title="Empty State",
    navbar=app_navbar(),
    with_header=False,
)
def empty_state_examples() -> rx.Component:
    """Page demonstrating the Mantine EmptyState component."""
    return mn.container(
        mn.stack(
            mn.title("Empty State", order=1),
            mn.text(
                "Placeholder for no-data situations with an optional "
                "call-to-action (Mantine 9.4).",
                size="md",
                c="dimmed",
            ),
            rx.link("← Back to Home", href="/", size="3"),
            example_box(
                "Shorthand props",
                mn.empty_state(
                    icon=rx.icon("search-x", size=32),
                    title="No results found",
                    description="Try adjusting your filters or search keywords.",
                    with_indicator_background=True,
                    variant="light",
                    color="blue",
                    align="center",
                ),
            ),
            example_box(
                "With action (compound sub-components)",
                mn.empty_state(
                    mn.empty_state.indicator(rx.icon("inbox", size=32)),
                    mn.empty_state.title("Your inbox is empty"),
                    mn.empty_state.description("New messages will appear here."),
                    mn.empty_state.actions(
                        mn.button("Refresh", variant="light"),
                    ),
                    align="center",
                ),
            ),
            w="100%",
            mb="6rem",
            gap="sm",
        ),
        size="lg",
        w="100%",
    )
