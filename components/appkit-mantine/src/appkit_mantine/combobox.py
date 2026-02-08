"""Mantine Select wrapper for Reflex.

Docs: https://mantine.dev/core/select/
"""

from __future__ import annotations

from typing import Any, Literal

import reflex as rx
from reflex.event import EventHandler, input_event
from reflex.vars.base import Var

from appkit_mantine.base import MantineInputComponentBase


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

    def get_event_triggers(self) -> dict[str, Any]:
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

    max_dropdown_height: Var[str | int] = "200px"
    """Max height of the dropdown."""

    # Event handlers
    on_option_submit: EventHandler[input_event] = None
    """Called when option is submitted from dropdown."""

    def get_event_triggers(self) -> dict[str, Any]:
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

    def get_event_triggers(self) -> dict[str, Any]:
        return {
            **super().get_event_triggers(),
            "on_change": lambda value: [value],
            "on_option_submit": lambda value, option: [value, option],
        }


select = Select.create
multi_select = MultiSelect.create
autocomplete = Autocomplete.create
