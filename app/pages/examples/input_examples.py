"""Consolidated Input Examples.

Demonstrates usage of various Mantine input components:
- TextInput / Input (Text)
- Textarea
- NumberInput
- JsonInput
- TagsInput
"""

from __future__ import annotations

import contextlib
import json
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any

import reflex as rx

import appkit_mantine as mn
from appkit_user.authentication.templates import navbar_layout

from app.components.examples import example_box
from app.components.navbar import app_navbar

MIN_CRITERIA_FOR_FAIR = 3
MIN_CRITERIA_FOR_GOOD = 4


class InputExamplesState(rx.State):
    """Consolidated state for all input examples."""

    # --- Text / General Input ---
    text_value: str = ""
    text_error: str = ""

    def set_text_value(self, val: str) -> None:
        """Set text value."""
        self.text_value = val

    # --- Number Input ---
    age: int = 18
    price: float = 9.99
    percent: float = 0.5

    def set_age(self, val: float | str) -> None:
        """Set age."""
        if val == "":
            self.age = 0
            return
        with contextlib.suppress(ValueError):
            self.age = int(float(val))

    def set_price(self, val: float | str) -> None:
        """Set price."""
        if val == "":
            self.price = 0.0
            return
        with contextlib.suppress(ValueError):
            self.price = float(val)

    def set_percent(self, val: float | str) -> None:
        """Set percent."""
        if val == "":
            self.percent = 0.0
            return
        with contextlib.suppress(ValueError):
            self.percent = float(val)

    # --- Textarea ---
    bio: str = ""
    comment: str = ""

    def set_bio(self, val: str) -> None:
        """Set bio."""
        self.bio = val

    def set_comment(self, val: str) -> None:
        """Set comment."""
        self.comment = val

    # --- JSON Input ---
    json_value: str = ""
    json_error: str = ""

    def set_json_value(self, val: str) -> None:
        """Set JSON value."""
        self.json_value = val

    def validate_json(self, val: str) -> None:
        """Validate JSON on blur."""
        if not val:
            self.json_error = ""
            return
        try:
            json.loads(val)
            self.json_error = ""
        except json.JSONDecodeError as e:
            self.json_error = f"Invalid JSON: {e}"

    # --- Tags Input ---
    tags_basic: list[str] = ["React", "Reflex"]
    tags_controlled: list[str] = ["Python"]

    def set_tags_basic(self, val: list[str]) -> None:
        """Set basic tags."""
        self.tags_basic = val

    def set_tags_controlled(self, val: list[str]) -> None:
        """Set controlled tags."""
        self.tags_controlled = val

    # --- Date Input ---
    selected_date: str = ""
    appointment_date: str = ""
    booking_date: str = ""
    event_date: str = ""
    birth_date: str = ""
    birth_date_error: str = ""

    # Date Range Form
    start_date: str = ""
    end_date: str = ""
    start_date_error: str = ""
    end_date_error: str = ""

    def set_selected_date(self, value: str) -> None:
        """Set the selected date."""
        self.selected_date = value

    def set_appointment_date(self, value: str) -> None:
        """Set the appointment date."""
        self.appointment_date = value

    def set_booking_date(self, value: str) -> None:
        """Set the booking date."""
        self.booking_date = value

    def set_event_date(self, value: str) -> None:
        """Set the event date."""
        self.event_date = value

    def set_birth_date(self, value: str) -> None:
        """Set the birth date."""
        self.birth_date = value

    async def validate_birth_date(self) -> AsyncGenerator[Any, Any]:
        """Validate birth date is within acceptable age range."""
        if not self.birth_date:
            self.birth_date_error = "Birth date is required"
            yield
            return

        try:
            # Parse the date
            birth = datetime.fromisoformat(self.birth_date)
            today = datetime.now(tz=UTC)

            # Calculate age (18-120)
            age = (
                today.year
                - birth.year
                - ((today.month, today.day) < (birth.month, birth.day))
            )
            min_age = 18
            max_age = 120

            if age < min_age:
                self.birth_date_error = f"You must be at least {min_age} years old"
            elif age > max_age:
                self.birth_date_error = "Please enter a valid birth date"
            else:
                self.birth_date_error = ""

        except (ValueError, AttributeError):
            self.birth_date_error = "Invalid date format"

        yield

    def set_start_date(self, value: str) -> None:
        """Set the start date."""
        self.start_date = value

    def set_end_date(self, value: str) -> None:
        """Set the end date."""
        self.end_date = value

    async def validate_dates(self) -> AsyncGenerator[Any, Any]:
        """Validate that start date is before end date."""
        self.start_date_error = ""
        self.end_date_error = ""

        max_booking_days = 365

        if not self.start_date:
            self.start_date_error = "Start date is required"
            yield
            return

        if not self.end_date:
            self.end_date_error = "End date is required"
            yield
            return

        try:
            start = datetime.fromisoformat(self.start_date)
            end = datetime.fromisoformat(self.end_date)

            if start > end:
                self.end_date_error = "End date must be after start date"
            elif (end - start).days > max_booking_days:
                self.end_date_error = "Date range cannot exceed one year"

        except (ValueError, AttributeError):
            self.start_date_error = "Invalid date format"
            self.end_date_error = "Invalid date format"

        yield

    async def submit_date_form(self) -> AsyncGenerator[Any, Any]:
        """Handle form submission."""
        # Call validate_dates() as async generator
        async for _ in self.validate_dates():
            pass

        if not self.start_date_error and not self.end_date_error:
            yield rx.toast.success(
                f"Booking confirmed from {self.start_date} to {self.end_date}",
                position="top-right",
            )
        else:
            yield rx.toast.error(
                "Please fix the errors before submitting",
                position="top-right",
            )

    # --- Password Input ---
    password_basic_value: str = ""
    controlled_password: str = ""
    show_password: bool = False

    sync_password_1: str = ""
    sync_password_2: str = ""
    sync_visible: bool = False

    error_password: str = ""
    error_message: str = ""

    # Use disabled value directly in component if constant, or here
    disabled_password_value: str = "DisabledPassword123"  # noqa: S105

    strength_password: str = ""
    strength_label: str = ""
    strength_color: str = "red"
    strength_value: int = 0

    form_password: str = ""
    form_confirm: str = ""
    form_error: str = ""
    form_submitted: bool = False

    def set_password_basic_value(self, value: str) -> None:
        self.password_basic_value = value

    def set_show_password(self, visible: bool) -> None:
        self.show_password = visible

    def set_controlled_password(self, value: str) -> None:
        self.controlled_password = value

    def set_sync_visible(self, visible: bool) -> None:
        self.sync_visible = visible

    def set_sync_password_1(self, value: str) -> None:
        self.sync_password_1 = value

    def set_sync_password_2(self, value: str) -> None:
        self.sync_password_2 = value

    def set_error_password(self, value: str) -> None:
        self.error_password = value
        min_len = 8
        if len(value) > 0 and len(value) < min_len:
            self.error_message = f"Password must be at least {min_len} characters"
        else:
            self.error_message = ""

    def set_strength_password(self, value: str) -> None:
        self.strength_password = value
        # Strength logic (simplified from original for brevity/cleanliness)
        length = len(value)
        has_upper = any(c.isupper() for c in value)
        has_lower = any(c.islower() for c in value)
        has_digit = any(c.isdigit() for c in value)
        has_special = any(not c.isalnum() for c in value)
        criteria_met = sum([has_upper, has_lower, has_digit, has_special])

        weak_len = 6
        min_len = 8

        if length == 0:
            self.strength_value = 0
            self.strength_label = ""
            self.strength_color = "red"
        elif length < weak_len:
            self.strength_value = 20
            self.strength_label = "Too short"
            self.strength_color = "red"
        elif length < min_len:
            self.strength_value = 40
            self.strength_label = "Weak"
            self.strength_color = "orange"
        elif criteria_met < MIN_CRITERIA_FOR_FAIR:
            self.strength_value = 60
            self.strength_label = "Fair"
            self.strength_color = "yellow"
        elif criteria_met < MIN_CRITERIA_FOR_GOOD:
            self.strength_value = 80
            self.strength_label = "Good"
            self.strength_color = "blue"
        else:
            self.strength_value = 100
            self.strength_label = "Strong"
            self.strength_color = "green"

    def set_form_password(self, value: str) -> None:
        self.form_password = value
        self._validate_password_form()

    def set_form_confirm(self, value: str) -> None:
        self.form_confirm = value
        self._validate_password_form()

    def _validate_password_form(self) -> None:
        min_len = 8
        if len(self.form_password) > 0 and len(self.form_password) < min_len:
            self.form_error = f"Password must be at least {min_len} characters"
        elif len(self.form_confirm) > 0 and self.form_password != self.form_confirm:
            self.form_error = "Passwords do not match"
        else:
            self.form_error = ""

    def submit_password_form(self) -> None:
        self._validate_password_form()
        if not self.form_error and self.form_password:
            self.form_submitted = True

    # --- Slider & Switch ---
    slider_value: int = 50
    range_slider_value: list[int] = [20, 80]
    switch_checked: bool = False

    def set_slider_value(self, val: int) -> None:
        self.slider_value = val

    def set_range_slider_value(self, val: list[int]) -> None:
        self.range_slider_value = val

    def set_switch_checked(self, val: bool) -> None:
        self.switch_checked = val


