"""Navigation component examples."""

from __future__ import annotations

import reflex as rx

import appkit_mantine as mn
from appkit_user.authentication.templates import navbar_layout

from app.components.examples import example_box
from app.components.navbar import app_navbar


class NavigationState(rx.State):
    """State for navigation examples."""

    # Pagination
    active_page: int = 1

    @rx.event
    def set_page(self, page: int) -> None:
        self.active_page = page

    # Stepper
    active_step: int = 1

    @rx.event
    def next_step(self) -> None:
        self.active_step = min(self.active_step + 1, 3)

    @rx.event
    def prev_step(self) -> None:
        self.active_step = max(self.active_step - 1, 0)


@navbar_layout(
    route="/navigation",
    title="Navigation Examples",
    navbar=app_navbar(),
    with_header=False,
)
def navigation_examples() -> rx.Component:
    """Consolidated navigation components page."""
    return mn.container(
        mn.stack(
            mn.title("Navigation", order=1),
            mn.text(
                "Components for navigating between pages or steps.",
                size="md",
                c="dimmed",
            ),
            # Breadcrumbs
            mn.title("Breadcrumbs", order=2, mt="lg"),
            mn.text("Show current location path.", size="sm", c="dimmed"),
            example_box(
                "Basic Breadcrumbs",
                mn.breadcrumbs(
                    rx.link("Home", href="#"),
                    rx.link("Mantine", href="#"),
                    rx.link("Core", href="#"),
                    rx.text("Breadcrumbs"),
                    separator="/",
                    separator_margin="sm",
                ),
            ),
            # Pagination
            mn.title("Pagination", order=2, mt="lg"),
            mn.text("Navigate through pages.", size="sm", c="dimmed"),
            mn.simple_grid(
                example_box(
                    "Controlled Pagination",
                    mn.stack(
                        rx.text(f"Active Page: {NavigationState.active_page}"),
                        mn.pagination(
                            total=20,
                            value=NavigationState.active_page,
                            on_change=NavigationState.set_page,
                            with_edges=True,
                        ),
                        gap="md",
                    ),
                ),
                example_box(
                    "Styles",
                    mn.pagination(
                        total=10,
                        color="orange",
                        radius="xl",
                        default_value=5,
                    ),
                ),
                cols=1,
                spacing="md",
            ),
            # Stepper
            mn.title("Stepper", order=2, mt="lg"),
            mn.text("Display progress through a sequence.", size="sm", c="dimmed"),
            example_box(
                "Basic Stepper",
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
                        active=NavigationState.active_step,
                    ),
                    rx.hstack(
                        mn.button(
                            "Back",
                            variant="default",
                            on_click=NavigationState.prev_step,
                        ),
                        mn.button("Next step", on_click=NavigationState.next_step),
                    ),
                    gap="md",
                ),
            ),
            # Tabs
            mn.title("Tabs", order=2, mt="lg"),
            mn.text("Switch between different views.", size="sm", c="dimmed"),
            example_box(
                "Tab Interface",
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
            ),
            spacing="md",
            w="100%",
            mb="6rem",
        ),
        size="lg",
        w="100%",
    )
