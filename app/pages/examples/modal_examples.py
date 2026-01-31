"""Modal component examples - comprehensive demonstrations.

This module showcases various Modal configurations and usage patterns:
- Basic modal with title
- Centered modal
- Fullscreen modal
- Custom sizes and styling
- Modal without header
- Compound components
- Multiple modals with Modal.Stack

Based on: https://mantine.dev/core/modal/
"""

from collections.abc import AsyncGenerator
from typing import Any

import reflex as rx

import appkit_mantine as mn
from appkit_user.authentication.templates import navbar_layout

from app.components.navbar import app_navbar


class ModalExamplesState(rx.State):
    """State management for modal examples."""

    # Basic modal
    basic_opened: bool = False

    # Centered modal
    centered_opened: bool = False

    # No header modal
    no_header_opened: bool = False

    # Custom size modal
    size_opened: bool = False
    current_size: str = "md"

    # Fullscreen modal
    fullscreen_opened: bool = False

    # Custom overlay modal
    overlay_opened: bool = False

    # Compound components modal
    compound_opened: bool = False

    # Stack modals
    stack_first_opened: bool = False
    stack_second_opened: bool = False
    stack_third_opened: bool = False

    # Data for demonstration
    modal_data: dict[str, str] = {}

    # Basic modal handlers
    def open_basic(self) -> None:
        """Open basic modal."""
        self.basic_opened = True

    def close_basic(self) -> None:
        """Close basic modal."""
        self.basic_opened = False

    # Centered modal handlers
    def open_centered(self) -> None:
        """Open centered modal."""
        self.centered_opened = True

    def close_centered(self) -> None:
        """Close centered modal."""
        self.centered_opened = False

    # No header modal handlers
    def open_no_header(self) -> None:
        """Open modal without header."""
        self.no_header_opened = True

    def close_no_header(self) -> None:
        """Close modal without header."""
        self.no_header_opened = False

    # Size modal handlers
    def open_with_size(self, size: str) -> None:
        """Open modal with specific size."""
        self.current_size = size
        self.size_opened = True

    def close_size(self) -> None:
        """Close size modal."""
        self.size_opened = False

    # Fullscreen modal handlers
    def open_fullscreen(self) -> None:
        """Open fullscreen modal."""
        self.fullscreen_opened = True

    def close_fullscreen(self) -> None:
        """Close fullscreen modal."""
        self.fullscreen_opened = False

    # Overlay modal handlers
    def open_overlay(self) -> None:
        """Open modal with custom overlay."""
        self.overlay_opened = True

    def close_overlay(self) -> None:
        """Close overlay modal."""
        self.overlay_opened = False

    # Compound components modal handlers
    def open_compound(self) -> None:
        """Open compound components modal."""
        self.compound_opened = True

    def close_compound(self) -> None:
        """Close compound components modal."""
        self.compound_opened = False

    # Stack modal handlers
    def open_stack_first(self) -> None:
        """Open first modal in stack."""
        self.stack_first_opened = True

    def close_stack_first(self) -> None:
        """Close first modal in stack."""
        self.stack_first_opened = False

    def open_stack_second(self) -> None:
        """Open second modal in stack."""
        self.stack_second_opened = True

    def close_stack_second(self) -> None:
        """Close second modal in stack."""
        self.stack_second_opened = False

    def open_stack_third(self) -> None:
        """Open third modal in stack."""
        self.stack_third_opened = True

    def close_stack_third(self) -> None:
        """Close third modal in stack."""
        self.stack_third_opened = False

    def close_all_stack(self) -> None:
        """Close all modals in stack."""
        self.stack_first_opened = False
        self.stack_second_opened = False
        self.stack_third_opened = False

    @rx.event
    async def on_exit_demo(self) -> AsyncGenerator[Any, Any]:
        """Demonstrate onExitTransitionEnd."""
        self.modal_data = {}
        yield rx.toast.success(
            "Data cleared after exit transition!", position="top-right"
        )


def basic_modal_example() -> rx.Component:
    """Basic modal example with title and content."""
    return rx.vstack(
        rx.heading("Basic Modal", size="6"),
        rx.text(
            "Simple modal with title, content, and close button.",
            color="gray",
        ),
        mn.modal(
            rx.vstack(
                rx.text("This is a basic modal with a title and close button."),
                rx.text(
                    "Click the close button, press Escape, or click outside to close."
                ),
                spacing="3",
            ),
            title="Authentication",
            opened=ModalExamplesState.basic_opened,
            on_close=ModalExamplesState.close_basic,
        ),
        mn.button(
            "Open Modal",
            on_click=ModalExamplesState.open_basic,
        ),
        spacing="3",
        align="start",
        width="100%",
    )


