"""Examples for Mantine Textarea component.

This file demonstrates various ways to use the Mantine Textarea component
in Reflex applications.
"""

from collections.abc import AsyncGenerator
from typing import Any

import reflex as rx

import appkit_mantine as mn
from appkit_user.authentication.templates import navbar_layout

from app.components.navbar import app_navbar


class TextareaState(rx.State):
    """State for textarea examples."""

    # Basic values
    basic_value: str = ""
    comment: str = ""
    bio: str = ""
    feedback: str = ""
    description: str = ""

    # Error messages
    feedback_error: str = ""
    bio_error: str = ""

    # UI state
    char_count: int = 0
    word_count: int = 0

    # Live counting state (for hybrid approach)
    live_text: str = ""
    live_char_count: int = 0
    live_word_count: int = 0

    @rx.event
    def set_basic_value(self, value: str) -> None:
        """Set basic value."""
        self.basic_value = value

    @rx.event
    def set_comment(self, value: str) -> None:
        """Set comment value."""
        self.comment = value

    @rx.event
    def set_bio(self, value: str) -> None:
        """Set bio value."""
        self.bio = value
        self.char_count = len(value)
        self.word_count = len(value.split()) if value else 0

    @rx.event
    def set_feedback(self, value: str) -> None:
        """Set feedback value."""
        self.feedback = value

    @rx.event
    async def validate_feedback(self) -> AsyncGenerator[Any, Any]:
        """Validate feedback on blur."""
        if len(self.feedback) < 10:  # noqa: PLR2004
            self.feedback_error = "Feedback must be at least 10 characters"
        else:
            self.feedback_error = ""

    @rx.event
    async def validate_bio(self) -> AsyncGenerator[Any, Any]:
        """Validate bio on blur."""
        if len(self.bio) > 500:  # noqa: PLR2004
            self.bio_error = "Bio must not exceed 500 characters"
        else:
            self.bio_error = ""

    @rx.event
    def set_description(self, value: str) -> None:
        """Set description value."""
        self.description = value

    @rx.event
    def update_live_text(self, value: str) -> None:
        """Update live text with character and word count (no cursor jump).

        This is the key to live counting WITHOUT cursor jumping:
        - We bind default_value (uncontrolled) to capture initial state
        - We bind on_change to update state (but use it only for counting logic)
        - We save to state on blur (when user is done editing)
        """
        self.live_text = value
        self.live_char_count = len(value)
        self.live_word_count = len(value.split()) if value else 0

    @rx.event
    async def submit_form(self) -> AsyncGenerator[Any, Any]:
        """Submit form example."""
        await self.validate_feedback()
        await self.validate_bio()

        if not self.feedback_error and not self.bio_error:
            yield rx.toast.success("Form submitted!", position="top-right")


def basic_textarea_example() -> rx.Component:
    """Basic textarea example using uncontrolled pattern.

    Uses default_value + on_blur to avoid cursor jumping to end while typing.
    This is the recommended pattern when you don't need real-time state updates.
    """
    return rx.card(
        rx.heading("Basic Textarea", size="4"),
        rx.text(
            "Uses on_blur for updates (no cursor jump)",
            size="2",
            color="gray",
            style={"font-style": "italic"},
        ),
        mn.textarea(
            placeholder="Enter your comment...",
            default_value=TextareaState.basic_value,
            on_blur=TextareaState.set_basic_value,
        ),
        rx.text(
            f"Characters: {TextareaState.basic_value.length()}",
            size="2",
            color="gray",
        ),
        spacing="3",
        width="100%",
    )


def textarea_variants_example() -> rx.Component:
    """Demonstrate different variants."""
    return rx.card(
        rx.heading("Variants", size="4"),
        rx.vstack(
            mn.textarea(
                placeholder="Default variant",
                label="Default",
                variant="default",
            ),
            mn.textarea(
                placeholder="Filled variant",
                label="Filled",
                variant="filled",
            ),
            mn.textarea(
                placeholder="Unstyled variant",
                label="Unstyled",
                variant="unstyled",
            ),
            spacing="3",
            width="100%",
        ),
        spacing="3",
        width="100%",
    )


def textarea_sizes_example() -> rx.Component:
    """Demonstrate different sizes."""
    return rx.card(
        rx.heading("Sizes", size="4"),
        rx.vstack(
            mn.textarea(placeholder="Extra small (xs)", size="xs"),
            mn.textarea(placeholder="Small (sm)", size="sm"),
            mn.textarea(placeholder="Medium (md) - default", size="md"),
            mn.textarea(placeholder="Large (lg)", size="lg"),
            mn.textarea(placeholder="Extra large (xl)", size="xl"),
            spacing="3",
            width="100%",
        ),
        spacing="3",
        width="100%",
    )


