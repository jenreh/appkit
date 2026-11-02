"""Tour examples (Mantine 9.7)."""

from __future__ import annotations

import reflex as rx

import appkit_mantine as mn
from appkit_user.authentication.templates import navbar_layout

from app.components.examples import example_box
from app.components.navbar import app_navbar


class TourExamplesState(rx.State):
    """State for Tour examples."""

    guided_active: bool = False
    guided_step: int = 0
    beacon_active: bool = False

    @rx.event
    def start_guided(self) -> None:
        self.guided_step = 0
        self.guided_active = True

    @rx.event
    def set_guided_step(self, step: int) -> None:
        self.guided_step = step

    @rx.event
    def close_guided(self) -> None:
        self.guided_active = False

    @rx.event
    def start_beacon(self) -> None:
        self.beacon_active = True

    @rx.event
    def close_beacon(self) -> None:
        self.beacon_active = False


@navbar_layout(
    route="/examples/tour",
    title="Tour",
    navbar=app_navbar(),
    with_header=False,
)
def tour_examples() -> rx.Component:
    """Tour examples page."""
    return mn.container(
        mn.stack(
            mn.title("Tour", order=1, size="xl"),
            mn.text(
                "Step-by-step onboarding with a spotlight overlay. Steps point at "
                "elements via CSS selectors.",
                size="md",
                c="dimmed",
            ),
            mn.simple_grid(
                example_box(
                    "Guided tour",
                    mn.stack(
                        mn.group(
                            mn.button("First target", id="tour-target-1"),
                            mn.text_input(
                                placeholder="Second target", id="tour-target-2"
                            ),
                        ),
                        mn.button(
                            "Start guided tour",
                            on_click=TourExamplesState.start_guided,
                            variant="light",
                        ),
                    ),
                ),
                example_box(
                    "Beacon mode",
                    mn.stack(
                        mn.group(
                            mn.badge("Alpha", id="beacon-target-1", size="lg"),
                            mn.badge(
                                "Beta", id="beacon-target-2", size="lg", color="teal"
                            ),
                        ),
                        mn.button(
                            "Show beacons",
                            on_click=TourExamplesState.start_beacon,
                            variant="light",
                        ),
                    ),
                ),
                cols=2,
                spacing="md",
            ),
            mn.tour(
                mn.tour.step(
                    "Welcome! This short tour shows the main controls.",
                    title="Welcome",
                ),
                mn.tour.step(
                    "This button triggers the primary action.",
                    target="#tour-target-1",
                    title="Primary action",
                ),
                mn.tour.step(
                    "Type your input here.",
                    target="#tour-target-2",
                    title="Input",
                    position="bottom",
                ),
                active=TourExamplesState.guided_active,
                step=TourExamplesState.guided_step,
                on_step_change=TourExamplesState.set_guided_step,
                on_close=TourExamplesState.close_guided,
            ),
            mn.tour(
                mn.tour.step("First badge.", target="#beacon-target-1", title="Alpha"),
                mn.tour.step("Second badge.", target="#beacon-target-2", title="Beta"),
                mode="beacon",
                default_step=-1,
                active=TourExamplesState.beacon_active,
                on_close=TourExamplesState.close_beacon,
            ),
            spacing="md",
            w="100%",
            mb="6rem",
        ),
        size="lg",
        w="100%",
    )