def text_input_content() -> rx.Component:
    """Content for Text Input tab."""
    return mn.stack(
        mn.simple_grid(
            example_box(
                "Basic usage",
                mn.stack(
                    mn.text_input(label="Simple input", placeholder="Your name"),
                    mn.text_input(
                        label="With description",
                        description="Enter your full name",
                        placeholder="John Doe",
                    ),
                    mn.text_input(
                        label="With error",
                        placeholder="Invalid email",
                        error="Invalid email address",
                        default_value="hello@",
                    ),
                    gap="md",
                ),
            ),
            example_box(
                "With sections",
                mn.stack(
                    mn.text_input(
                        label="Left section",
                        left_section=rx.icon("at-sign", size=16),
                        placeholder="Your email",
                    ),
                    mn.text_input(
                        label="Right section",
                        right_section=rx.icon("info", size=16),
                        placeholder="More info",
                    ),
                ),
            ),
            example_box(
                "Controlled State",
                mn.stack(
                    mn.text_input(
                        label="Bind to State",
                        value=InputExamplesState.text_value,
                        on_change=InputExamplesState.set_text_value,
                    ),
                    mn.text(
                        f"Current value: {InputExamplesState.text_value}",
                        size="sm",
                        c="dimmed",
                    ),
                    gap="md",
                ),
            ),
            cols=2,
            spacing="md",
            w="100%",
        ),
        w="100%",
    )


