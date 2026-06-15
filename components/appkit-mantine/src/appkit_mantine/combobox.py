"""Mantine Select wrapper for Reflex.

Docs: https://mantine.dev/core/select/
"""

from __future__ import annotations

from typing import Any, Literal

import reflex as rx
from reflex.event import EventHandler, input_event
from reflex.vars.base import Var

from appkit_mantine.base import MantineInputComponentBase, MantineLayoutComponentBase


class MantineComboboxBase(MantineInputComponentBase):
    """Base class for Mantine Combobox-based components.

    Shared props between Select, MultiSelect, and Autocomplete.
    """

    data: Var[list[Any]] = None
    limit: Var[int] = None
    max_dropdown_height: Var[str | int] = None
    dropdown_opened: Var[bool] = None
    default_dropdown_opened: Var[bool] = None
    filter: Var[Any] = None
    clearable: Var[bool] = None

    # Event handlers
    on_dropdown_close: EventHandler[rx.event.no_args_event_spec] = None
    on_dropdown_open: EventHandler[rx.event.no_args_event_spec] = None


class MantineSelectBase(MantineComboboxBase):
    """Base class for Select and MultiSelect components."""

    searchable: Var[bool] = False
    search_value: Var[str] = None
    default_search_value: Var[str] = None
    nothing_found_message: Var[str] = "No options"
    check_icon_position: Var[Literal["left", "right"]] = "left"
    with_scroll_area: Var[bool] = True
    combobox_props: Var[dict[str, Any]] = None

    # Event handlers
    on_search_change: EventHandler[lambda value: [value]] = None
    on_clear: EventHandler[rx.event.no_args_event_spec] = None
    on_option_submit: EventHandler[lambda item: [item]] = None


class Select(MantineSelectBase):
    """Reflex wrapper for Mantine Select.

    Inherits common input props from MantineInputComponentBase. Use `data` as
    list[str] or list[dict(value,label)].
    """

    tag = "Select"

    allow_deselect: Var[bool] = True
    auto_select_on_blur: Var[bool] = False
    render_option: Var[Any] = None
    select_first_option_on_change: Var[bool] = False

    # Redefine default to match original component
    max_dropdown_height: Var[str | int] = "240px"

    @classmethod
    def get_event_triggers(cls) -> dict[str, Any]:
        # Map on_change so Reflex state receives a simple string (empty when null)
        def _on_change(value: Var) -> list[Var]:
            return [value]

        return {
            **super().get_event_triggers(),
            "on_change": _on_change,
        }


class MultiSelect(MantineSelectBase):
    """Reflex wrapper for Mantine MultiSelect.

    MultiSelect provides a way to enter multiple values from predefined options.
    It supports various data formats (strings, objects, groups) and features like
    search, max values limit, and hiding picked options.

    Inherits common input props from MantineInputComponentBase. Use `data` as
    list[str], list[dict(value,label)], or grouped format.

    Example:
        ```python
        mn.multi_select(
            label="Favorite frameworks",
            data=["React", "Vue", "Angular", "Svelte"],
            value=state.selected_frameworks,
            on_change=state.set_selected_frameworks,
            searchable=True,
        )
        ```
    """

    tag = "MultiSelect"

    # MultiSelect specific props
    clear_search_on_change: Var[bool] = False
    """Clear search value when item is selected."""

    max_values: Var[int] = None
    """Maximum number of values that can be selected."""

    hide_picked_options: Var[bool] = False
    """If set, picked options are removed from the options list."""

    with_check_icon: Var[bool] = True
    """If set, check icon is displayed near the selected option label."""

    render_pill: Var[Any] = None
    """Custom pill renderer (Mantine 9+)."""

    max_dropdown_height: Var[str | int] = "200px"
    """Max height of the dropdown."""

    # Event handlers
    on_option_submit: EventHandler[input_event] = None
    """Called when option is submitted from dropdown."""

    @classmethod
    def get_event_triggers(cls) -> dict[str, Any]:
        """Transform events to work with Reflex state system.

        MultiSelect sends array values directly from Mantine, so we forward them
        as-is to maintain the array structure expected by Reflex state.
        """

        def _on_change(value: Var) -> list[Var]:
            # Mantine MultiSelect sends the array directly, forward it as-is
            return [value]

        return {
            **super().get_event_triggers(),
            "on_change": _on_change,
        }


class Autocomplete(MantineComboboxBase):
    """Reflex wrapper for Mantine Autocomplete.

    Note: Mantine Autocomplete accepts string arrays as `data`. It does not
    support `{value,label}` objects like Select.
    """

    tag = "Autocomplete"

    # Autocomplete-specific props
    render_option: rx.Var[Any] = None
    auto_select_on_blur: rx.Var[bool] = None

    # Event handlers
    on_option_submit: rx.EventHandler[lambda value, option: [value, option]] = None

    _rename_props = {
        **MantineInputComponentBase._rename_props,  # noqa: SLF001
    }

    @classmethod
    def get_event_triggers(cls) -> dict[str, Any]:
        return {
            **super().get_event_triggers(),
            "on_change": lambda value: [value],
            "on_option_submit": lambda value, option: [value, option],
        }