def centered_modal_example() -> rx.Component:
    """Centered modal example."""
    return rx.vstack(
        rx.heading("Centered Modal", size="6"),
        rx.text("Modal vertically centered on the screen.", color="gray"),
        mn.modal(
            rx.text("This modal is vertically centered using the centered prop."),
            title="Centered Modal",
            opened=ModalExamplesState.centered_opened,
            on_close=ModalExamplesState.close_centered,
            centered=True,
        ),
        mn.button(
            "Open Centered Modal",
            on_click=ModalExamplesState.open_centered,
        ),
        spacing="3",
        align="start",
        width="100%",
    )


def no_header_modal_example() -> rx.Component:
    """Modal without header."""
    return rx.vstack(
        rx.heading("No Header Modal", size="6"),
        rx.text("Modal without title and close button.", color="gray"),
        mn.modal(
            rx.text("Modal without header. Press Escape or click outside to close."),
            opened=ModalExamplesState.no_header_opened,
            on_close=ModalExamplesState.close_no_header,
            with_close_button=False,
        ),
        mn.button(
            "Open Without Header",
            on_click=ModalExamplesState.open_no_header,
        ),
        spacing="3",
        align="start",
        width="100%",
    )


def size_modal_example() -> rx.Component:
    """Modal with different sizes."""
    return rx.vstack(
        rx.heading("Modal Sizes", size="6"),
        rx.text("Modals with predefined and custom sizes.", color="gray"),
        mn.modal(
            rx.text(f"This modal uses size: {ModalExamplesState.current_size}"),
            title=f"Size: {ModalExamplesState.current_size}",
            opened=ModalExamplesState.size_opened,
            on_close=ModalExamplesState.close_size,
            size=ModalExamplesState.current_size,
        ),
        rx.hstack(
            mn.button(
                "xs",
                on_click=lambda: ModalExamplesState.open_with_size("xs"),
            ),
            mn.button(
                "sm",
                on_click=lambda: ModalExamplesState.open_with_size("sm"),
            ),
            mn.button(
                "md",
                on_click=lambda: ModalExamplesState.open_with_size("md"),
            ),
            mn.button(
                "lg",
                on_click=lambda: ModalExamplesState.open_with_size("lg"),
            ),
            mn.button(
                "xl",
                on_click=lambda: ModalExamplesState.open_with_size("xl"),
            ),
            mn.button(
                "70%",
                on_click=lambda: ModalExamplesState.open_with_size("70%"),
            ),
            spacing="2",
        ),
        spacing="3",
        align="start",
        width="100%",
    )


def fullscreen_modal_example() -> rx.Component:
    """Fullscreen modal example."""
    return rx.vstack(
        rx.heading("Fullscreen Modal", size="6"),
        rx.text("Modal that takes the entire screen.", color="gray"),
        mn.modal(
            rx.vstack(
                rx.text("This is a fullscreen modal."),
                rx.text("It takes up the entire screen with no border radius."),
                rx.text("Best used with fade transition."),
                spacing="3",
            ),
            title="Fullscreen Modal",
            opened=ModalExamplesState.fullscreen_opened,
            on_close=ModalExamplesState.close_fullscreen,
            full_screen=True,
            radius=0,
            transition_props={"transition": "fade", "duration": 200},
        ),
        mn.button(
            "Open Fullscreen Modal",
            on_click=ModalExamplesState.open_fullscreen,
        ),
        spacing="3",
        align="start",
        width="100%",
    )


def overlay_modal_example() -> rx.Component:
    """Modal with custom overlay."""
    return rx.vstack(
        rx.heading("Custom Overlay", size="6"),
        rx.text("Modal with customized overlay appearance.", color="gray"),
        mn.modal(
            rx.text("This modal has a custom overlay with increased opacity and blur."),
            title="Custom Overlay",
            opened=ModalExamplesState.overlay_opened,
            on_close=ModalExamplesState.close_overlay,
            overlay_props={
                "backgroundOpacity": 0.55,
                "blur": 3,
            },
        ),
        mn.button(
            "Open with Custom Overlay",
            on_click=ModalExamplesState.open_overlay,
        ),
        spacing="3",
        align="start",
        width="100%",
    )