def textarea_content() -> rx.Component:
    """Content for Textarea tab."""
    return mn.stack(
        mn.simple_grid(
            example_box(
                "Basic Textarea",
                mn.stack(
                    mn.textarea(
                        label="Comment",
                        placeholder="Type your comment...",
                        autosize=True,
                        min_rows=2,
                        max_rows=4,
                    ),
                    mn.textarea(
                        label="No resize",
                        placeholder="Cannot resize this",
                        resize="none",
                    ),
                    gap="md",
                ),
            ),
            example_box(
                "Uncontrolled (on_blur)",
                mn.stack(
                    mn.textarea(
                        label="Bio",
                        description="Updates state on blur",
                        placeholder="Tell us about yourself",
                        default_value=InputExamplesState.bio,
                        on_blur=InputExamplesState.set_bio,
                    ),
                    mn.text(
                        f"Stored: {InputExamplesState.bio}",
                        size="sm",
                        c="dimmed",
                    ),
                    gap="md",
                ),
            ),
            cols=2,
            spacing="md",
            w="100%",
        ),
        w="100%",
    )


def number_input_content() -> rx.Component:
    """Content for Number Input tab."""
    return mn.stack(
        mn.simple_grid(
            example_box(
                "Basic Number Usage",
                mn.stack(
                    mn.number_input(
                        label="Age",
                        description="Min 0, max 120",
                        min=0,
                        max=120,
                        default_value=18,
                    ),
                    mn.number_input(
                        label="Step",
                        description="Step of 5",
                        step=5,
                        default_value=10,
                    ),
                    gap="md",
                ),
            ),
            example_box(
                "Formatting",
                mn.stack(
                    mn.number_input(
                        label="Price",
                        prefix="$",
                        decimal_scale=2,
                        fixed_decimal_scale=True,
                        default_value=19.99,
                    ),
                    mn.number_input(
                        label="Percentage",
                        suffix="%",
                        default_value=50,
                    ),
                    gap="md",
                ),
            ),
            example_box(
                "Bound to State",
                mn.stack(
                    mn.number_input(
                        label="Price (State)",
                        value=InputExamplesState.price,
                        on_change=InputExamplesState.set_price,
                        prefix="€",
                        decimal_scale=2,
                    ),
                    mn.text(
                        f"State value: {InputExamplesState.price}",
                        size="sm",
                        c="dimmed",
                    ),
                    gap="md",
                ),
            ),
            cols=2,
            spacing="md",
            w="100%",
        ),
        w="100%",
    )