class ComboboxRoot(MantineLayoutComponentBase):
    """Mantine Combobox root component — low-level dropdown primitive.

    https://mantine.dev/core/combobox/
    """

    tag = "Combobox"

    _rename_props = {
        "arrow_offset": "arrowOffset",
        "close_on_option_select": "closeOnOptionSelect",
        "dropdown_padding": "dropdownPadding",
        "on_close": "onClose",
        "on_open": "onOpen",
        "on_option_submit": "onOptionSubmit",
        "position_dependencies": "positionDependencies",
        "reset_selection_on_option_hover": "resetSelectionOnOptionHover",
        "with_arrow": "withArrow",
        "within_portal": "withinPortal",
    }

    opened: Var[bool] = None
    position: Var[str] = None
    offset: Var[int] = None
    with_arrow: Var[bool] = None
    within_portal: Var[bool] = None
    dropdown_padding: Var[int] = None
    size: Var[str | int] = None
    close_on_option_select: Var[bool] = None
    reset_selection_on_option_hover: Var[bool] = None

    on_open: EventHandler[rx.event.no_args_event_spec] = None
    on_close: EventHandler[rx.event.no_args_event_spec] = None
    on_option_submit: EventHandler[lambda value: [value]] = None


class ComboboxTarget(MantineLayoutComponentBase):
    """Mantine Combobox.Target — wraps the trigger element."""

    tag = "Combobox.Target"


class ComboboxDropdown(MantineLayoutComponentBase):
    """Mantine Combobox.Dropdown — the dropdown panel."""

    tag = "Combobox.Dropdown"

    hidden: Var[bool] = None


class ComboboxOptions(MantineLayoutComponentBase):
    """Mantine Combobox.Options — wrapper for option list."""

    tag = "Combobox.Options"


class ComboboxOption(MantineLayoutComponentBase):
    """Mantine Combobox.Option — single selectable item."""

    tag = "Combobox.Option"

    value: Var[str] = None
    active: Var[bool] = None
    disabled: Var[bool] = None
    selected: Var[bool] = None


class ComboboxSearch(MantineLayoutComponentBase):
    """Mantine Combobox.Search — search input inside the dropdown."""

    tag = "Combobox.Search"

    value: Var[str] = None
    placeholder: Var[str] = None
    on_change: EventHandler[rx.event.input_event] = None


class ComboboxGroup(MantineLayoutComponentBase):
    """Mantine Combobox.Group — groups options with a label."""

    tag = "Combobox.Group"

    label: Var[str | Any] = None


class ComboboxEmpty(MantineLayoutComponentBase):
    """Mantine Combobox.Empty — shown when no options match."""

    tag = "Combobox.Empty"


class ComboboxChevron(MantineLayoutComponentBase):
    """Mantine Combobox.Chevron — dropdown arrow indicator."""

    tag = "Combobox.Chevron"

    size: Var[str | int] = None
    error: Var[str | bool] = None


class ComboboxHeader(MantineLayoutComponentBase):
    """Mantine Combobox.Header — sticky header in dropdown."""

    tag = "Combobox.Header"


class ComboboxFooter(MantineLayoutComponentBase):
    """Mantine Combobox.Footer — sticky footer in dropdown."""

    tag = "Combobox.Footer"


class ComboboxNamespace(rx.ComponentNamespace):
    """Namespace for Combobox components."""

    __call__ = staticmethod(ComboboxRoot.create)
    target = staticmethod(ComboboxTarget.create)
    dropdown = staticmethod(ComboboxDropdown.create)
    options = staticmethod(ComboboxOptions.create)
    option = staticmethod(ComboboxOption.create)
    search = staticmethod(ComboboxSearch.create)
    group = staticmethod(ComboboxGroup.create)
    empty = staticmethod(ComboboxEmpty.create)
    chevron = staticmethod(ComboboxChevron.create)
    header = staticmethod(ComboboxHeader.create)
    footer = staticmethod(ComboboxFooter.create)


class Pill(MantineLayoutComponentBase):
    """Mantine Pill component — removable tag/pill.

    https://mantine.dev/core/pill/
    """

    tag = "Pill"

    _rename_props = {
        "remove_button_props": "removeButtonProps",
        "with_remove_button": "withRemoveButton",
    }

    disabled: Var[bool] = None
    radius: Var[str | int] = None
    size: Var[str | int] = None
    with_remove_button: Var[bool] = None
    remove_button_props: Var[dict] = None

    on_remove: EventHandler[rx.event.no_args_event_spec] = None


class PillGroup(MantineLayoutComponentBase):
    """Mantine Pill.Group — container for multiple pills."""

    tag = "Pill.Group"

    disabled: Var[bool] = None


