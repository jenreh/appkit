"""Examples demonstrating Mantine NumberFormatter usage."""

from __future__ import annotations

import reflex as rx

import appkit_mantine as mn

from app.components.navbar import app_navbar
from app.components.templates import navbar_layout


class NumberFormatterState(rx.State):
    value: float = 1_234_567.8901

    @rx.event
    def set_value(self, v: str | float | None) -> None:
        self.value = v or ""


@navbar_layout(
    route="/examples/number-formatter",
    title="Rich Select Examples",
    navbar=app_navbar(),
    with_header=False,
)
def number_formatter_examples() -> rx.Component:
    return rx.container(
        rx.color_mode.button(position="top-right"),
        rx.vstack(
            rx.heading("NumberFormatter Examples", size="8"),
            rx.text("Basic formatters and custom parser/format examples."),
            rx.link("← Back to Home", href="/"),
            rx.grid(
                rx.card(
                    rx.vstack(
                        rx.heading("Basic formatter", size="4"),
                        mn.number_formatter(
                            value=NumberFormatterState.value,
                            prefix="$ ",
                        ),
                        rx.text("Value: ", NumberFormatterState.value),
                        spacing="3",
                    ),
                    padding="4",
                ),
                rx.card(
                    rx.vstack(
                        rx.heading("EUR formatter", size="4"),
                        mn.number_formatter(
                            value=NumberFormatterState.value,
                            suffix=" €",
                            decimal_scale=2,
                            decimal_separator=",",
                            thousand_separator=".",
                        ),
                        rx.text("Value: ", NumberFormatterState.value),
                        spacing="3",
                    ),
                    padding="4",
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
