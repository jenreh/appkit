"""Advanced input component examples — Color, Rating, Pin, Chip, etc."""

from __future__ import annotations

import reflex as rx

import appkit_mantine as mn
from appkit_user.authentication.templates import navbar_layout

from app.components.examples import example_box
from app.components.navbar import app_navbar


class InputsAdvancedState(rx.State):
    color_value: str = "#228be6"
    picker_value: str = "#228be6"
    hue_value: float = 180.0
    alpha_value: float = 0.5
    angle_value: float = 90.0
    rating_value: float = 3.0
    pin_value: str = ""
    chip_checked: bool = False
    chip_group_value: str = "react"
    native_select_value: str = ""
    fieldset_name: str = ""
    fieldset_email: str = ""

    def set_color(self, value: str) -> None:
        self.color_value = value

    def set_picker(self, value: str) -> None:
        self.picker_value = value

    def set_hue(self, value: float) -> None:
        self.hue_value = value

    def set_alpha(self, value: float) -> None:
        self.alpha_value = value

    def set_angle(self, value: float) -> None:
        self.angle_value = value

    def set_rating(self, value: float) -> None:
        self.rating_value = value

    def set_pin(self, value: str) -> None:
        self.pin_value = value

    def set_chip(self, checked: bool) -> None:
        self.chip_checked = checked

    def set_chip_group(self, value: str) -> None:
        self.chip_group_value = value


