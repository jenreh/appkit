from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal

import reflex as rx
from reflex.event import EventHandler
from reflex.vars.base import Var

from appkit_mantine.base import MantineInputComponentBase, MantineLayoutComponentBase
from appkit_mantine.date import DateInput

IMASK_VERSION: str = "7.6.1"


class Input(MantineInputComponentBase):
    """Mantine Input component - polymorphic base input element.

    The Input component is a polymorphic component that can be used to create
    custom inputs. It supports left and right sections for icons or controls,
    multiple variants, sizes, and full accessibility support.

    Note: In most cases, you should use TextInput or other specialized input
    components instead of using Input directly. Input is designed as a base
    for creating custom inputs.
    """

    tag = "Input"

    # Polymorphic component prop - can change the underlying element
    component: Var[str]


# ============================================================================
# Input.Wrapper Component
# ============================================================================


class InputWrapper(MantineInputComponentBase):
    """Mantine Input.Wrapper component - wraps input with label, description, and error.

    Input.Wrapper is used in all Mantine inputs under the hood to provide
    consistent layout for labels, descriptions, and error messages.

    The inputWrapperOrder prop controls the order of rendered elements:
    - label: Input label
    - input: Input element
    - description: Input description
    - error: Error message
    """

    tag = "Input.Wrapper"

    # Props
    with_asterisk: Var[bool]  # Shows asterisk without required attribute

    # Layout control - order of elements in wrapper
    input_wrapper_order: Var[list[Literal["label", "input", "description", "error"]]]

    # Container for custom input wrapping
    input_container: Var[Any]


# ============================================================================
# Input Sub-Components
# ============================================================================


class InputLabel(MantineInputComponentBase):
    """Mantine Input.Label component - label element for inputs.

    Used to create custom form layouts when Input.Wrapper doesn't meet requirements.
    """

    tag = "Input.Label"

    # Props
    html_for: Var[str]  # ID of associated input


class InputDescription(MantineInputComponentBase):
    """Mantine Input.Description component - description text for inputs.

    Used to create custom form layouts when Input.Wrapper doesn't meet requirements.
    """

    tag = "Input.Description"


class InputError(MantineInputComponentBase):
    """Mantine Input.Error component - error message for inputs.

    Used to create custom form layouts when Input.Wrapper doesn't meet requirements.
    """

    tag = "Input.Error"


class InputPlaceholder(MantineInputComponentBase):
    """Mantine Input.Placeholder component - placeholder for button-based inputs.

    Used to add placeholder text to Input components based on button elements
    or that don't support placeholder property natively.
    """

    tag = "Input.Placeholder"


class InputClearButton(MantineInputComponentBase):
    """Mantine Input.ClearButton component - clear button for inputs.

    Use to add a clear button to custom inputs. Size is automatically
    inherited from the input.
    """

    tag = "Input.ClearButton"

    # Event handlers
    on_click: EventHandler[rx.event.no_args_event_spec]


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


