"""Date component examples."""

from __future__ import annotations

import reflex as rx

import appkit_mantine as mn
from appkit_user.authentication.templates import navbar_layout

from app.components.examples import example_box
from app.components.navbar import app_navbar


class DateExampleState(rx.State):
    """State for date examples."""

    date_value: str = ""
    date_range: list[str] = []
    datetime_value: str = ""
    time_value: str = ""

    def set_date_value(self, val: str) -> None:
        """Set date value."""
        self.date_value = val

    def set_datetime_value(self, val: str) -> None:
        """Set datetime value."""
        self.datetime_value = val

    def set_time_value(self, val: str) -> None:
        """Set time value."""
        self.time_value = val


@navbar_layout(
    route="/examples/date",
    title="Date Examples",
    description="Mantine Date Components",
    navbar=app_navbar(),
    with_header=False,
)
def date_examples_page() -> rx.Component:
    """Date examples page."""
    return mn.container(
        mn.stack(
            mn.title("Dates & Time", order=1),
            mn.text(
                "Components for capturing date and time input.",
                size="md",
                c="dimmed",
            ),
            # Inputs Section
            mn.title("Inputs", order=2, mt="lg"),
            mn.text(
                "Input components with dropdowns or modals.", size="sm", c="dimmed"
            ),
            mn.simple_grid(
                example_box(
                    "DateInput (Basic)",
                    mn.date_input(
                        label="Date Input",
                        placeholder="Pick a date",
                        value=DateExampleState.date_value,
                        on_change=DateExampleState.set_date_value,
                        clearable=True,
                    ),
                    state_value=DateExampleState.date_value,
                ),
                example_box(
                    "DatePickerInput (Popover)",
                    mn.date_picker_input(
                        label="Date Picker",
                        placeholder="Pick date",
                        clearable=True,
                    ),
                ),
                example_box(
                    "DatePickerInput (Range)",
                    mn.date_picker_input(
                        label="Date Range",
                        placeholder="Pick range",
                        type="range",
                        clearable=True,
                    ),
                ),
                example_box(
                    "DateTimePicker",
                    mn.date_time_picker(
                        label="Date & Time",
                        placeholder="Pick date and time",
                        value=DateExampleState.datetime_value,
                        on_change=DateExampleState.set_datetime_value,
                        clearable=True,
                    ),
                    state_value=DateExampleState.datetime_value,
                ),
                example_box(
                    "MonthPickerInput",
                    mn.month_picker_input(
                        label="Pick Month",
                        placeholder="Pick a month",
                    ),
                ),
                example_box(
                    "YearPickerInput",
                    mn.year_picker_input(
                        label="Pick Year",
                        placeholder="Pick a year",
                    ),
                ),
                example_box(
                    "TimeInput",
                    mn.time_input(
                        label="Time Input",
                        with_seconds=True,
                    ),
                ),
                cols=2,
                spacing="md",
            ),
            # Inline Pickers Section
            mn.title("Inline Pickers", order=2, mt="lg"),
            mn.text(
                "Calendar components rendered directly in the page.",
                size="sm",
                c="dimmed",
            ),
            mn.simple_grid(
                example_box(
                    "Calendar",
                    mn.center(mn.calendar()),
                ),
                example_box(
                    "DatePicker (Range)",
                    mn.center(
                        mn.date_picker(
                            number_of_columns=1,
                            type="range",
                        )
                    ),
                ),
                example_box(
                    "MonthPicker",
                    mn.center(mn.month_picker()),
                ),
                example_box(
                    "YearPicker",
                    mn.center(mn.year_picker()),
                ),
                example_box(
                    "TimeGrid",
                    mn.center(
                        mn.time_grid(
                            data=["09:00", "10:00", "11:00", "12:00"],
                        )
                    ),
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