class PillsInput(MantineLayoutComponentBase):
    """Mantine PillsInput — input with pills inside.

    https://mantine.dev/core/pills-input/
    """

    tag = "PillsInput"

    _rename_props = {
        "left_section": "leftSection",
        "left_section_pointer_events": "leftSectionPointerEvents",
        "left_section_width": "leftSectionWidth",
        "right_section": "rightSection",
        "right_section_pointer_events": "rightSectionPointerEvents",
        "right_section_width": "rightSectionWidth",
        "with_asterisk": "withAsterisk",
        "with_error_styles": "withErrorStyles",
    }

    label: Var[str | Any] = None
    description: Var[str | Any] = None
    error: Var[str | bool] = None
    required: Var[bool] = None
    disabled: Var[bool] = None
    loading: Var[bool] = None
    pointer: Var[bool] = None
    radius: Var[str | int] = None
    size: Var[str | int] = None
    left_section: Var[Any] = None
    right_section: Var[Any] = None
    left_section_width: Var[str | int] = None
    right_section_width: Var[str | int] = None
    left_section_pointer_events: Var[str] = None
    right_section_pointer_events: Var[str] = None
    with_asterisk: Var[bool] = None
    with_error_styles: Var[bool] = None


class PillsInputField(MantineLayoutComponentBase):
    """Mantine PillsInput.Field — text input field inside PillsInput."""

    tag = "PillsInput.Field"

    pointer: Var[bool] = None
    type: Var[Literal["hidden", "auto", "visible"]] = None
    value: Var[str] = None
    placeholder: Var[str] = None

    on_change: EventHandler[rx.event.input_event] = None
    on_key_down: EventHandler[rx.event.key_event] = None


class TreeSelect(MantineLayoutComponentBase):
    """Mantine TreeSelect component — hierarchical data selection.

    https://mantine.dev/core/tree-select/
    """

    tag = "TreeSelect"

    _rename_props = {
        "allow_deselect": "allowDeselect",
        "check_strictly": "checkStrictly",
        "checked_strategy": "checkedStrategy",
        "chevron_aria_labels": "chevronAriaLabels",
        "chevron_color": "chevronColor",
        "clear_search_on_change": "clearSearchOnChange",
        "default_dropdown_opened": "defaultDropdownOpened",
        "default_expand_all": "defaultExpandAll",
        "default_expanded_values": "defaultExpandedValues",
        "default_search_value": "defaultSearchValue",
        "default_value": "defaultValue",
        "dropdown_opened": "dropdownOpened",
        "expand_on_click": "expandOnClick",
        "expanded_values": "expandedValues",
        "max_displayed_values": "maxDisplayedValues",
        "max_dropdown_height": "maxDropdownHeight",
        "max_values": "maxValues",
        "nothing_found_message": "nothingFoundMessage",
        "on_clear": "onClear",
        "on_dropdown_close": "onDropdownClose",
        "on_dropdown_open": "onDropdownOpen",
        "on_expanded_change": "onExpandedChange",
        "on_remove": "onRemove",
        "on_search_change": "onSearchChange",
        "open_on_focus": "openOnFocus",
        "render_node": "renderNode",
        "search_value": "searchValue",
        "with_lines": "withLines",
        "with_asterisk": "withAsterisk",
        "with_error_styles": "withErrorStyles",
    }

    data: Var[list[dict[str, Any]]] = None
    value: Var[str | list[str]] = None
    default_value: Var[str | list[str]] = None
    mode: Var[str] = None
    searchable: Var[bool] = None
    search_value: Var[str] = None
    default_search_value: Var[str] = None
    clearable: Var[bool] = None
    disabled: Var[bool] = None
    required: Var[bool] = None
    label: Var[Any] = None
    description: Var[Any] = None
    error: Var[Any] = None
    radius: Var[str | int] = None
    size: Var[str | int] = None
    max_dropdown_height: Var[str | int] = None
    max_values: Var[int] = None
    nothing_found_message: Var[Any] = None
    allow_deselect: Var[bool] = None
    expand_on_click: Var[bool] = None
    with_lines: Var[bool] = None
    expanded_values: Var[list[str]] = None
    default_expanded_values: Var[list[str]] = None
    default_expand_all: Var[bool] = None

    on_change: EventHandler[lambda value: [value]] = None
    on_clear: EventHandler[rx.event.no_args_event_spec] = None
    on_search_change: EventHandler[lambda value: [value]] = None
    on_dropdown_open: EventHandler[rx.event.no_args_event_spec] = None
    on_dropdown_close: EventHandler[rx.event.no_args_event_spec] = None
    on_expanded_change: EventHandler[lambda values: [values]] = None


class PillNamespace(rx.ComponentNamespace):
    """Namespace for Pill components."""

    __call__ = staticmethod(Pill.create)
    group = staticmethod(PillGroup.create)


class PillsInputNamespace(rx.ComponentNamespace):
    """Namespace for PillsInput components."""

    __call__ = staticmethod(PillsInput.create)
    field = staticmethod(PillsInputField.create)


combobox = ComboboxNamespace()
pill = PillNamespace()
pills_input = PillsInputNamespace()
select = Select.create
multi_select = MultiSelect.create
autocomplete = Autocomplete.create
tree_select = TreeSelect.create