class NumberInput(MantineInputComponentBase):
    """Mantine NumberInput component for numeric input with controls.

    Based on: https://mantine.dev/core/number-input/

    Inherits common input props from MantineInputComponentBase.
    See `mantine_number_input()` function for detailed documentation and examples.
    """

    tag = "NumberInput"
    alias = "MantineNumberInput"

    # Prop aliasing for camelCase React props
    _rename_props = {
        **MantineInputComponentBase._rename_props,  # noqa: SLF001
        "clamp_behavior": "clampBehavior",
        "decimal_scale": "decimalScale",
        "fixed_decimal_scale": "fixedDecimalScale",
        "decimal_separator": "decimalSeparator",
        "allow_decimal": "allowDecimal",
        "allow_negative": "allowNegative",
        "thousand_separator": "thousandSeparator",
        "thousands_group_style": "thousandsGroupStyle",
        "hide_controls": "hideControls",
        "start_value": "startValue",
        "with_keyboard_events": "withKeyboardEvents",
        "allow_mouse_wheel": "allowMouseWheel",
        "allow_leading_zeros": "allowLeadingZeros",
        "allowed_decimal_separators": "allowedDecimalSeparators",
        "select_all_on_focus": "selectAllOnFocus",
        "step_hold_delay": "stepHoldDelay",
        "step_hold_interval": "stepHoldInterval",
        "trim_leading_zeroes_on_blur": "trimLeadingZeroesOnBlur",
        "value_is_numeric_string": "valueIsNumericString",
    }

    # Numeric constraints
    min: Var[int | float] = None
    """Minimum allowed value."""

    max: Var[int | float] = None
    """Maximum allowed value."""

    step: Var[int | float] = None
    """Step for increment/decrement (default: 1)."""

    clamp_behavior: Var[Literal["strict", "blur", "none"]] = None
    """Value clamping behavior: strict (clamp on input), blur (clamp on blur),
    none (no clamping)."""

    # Decimal handling
    decimal_scale: Var[int] = None
    """Maximum number of decimal places."""

    fixed_decimal_scale: Var[bool] = None
    """Pad decimals with zeros to match decimal_scale."""

    decimal_separator: Var[str] = None
    """Decimal separator character (default: ".")."""

    allowed_decimal_separators: Var[list[str]] = None
    """Characters which when pressed result in a decimal separator
    (default: ['.', ','])."""

    allow_decimal: Var[bool] = None
    """Allow decimal input (default: True)."""

    # Zero formatting
    allow_leading_zeros: Var[bool] = None
    """Determines whether leading zeros are allowed during input (default: True)."""

    trim_leading_zeroes_on_blur: Var[bool] = None
    """If set, leading zeros are removed on blur (default: True)."""

    # Number formatting
    allow_negative: Var[bool] = None
    """Allow negative numbers (default: True)."""

    prefix: Var[str] = None
    """Text prefix (e.g., "$")."""

    suffix: Var[str] = None
    """Text suffix (e.g., "%")."""

    thousand_separator: Var[str | bool] = None
    """Thousand separator character or True for locale default."""

    thousands_group_style: Var[Literal["thousand", "lakh", "wan", "none"]] = None
    """Grouping style: thousand (1,000,000), lakh (1,00,000), wan (1,0000),
    none (no grouping)."""

    value_is_numeric_string: Var[bool] = None
    """Advanced: Set to true if passing numeric strings and using formatting
    props like prefix or suffix."""

    select_all_on_focus: Var[bool] = None
    """If set, all text is selected when the input receives focus (default: False)."""

    # Controls
    hide_controls: Var[bool] = None
    """Hide increment/decrement buttons."""

    start_value: Var[int | float] = None
    """Value when empty input is focused (default: 0)."""

    step_hold_delay: Var[int] = None
    """Initial delay in milliseconds before stepping the value."""

    step_hold_interval: Var[int] = None
    """Interval in milliseconds between value steps when increment/decrement
    button is held down."""

    with_keyboard_events: Var[bool] = None
    """Enable up/down keyboard events for incrementing/decrementing (default: True).

    When True, pressing up/down arrow keys while focused increments/decrements
    the value by the step amount. Essential for keyboard-based navigation."""

    allow_mouse_wheel: Var[bool] = None
    """Enable mouse wheel increments/decrements (default: False)."""

    on_max_reached: EventHandler[rx.event.no_args_event_spec] = None
    """Called when the decrement button or arrow down key is pressed and
    the value has reached the minimum."""

    on_min_reached: EventHandler[rx.event.no_args_event_spec] = None
    """Called when the increment button or arrow up key is pressed and
    the value has reached the maximum."""

    on_value_change: EventHandler[rx.event.input_event] = None
    """Called when value changes with react-number-format payload."""

    def get_event_triggers(self) -> dict[str, Any]:
        """Override event triggers to handle NumberInput value emission.

        Mantine NumberInput sends the numeric value directly (or empty string),
        not an event object like standard input. The up/down arrow controls and
        keyboard events (up/down keys) depend on proper value transformation
        for Reflex state compatibility.

        References:
        - https://mantine.dev/core/number-input/?t=props (see withKeyboardEvents)
        - NumberInput extends react-number-format NumericFormat component
        - Increment/decrement controls automatically use onChange when step occurs
        """

        def _on_change(value: Var) -> list[Var]:
            # Mantine NumberInput sends value directly (number or empty string)
            # Forward it as-is to Reflex state
            return [value]

        return {
            **super().get_event_triggers(),
            "on_change": _on_change,
        }


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

    # Event handlers (password-specific)
    on_visibility_change: EventHandler[lambda visible: [visible]] = None
    """Called when visibility toggle is clicked (receives boolean)."""


