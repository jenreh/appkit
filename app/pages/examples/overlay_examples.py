"""Overlay component examples."""

from __future__ import annotations

import reflex as rx

import appkit_mantine as mn
from appkit_user.authentication.templates import navbar_layout

from app.components.examples import example_box
from app.components.navbar import app_navbar


class OverlayExamplesState(rx.State):
    dialog_opened: bool = False
    loading_visible: bool = True

    def open_dialog(self) -> None:
        self.dialog_opened = True

    def close_dialog(self) -> None:
        self.dialog_opened = False

    def toggle_loading(self) -> None:
        self.loading_visible = not self.loading_visible


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
        mn.stack(
            rx.heading("Floating Panels", size="8"),
            rx.text(
                "Popover, Dialog, overlays, and floating indicators",
                size="3",
                color="gray",
            ),
            mn.simple_grid(
                example_box(
                    "Popover",
                    mn.popover(
                        mn.popover.target(mn.button("Open popover", variant="light")),
                        mn.popover.dropdown(
                            mn.stack(
                                mn.text("Popover content", fw="bold"),
                                mn.text(
                                    "Useful for compact contextual panels.",
                                    size="sm",
                                ),
                                gap="xs",
                            )
                        ),
                        width=260,
                        shadow="md",
                        with_arrow=True,
                    ),
                ),
                example_box(
                    "Dialog",
                    mn.stack(
                        mn.button(
                            "Open dialog",
                            on_click=OverlayExamplesState.open_dialog,
                        ),
                        mn.dialog(
                            mn.stack(
                                mn.text("Dialog content", fw="bold"),
                                mn.text("Small floating panel with close button."),
                            ),
                            opened=OverlayExamplesState.dialog_opened,
                            on_close=OverlayExamplesState.close_dialog,
                            with_close_button=True,
                            within_portal=False,
                            shadow="md",
                            radius="md",
                            position={"top": 20, "right": 20},
                        ),
                    ),
                ),
                example_box(
                    "Overlay",
                    mn.box(
                        mn.image(
                            src="https://raw.githubusercontent.com/mantinedev/mantine/master/.demo/images/bg-8.png",
                            h=160,
                            radius="md",
                        ),
                        mn.overlay(color="#000", background_opacity=0.45, blur=2),
                        mn.center(
                            mn.text("Overlay label", c="white", fw="bold"),
                            pos="absolute",
                            top=0,
                            left=0,
                            right=0,
                            bottom=0,
                        ),
                        pos="relative",
                        h=160,
                    ),
                ),
                example_box(
                    "LoadingOverlay",
                    mn.box(
                        mn.loading_overlay(
                            visible=OverlayExamplesState.loading_visible,
                            label="Loading data...",
                        ),
                        mn.stack(
                            mn.text("Content below the loading overlay."),
                            mn.button(
                                "Toggle loading",
                                on_click=OverlayExamplesState.toggle_loading,
                                variant="light",
                            ),
                        ),
                        pos="relative",
                        mih=140,
                        p="md",
                    ),
                ),
                example_box(
                    "FloatingIndicator",
                    mn.box(
                        mn.group(
                            mn.button("React", id="indicator-react", variant="subtle"),
                            mn.button("Vue", variant="subtle"),
                            mn.button("Svelte", variant="subtle"),
                        ),
                        mn.floating_indicator(
                            parent=rx.Var(
                                _js_expr="document.getElementById('indicator-parent')",
                            ),
                            target=rx.Var(
                                _js_expr="document.getElementById('indicator-react')",
                            ),
                            transition_duration=150,
                        ),
                        id="indicator-parent",
                        pos="relative",
                        bg="gray.1",
                        p="sm",
                    ),
                ),
                cols=2,
                spacing="md",
            ),
            w="100%",
            p="12px",
        ),
    )