def json_input_content() -> rx.Component:
    """Content for JSON Input tab."""
    return mn.stack(
        mn.simple_grid(
            example_box(
                "JSON Validation",
                mn.stack(
                    mn.json_input(
                        label="Config JSON",
                        placeholder='{"key": "value"}',
                        validation_error=InputExamplesState.json_error,
                        format_on_blur=True,
                        autosize=True,
                        min_rows=4,
                        on_change=InputExamplesState.set_json_value,
                        on_blur=InputExamplesState.validate_json,
                    ),
                    mn.text(
                        "Typing invalid JSON will show error on blur.",
                        size="xs",
                        c="dimmed",
                    ),
                    gap="md",
                ),
            ),
            cols=1,
            spacing="md",
            w="100%",
        ),
        w="100%",
    )


def tags_input_content() -> rx.Component:
    """Content for Tags Input tab."""
    return mn.stack(
        mn.simple_grid(
            example_box(
                "Basic Tags",
                mn.stack(
                    mn.tags_input(
                        label="Frameworks",
                        placeholder="Add frameworks",
                        default_value=["React", "Vue", "Reflex"],
                    ),
                    mn.tags_input(
                        label="Max 3 tags",
                        placeholder="Pick 3",
                        max_tags=3,
                    ),
                    gap="md",
                ),
            ),
            example_box(
                "Controlled Tags",
                mn.stack(
                    mn.tags_input(
                        label="Controlled",
                        value=InputExamplesState.tags_controlled,
                        on_change=InputExamplesState.set_tags_controlled,
                    ),
                    mn.text(
                        f"Tags: {InputExamplesState.tags_controlled}",
                        size="sm",
                        c="dimmed",
                    ),
                    gap="md",
                ),
            ),
            example_box(
                "Suggestions",
                mn.stack(
                    mn.tags_input(
                        label="With data",
                        data=["Apple", "Banana", "Cherry", "Date"],
                        placeholder="Pick a fruit",
                    ),
                    mn.tags_input(
                        label="Only allow from list",
                        data=["Red", "Green", "Blue"],
                        placeholder="Pick a color",
                        allow_new=False,
                    ),
                    gap="md",
                ),
            ),
            cols=2,
            spacing="md",
            w="100%",
        ),
        w="100%",
    )


def password_input_content() -> rx.Component:
    """Content for Password Input tab."""
    return mn.stack(
        mn.simple_grid(
            example_box(
                "Basic Usage",
                mn.stack(
                    mn.password_input(
                        label="Password",
                        description="Min 8 chars",
                        placeholder="Enter password",
                        on_change=InputExamplesState.set_password_basic_value,
                    ),
                    mn.text(
                        f"Value: {InputExamplesState.password_basic_value}",
                        size="sm",
                        c="dimmed",
                    ),
                    gap="md",
                ),
            ),
            example_box(
                "Controlled Visibility",
                mn.stack(
                    mn.password_input(
                        label="Password",
                        visible=InputExamplesState.show_password,
                        on_visibility_change=InputExamplesState.set_show_password,
                        on_change=InputExamplesState.set_controlled_password,
                    ),
                    rx.switch(
                        checked=InputExamplesState.show_password,
                        on_change=InputExamplesState.set_show_password,
                    ),
                    mn.text("Toggle switch to show password", size="xs", c="dimmed"),
                    gap="md",
                ),
            ),
            example_box(
                "Synchronized",
                mn.stack(
                    mn.password_input(
                        label="Password",
                        visible=InputExamplesState.sync_visible,
                        on_visibility_change=InputExamplesState.set_sync_visible,
                        on_change=InputExamplesState.set_sync_password_1,
                    ),
                    mn.password_input(
                        label="Confirm",
                        visible=InputExamplesState.sync_visible,
                        on_visibility_change=InputExamplesState.set_sync_visible,
                        on_change=InputExamplesState.set_sync_password_2,
                    ),
                    gap="md",
                ),
            ),
            example_box(
                "Error State",
                mn.stack(
                    mn.password_input(
                        label="Password",
                        error=InputExamplesState.error_message,
                        on_change=InputExamplesState.set_error_password,
                    ),
                    gap="md",
                ),
            ),
            example_box(
                "With Icon",
                mn.stack(
                    mn.password_input(
                        label="Password",
                        left_section=rx.icon("lock", size=16),
                        left_section_pointer_events="none",
                    ),
                    gap="md",
                ),
            ),
            example_box(
                "Strong Password",
                mn.stack(
                    mn.password_input(
                        label="New Password",
                        description="Include symbols",
                        on_change=InputExamplesState.set_strength_password,
                    ),
                    rx.cond(
                        InputExamplesState.strength_value > 0,
                        mn.stack(
                            rx.hstack(
                                mn.text("Strength:", size="xs"),
                                mn.text(
                                    InputExamplesState.strength_label,
                                    size="xs",
                                    c=InputExamplesState.strength_color,
                                ),
                            ),
                            rx.progress(
                                value=InputExamplesState.strength_value,
                                color=InputExamplesState.strength_color,
                            ),
                            gap="xs",
                        ),
                    ),
                    gap="md",
                ),
            ),
            cols=2,
            spacing="md",
            w="100%",
        ),
        w="100%",
    )


