from __future__ import annotations

from collections.abc import Callable
from typing import Any, Final, Literal

import reflex as rx
from reflex.event import EventHandler
from reflex.vars.base import Var

from appkit_mantine.base import MantineInputComponentBase
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

    allow_decimal: Var[bool] = None
    """Allow decimal input (default: True)."""

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

    # Controls
    hide_controls: Var[bool] = None
    """Hide increment/decrement buttons."""

    start_value: Var[int | float] = None
    """Value when empty input is focused (default: 0)."""

    with_keyboard_events: Var[bool] = None
    """Enable up/down keyboard events for incrementing/decrementing (default: True).

    When True, pressing up/down arrow keys while focused increments/decrements
    the value by the step amount. Essential for keyboard-based navigation."""

    allow_mouse_wheel: Var[bool] = None
    """Enable mouse wheel increments/decrements (default: False)."""

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


class MaskedInput(MantineInputComponentBase):
    """Mantine InputBase with IMask integration for masked input fields.

    This component combines Mantine's InputBase with react-imask for automatic
    input formatting. It inherits all common input props from MantineInputComponentBase
    (label, description, error, sections, etc.) and adds IMask-specific configuration.

    Based on: https://imask.js.org/guide.html

    IMPORTANT: This is an UNCONTROLLED component!
    - DO NOT use 'value' prop (it prevents typing)
    - Use 'on_accept' to capture formatted values
    - Use 'default_value' for initial values only

    Inherits from MantineInputComponentBase:
    - Input.Wrapper props (label, description, error, required, with_asterisk)
    - Visual variants (variant, size, radius)
    - State props (default_value, placeholder, disabled, read_only)
    - HTML attributes (name, id, aria_label, max_length, pattern, etc.)
    - Section props (left_section, right_section with widths and pointer_events)
    - Mantine style props (w, maw, m, mt, mb, ml, mr, mx, my, p, etc.)
    - Event handlers (on_focus, on_blur, on_key_down, on_key_up)

    Example:
        ```python
        import reflex as rx
        from appkit_mantine import masked_input


        class State(rx.State):
            phone: str = ""

            def handle_phone(self, value: str) -> None:
                self.phone = value


        # Phone number input - CORRECT USAGE
        masked_input(
            mask="+1 (000) 000-0000",
            label="Your phone",
            placeholder="Your phone",
            on_accept=State.handle_phone,  # ✅ Capture value here
            # value=State.phone,  # ❌ DO NOT USE - prevents typing!
        )

        # Credit card input with icon
        masked_input(
            mask="0000 0000 0000 0000",
            label="Card number",
            placeholder="Card number",
            left_section=rx.icon("credit-card"),
            left_section_pointer_events="none",
            on_accept=State.handle_card,
        )

        # Date input
        masked_input(
            mask="00/00/0000",
            label="Date",
            placeholder="MM/DD/YYYY",
            description="Enter date in MM/DD/YYYY format",
            left_section=rx.icon("calendar"),
            on_accept=State.handle_date,
        )

        # With initial value
        masked_input(
            mask="+1 (000) 000-0000",
            label="Phone",
            default_value="+1 (555) 123-4567",  # ✅ Use default_value
            on_accept=State.handle_phone,
        )

        # With validation
        masked_input(
            mask="+1 (000) 000-0000",
            label="Phone",
            required=True,
            with_asterisk=True,
            error=State.phone_error,
            on_accept=State.handle_phone,
        )
        ```
    """

    tag = "InputBase"
    lib_dependencies: list[str] = [f"react-imask@{IMASK_VERSION}"]

    def _get_custom_code(self) -> str:
        return """import '@mantine/core/styles.css';
import { IMaskInput } from 'react-imask';"""

    # Extend base _rename_props with IMask-specific camelCase conversions
    _rename_props = {
        **MantineInputComponentBase._rename_props,  # noqa: SLF001
        "placeholder_char": "placeholderChar",
    }

    # ========================================================================
    # Component Configuration
    # ========================================================================

    component: Final[Var[rx.Var]] = rx.Var(
        "IMaskInput"
    )  # read-only: ensures IMaskInput is used and should never be reassigned

    # ========================================================================
    # IMask-Specific Props - Only props unique to masked input
    # ========================================================================

    mask: Var[str] = None
    """Mask pattern (e.g., '+1 (000) 000-0000', '0000 0000 0000 0000')."""

    definitions: Var[dict] = None
    """Custom pattern definitions for mask characters."""

    blocks: Var[dict] = None
    """Block-based mask configuration for complex patterns."""

    lazy: Var[bool] = None
    """Show placeholder before typing (default: True)."""

    placeholder_char: Var[str] = None
    """Character for placeholder (default: '_')."""

    overwrite: Var[bool] = None
    """Allow overwriting characters (default: False)."""

    autofix: Var[bool] = None
    """Auto-fix input on blur (default: False)."""

    eager: Var[bool] = None
    """Eager mode for immediate mask display."""

    unmask: Var[bool | Literal["typed"]] = None
    """Return unmasked value. True = all unmasked, 'typed' = only typed chars."""

    # ========================================================================
    # IMask-Specific Event Handlers
    # ========================================================================

    on_accept: EventHandler[rx.event.input_event]
    """Called when mask accepts input (receives value directly, not event).
    Use this instead of on_change for masked inputs."""

    on_complete: EventHandler[rx.event.input_event]
    """Called when mask is completely filled (receives value directly)."""


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


# ============================================================================
# Convenience Functions
# ============================================================================


class InputNamespace(rx.ComponentNamespace):
    """Namespace for Combobox components."""

    input = staticmethod(Input.create)
    text = staticmethod(TextInput.create)
    password = staticmethod(PasswordInput.create)
    number = staticmethod(NumberInput.create)
    masked = staticmethod(MaskedInput.create)
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
text_input = TextInput.create
password_input = PasswordInput.create
number_input = NumberInput.create
json_input = JsonInput.create
tags_input = TagsInput.create
masked_input = MaskedInput.create
textarea = Textarea.create
input_wrapper = InputWrapper.create
