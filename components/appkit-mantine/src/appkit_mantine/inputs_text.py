"""Mantine text-entry inputs: TextInput, PasswordInput, Textarea, JsonInput,
MaskInput, and PinInput."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal

from reflex.event import EventHandler
from reflex.vars.base import Var

from appkit_mantine.base import MantineInputComponentBase

IMASK_VERSION: str = "7.6.1"


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


class PasswordInput(MantineInputComponentBase):
    """Mantine PasswordInput component with visibility toggle.

    Based on: https://mantine.dev/core/password-input/

    Inherits common input props from MantineInputComponentBase.
    See `mantine_password_input()` function for detailed documentation and examples.
    """

    tag = "PasswordInput"

    # Password visibility control
    visible: Var[bool] = None
    """Control password visibility state (controlled component)."""

    default_visible: Var[bool] = None
    """Default visibility state (uncontrolled component)."""

    # Visibility toggle customization
    visibility_toggle_icon: Var[Any] = None
    """Custom icon component for the visibility toggle button."""

    visibility_toggle_button_props: Var[dict] = None
    """Props to pass to the visibility toggle button."""

    visibility_toggle_focusable: Var[bool] = None
    """Whether the visibility toggle button is focusable with keyboard.

    False by default: the button is excluded from the tab order
    (tabindex="-1"). Set True to include it (tabindex="0").
    """

    # Event handlers (password-specific)
    on_visibility_change: EventHandler[lambda visible: [visible]] = None
    """Called when visibility toggle is clicked (receives boolean)."""


class MaskInput(MantineInputComponentBase):
    """Mantine MaskInput component for formatted text entry.

    Provides standard input props and supports mask pattern for formatted text.
    Based on: https://mantine.dev/core/mask-input/

    IMPORTANT: For reliable behavior in Reflex, use this as an UNCONTROLLED component!
    - DO NOT use the 'value' prop for active typing (causes cursor jumping or blocking)
    - Use 'on_change' to capture formatted values as the user types
    - Use 'default_value' for initial static values only

    Example:
        ```python
        import reflex as rx
        from appkit_mantine import masked_input


        class State(rx.State):
            phone: str = ""

            def handle_phone(self, value: str) -> None:
                self.phone = value


        masked_input(
            mask="(999) 999-9999",
            placeholder="(___) ___-____",
            label="Your phone",
            default_value="+1 (555) 123-4567",
            on_change=State.handle_phone,
        )
        ```
    """

    tag = "MaskInput"
    alias = "MantineMaskInput"

    # Extend base _rename_props with MaskInput-specific camelCase conversions

    # ========================================================================
    # MaskInput Props
    # ========================================================================

    mask: Var[str | list[Any]] = None
    """Mask pattern definition (e.g., '(999) 999-9999')."""

    modify: Var[Any] = None
    """Function to change the mask dynamically based on the current input value."""

    tokens: Var[dict[str, Any]] = None
    """Dictionary mapping pattern characters to RegExp/tokens."""

    transform: Var[Any] = None
    """Function to convert characters before validation."""

    slot_char: Var[str] = None
    """Character for the placeholder slot (default: '_')."""

    separate: Var[bool] = None
    """Decouple raw and display values."""

    always_show_mask: Var[bool] = None
    """Show the mask even when the field is empty and unfocused."""

    show_mask_on_focus: Var[bool] = None
    """Show the mask placeholder on focus (default: True)."""

    auto_clear: Var[bool] = None
    """Clear the value on blur when the mask is incomplete."""

    on_complete: EventHandler[lambda masked_value, _raw_value: [masked_value]] = None
    """Called with the masked value once all required slots are filled."""

    @classmethod
    def get_event_triggers(cls) -> dict[str, Any]:
        """Transform events to work with Reflex state system."""

        def _on_change(value: Var) -> list[Var]:
            # Mantine MaskInput sends the string value directly, forward it as-is
            return [value]

        return {
            **super().get_event_triggers(),
            "on_change": _on_change,
        }


class JsonInput(MantineInputComponentBase):
    """Mantine JsonInput component wrapper for Reflex.

    Based on https://mantine.dev/core/json-input/

    Inherits all common input props from MantineInputComponentBase and adds
    JSON-specific features like formatting on blur, validation error, parser
    and custom pretty printing.
    """

    tag = "JsonInput"
    alias = "MantineJsonInput"

    # JSON-specific props
    format_on_blur: Var[bool] = None
    """If true, formats (pretty prints) the JSON on blur."""

    # Validation and parsing
    validation_error: Var[str] = None
    """Custom validation error message shown when JSON is invalid."""

    parser: Var[Callable[[str], Any]] = None
    """Optional parser function to parse the input string into JSON value."""

    pretty: Var[bool] = None
    """When formatting, pretty-print the JSON (multi-line) if True."""

    # Textarea-like props (rows/autosize)
    autosize: Var[bool] = None
    min_rows: Var[int] = None
    max_rows: Var[int] = None


class Textarea(MantineInputComponentBase):
    """Mantine Textarea component with autosize support.

    Based on: https://mantine.dev/core/textarea/

    Inherits common input props from MantineInputComponentBase.

    ⚠️ CURSOR JUMPING WITH CONTROLLED INPUTS:
    When using value + on_change (controlled input), the cursor will jump to the
    end while typing because:
    - Every keystroke updates the state
    - Every state update causes a re-render
    - React resets the cursor position to the end

    SOLUTION: Use default_value + on_blur instead for production code.
    This is documented in the module docstring above.

    See `mantine_textarea()` function for detailed documentation and examples.
    """

    tag = "Textarea"

    # HTML textarea attributes
    rows: Var[int] = None
    """Number of visible text lines (when not using autosize)."""

    cols: Var[int] = None
    """Visible width in characters."""

    wrap: Var[Literal["soft", "hard", "off"]] = None
    """Text wrapping behavior: soft (default), hard, or off."""

    # Autosize feature (uses react-textarea-autosize)
    autosize: Var[bool] = None
    """Enable automatic height adjustment based on content."""

    min_rows: Var[int] = None
    """Minimum number of rows when using autosize."""

    max_rows: Var[int] = None
    """Maximum number of rows when using autosize."""

    # Resize control
    resize: Var[Literal["none", "vertical", "both", "horizontal"]] = None
    """CSS resize property to control manual resizing."""

    bottom_section: Var[Any] = None
    """Content rendered inside the input border below the textarea (Mantine 9.3).

    Useful for character counters or supplementary controls.
    """

    # Mantine styles prop for targeting internal sub-components
    styles: Var[dict] = None
    """Mantine styles object for targeting internal elements (root, wrapper, input)."""


class PinInput(MantineInputComponentBase):
    """Mantine PinInput component — individual character pin/code entry.

    https://mantine.dev/core/pin-input/
    """

    tag = "PinInput"

    length: Var[int] = None
    """Number of input fields (default: 4)."""

    mask: Var[bool] = None
    """If set, inputs are rendered as password."""

    placeholder: Var[str] = None
    type: Var[Literal["number", "alphanumeric"]] = None
    input_type: Var[str] = None
    input_mode: Var[str] = None
    manage_focus: Var[bool] = None
    one_time_code: Var[bool] = None
    auto_focus: Var[bool] = None

    on_complete: EventHandler[lambda value: [value]] = None

    @classmethod
    def get_event_triggers(cls) -> dict[str, Any]:
        def _on_change(value: Var) -> list[Var]:
            return [value]

        return {
            **super().get_event_triggers(),
            "on_change": _on_change,
        }
