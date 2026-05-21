"""Layout component examples."""

from __future__ import annotations

import reflex as rx

import appkit_mantine as mn
from appkit_user.authentication.templates import navbar_layout

from app.components.examples import example_box
from app.components.navbar import app_navbar


class LayoutExamplesState(rx.State):
    collapse_opened: bool = False
    counter: int = 1234
    rolling_value: int = 1234

    def toggle_collapse(self) -> None:
        self.collapse_opened = not self.collapse_opened

    def increment(self) -> None:
        self.rolling_value += 1000

    def decrement(self) -> None:
        if self.rolling_value > 0:
            self.rolling_value -= 1000


OVERFLOW_ITEMS = [
    {"label": "Design"},
    {"label": "Build"},
    {"label": "Test"},
    {"label": "Ship"},
    {"label": "Observe"},
]


@navbar_layout(
    route="/layout",
    title="Layout Components",
    navbar=app_navbar(),
    with_header=False,
)
def layout_examples() -> rx.Component:
    return mn.container(
        mn.stack(
            mn.title("Layout Components", order=1, size="xl"),
            mn.text(
                "Components for structuring the page layout.",
                size="md",
                c="dimmed",
            ),
            example_box(
                "App Shell (Example Setup)",
                mn.app_shell(
                    mn.app_shell.header("Header", p="sm"),
                    mn.app_shell.navbar("Navbar", p="sm"),
                    mn.app_shell.main("Main content"),
                    header={"height": 60},
                    navbar={"width": 300, "breakpoint": "sm"},
                    padding="md",
                    h=200,
                ),
            ),
            example_box(
                "Visually Hidden",
                mn.group(
                    mn.visually_hidden("This is visually hidden for accessibility"),
                    mn.text("A visually hidden element is next to this text."),
                ),
            ),
            example_box("Portal", mn.portal(mn.text("I am in a portal"))),
            mn.title("Motion & Overflow", order=2, mt="lg"),
            mn.simple_grid(
                example_box(
                    "Collapse",
                    mn.stack(
                        mn.button(
                            "Toggle content",
                            on_click=LayoutExamplesState.toggle_collapse,
                            variant="light",
                        ),
                        mn.collapse(
                            mn.paper(
                                mn.text("Collapsed content keeps layout tidy."),
                                with_border=True,
                                p="md",
                                radius="md",
                            ),
                            expanded=LayoutExamplesState.collapse_opened,
                            transition_duration=250,
                        ),
                    ),
                ),
                example_box(
                    "Transition",
                    mn.stack(
                        mn.button(
                            "Toggle transition",
                            on_click=LayoutExamplesState.toggle_collapse,
                            variant="outline",
                        ),
                        mn.transition(
                            rx.Var(
                                "({ transitionStyles }) => "
                                "<div style={transitionStyles}>"
                                "Animated transition content"
                                "</div>",
                                _var_type=rx.Component,
                            ),
                            mounted=LayoutExamplesState.collapse_opened,
                            transition="fade",
                            duration=250,
                            keep_mounted=True,
                        ),
                    ),
                ),
                example_box(
                    "Marquee",
                    mn.marquee(
                        mn.badge("Build"),
                        mn.badge("Review", color="teal"),
                        mn.badge("Release", color="orange"),
                        duration=12,
                        gap="md",
                        pause_on_hover=True,
                        fade_edges=True,
                    ),
                ),
                example_box(
                    "Scroller",
                    mn.scroller(
                        mn.group(
                            mn.button("Overview", variant="light"),
                            mn.button("Metrics", variant="light"),
                            mn.button("Deployments", variant="light"),
                            mn.button("Incidents", variant="light"),
                            mn.button("Settings", variant="light"),
                            wrap="nowrap",
                        ),
                        scroll_amount=160,
                        control_size=28,
                    ),
                ),
                example_box(
                    "OverflowList",
                    mn.overflow_list(
                        data=OVERFLOW_ITEMS,
                        max_visible_items=3,
                        gap="xs",
                        render_item=rx.Var(
                            "(item) => <span>{item.label}</span>",
                            _var_type=rx.Component,
                        ),
                        render_overflow=rx.Var(
                            "(items) => <span>+{items.length} more</span>",
                            _var_type=rx.Component,
                        ),
                    ),
                ),
                example_box(
                    "RollingNumber",
                    mn.stack(
                        mn.rolling_number(
                            value=LayoutExamplesState.rolling_value,
                            thousand_separator=",",
                            prefix="$",
                            animation_duration=350,
                        ),
                        mn.group(
                            mn.button(
                                "-1000",
                                variant="default",
                                on_click=LayoutExamplesState.decrement,
                            ),
                            mn.button(
                                "+1000",
                                on_click=LayoutExamplesState.increment,
                            ),
                        ),
                    ),
                ),
                example_box(
                    "FloatingWindow",
                    mn.box(
                        mn.floating_window(
                            mn.paper(
                                mn.stack(
                                    mn.text("Drag handle", fw="bold"),
                                    mn.text("Floating content", size="sm", c="dimmed"),
                                    gap="xs",
                                ),
                                p="sm",
                            ),
                            enabled=True,
                            within_portal=False,
                            initial_position={"x": 24, "y": 24},
                            shadow="md",
                            radius="md",
                            with_border=True,
                        ),
                        pos="relative",
                        h=160,
                        bg="gray.0",
                        p="md",
                    ),
                ),
                cols=2,
                spacing="md",
                w="100%",
            ),
            gap="xl",
            w="100%",
            padding_y="xl",
        ),
        size="lg",
        w="100%",
    )
