"""Notifications examples (Mantine 9.7)."""

from __future__ import annotations

import reflex as rx

import appkit_mantine as mn
from appkit_user.authentication.templates import navbar_layout

from app.components.examples import example_box
from app.components.navbar import app_navbar


class NotificationsExamplesState(rx.State):
    """Handlers returning the imperative notification helpers."""

    layout: str = "default"

    @rx.event
    def set_layout(self, value: str) -> None:
        self.layout = value

    @rx.event
    def show_basic(self) -> rx.event.EventSpec:
        return mn.notifications.show(
            "Your changes were saved.", title="Saved", color="teal"
        )

    @rx.event
    def show_progress(self) -> rx.event.EventSpec:
        return mn.notifications.show(
            "This closes in 5 seconds.",
            title="Auto close progress",
            auto_close=5000,
            with_auto_close_progress=True,
        )

    @rx.event
    def show_loading(self) -> rx.event.EventSpec:
        return mn.notifications.show(
            "Processing...",
            id="job",
            title="Working",
            loading=True,
            auto_close=False,
            with_close_button=False,
        )

    @rx.event
    def finish_loading(self) -> rx.event.EventSpec:
        return mn.notifications.update(
            "job",
            title="Done",
            message="The job finished.",
            color="teal",
            loading=False,
            auto_close=3000,
            with_close_button=True,
        )

    @rx.event
    def run_promise_ok(self) -> rx.event.EventSpec:
        return mn.notifications.promise(
            "new Promise((resolve) => setTimeout(resolve, 1500))",
            loading={"title": "Saving", "message": "Please wait"},
            success={"title": "Saved", "message": "Request succeeded"},
            error={"title": "Failed", "message": "Request failed"},
        )

    @rx.event
    def run_promise_fail(self) -> rx.event.EventSpec:
        return mn.notifications.promise(
            "new Promise((_, reject) => setTimeout(() => reject(new Error('x')), 1e3))",
            loading={"title": "Saving", "message": "Please wait"},
            success={"title": "Saved", "message": "Request succeeded"},
            error={"title": "Failed", "message": "Request failed"},
        )

    @rx.event
    def clean(self) -> rx.event.EventSpec:
        return mn.notifications.clean()


@navbar_layout(
    route="/examples/notifications",
    title="Notifications",
    navbar=app_navbar(),
    with_header=False,
)
def notifications_examples() -> rx.Component:
    """Notifications examples page."""
    state = NotificationsExamplesState
    return mn.container(
        mn.notifications_provider(position="top-right", limit=5, layout=state.layout),
        mn.stack(
            mn.title("Notifications", order=1, size="xl"),
            mn.text(
                "mn.notifications_provider() renders the stack; handlers trigger "
                "notifications with mn.notifications.show / update / promise.",
                size="md",
                c="dimmed",
            ),
            mn.simple_grid(
                example_box(
                    "show",
                    mn.group(
                        mn.button("Basic", on_click=state.show_basic),
                        mn.button(
                            "With auto-close progress",
                            on_click=state.show_progress,
                            variant="light",
                        ),
                    ),
                ),
                example_box(
                    "show + update",
                    mn.group(
                        mn.button("Start job", on_click=state.show_loading),
                        mn.button(
                            "Finish job",
                            on_click=state.finish_loading,
                            variant="light",
                        ),
                    ),
                ),
                example_box(
                    "promise",
                    mn.group(
                        mn.button("Resolves", on_click=state.run_promise_ok),
                        mn.button(
                            "Rejects",
                            on_click=state.run_promise_fail,
                            color="red",
                            variant="light",
                        ),
                    ),
                ),
                example_box(
                    "Layout (stacked: Mantine 9.6)",
                    mn.stack(
                        mn.segmented_control(
                            data=["default", "stacked"],
                            value=state.layout,
                            on_change=state.set_layout,
                        ),
                        mn.text(
                            "Stacked shows only the latest notification fully; "
                            "older ones peek out behind it.",
                            size="sm",
                            c="dimmed",
                        ),
                    ),
                ),
                example_box(
                    "clean",
                    mn.button("Clear all", on_click=state.clean, variant="default"),
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