@navbar_layout(
    route="/inputs-advanced",
    title="Advanced Inputs",
    navbar=app_navbar(),
    with_header=False,
)
def inputs_advanced_examples() -> rx.Component:
    return mn.container(
        mn.stack(
            mn.title("Advanced Inputs", order=1, size="xl"),
            mn.text(
                "Color pickers, ratings, pin inputs, chips, and more.",
                size="md",
                c="dimmed",
            ),
            # Chip
            mn.title("Chip", order=2, mt="lg"),
            mn.simple_grid(
                example_box(
                    "Single Chip",
                    mn.chip(
                        "Active",
                        checked=InputsAdvancedState.chip_checked,
                        on_change=InputsAdvancedState.set_chip,
                        color="blue",
                    ),
                    state_value=InputsAdvancedState.chip_checked.to_string(),
                ),
                example_box(
                    "Chip Group",
                    mn.chip.group(
                        mn.group(
                            mn.chip("React", value="react"),
                            mn.chip("Vue", value="vue"),
                            mn.chip("Angular", value="angular"),
                            gap="xs",
                        ),
                        value=InputsAdvancedState.chip_group_value,
                        on_change=InputsAdvancedState.set_chip_group,
                    ),
                    state_value=InputsAdvancedState.chip_group_value,
                ),
                cols=2,
                spacing="md",
            ),
            # Rating
            mn.title("Rating", order=2, mt="lg"),
            mn.simple_grid(
                example_box(
                    "Star Rating",
                    mn.rating(
                        value=InputsAdvancedState.rating_value,
                        on_change=InputsAdvancedState.set_rating,
                    ),
                    state_value=InputsAdvancedState.rating_value.to_string(),
                ),
                example_box(
                    "Read Only Rating",
                    mn.rating(value=4.5, fractions=2, read_only=True),
                ),
                cols=2,
                spacing="md",
            ),
            # Pin Input
            mn.title("Pin Input", order=2, mt="lg"),
            mn.simple_grid(
                example_box(
                    "OTP / PIN Code",
                    mn.pin_input(
                        length=4,
                        value=InputsAdvancedState.pin_value,
                        on_change=InputsAdvancedState.set_pin,
                        placeholder="○",
                        type="number",
                    ),
                    state_value=InputsAdvancedState.pin_value,
                ),
                example_box(
                    "Masked PIN",
                    mn.pin_input(length=4, mask=True, placeholder="○"),
                ),
                cols=2,
                spacing="md",
            ),
            example_box(
                "File Input",
                mn.stack(
                    mn.file_input(placeholder="Pick file"),
                    mn.file_input(placeholder="Multiple files", multiple=True),
                ),
            ),
            # Native Select
            mn.title("Native Select", order=2, mt="lg"),
            example_box(
                "Browser Native Select",
                mn.native_select(
                    data=["React", "Vue", "Angular", "Svelte"],
                    label="Framework",
                    placeholder="Pick one",
                ),
            ),
            # Fieldset
            mn.title("Fieldset", order=2, mt="lg"),
            example_box(
                "Form Fieldset",
                mn.fieldset(
                    mn.stack(
                        mn.text_input(
                            label="Name",
                            placeholder="Enter name",
                            value=InputsAdvancedState.fieldset_name,
                            on_change=InputsAdvancedState.set_fieldset_name,
                        ),
                        mn.text_input(
                            label="Email",
                            placeholder="Enter email",
                            value=InputsAdvancedState.fieldset_email,
                            on_change=InputsAdvancedState.set_fieldset_email,
                        ),
                        gap="sm",
                    ),
                    legend="Contact Info",
                    radius="md",
                ),
            ),
            # Color Input
            mn.title("Color Input", order=2, mt="lg"),
            mn.simple_grid(
                example_box(
                    "Color Input with Picker",
                    mn.color_input(
                        label="Brand Color",
                        value=InputsAdvancedState.color_value,
                        on_change=InputsAdvancedState.set_color,
                        format="hex",
                        swatches=[
                            "#25262b",
                            "#868e96",
                            "#fa5252",
                            "#e64980",
                            "#be4bdb",
                            "#228be6",
                            "#15aabf",
                            "#12b886",
                        ],
                    ),
                    state_value=InputsAdvancedState.color_value,
                ),
                example_box(
                    "Color Picker",
                    mn.color_picker(
                        value=InputsAdvancedState.picker_value,
                        on_change=InputsAdvancedState.set_picker,
                        format="hex",
                        swatches=[
                            "#25262b",
                            "#868e96",
                            "#fa5252",
                            "#e64980",
                            "#be4bdb",
                            "#228be6",
                            "#15aabf",
                        ],
                        swatches_per_row=7,
                    ),
                    state_value=InputsAdvancedState.picker_value,
                ),
                cols=2,
                spacing="md",
            ),
            # Color Sliders
            mn.title("Color Sliders", order=2, mt="lg"),
            mn.simple_grid(
                example_box(
                    "Hue Slider",
                    mn.stack(
                        mn.hue_slider(
                            value=InputsAdvancedState.hue_value,
                            on_change=InputsAdvancedState.set_hue,
                        ),
                        mn.text(
                            f"Hue: {InputsAdvancedState.hue_value}°",
                            size="sm",
                            c="dimmed",
                        ),
                        gap="sm",
                    ),
                ),
                example_box(
                    "Alpha Slider",
                    mn.stack(
                        mn.alpha_slider(
                            value=InputsAdvancedState.alpha_value,
                            on_change=InputsAdvancedState.set_alpha,
                            color="#228be6",
                        ),
                        mn.text(
                            f"Alpha: {InputsAdvancedState.alpha_value}",
                            size="sm",
                            c="dimmed",
                        ),
                        gap="sm",
                    ),
                ),
                example_box(
                    "Angle Slider",
                    mn.stack(
                        mn.angle_slider(
                            value=InputsAdvancedState.angle_value,
                            on_change=InputsAdvancedState.set_angle,
                            with_label=True,
                        ),
                        mn.text(
                            f"Angle: {InputsAdvancedState.angle_value}°",
                            size="sm",
                            c="dimmed",
                        ),
                        gap="sm",
                    ),
                ),
                cols=3,
                spacing="md",
            ),
            gap="lg",
            w="100%",
            padding_y="lg",
        ),
        size="lg",
        w="100%",
    )
