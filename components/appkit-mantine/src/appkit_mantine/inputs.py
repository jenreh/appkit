from __future__ import annotations

from typing import Any, Literal

import reflex as rx
from reflex.event import EventHandler
from reflex.vars.base import Var

from appkit_mantine import multi_select, textarea
from appkit_mantine.autocomplete import Autocomplete
from appkit_mantine.base import MantineInputComponentBase
from appkit_mantine.date import DateInput
from appkit_mantine.json_input import JsonInput
from appkit_mantine.masked_input import MaskedInput
from appkit_mantine.number_input import NumberInput
from appkit_mantine.password_input import PasswordInput
from appkit_mantine.rich_select import RichSelect
from appkit_mantine.select import Select
from appkit_mantine.tags_input import TagsInput
from appkit_mantine.text_input import TextInput


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
    textarea = staticmethod(textarea.Textarea.create)
    json = staticmethod(JsonInput.create)
    date = staticmethod(DateInput.create)
    select = staticmethod(Select.create)
    rich_select = staticmethod(RichSelect.create)
    multi_select = staticmethod(multi_select.MultiSelect.create)
    autocomplete = staticmethod(Autocomplete.create)
    tags = staticmethod(TagsInput.create)

    # Sub-components
    wrapper = staticmethod(InputWrapper.create)
    label = staticmethod(InputLabel.create)
    description = staticmethod(InputDescription.create)
    error = staticmethod(InputError.create)
    placeholder = staticmethod(InputPlaceholder.create)
    clear_button = staticmethod(InputClearButton.create)


form = InputNamespace()
