"""Examples demonstrating Mantine NavigationProgress component usage.

This file shows comprehensive examples of how to use the NavigationProgress
component for top-of-page loading indicators and progress tracking.

Documentation: https://mantine.dev/x/nprogress/
Run with: reflex run
"""

import asyncio
from collections.abc import AsyncGenerator
from typing import Any

import reflex as rx

import appkit_mantine as mn

from app.components.navbar import app_navbar
from app.components.templates import navbar_layout

# ============================================================================
# State Management for Examples
# ============================================================================


class NProgressExamplesState(rx.State):
    """State for NavigationProgress examples."""

    is_loading: bool = False

    # Simulated loading states
    data_loaded: bool = False
    upload_progress: int = 0

    def start_progress(self) -> rx.event.EventSpec:
        """Start the progress bar."""
        self.is_loading = True

        # Minimal client-side script to start the mantine nprogress bar and
        # emit a short debug message. Keep strings short for linting.
        script = (
            "console.log('Starting nprogress'); "
            "window.nprogress && window.nprogress.start();"
        )

        return rx.call_script(script)

    def stop_progress(self) -> rx.event.EventSpec:
        """Stop the progress bar."""
        self.is_loading = False
        return rx.call_script("window.nprogress && window.nprogress.stop()")

    def increment_progress(self) -> rx.event.EventSpec:
        """Increment progress by default amount."""
        return rx.call_script("window.nprogress && window.nprogress.increment()")

    def decrement_progress(self) -> rx.event.EventSpec:
        """Decrement progress by default amount."""
        return rx.call_script("window.nprogress && window.nprogress.decrement()")

    def set_progress_50(self) -> rx.event.EventSpec:
        """Set progress to 50%."""
        return rx.call_script("window.nprogress && window.nprogress.set(50)")

    def set_progress_75(self) -> rx.event.EventSpec:
        """Set progress to 75%."""
        return rx.call_script("window.nprogress && window.nprogress.set(75)")

    def reset_progress(self) -> rx.event.EventSpec:
        """Reset progress to 0."""
        return rx.call_script("window.nprogress && window.nprogress.reset()")

    def complete_progress(self) -> rx.event.EventSpec:
        """Complete the progress (100%) and fade out."""
        self.is_loading = False
        return rx.call_script("window.nprogress && window.nprogress.complete()")

    @rx.event(background=True)
    async def simulate_loading(self) -> AsyncGenerator[Any, Any]:
        """Simulate a loading process with incremental progress updates."""
        # The `async with self` block is used to sync state changes.

        # --- Step 1: Start the progress bar ---
        async with self:
            # This script call is sent immediately.
            yield rx.call_script("window.nprogress && window.nprogress.start()")
        await asyncio.sleep(0.5)

        # --- Step 2: Incremental progress updates ---
        async with self:
            yield rx.call_script("window.nprogress && window.nprogress.set(0.3)")
        await asyncio.sleep(0.5)

        async with self:
            yield rx.call_script("window.nprogress && window.nprogress.set(0.6)")
        await asyncio.sleep(0.5)

        async with self:
            yield rx.call_script("window.nprogress && window.nprogress.set(0.9)")
        await asyncio.sleep(0.5)

        # --- Step 3: Finalize the state and complete the bar ---
        async with self:
            self.data_loaded = True
            self.is_loading = False
            # This final script call is also sent immediately.
            yield rx.call_script("window.nprogress && window.nprogress.complete()")

    @rx.event(background=True)
    async def simulate_upload(self) -> AsyncGenerator[Any, Any]:
        """Simulate file upload with progress tracking."""
        # Start progress
        # Start the progress bar via script and yield control to the event loop
        yield rx.call_script("window.nprogress && window.nprogress.start()")

        # Update progress incrementally
        for i in range(0, 101, 10):
            # Update state inside context manager to avoid ImmutableStateError
            async with self:
                self.upload_progress = i  # State update triggers render
                # Also notify the client to set the nprogress bar value
                yield rx.call_script(f"window.nprogress && window.nprogress.set({i})")

            # Small pause between updates
            await asyncio.sleep(0.3)

        # Complete the progress bar and yield final script call
        yield rx.call_script("window.nprogress && window.nprogress.complete()")