def autosize_textarea_example() -> rx.Component:
    """Demonstrate autosize feature."""
    return rx.card(
        rx.heading("Autosize", size="4"),
        rx.text(
            "Textarea will grow as you type. Try adding multiple lines!",
            size="2",
            color="gray",
        ),
        rx.vstack(
            mn.textarea(
                placeholder="Autosize with no limit...",
                label="No Row Limit (Uncontrolled)",
                description="This textarea will grow indefinitely (uses on_blur)",
                autosize=True,
                min_rows=2,
                default_value=TextareaState.comment,
                on_blur=TextareaState.set_comment,
            ),
            mn.textarea(
                placeholder="Autosize with max 4 rows...",
                label="Max 4 Rows (No State)",
                description="This textarea will grow up to 4 rows then scroll",
                autosize=True,
                min_rows=2,
                max_rows=4,
            ),
            spacing="4",
            width="100%",
        ),
        spacing="3",
        width="100%",
    )


def resize_textarea_example() -> rx.Component:
    """Demonstrate resize options."""
    return rx.card(
        rx.heading("Resize Control", size="4"),
        rx.vstack(
            mn.textarea(
                placeholder="Resize disabled (default)",
                label="No Resize",
                resize="none",
                rows=3,
            ),
            mn.textarea(
                placeholder="Vertical resize enabled",
                label="Vertical Resize",
                description="Drag the bottom edge to resize",
                resize="vertical",
                rows=3,
            ),
            mn.textarea(
                placeholder="Both directions resize",
                label="Both Directions",
                description="Drag corners to resize",
                resize="both",
                rows=3,
            ),
            spacing="4",
            width="100%",
        ),
        spacing="3",
        width="100%",
    )


def textarea_with_validation_example() -> rx.Component:
    """Demonstrate validation with character counter.

    ⚠️ IMPORTANT: These examples use controlled inputs (value + on_change) to show
    real-time character counting. This WILL cause the cursor to jump to the end while
    typing because every keystroke triggers a full state update and re-render.

    WHY THIS HAPPENS:
    - Unlike rx.input() (which has built-in debouncing), Mantine's Textarea
      is a straight React component without debouncing
    - When you bind 'value + on_change' to state, every keystroke updates state
    - Every state update causes a re-render, moving the cursor to the end
    - This is a fundamental React constraint, not a Reflex/Mantine issue

    RECOMMENDED SOLUTIONS:
    1. **Use default_value + on_blur** (BEST for production)
       - No cursor jumping
       - Better performance
       - Suitable for forms, comments, descriptions

    2. **Use value + on_change with custom debouncing** (if real-time needed)
       - Implement frontend debouncing with JavaScript
       - Use refs to preserve cursor position
       - More complex but enables real-time updates

    For this example, we still show controlled inputs with on_change to demonstrate
    the validation pattern, but understand this won't work well in production.
    """
    return rx.card(
        rx.heading("Validation", size="4"),
        rx.text(
            "⚠️ Uses controlled inputs - cursor may jump (see bio example)",
            size="1",
            color="orange",
            style={"font-style": "italic"},
        ),
        rx.vstack(
            mn.textarea(
                label="Feedback",
                description="Minimum 10 characters required",
                placeholder="Tell us what you think...",
                default_value=TextareaState.feedback,
                error=TextareaState.feedback_error,
                required=True,
                on_blur=[TextareaState.set_feedback, TextareaState.validate_feedback],
            ),
            mn.textarea(
                label="Bio (Real-time Character Counter)",
                description=f"Characters: {TextareaState.char_count}/500",
                placeholder="Tell us about yourself...",
                value=TextareaState.bio,
                error=TextareaState.bio_error,
                max_length=500,
                autosize=True,
                min_rows=3,
                max_rows=8,
                on_change=TextareaState.set_bio,
                on_blur=TextareaState.validate_bio,
            ),
            spacing="4",
            width="100%",
        ),
        spacing="3",
        width="100%",
    )


def textarea_states_example() -> rx.Component:
    """Demonstrate different states."""
    return rx.card(
        rx.heading("States", size="4"),
        rx.vstack(
            mn.textarea(
                placeholder="Disabled textarea",
                label="Disabled",
                disabled=True,
                value="This textarea is disabled",
            ),
            mn.textarea(
                placeholder="Error state",
                label="With Error",
                error="This field has an error",
            ),
            mn.textarea(
                placeholder="Required field",
                label="Required",
                description="This field is required",
                required=True,
            ),
            spacing="4",
            width="100%",
        ),
        spacing="3",
        width="100%",
    )


