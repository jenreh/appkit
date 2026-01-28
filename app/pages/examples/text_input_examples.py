"""TextInput component examples.

Based on: https://mantine.dev/core/text-input/
"""

import reflex as rx

import appkit_mantine as mn
from appkit_user.authentication.templates import navbar_layout

from app.components.navbar import app_navbar


class TextInputExamplesState(rx.State):
    """State for TextInput examples."""

    value: str = ""

    def set_value(self, val: str) -> None:
        self.value = val


def basic_example() -> rx.Component:
    return rx.vstack(
        rx.heading("Basic Usage", size="6"),
        mn.text_input(
            label="Input label",
            description="Input description",
            placeholder="Input placeholder",
        ),
        align="start",
        width="100%",
    )


def controlled_example() -> rx.Component:
    return rx.vstack(
        rx.heading("Controlled Input", size="6"),
        mn.text_input(
            label="Controlled input",
            value=TextInputExamplesState.value,
            on_change=TextInputExamplesState.set_value,
            placeholder="Type something...",
        ),
        rx.text(f"Current value: {TextInputExamplesState.value}"),
        align="start",
        width="100%",
    )


def sections_example() -> rx.Component:
    return rx.vstack(
        rx.heading("Left and Right Sections", size="6"),
        mn.text_input(
            label="With icon",
            placeholder="Your email",
            left_section=rx.icon("at-sign", size=16),
        ),
        mn.text_input(
            label="With right section",
            placeholder="Your email",
            right_section=rx.icon("info", size=16),
        ),
        align="start",
        width="100%",
    )


def error_example() -> rx.Component:
    return rx.vstack(
        rx.heading("Error State", size="6"),
        mn.text_input(
            label="Boolean error",
            placeholder="Boolean error",
            error=True,
        ),
        mn.text_input(
            label="With error message",
            placeholder="With error message",
            error="Invalid email",
        ),
        align="start",
        width="100%",
    )


def disabled_example() -> rx.Component:
    return rx.vstack(
        rx.heading("Disabled State", size="6"),
        mn.text_input(
            label="Disabled input",
            placeholder="Disabled input",
            disabled=True,
        ),
        align="start",
        width="100%",
    )


def namespace_example() -> rx.Component:
    return rx.vstack(
        rx.heading("Using Namespace (mn.form.text)", size="6"),
        mn.form.text(
            label="Namespace input",
            placeholder="Created via mn.form.text",
        ),
        align="start",
        width="100%",
    )


@navbar_layout(
    route="/text-input",
    title="TextInput Examples",
    navbar=app_navbar(),
    with_header=False,
)
def text_input_examples_page() -> rx.Component:
    return rx.container(
        rx.vstack(
            rx.heading("TextInput Examples", size="9", mb="4"),
            rx.text(
                "Capture string input from user. Supports labels, descriptions, "
                "errors, and sections.",
                mb="4",
            ),
            basic_example(),
            rx.divider(),
            controlled_example(),
            rx.divider(),
            sections_example(),
            rx.divider(),
            error_example(),
            rx.divider(),
            disabled_example(),
            rx.divider(),
            namespace_example(),
            spacing="6",
            align="start",
            width="100%",
        ),
        size="3",
        py="8",
    )