class TagsInput(MantineInputComponentBase):
    """Reflex wrapper for Mantine TagsInput.

    TagsInput provides a way to enter multiple values as tags. Users can type
    values and press Enter to create tags, or select from predefined options.
    Supports various data formats and features like max tags limit, duplicates
    control, and split characters.

    Inherits common input props from MantineInputComponentBase. Use `data` as
    list[str], list[dict(value,label)], or grouped format.

    Example:
        ```python
        mn.tags_input(
            label="Skills",
            data=["React", "Python", "JavaScript", "TypeScript"],
            value=state.skills,
            on_change=state.set_skills,
            max_tags=5,
        )
        ```
    """

    tag = "TagsInput"

    # Core data and value props
    data: Var[list[Any]] = None
    """Data used to generate options. Values must be unique."""

    # Tag creation behavior
    # Defaults match Mantine TagsInput (see mantine source)
    accept_value_on_blur: Var[bool] = True
    """If set, the value is accepted when the input loses focus. Defaults to True."""

    allow_duplicates: Var[bool] = False
    """If set, duplicate tags are allowed. Defaults to False."""

    max_tags: Var[int] = None
    """Maximum number of tags that can be added.
    Mantine default is Infinity when omitted.
    """

    split_chars: Var[list[str]] = [","]
    """Characters that should be used to split input value into tags.
    Defaults to [','].
    """

    # Search and filtering - Mantine supports controlled searchValue and onSearchChange
    search_value: Var[str] = None
    """Controlled search value."""

    default_search_value: Var[str] = None
    """Default search value."""

    filter: Var[Any] = None
    """Function based on which items are filtered and sorted."""

    # Visual options
    render_option: Var[Any] = None
    """Function to render option in dropdown."""

    render_pill: Var[Any] = None
    """Function to render pill (Mantine 9+)."""

    # Clear functionality
    clearable: Var[bool] = False
    """If set, the clear button is displayed in the right section. Defaults to False."""

    # Dropdown behavior
    limit: Var[int] = None
    """Maximum number of options displayed at a time."""

    # Align with Mantine's common dropdown default (OptionsDropdown uses 220px mah)
    max_dropdown_height: Var[str | int] = 220

    with_scroll_area: Var[bool] = True
    """Determines whether the options should be wrapped with ScrollArea.
    Defaults to True.
    """

    # Combobox integration
    combobox_props: Var[dict[str, Any]] = None
    """Props passed down to the underlying Combobox component."""

    # Event handlers
    on_search_change: EventHandler[lambda value: [value]] = None
    """Called when search value changes."""

    on_duplicate: EventHandler[lambda value: [value]] = None
    """Called when user attempts to add a duplicate tag."""

    on_remove: EventHandler[lambda value: [value]] = None
    """Called when a tag is removed (alias for Mantine onRemove)."""

    on_clear: EventHandler[list] = None
    """Called when the clear button is clicked."""

    on_dropdown_close: EventHandler[list] = None
    """Called when dropdown closes."""

    on_dropdown_open: EventHandler[list] = None
    """Called when dropdown opens."""

    on_option_submit: EventHandler[lambda value: [value]] = None
    """Called when option is submitted from dropdown."""

    # (on_remove is the Mantine prop name; keep that as primary)

    def get_event_triggers(self) -> dict[str, Any]:
        """Transform events to work with Reflex state system.

        TagsInput sends array values directly from Mantine, so we forward them
        as-is to maintain the array structure expected by Reflex state.
        """

        def _on_change(value: Var) -> list[Var]:
            # Mantine TagsInput sends the array directly, forward it as-is
            return [value]

        return {
            **super().get_event_triggers(),
            "on_change": _on_change,
        }


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
    _rename_props = {
        **MantineInputComponentBase._rename_props,  # noqa: SLF001
        "slot_char": "slotChar",
    }

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

    def get_event_triggers(self) -> dict[str, Any]:
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

    # Mantine styles prop for targeting internal sub-components
    styles: Var[dict] = None
    """Mantine styles object for targeting internal elements (root, wrapper, input)."""