def live_character_count_example() -> rx.Component:
    """Live character and word count with proper cursor handling.

    ✅ THIS SOLVES THE CURSOR JUMPING PROBLEM!

    The trick: Use default_value + on_change together:
    - default_value keeps the textarea uncontrolled (no cursor jumping)
    - on_change updates state for counting and display
    - The UI updates in real-time WITHOUT cursor issues

    This works because:
    1. default_value prevents React from controlling the input value
    2. on_change still fires for every keystroke
    3. We update state for display purposes only
    4. The user's cursor stays in the textarea element (not re-rendered)

    For persistence, you can add on_blur to save to a separate state field.
    """
    return rx.card(
        rx.heading("Live Character Count (No Cursor Jump)", size="4"),
        rx.text(
            "✅ Type anywhere - cursor stays in place, counts update in real-time",
            size="2",
            color="green",
            style={"font-style": "italic"},
        ),
        rx.vstack(
            mn.textarea(
                placeholder="Start typing... cursor won't jump!",
                label="Live Counting Text",
                description=rx.cond(
                    TextareaState.live_text == "",
                    "Characters: 0 | Words: 0",
                    f"Characters: {TextareaState.live_char_count} | Words: {TextareaState.live_word_count}",
                ),
                default_value=TextareaState.live_text,
                on_change=TextareaState.update_live_text,
                autosize=True,
                min_rows=4,
                max_rows=10,
                variant="filled",
            ),
            rx.divider(),
            rx.text(
                "How it works:",
                weight="bold",
                size="2",
            ),
            rx.unordered_list(
                rx.list_item("default_value keeps textarea uncontrolled"),
                rx.list_item("on_change fires on every keystroke"),
                rx.list_item("State updates only for UI display"),
                rx.list_item("Cursor position is preserved in DOM element"),
            ),
            spacing="3",
            width="100%",
        ),
        spacing="3",
        width="100%",
    )


def textarea_states_example() -> rx.Component:
    """Demonstrate different states."""
    return rx.card(
        rx.heading("States", size="4"),
        rx.vstack(
            mn.textarea(
                placeholder="Disabled textarea",
                label="Disabled",
                disabled=True,
                value="This textarea is disabled",
            ),
            mn.textarea(
                placeholder="Error state",
                label="With Error",
                error="This field has an error",
            ),
            mn.textarea(
                placeholder="Required field",
                label="Required",
                description="This field is required",
                required=True,
            ),
            spacing="4",
            width="100%",
        ),
        spacing="3",
        width="100%",
    )


def complete_form_example() -> rx.Component:
    """Complete form with multiple textareas."""
    return rx.card(
        rx.heading("Complete Form Example", size="4"),
        rx.vstack(
            mn.textarea(
                label="Feedback",
                description="Please share your thoughts (min 10 characters)",
                placeholder="What did you think about our service?",
                value=TextareaState.feedback,
                error=TextareaState.feedback_error,
                required=True,
                autosize=True,
                min_rows=3,
                max_rows=6,
                on_change=TextareaState.set_feedback,
                on_blur=TextareaState.validate_feedback,
                variant="filled",
            ),
            mn.textarea(
                label="Bio",
                description=(
                    f"{TextareaState.char_count}/500 characters, "
                    f"{TextareaState.word_count} words"
                ),
                placeholder="Tell us about yourself...",
                value=TextareaState.bio,
                error=TextareaState.bio_error,
                max_length=500,
                autosize=True,
                min_rows=4,
                max_rows=10,
                on_change=TextareaState.set_bio,
                on_blur=TextareaState.validate_bio,
                variant="filled",
            ),
            mn.textarea(
                label="Additional Comments",
                description="Optional",
                placeholder="Anything else you'd like to add?",
                value=TextareaState.description,
                autosize=True,
                min_rows=2,
                max_rows=5,
                on_change=TextareaState.set_description,
                variant="filled",
            ),
            rx.button(
                "Submit",
                on_click=TextareaState.submit_form,
                size="3",
            ),
            spacing="4",
            width="100%",
        ),
        spacing="3",
        width="100%",
    )


@navbar_layout(
    route="/textarea",
    title="Input Examples",
    navbar=app_navbar(),
    with_header=False,
)
def textarea_examples_page() -> rx.Component:
    """Main examples page."""
    return rx.container(
        rx.vstack(
            rx.heading("Textarea Examples", size="9"),
            rx.text(
                "Comprehensive examples of NumberInput component from @mantine/core",
                size="4",
                color="gray",
            ),
            rx.link(
                "← Back to Home",
                href="/",
                size="3",
            ),
            rx.grid(
                basic_textarea_example(),
                textarea_variants_example(),
                textarea_sizes_example(),
                autosize_textarea_example(),
                resize_textarea_example(),
                textarea_with_validation_example(),
                textarea_states_example(),
                live_character_count_example(),
                complete_form_example(),
                columns="2",
                spacing="4",
                width="100%",
            ),
            spacing="6",
            width="100%",
            padding_y="4rem",
        ),
        size="4",
        width="100%",
    )