def slider_switch_content() -> rx.Component:
    """Content for Slider & Switch tab."""
    return mn.stack(
        mn.simple_grid(
            example_box(
                "Basic Slider",
                mn.stack(
                    mn.slider(
                        label=None,
                        default_value=40,
                        marks=[
                            {"value": 20, "label": "20%"},
                            {"value": 50, "label": "50%"},
                            {"value": 80, "label": "80%"},
                        ],
                    ),
                    mn.slider(
                        color="red",
                        size="xl",
                        radius="xs",
                        default_value=60,
                        label_always_on=True,
                    ),
                    gap="xl",
                ),
            ),
            example_box(
                "Controlled Slider",
                mn.stack(
                    mn.slider(
                        value=InputExamplesState.slider_value,
                        on_change=InputExamplesState.set_slider_value,
                    ),
                    mn.text(
                        f"Value: {InputExamplesState.slider_value}",
                        size="sm",
                        c="dimmed",
                    ),
                    gap="md",
                ),
            ),
            example_box(
                "Range Slider",
                mn.stack(
                    mn.range_slider(
                        min_range=10,
                        min=0,
                        max=100,
                        step=5,
                        value=InputExamplesState.range_slider_value,
                        on_change=InputExamplesState.set_range_slider_value,
                    ),
                    mn.text(
                        f"Range: {InputExamplesState.range_slider_value}",
                        size="sm",
                        c="dimmed",
                    ),
                    gap="md",
                ),
            ),
            example_box(
                "Switches",
                mn.stack(
                    mn.switch(
                        label="Basic switch",
                        default_checked=True,
                    ),
                    mn.switch(
                        label="Controlled switch",
                        checked=InputExamplesState.switch_checked,
                        on_change=InputExamplesState.set_switch_checked,
                    ),
                    mn.group(
                        mn.switch(
                            size="lg",
                            on_label="ON",
                            off_label="OFF",
                        ),
                        mn.switch(
                            color="red",
                            label="Red switch",
                            default_checked=True,
                        ),
                    ),
                    gap="md",
                ),
            ),
            cols=2,
            spacing="md",
            w="100%",
        ),
        w="100%",
    )


@navbar_layout(
    route="/inputs",
    title="Input Examples",
    navbar=app_navbar(),
    with_header=False,
)
def input_examples_page() -> rx.Component:
    """Consolidated input examples page."""
    return mn.container(
        mn.stack(
            mn.title("Input Components", order=1, mb="md"),
            mn.text(
                "Comprehensive guide to Mantine input components in Reflex.",
                c="dimmed",
                mb="lg",
            ),
            mn.tabs(
                mn.tabs.list(
                    mn.tabs.tab("TextInput", value="text"),
                    mn.tabs.tab("PasswordInput", value="password"),
                    mn.tabs.tab("Textarea", value="textarea"),
                    mn.tabs.tab("NumberInput", value="number"),
                    mn.tabs.tab("JsonInput", value="json"),
                    mn.tabs.tab("TagsInput", value="tags"),
                    mn.tabs.tab("Sliders & Switch", value="slider_switch"),
                ),
                mn.tabs.panel(
                    text_input_content(),
                    value="text",
                    py="md",
                ),
                mn.tabs.panel(
                    password_input_content(),
                    value="password",
                    py="md",
                ),
                mn.tabs.panel(
                    textarea_content(),
                    value="textarea",
                    py="md",
                ),
                mn.tabs.panel(
                    number_input_content(),
                    value="number",
                    py="md",
                ),
                mn.tabs.panel(
                    json_input_content(),
                    value="json",
                    py="md",
                ),
                mn.tabs.panel(
                    tags_input_content(),
                    value="tags",
                    py="md",
                ),
                mn.tabs.panel(
                    slider_switch_content(),
                    value="slider_switch",
                    py="md",
                ),
                default_value="text",
            ),
            py="12px",
            w="100%",
        ),
        size="lg",
        w="100%",
    )
