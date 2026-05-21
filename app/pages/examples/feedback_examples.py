"""Feedback component examples."""

from __future__ import annotations

import random

import reflex as rx

import appkit_mantine as mn
from appkit_user.authentication.templates import navbar_layout

from app.components.examples import example_box
from app.components.navbar import app_navbar


class ProgressState(rx.State):
    """State for progress examples."""

    value: int = 50

    def randomize(self) -> None:
        """Set value to random int between 0 and 100."""
        self.value = random.randint(0, 100)  # noqa: S311


@navbar_layout(
    route="/feedback",
    title="Feedback Components",
    navbar=app_navbar(),
    with_header=False,
)
def feedback_examples() -> rx.Component:
    """Consolidated feedback components examples page."""
    return mn.container(
        mn.stack(
            mn.title("Feedback Components", order=1, size="xl"),
            mn.text(
                "Components for showing messages, notifications, and progress.",
                size="md",
                c="dimmed",
            ),
            # Alert examples
            mn.title("Alert", order=2, mt="lg"),
            mn.text(
                "Important messages and feedback to users.",
                size="sm",
                c="dimmed",
                mb="md",
            ),
            mn.simple_grid(
                example_box(
                    "Success",
                    mn.alert(
                        "Application initialized successfully",
                        title="Success",
                        color="green",
                        icon=rx.icon("check"),
                        radius="md",
                    ),
                ),
                example_box(
                    "Error",
                    mn.alert(
                        "Something went wrong",
                        title="Error",
                        color="red",
                        icon=rx.icon("circle-alert"),
                        variant="filled",
                        radius="md",
                    ),
                ),
                example_box(
                    "Warning",
                    mn.alert(
                        "Review your settings",
                        title="Warning",
                        color="orange",
                        variant="outline",
                        radius="md",
                        with_close_button=True,
                    ),
                ),
                cols=3,
                spacing="md",
            ),
            # Notification examples
            mn.title("Notification", order=2, mt="lg"),
            mn.text(
                "Show notifications to users for important updates.",
                size="sm",
                c="dimmed",
                mb="md",
            ),
            mn.simple_grid(
                example_box(
                    "Info Notification",
                    mn.notification(
                        "We noticed you haven't logged in for a while",
                        title="Reminder",
                        color="blue",
                        icon=rx.icon("info"),
                    ),
                ),
                example_box(
                    "Success with Loading",
                    mn.notification(
                        "Your data has been saved",
                        title="Success",
                        color="green",
                        icon=rx.icon("check"),
                        loading=True,
                    ),
                ),
                example_box(
                    "Error Notification",
                    mn.notification(
                        "Failed to upload file",
                        title="Error",
                        color="red",
                        with_border=True,
                    ),
                ),
                cols=3,
                spacing="md",
            ),
            # Progress examples
            mn.title("Progress", order=2, mt="lg"),
            mn.text(
                "Show completion status and progress bars.",
                size="sm",
                c="dimmed",
                mb="md",
            ),
            mn.stack(
                mn.title("Simple Progress", order=4),
                mn.simple_grid(
                    example_box(
                        "Basic Progress",
                        mn.progress(
                            value=ProgressState.value,
                            size="xl",
                            radius="xl",
                        ),
                    ),
                    example_box(
                        "Striped & Animated",
                        mn.progress(
                            value=ProgressState.value,
                            color="pink",
                            striped=True,
                            animated=True,
                        ),
                    ),
                    cols=2,
                    spacing="md",
                ),
                mn.title("Compound Progress", order=4, mt="md"),
                example_box(
                    "Multi-section Progress",
                    mn.stack(
                        mn.progress.root(
                            mn.progress.section(
                                mn.progress.label("Docs"),
                                value=20,
                                color="cyan",
                            ),
                            mn.progress.section(
                                mn.progress.label("Code"),
                                value=15,
                                color="orange",
                            ),
                            mn.progress.section(
                                mn.progress.label("Tests"),
                                value=30,
                                color="grape",
                            ),
                            size="xl",
                            radius="xl",
                        ),
                        mn.button(
                            "Randomize Value",
                            on_click=ProgressState.randomize,
                            size="sm",
                            mt="md",
                        ),
                        spacing="md",
                        width="100%",
                    ),
                ),
                spacing="md",
            ),
            # Loader examples
            mn.title("Loader", order=2, mt="lg"),
            mn.text(
                "Animated loading indicators.",
                size="sm",
                c="dimmed",
                mb="md",
            ),
            mn.simple_grid(
                example_box(
                    "Oval (default)",
                    mn.loader(type="oval", color="blue"),
                ),
                example_box(
                    "Bars",
                    mn.loader(type="bars", color="teal"),
                ),
                example_box(
                    "Dots",
                    mn.loader(type="dots", color="violet"),
                ),
                cols=3,
                spacing="md",
            ),
            # Ring Progress examples
            mn.title("Ring Progress", order=2, mt="lg"),
            mn.text(
                "Circular progress rings.",
                size="sm",
                c="dimmed",
                mb="md",
            ),
            mn.simple_grid(
                example_box(
                    "Single Section",
                    mn.ring_progress(
                        sections=[{"value": 65, "color": "blue"}],
                        label=mn.center(mn.text("65%", fw="bold", ta="center")),
                    ),
                ),
                example_box(
                    "Multi-Section",
                    mn.ring_progress(
                        sections=[
                            {
                                "value": 40,
                                "color": "blue",
                                "tooltip": "Documents - 40%",
                            },
                            {"value": 25, "color": "orange", "tooltip": "Images - 25%"},
                            {"value": 15, "color": "teal", "tooltip": "Code - 15%"},
                        ],
                        round_caps=True,
                        size=120,
                    ),
                ),
                cols=2,
                spacing="md",
            ),
            # Semi-circle Progress
            mn.title("Semi-Circle Progress", order=2, mt="lg"),
            mn.text(
                "Half-circle progress indicator.",
                size="sm",
                c="dimmed",
                mb="md",
            ),
            mn.simple_grid(
                example_box(
                    "Basic",
                    mn.semi_circle_progress(
                        value=ProgressState.value,
                        filled_segment_color="blue",
                        size=200,
                        label=mn.text(
                            f"{ProgressState.value}%",
                            ta="center",
                            fw="bold",
                            fz="xl",
                        ),
                        label_position="center",
                    ),
                ),
                example_box(
                    "With Button",
                    mn.stack(
                        mn.semi_circle_progress(
                            value=ProgressState.value,
                            filled_segment_color="teal",
                            size=150,
                        ),
                        mn.button(
                            "Randomize",
                            on_click=ProgressState.randomize,
                            size="sm",
                        ),
                        align="center",
                        gap="sm",
                    ),
                ),
                cols=2,
                spacing="md",
            ),
            # Skeleton examples
            mn.title("Skeleton", order=2, mt="lg"),
            mn.text(
                "Loading placeholders for content that's being loaded.",
                size="sm",
                c="dimmed",
                mb="md",
            ),
            mn.simple_grid(
                example_box(
                    "Skeleton Loading",
                    mn.stack(
                        mn.stack(
                            mn.skeleton(height=50, circle=True),
                            mn.skeleton(height=16, radius="xl"),
                            rx.spacer(),
                            direction="row",
                            width="100%",
                            align="center",
                            spacing="md",
                        ),
                        mn.skeleton(height=8, radius="xl"),
                        mn.skeleton(height=8, radius="xl", width="70%"),
                        mn.skeleton(height=8, radius="xl", width="40%"),
                        spacing="md",
                        width="100%",
                    ),
                ),
                cols=1,
                spacing="md",
            ),
            spacing="lg",
            width="100%",
            padding_y="lg",
        ),
        size="lg",
        width="100%",
    )
