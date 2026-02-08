"""Navigation component examples."""

from __future__ import annotations

import reflex as rx

import appkit_mantine as mn
from appkit_user.authentication.templates import navbar_layout

from app.components.navbar import app_navbar


@navbar_layout(
    route="/breadcrumbs",
    title="Breadcrumbs Examples",
    navbar=app_navbar(),
    with_header=False,
)
def breadcrumbs_examples() -> rx.Component:
    return rx.container(
        rx.vstack(
            rx.heading("Breadcrumbs", size="8"),
            rx.text("Show current location path", size="3", color="gray"),
            mn.card(
                mn.breadcrumbs(
                    rx.link("Home", href="#"),
                    rx.link("Mantine", href="#"),
                    rx.link("Core", href="#"),
                    rx.text("Breadcrumbs"),
                    separator="-",
                    separator_margin="md",
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


class PaginationState(rx.State):
    active_page: int = 1

    @rx.event
    def set_page(self, page: int) -> None:
        self.active_page = page


@navbar_layout(
    route="/pagination",
    title="Pagination Examples",
    navbar=app_navbar(),
    with_header=False,
)
def pagination_examples() -> rx.Component:
    return rx.container(
        rx.vstack(
            rx.heading("Pagination", size="8"),
            rx.text("Navigate through pages", size="3", color="gray"),
            mn.card(
                mn.stack(
                    rx.text(f"Active Page: {PaginationState.active_page}"),
                    mn.pagination(
                        total=20,
                        value=PaginationState.active_page,
                        on_change=PaginationState.set_page,
                        with_edges=True,
                    ),
                    mn.pagination(
                        total=10,
                        color="orange",
                        radius="xl",
                        default_value=5,
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


class StepperState(rx.State):
    active: int = 1

    @rx.event
    def next_step(self) -> None:
        self.active = min(self.active + 1, 3)

    @rx.event
    def prev_step(self) -> None:
        self.active = max(self.active - 1, 0)


@navbar_layout(
    route="/stepper",
    title="Stepper Examples",
    navbar=app_navbar(),
    with_header=False,
)
def stepper_examples() -> rx.Component:
    return rx.container(
        rx.vstack(
            rx.heading("Stepper", size="8"),
            rx.text("Display progress through a sequence", size="3", color="gray"),
            mn.card(
                mn.stack(
                    mn.stepper(
                        mn.stepper.step(
                            label="First step",
                            description="Create an account",
                        ),
                        mn.stepper.step(
                            label="Second step",
                            description="Verify email",
                        ),
                        mn.stepper.step(
                            label="Final step",
                            description="Get full access",
                        ),
                        mn.stepper.completed(
                            rx.text(
                                "Completed, click back button to get to previous step"
                            ),
                        ),
                        active=StepperState.active,
                    ),
                    rx.hstack(
                        mn.button(
                            "Back", variant="default", on_click=StepperState.prev_step
                        ),
                        mn.button("Next step", on_click=StepperState.next_step),
                    ),
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
    route="/tabs",
    title="Tabs Examples",
    navbar=app_navbar(),
    with_header=False,
)
def tabs_examples() -> rx.Component:
    return rx.container(
        rx.vstack(
            rx.heading("Tabs", size="8"),
            rx.text("Switch between different views", size="3", color="gray"),
            mn.card(
                mn.tabs(
                    mn.tabs.list(
                        mn.tabs.tab(
                            "Gallery", value="gallery", left_section=rx.icon("image")
                        ),
                        mn.tabs.tab(
                            "Messages",
                            value="messages",
                            left_section=rx.icon("message-circle"),
                        ),
                        mn.tabs.tab(
                            "Settings",
                            value="settings",
                            left_section=rx.icon("settings"),
                        ),
                    ),
                    mn.tabs.panel("Gallery content", value="gallery", pt="xs"),
                    mn.tabs.panel("Messages content", value="messages", pt="xs"),
                    mn.tabs.panel("Settings content", value="settings", pt="xs"),
                    default_value="gallery",
                    variant="outline",
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
