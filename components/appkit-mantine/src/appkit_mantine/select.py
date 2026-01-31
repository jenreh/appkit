"""Mantine Select wrapper for Reflex.

Docs: https://mantine.dev/core/select/
"""

from __future__ import annotations

from typing import Any, Literal

from reflex.event import EventHandler
from reflex.vars.base import Var

from appkit_mantine.base import MantineInputComponentBase


class Select(MantineInputComponentBase):
    """Reflex wrapper for Mantine Select.

    Inherits common input props from MantineInputComponentBase. Use `data` as
    list[str] or list[dict(value,label)].
    """

    tag = "Select"

    allow_deselect: Var[bool] = True
    auto_select_on_blur: Var[bool] = False
    check_icon_position: Var[Literal["left", "right"]] = "left"
    clearable: Var[bool] = False
    combobox_props: Var[dict[str, Any]] = None
    data: Var[list[Any]]
    default_dropdown_opened: Var[bool] = False
    default_search_value: Var[str]
    dropdown_opened: Var[bool]
    filter: Var[Any]
    limit: Var[int]
    max_dropdown_height: Var[str | int] = "240px"
    nothing_found_message: Var[str] = "No options"
    render_option: Var[Any]
    searchable: Var[bool] = False
    search_value: Var[str]
    select_first_option_on_change: Var[bool] = False
    value: Var[str | int | float | list]
    with_scroll_area: Var[bool] = True

    # Event handlers
    # on_change receives value from Mantine; we forward it
    on_clear: EventHandler[lambda item: [item]] = None
    on_dropdown_close: EventHandler[lambda item: [item]] = None
    on_dropdown_open: EventHandler[lambda item: [item]] = None
    on_option_submit: EventHandler[lambda item: [item]] = None
    on_search_change: EventHandler[lambda value: [value]] = None

    def get_event_triggers(self) -> dict[str, Any]:
        # Map on_change so Reflex state receives a simple string (empty when null)
        def _on_change(value: Var) -> list[Var]:
            return [value]

        return {
            **super().get_event_triggers(),
            "on_change": _on_change,
        }


select = Select.create