class NativeSelect(MantineInputComponentBase):
    """Mantine NativeSelect component — native browser select element.

    https://mantine.dev/core/native-select/
    """

    tag = "NativeSelect"

    data: Var[list[Any]] = None
    """Options as list of strings or {value, label, disabled?} dicts."""


class FileInput(MantineInputComponentBase):
    """Mantine FileInput component — file picker with input wrapper.

    https://mantine.dev/core/file-input/
    """

    tag = "FileInput"

    _rename_props = {
        **MantineInputComponentBase._rename_props,  # noqa: SLF001
        "accept": "accept",
        "capture": "capture",
        "clearable": "clearable",
        "multiple": "multiple",
        "value_component": "valueComponent",
    }

    accept: Var[str] = None
    capture: Var[str | bool] = None
    multiple: Var[bool] = None
    clearable: Var[bool] = None
    value_component: Var[Any] = None

    def get_event_triggers(self) -> dict[str, Any]:
        def _on_change(value: Var) -> list[Var]:
            return [value]

        return {
            **super().get_event_triggers(),
            "on_change": _on_change,
        }


class PinInput(MantineInputComponentBase):
    """Mantine PinInput component — individual character pin/code entry.

    https://mantine.dev/core/pin-input/
    """

    tag = "PinInput"

    _rename_props = {
        **MantineInputComponentBase._rename_props,  # noqa: SLF001
        "auto_focus": "autoFocus",
        "input_mode": "inputMode",
        "input_type": "inputType",
        "manage_focus": "manageFocus",
        "one_time_code": "oneTimeCode",
        "restrict_to_marks": "restrictToMarks",
    }

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

    def get_event_triggers(self) -> dict[str, Any]:
        def _on_change(value: Var) -> list[Var]:
            return [value]

        return {
            **super().get_event_triggers(),
            "on_change": _on_change,
        }


class Rating(MantineLayoutComponentBase):
    """Mantine Rating component — star/symbol rating input.

    https://mantine.dev/core/rating/
    """

    tag = "Rating"

    _rename_props = {
        "allow_clear": "allowClear",
        "default_value": "defaultValue",
        "empty_symbol": "emptySymbol",
        "full_symbol": "fullSymbol",
        "get_symbol_label": "getSymbolLabel",
        "highlight_selected_only": "highlightSelectedOnly",
        "on_change_end": "onChangeEnd",
        "on_hover": "onHover",
        "read_only": "readOnly",
    }

    value: Var[int | float] = None
    default_value: Var[int | float] = None
    count: Var[int] = None
    fractions: Var[int] = None
    color: Var[str] = None
    size: Var[str | int] = None
    name: Var[str] = None
    read_only: Var[bool] = None
    allow_clear: Var[bool] = None
    highlight_selected_only: Var[bool] = None
    empty_symbol: Var[Any] = None
    full_symbol: Var[Any] = None

    on_change: EventHandler[lambda value: [value]] = None
    on_hover: EventHandler[lambda value: [value]] = None


class Fieldset(MantineLayoutComponentBase):
    """Mantine Fieldset component — groups related inputs with a legend.

    https://mantine.dev/core/fieldset/
    """

    tag = "Fieldset"

    legend: Var[Any] = None
    radius: Var[str | int] = None
    disabled: Var[bool] = None
    variant: Var[Literal["default", "filled", "unstyled"]] = None


class Chip(MantineLayoutComponentBase):
    """Mantine Chip component — toggleable chip/tag input.

    https://mantine.dev/core/chip/
    """

    tag = "Chip"

    _rename_props = {
        "auto_contrast": "autoContrast",
        "default_checked": "defaultChecked",
    }

    auto_contrast: Var[bool] = None
    checked: Var[bool] = None
    color: Var[str] = None
    default_checked: Var[bool] = None
    disabled: Var[bool] = None
    icon: Var[Any] = None
    id: Var[str] = None
    radius: Var[str | int] = None
    size: Var[str | int] = None
    type: Var[Literal["checkbox", "radio"]] = None
    value: Var[str] = None
    variant: Var[Literal["outline", "light", "filled"]] = None

    on_change: EventHandler[lambda checked: [checked]] = None


