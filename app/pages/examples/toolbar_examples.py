"""Toggle and Toolbar examples (Mantine 9.7)."""

from __future__ import annotations

import reflex as rx

import appkit_mantine as mn
from appkit_user.authentication.templates import navbar_layout

from app.components.examples import example_box
from app.components.navbar import app_navbar


class ToolbarExamplesState(rx.State):
    """State for Toggle and Toolbar examples."""

    bold: bool = False
    formatting: list[str] = ["bold"]
    alignment: str = "left"

    @rx.event
    def set_bold(self, active: bool) -> None:
        self.bold = active

    @rx.event
    def set_formatting(self, value: list[str]) -> None:
        self.formatting = value

    @rx.event
    def set_alignment(self, value: str | None) -> None:
        self.alignment = value or ""


def _icon(name: str) -> rx.Component:
    return rx.icon(name, size=16)


@navbar_layout(
    route="/examples/toolbar",
    title="Toggle & Toolbar",
    navbar=app_navbar(),
    with_header=False,
)
def toolbar_examples() -> rx.Component:
    """Toggle and Toolbar examples page."""
    return mn.container(
        mn.stack(
            mn.title("Toggle & Toolbar", order=1, size="xl"),
            mn.text(
                "Toggle is a button with an active state. Toolbar groups toggles "
                "with roving tabindex keyboard navigation.",
                size="md",
                c="dimmed",
            ),
            mn.simple_grid(
                example_box(
                    "Toggle (uncontrolled)",
                    mn.group(
                        mn.toggle(_icon("bold"), aria_label="Bold"),
                        mn.toggle(
                            _icon("italic"), default_active=True, aria_label="Italic"
                        ),
                        mn.toggle(
                            _icon("underline"), disabled=True, aria_label="Underline"
                        ),
                    ),
                ),
                example_box(
                    "Toggle (controlled)",
                    mn.group(
                        mn.toggle(
                            _icon("bold"),
                            active=ToolbarExamplesState.bold,
                            on_active_change=ToolbarExamplesState.set_bold,
                            variant="filled",
                            color="blue",
                            aria_label="Bold",
                        ),
                        mn.text(
                            rx.cond(ToolbarExamplesState.bold, "Bold on", "Bold off"),
                            size="sm",
                        ),
                    ),
                ),
                example_box(
                    "autoWidth & autoContrast",
                    mn.group(
                        mn.toggle("Save", auto_width=True),
                        mn.toggle("Active", auto_width=True, default_active=True),
                        mn.toggle(
                            _icon("bold"),
                            variant="filled",
                            color="lime.4",
                            default_active=True,
                            auto_contrast=True,
                            aria_label="Auto contrast",
                        ),
                    ),
                ),
                example_box(
                    "Toolbar with toggle groups",
                    mn.stack(
                        mn.toolbar(
                            mn.toolbar.toggle_group(
                                mn.toolbar.toggle_item(
                                    _icon("bold"), value="bold", aria_label="Bold"
                                ),
                                mn.toolbar.toggle_item(
                                    _icon("italic"), value="italic", aria_label="Italic"
                                ),
                                type="multiple",
                                value=ToolbarExamplesState.formatting,
                                on_change=ToolbarExamplesState.set_formatting,
                            ),
                            mn.toolbar.divider(),
                            mn.toolbar.toggle_group(
                                mn.toolbar.toggle_item(
                                    _icon("align-left"), value="left", aria_label="Left"
                                ),
                                mn.toolbar.toggle_item(
                                    _icon("align-center"),
                                    value="center",
                                    aria_label="Center",
                                ),
                                mn.toolbar.toggle_item(
                                    _icon("align-right"),
                                    value="right",
                                    aria_label="Right",
                                ),
                                type="single",
                                value=ToolbarExamplesState.alignment,
                                on_change=ToolbarExamplesState.set_alignment,
                            ),
                        ),
                        mn.text(
                            "Formatting: ",
                            ToolbarExamplesState.formatting.join(", "),
                            " · Alignment: ",
                            ToolbarExamplesState.alignment,
                            size="sm",
                            c="dimmed",
                        ),
                    ),
                ),
                example_box(
                    "Vertical, filled toolbar",
                    mn.toolbar(
                        mn.toolbar.toggle_group(
                            mn.toolbar.toggle_item(
                                _icon("house"), value="home", aria_label="Home"
                            ),
                            mn.toolbar.toggle_item(
                                _icon("search"), value="search", aria_label="Search"
                            ),
                            mn.toolbar.toggle_item(
                                _icon("settings"),
                                value="settings",
                                aria_label="Settings",
                            ),
                            type="single",
                            default_value="home",
                        ),
                        orientation="vertical",
                        variant="filled",
                        color="blue",
                        radius="md",
                    ),
                ),
                example_box(
                    "Stateless toggle",
                    mn.toolbar(
                        mn.toolbar.toggle(
                            _icon("star"), active=True, aria_label="Starred"
                        ),
                        mn.toolbar.toggle("Save", auto_width=True),
                        with_border=False,
                    ),
                ),
                cols=2,
                spacing="md",
            ),
            spacing="md",
            w="100%",
            mb="6rem",
        ),
        size="lg",
        w="100%",
    )
