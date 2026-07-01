"""DataList component examples (Mantine 9.4, ``@mantine/core``)."""

from __future__ import annotations

import reflex as rx

import appkit_mantine as mn
from appkit_user.authentication.templates import navbar_layout

from app.components.examples import example_box
from app.components.navbar import app_navbar


def _items() -> list[rx.Component]:
    rows = [
        ("Name", "Jane Doe"),
        ("Email", "jane@example.com"),
        ("Role", "Administrator"),
        ("Status", "Active"),
    ]
    return [
        mn.data_list.item(
            mn.data_list.item_label(label),
            mn.data_list.item_value(value),
        )
        for label, value in rows
    ]


@navbar_layout(
    route="/data-list",
    title="Data List",
    navbar=app_navbar(),
    with_header=False,
)
def data_list_examples() -> rx.Component:
    """Page demonstrating the Mantine DataList component."""
    return mn.container(
        mn.stack(
            mn.title("Data List", order=1),
            mn.text(
                "Semantic label/value pairs rendered as dl/dt/dd (Mantine 9.4).",
                size="md",
                c="dimmed",
            ),
            rx.link("← Back to Home", href="/", size="3"),
            example_box(
                "Horizontal with dividers",
                mn.data_list(
                    *_items(),
                    orientation="horizontal",
                    with_divider=True,
                    label_width=120,
                ),
            ),
            example_box(
                "Vertical",
                mn.data_list(
                    *_items(),
                    orientation="vertical",
                    gap="md",
                ),
            ),
            w="100%",
            mb="6rem",
            gap="sm",
        ),
        size="lg",
        w="100%",
    )
