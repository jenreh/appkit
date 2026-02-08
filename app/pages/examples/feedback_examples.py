"""Feedback component examples."""

from __future__ import annotations

import reflex as rx

import appkit_mantine as mn
from appkit_user.authentication.templates import navbar_layout

from app.components.navbar import app_navbar


@navbar_layout(
    route="/alert",
    title="Alert Examples",
    navbar=app_navbar(),
    with_header=False,
)
def alert_examples() -> rx.Component:
    return rx.container(
        rx.vstack(
            rx.heading("Alert", size="8"),
            rx.text("Important messages/feedback", size="3", color="gray"),
            mn.card(
                mn.stack(
                    mn.alert(
                        "Application initialized successfully",
                        title="Success",
                        color="green",
                        icon=rx.icon("check"),
                        radius="md",
                    ),
                    mn.alert(
                        "Something went wrong",
                        title="Error",
                        color="red",
                        icon=rx.icon("circle-alert"),
                        variant="filled",
                        radius="md",
                    ),
                    mn.alert(
                        "Review your settings",
                        title="Warning",
                        color="orange",
                        variant="outline",
                        radius="md",
                        with_close_button=True,
                    ),
                    spacing="4",
                    width="100%",
                ),
                with_border=True,
                shadow="sm",
                padding="lg",
                radius="md",
                w="100%",
            ),
            spacing="6",
            width="100%",
            padding_y="8",
        ),
        size="3",
        width="100%",
    )


@navbar_layout(
    route="/notification",
    title="Notification Examples",
    navbar=app_navbar(),
    with_header=False,
)
def notification_examples() -> rx.Component:
    return rx.container(
        rx.vstack(
            rx.heading("Notification", size="8"),
            rx.text("Show notifications to user", size="3", color="gray"),
            mn.card(
                mn.stack(
                    mn.notification(
                        "We noticed you haven't logged in for a while",
                        title="Reminder",
                        color="blue",
                        icon=rx.icon("info"),
                    ),
                    mn.notification(
                        "Your data has been saved",
                        title="Success",
                        color="green",
                        icon=rx.icon("check"),
                        loading=True,
                    ),
                    mn.notification(
                        "Failed to upload file",
                        title="Error",
                        color="red",
                        with_border=True,
                    ),
                    spacing="4",
                    width="100%",
                ),
                with_border=True,
                shadow="sm",
                padding="lg",
                radius="md",
                w="100%",
            ),
            spacing="6",
            width="100%",
            padding_y="8",
        ),
        size="3",
        width="100%",
    )


class ProgressState(rx.State):
    value: int = 50

    @rx.event
    def randomize(self) -> None:
        import random  # noqa: PLC0415

        self.value = random.randint(0, 100)  # noqa: S311


@navbar_layout(
    route="/progress",
    title="Progress Examples",
    navbar=app_navbar(),
    with_header=False,
)
def progress_examples() -> rx.Component:
    return rx.container(
        rx.vstack(
            rx.heading("Progress", size="8"),
            rx.text("Show completion status", size="3", color="gray"),
            mn.card(
                mn.stack(
                    rx.heading("Simple", size="4"),
                    mn.progress(value=ProgressState.value, size="xl", radius="xl"),
                    mn.progress(
                        value=ProgressState.value,
                        color="pink",
                        striped=True,
                        animated=True,
                    ),
                    rx.heading("Compound", size="4"),
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
                    mn.button("Randomize", on_click=ProgressState.randomize),
                    spacing="6",
                    width="100%",
                ),
                with_border=True,
                shadow="sm",
                padding="lg",
                radius="md",
                w="100%",
            ),
            spacing="6",
            width="100%",
            padding_y="8",
        ),
        size="3",
        width="100%",
    )


@navbar_layout(
    route="/skeleton",
    title="Skeleton Examples",
    navbar=app_navbar(),
    with_header=False,
)
def skeleton_examples() -> rx.Component:
    return rx.container(
        rx.vstack(
            rx.heading("Skeleton", size="8"),
            rx.text("Loading placeholders", size="3", color="gray"),
            mn.card(
                mn.stack(
                    rx.hstack(
                        mn.skeleton(height=50, circle=True),
                        mn.skeleton(height=16, radius="xl"),
                        rx.spacer(),
                        width="100%",
                        align="center",
                        spacing="4",
                    ),
                    mn.skeleton(height=8, radius="xl"),
                    mn.skeleton(height=8, radius="xl", width="70%"),
                    mn.skeleton(height=8, radius="xl", width="40%"),
                    spacing="4",
                    width="100%",
                ),
                with_border=True,
                shadow="sm",
                padding="lg",
                radius="md",
                w="100%",
            ),
            spacing="6",
            width="100%",
            padding_y="8",
        ),
        size="3",
        width="100%",
    )