class ChipGroup(MantineLayoutComponentBase):
    """Mantine Chip.Group component — manages multiple Chip selections.

    https://mantine.dev/core/chip/
    """

    tag = "Chip.Group"

    _rename_props = {
        "default_value": "defaultValue",
    }

    value: Var[str | list[str]] = None
    default_value: Var[str | list[str]] = None
    multiple: Var[bool] = None

    on_change: EventHandler[lambda value: [value]] = None


class ColorInput(MantineInputComponentBase):
    """Mantine ColorInput component — color picker combined with text input.

    https://mantine.dev/core/color-input/
    """

    tag = "ColorInput"

    _rename_props = {
        **MantineInputComponentBase._rename_props,  # noqa: SLF001
        "close_on_color_swatch_click": "closeOnColorSwatchClick",
        "disallow_input": "disallowInput",
        "eye_dropper_button_props": "eyeDropperButtonProps",
        "eye_dropper_icon": "eyeDropperIcon",
        "fix_on_blur": "fixOnBlur",
        "on_change_end": "onChangeEnd",
        "popover_props": "popoverProps",
        "swatches_per_row": "swatchesPerRow",
        "with_eye_dropper": "withEyeDropper",
        "with_picker": "withPicker",
        "with_preview": "withPreview",
    }

    format: Var[Literal["hex", "hexa", "rgba", "rgb", "hsl", "hsla"]] = None
    swatches: Var[list[str]] = None
    swatches_per_row: Var[int] = None
    with_picker: Var[bool] = None
    with_preview: Var[bool] = None
    with_eye_dropper: Var[bool] = None
    disallow_input: Var[bool] = None
    close_on_color_swatch_click: Var[bool] = None
    fix_on_blur: Var[bool] = None
    popover_props: Var[dict] = None
    eye_dropper_icon: Var[Any] = None

    on_change_end: EventHandler[lambda value: [value]] = None

    def get_event_triggers(self) -> dict[str, Any]:
        def _on_change(value: Var) -> list[Var]:
            return [value]

        return {
            **super().get_event_triggers(),
            "on_change": _on_change,
        }


class ColorPicker(MantineLayoutComponentBase):
    """Mantine ColorPicker component — standalone color picker UI.

    https://mantine.dev/core/color-picker/
    """

    tag = "ColorPicker"

    _rename_props = {
        "alpha_label": "alphaLabel",
        "default_value": "defaultValue",
        "full_width": "fullWidth",
        "hidden_input_props": "hiddenInputProps",
        "hue_label": "hueLabel",
        "on_change_end": "onChangeEnd",
        "on_color_swatch_click": "onColorSwatchClick",
        "saturation_label": "saturationLabel",
        "swatches_per_row": "swatchesPerRow",
        "with_picker": "withPicker",
    }

    value: Var[str] = None
    default_value: Var[str] = None
    format: Var[Literal["hex", "hexa", "rgba", "rgb", "hsl", "hsla"]] = None
    swatches: Var[list[str]] = None
    swatches_per_row: Var[int] = None
    with_picker: Var[bool] = None
    size: Var[str | int] = None
    full_width: Var[bool] = None
    focusable: Var[bool] = None
    name: Var[str] = None
    alpha_label: Var[str] = None
    hue_label: Var[str] = None
    saturation_label: Var[str] = None

    on_change: EventHandler[lambda value: [value]] = None
    on_change_end: EventHandler[lambda value: [value]] = None
    on_color_swatch_click: EventHandler[lambda color: [color]] = None


