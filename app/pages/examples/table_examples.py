"""Examples for Mantine Table wrapper.

Demonstrates sticky header, scroll container, and vertical variant.
"""

from __future__ import annotations

import reflex as rx

import appkit_mantine as mn

from app.components.navbar import app_navbar
from app.components.templates import navbar_layout

elements = [
    {"position": 6, "mass": 12.011, "symbol": "C", "name": "Carbon"},
    {"position": 7, "mass": 14.007, "symbol": "N", "name": "Nitrogen"},
    {"position": 39, "mass": 88.906, "symbol": "Y", "name": "Yttrium"},
    {"position": 56, "mass": 137.33, "symbol": "Ba", "name": "Barium"},
    {"position": 58, "mass": 140.12, "symbol": "Ce", "name": "Cerium"},
]


def table_header() -> rx.Component:
    return mn.table.thead(
        mn.table.tr(
            mn.table.th("Element Position"),
            mn.table.th("Name"),
            mn.table.th("Symbol"),
            mn.table.th("Atomic Mass"),
        )
    )


def table_rows() -> rx.Component:
    return rx.foreach(
        elements,
        lambda el: mn.table.tr(
            mn.table.td(el["position"]),
            mn.table.td(el["name"]),
            mn.table.td(el["symbol"]),
            mn.table.td(el["mass"]),
            key=el["name"],
        ),
    )


@navbar_layout(
    route="/examples/table",
    title="Rich Select Examples",
    navbar=app_navbar(),
    with_header=False,
)
def table_examples() -> rx.Component:
    return (
        rx.container(
            rx.color_mode.button(position="top-right"),
            rx.vstack(
                rx.heading("Table Examples", size="8"),
                rx.text(
                    "Sticky header, scroll container, vertical variant, row selection."
                ),
                rx.link("← Back to Home", href="/"),
                # Sticky header
                rx.heading("Sticky header", size="4"),
                rx.scroll_area(
                    mn.table(
                        table_header(),
                        mn.table.tbody(
                            table_rows(),
                        ),
                        sticky_header=True,
                        width="100%",
                        with_table_border=True,
                        highlight_on_hover_color=rx.color("accent"),
                    ),
                    max_height="150px",
                    width="100%",
                ),
                rx.heading("Vertical variant", size="4", margin_top="1.5em"),
                mn.table(
                    mn.table.tbody(
                        mn.table.tr(
                            mn.table.th("Name"),
                            mn.table.td("Sample Item"),
                        ),
                        mn.table.tr(
                            mn.table.th("Category"),
                            mn.table.td("Demo"),
                        ),
                        mn.table.tr(
                            mn.table.th("Price"),
                            mn.table.td("$12.00"),
                        ),
                    ),
                    striped=True,
                    striped_color=rx.color("crimson"),
                    variant="vertical",
                    layout="fixed",
                    with_table_border=True,
                    with_column_borders=True,
                    highlight_on_hover=False,
                    width="100%",
                ),
                spacing="3",
                width="100%",
            ),
            spacing="3",
            width="100%",
        ),
    )
