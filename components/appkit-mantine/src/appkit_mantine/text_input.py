from typing import Literal

from reflex.vars.base import Var

from appkit_mantine.base import MantineInputComponentBase


class TextInput(MantineInputComponentBase):
    """Mantine TextInput component.

    Capture string input from user.

    Documentation: https://mantine.dev/core/text-input/
    """

    tag = "TextInput"

    # Specific props for TextInput
    with_error_styles: Var[bool] = None
    """Determines whether the input should have red border and red text color
    when the error prop is set."""

    input_wrapper_order: Var[
        list[Literal["label", "input", "description", "error"]]
    ] = None
    """Controls order of the elements."""


text_input = TextInput.create