class AlphaSlider(MantineLayoutComponentBase):
    """Mantine AlphaSlider component — alpha transparency slider.

    https://mantine.dev/core/alpha-slider/
    """

    tag = "AlphaSlider"

    _rename_props = {
        "on_change_end": "onChangeEnd",
        "on_scrub_end": "onScrubEnd",
        "on_scrub_start": "onScrubStart",
    }

    value: Var[int | float] = None
    color: Var[str] = None
    size: Var[str | int] = None
    focusable: Var[bool] = None

    on_change: EventHandler[lambda value: [value]] = None
    on_change_end: EventHandler[lambda value: [value]] = None
    on_scrub_start: EventHandler[rx.event.no_args_event_spec] = None
    on_scrub_end: EventHandler[rx.event.no_args_event_spec] = None


class AngleSlider(MantineLayoutComponentBase):
    """Mantine AngleSlider component — circular angle input slider.

    https://mantine.dev/core/angle-slider/
    """

    tag = "AngleSlider"

    _rename_props = {
        "default_value": "defaultValue",
        "format_label": "formatLabel",
        "hidden_input_props": "hiddenInputProps",
        "on_change_end": "onChangeEnd",
        "on_scrub_end": "onScrubEnd",
        "on_scrub_start": "onScrubStart",
        "restrict_to_marks": "restrictToMarks",
        "thumb_size": "thumbSize",
        "with_label": "withLabel",
    }

    value: Var[int | float] = None
    default_value: Var[int | float] = None
    step: Var[int] = None
    size: Var[int] = None
    thumb_size: Var[int] = None
    disabled: Var[bool] = None
    with_label: Var[bool] = None
    restrict_to_marks: Var[bool] = None
    marks: Var[list[dict]] = None
    name: Var[str] = None

    on_change: EventHandler[lambda value: [value]] = None
    on_change_end: EventHandler[lambda value: [value]] = None
    on_scrub_start: EventHandler[rx.event.no_args_event_spec] = None
    on_scrub_end: EventHandler[rx.event.no_args_event_spec] = None


class HueSlider(MantineLayoutComponentBase):
    """Mantine HueSlider component — hue color picker slider.

    https://mantine.dev/core/hue-slider/
    """

    tag = "HueSlider"

    _rename_props = {
        "on_change_end": "onChangeEnd",
        "on_scrub_end": "onScrubEnd",
        "on_scrub_start": "onScrubStart",
    }

    value: Var[int | float] = None
    size: Var[str | int] = None
    focusable: Var[bool] = None

    on_change: EventHandler[lambda value: [value]] = None
    on_change_end: EventHandler[lambda value: [value]] = None
    on_scrub_start: EventHandler[rx.event.no_args_event_spec] = None
    on_scrub_end: EventHandler[rx.event.no_args_event_spec] = None


# ============================================================================
# Convenience Functions
# ============================================================================


class ChipNamespace(rx.ComponentNamespace):
    """Namespace for Chip components."""

    __call__ = staticmethod(Chip.create)
    group = staticmethod(ChipGroup.create)


class InputNamespace(rx.ComponentNamespace):
    """Namespace for input components."""

    input = staticmethod(Input.create)
    text = staticmethod(TextInput.create)
    password = staticmethod(PasswordInput.create)
    number = staticmethod(NumberInput.create)
    masked = staticmethod(MaskInput.create)
    textarea = staticmethod(Textarea.create)
    json = staticmethod(JsonInput.create)
    date = staticmethod(DateInput.create)
    tags = staticmethod(TagsInput.create)

    # Sub-components
    wrapper = staticmethod(InputWrapper.create)
    label = staticmethod(InputLabel.create)
    description = staticmethod(InputDescription.create)
    error = staticmethod(InputError.create)
    placeholder = staticmethod(InputPlaceholder.create)
    clear_button = staticmethod(InputClearButton.create)


form = InputNamespace()


# Export convenience functions for direct access
alpha_slider = AlphaSlider.create
angle_slider = AngleSlider.create
chip = ChipNamespace()
color_input = ColorInput.create
color_picker = ColorPicker.create
fieldset = Fieldset.create
file_input = FileInput.create
hue_slider = HueSlider.create
json_input = JsonInput.create
masked_input = MaskInput.create
native_select = NativeSelect.create
number_input = NumberInput.create
password_input = PasswordInput.create
pin_input = PinInput.create
rating = Rating.create
tags_input = TagsInput.create
text_input = TextInput.create
textarea = Textarea.create
input_wrapper = InputWrapper.create