# ============================================================================
# Example Components
# ============================================================================


def basic_controls_example() -> rx.Component:
    """Basic progress bar controls."""
    return rx.card(
        rx.vstack(
            rx.heading("Basic Controls", size="6"),
            rx.text(
                "Control the navigation progress bar with start, stop, increment, "
                "decrement, set, reset, and complete actions.",
                size="2",
                color="gray",
            ),
            rx.flex(
                rx.button(
                    "Start",
                    on_click=NProgressExamplesState.start_progress,
                    variant="soft",
                    size="2",
                ),
                rx.button(
                    "Stop",
                    on_click=NProgressExamplesState.stop_progress,
                    variant="soft",
                    size="2",
                ),
                rx.button(
                    "Increment",
                    on_click=NProgressExamplesState.increment_progress,
                    variant="soft",
                    size="2",
                ),
                rx.button(
                    "Decrement",
                    on_click=NProgressExamplesState.decrement_progress,
                    variant="soft",
                    size="2",
                ),
                spacing="2",
                wrap="wrap",
            ),
            rx.flex(
                rx.button(
                    "Set 50%",
                    on_click=NProgressExamplesState.set_progress_50,
                    variant="soft",
                    size="2",
                ),
                rx.button(
                    "Set 75%",
                    on_click=NProgressExamplesState.set_progress_75,
                    variant="soft",
                    size="2",
                ),
                rx.button(
                    "Reset",
                    on_click=NProgressExamplesState.reset_progress,
                    variant="soft",
                    size="2",
                ),
                rx.button(
                    "Complete",
                    on_click=NProgressExamplesState.complete_progress,
                    variant="solid",
                    size="2",
                ),
                spacing="2",
                wrap="wrap",
            ),
            rx.callout(
                "Watch the progress bar at the top of the page!",
                icon="info",
                size="1",
            ),
            spacing="4",
            width="100%",
        ),
        width="100%",
    )


def simulated_loading_example() -> rx.Component:
    """Simulated loading process example."""
    return rx.card(
        rx.vstack(
            rx.heading("Simulated Loading Process", size="6"),
            rx.text(
                "Simulate a realistic loading process with incremental "
                "progress updates.",
                size="2",
                color="gray",
            ),
            rx.button(
                rx.cond(
                    NProgressExamplesState.is_loading,
                    "Loading...",
                    "Start Simulated Loading",
                ),
                on_click=NProgressExamplesState.simulate_loading,
                variant="solid",
                size="3",
                disabled=NProgressExamplesState.is_loading,
            ),
            rx.cond(
                NProgressExamplesState.data_loaded,
                rx.callout(
                    "Data loaded successfully!",
                    icon="check",
                    color="green",
                    size="1",
                ),
            ),
            spacing="4",
            width="100%",
        ),
        width="100%",
    )


def upload_simulation_example() -> rx.Component:
    """File upload simulation with progress tracking."""
    return rx.card(
        rx.vstack(
            rx.heading("Upload Progress Simulation", size="6"),
            rx.text(
                "Simulate file upload with synchronized progress bar and "
                "percentage display.",
                size="2",
                color="gray",
            ),
            rx.button(
                "Simulate Upload",
                on_click=NProgressExamplesState.simulate_upload,
                variant="solid",
                size="3",
            ),
            rx.cond(
                NProgressExamplesState.upload_progress > 0,
                rx.vstack(
                    rx.text(
                        f"Upload Progress: {NProgressExamplesState.upload_progress}%",
                        size="3",
                        weight="medium",
                    ),
                    rx.progress(
                        value=NProgressExamplesState.upload_progress,
                        max=100,
                        size="2",
                    ),
                    spacing="2",
                    width="100%",
                ),
            ),
            spacing="4",
            width="100%",
        ),
        width="100%",
    )