def compound_modal_example() -> rx.Component:
    """Modal using compound components."""
    return rx.vstack(
        rx.heading("Compound Components", size="6"),
        rx.text("Full control using Modal.Root and sub-components.", color="gray"),
        mn.modal.root(
            mn.modal.overlay(),
            mn.modal.content(
                mn.modal.header(
                    mn.modal.title("Custom Modal"),
                    mn.modal.close_button(),
                ),
                mn.modal.body(
                    rx.vstack(
                        rx.text("This modal is built using compound components:"),
                        rx.text("• Modal.Root - context provider"),
                        rx.text("• Modal.Overlay - backdrop"),
                        rx.text("• Modal.Content - main container"),
                        rx.text("• Modal.Header - sticky header"),
                        rx.text("• Modal.Title - title element"),
                        rx.text("• Modal.CloseButton - close button"),
                        rx.text("• Modal.Body - content area"),
                        spacing="2",
                        align="start",
                    )
                ),
            ),
            opened=ModalExamplesState.compound_opened,
            on_close=ModalExamplesState.close_compound,
        ),
        mn.button(
            "Open Compound Modal",
            on_click=ModalExamplesState.open_compound,
        ),
        spacing="3",
        align="start",
        width="100%",
    )


def stack_modal_example() -> rx.Component:
    """Multiple modals with Modal.Stack."""
    return rx.vstack(
        rx.heading("Modal Stack", size="6"),
        rx.text(
            "Multiple modals with automatic z-index and focus management.",
            color="gray",
        ),
        mn.modal.stack(
            mn.modal(
                rx.vstack(
                    rx.text("Are you sure you want to delete this page?"),
                    rx.text("This action cannot be undone."),
                    rx.hstack(
                        mn.button(
                            "Cancel",
                            on_click=ModalExamplesState.close_all_stack,
                            variant="outline",
                        ),
                        mn.button(
                            "Delete",
                            on_click=ModalExamplesState.open_stack_second,
                            color="red",
                        ),
                        spacing="3",
                        justify="end",
                        width="100%",
                    ),
                    spacing="3",
                ),
                title="Delete Page?",
                opened=ModalExamplesState.stack_first_opened,
                on_close=ModalExamplesState.close_stack_first,
                stack_id="first",
            ),
            mn.modal(
                rx.vstack(
                    rx.text("Are you sure you want to perform this action?"),
                    rx.text("If you are sure, press the confirm button below."),
                    rx.hstack(
                        mn.button(
                            "Cancel",
                            on_click=ModalExamplesState.close_all_stack,
                            variant="outline",
                        ),
                        mn.button(
                            "Confirm",
                            on_click=ModalExamplesState.open_stack_third,
                            color="red",
                        ),
                        spacing="3",
                        justify="end",
                        width="100%",
                    ),
                    spacing="3",
                ),
                title="Confirm Action",
                opened=ModalExamplesState.stack_second_opened,
                on_close=ModalExamplesState.close_stack_second,
                stack_id="second",
            ),
            mn.modal(
                rx.vstack(
                    rx.text("Really confirm this action?"),
                    rx.text(
                        "This is your last chance to cancel. "
                        "After you press confirm, the action will be performed."
                    ),
                    rx.hstack(
                        mn.button(
                            "Cancel",
                            on_click=ModalExamplesState.close_all_stack,
                            variant="outline",
                        ),
                        mn.button(
                            "Confirm",
                            on_click=ModalExamplesState.close_all_stack,
                            color="red",
                        ),
                        spacing="3",
                        justify="end",
                        width="100%",
                    ),
                    spacing="3",
                ),
                title="Really Confirm?",
                opened=ModalExamplesState.stack_third_opened,
                on_close=ModalExamplesState.close_stack_third,
                stack_id="third",
            ),
        ),
        mn.button(
            "Open Modal Stack",
            on_click=ModalExamplesState.open_stack_first,
        ),
        spacing="3",
        align="start",
        width="100%",
    )


@navbar_layout(
    route="/modal",
    title="Modal Examples",
    navbar=app_navbar(),
    with_header=False,
)
def modal_examples() -> rx.Component:
    """Main page component with all modal examples."""
    return rx.container(
        rx.vstack(
            rx.heading("Modal Examples", size="9"),
            rx.text(
                "Comprehensive examples of Mantine Modal component usage.",
                size="4",
                color="gray",
            ),
            rx.divider(),
            basic_modal_example(),
            rx.divider(),
            centered_modal_example(),
            rx.divider(),
            no_header_modal_example(),
            rx.divider(),
            size_modal_example(),
            rx.divider(),
            fullscreen_modal_example(),
            rx.divider(),
            overlay_modal_example(),
            rx.divider(),
            compound_modal_example(),
            rx.divider(),
            stack_modal_example(),
            spacing="6",
            padding="4",
            max_width="800px",
        ),
        size="4",
    )