def custom_styles_example() -> rx.Component:
    """Example showing custom progress bar styling."""
    return rx.card(
        rx.vstack(
            rx.heading("Custom Styling", size="6"),
            rx.text(
                "The NavigationProgress component supports color, size, and "
                "other styling options.",
                size="2",
                color="gray",
            ),
            rx.code_block(
                """# Default usage
mn.navigation_progress()

# Custom color
mn.navigation_progress(color="blue")

# Custom size
mn.navigation_progress(size=8)

# Custom z-index
mn.navigation_progress(z_index=10000)

# Disable transitions
mn.navigation_progress(with_transition=False)

# Set initial progress
mn.navigation_progress(initial_progress=20)
""",
                language="python",
                size="1",
            ),
            spacing="4",
            width="100%",
        ),
        width="100%",
    )


def integration_notes_example() -> rx.Component:
    """Integration notes and best practices."""
    return rx.card(
        rx.vstack(
            rx.heading("Integration Notes", size="6"),
            rx.vstack(
                rx.text("Component Setup:", weight="bold", size="3"),
                rx.text(
                    "1. Import the component: from mantine import navigation_progress",
                    size="2",
                ),
                rx.text(
                    "2. Add it to your app root (renders at top of page)",
                    size="2",
                ),
                rx.text(
                    "3. Control via JavaScript: "
                    "rx.call_script('window.nprogress.start()')",
                    size="2",
                ),
                spacing="2",
                align="start",
            ),
            rx.divider(),
            rx.vstack(
                rx.text("Available Methods:", weight="bold", size="3"),
                rx.unordered_list(
                    rx.list_item(
                        rx.code("start()"),
                        " - Start progress (auto-increments)",
                    ),
                    rx.list_item(rx.code("stop()"), " - Stop and hide progress bar"),
                    rx.list_item(
                        rx.code("set(value)"), " - Set progress to value (0-100)"
                    ),
                    rx.list_item(
                        rx.code("increment()"), " - Increment by small amount"
                    ),
                    rx.list_item(
                        rx.code("decrement()"), " - Decrement by small amount"
                    ),
                    rx.list_item(rx.code("reset()"), " - Reset to 0"),
                    rx.list_item(
                        rx.code("complete()"),
                        " - Set to 100% and fade out",
                    ),
                    size="2",
                ),
                spacing="2",
                align="start",
            ),
            rx.divider(),
            rx.callout(
                "The nprogress object is available globally as "
                "window.nprogress after the component mounts. Use "
                "rx.call_script() to control it from Reflex state.",
                icon="lightbulb",
                size="1",
            ),
            spacing="4",
            width="100%",
        ),
        width="100%",
    )


# ============================================================================
# Main Page
# ============================================================================


@navbar_layout(
    route="/examples/nprogress",
    title="Rich Select Examples",
    navbar=app_navbar(),
    with_header=False,
)
def nprogress_examples_page() -> rx.Component:
    """Main page showcasing NavigationProgress examples."""
    return rx.container(
        # Add the NavigationProgress component at the top
        mn.navigation_progress(
            color="blue",
            size=4,
        ),
        rx.color_mode.button(position="top-right"),
        rx.vstack(
            # Page header
            rx.vstack(
                rx.heading("NavigationProgress Examples", size="9"),
                rx.text(
                    "Top-of-page progress indicator using @mantine/nprogress",
                    size="4",
                    color="gray",
                ),
                rx.link(
                    "← Back to Home",
                    href="/",
                    size="3",
                ),
                rx.divider(),
                spacing="4",
                width="100%",
            ),
            # Examples
            basic_controls_example(),
            simulated_loading_example(),
            upload_simulation_example(),
            custom_styles_example(),
            integration_notes_example(),
            spacing="6",
            width="100%",
            padding_y="8",
        ),
        size="3",
        width="100%",
    )
