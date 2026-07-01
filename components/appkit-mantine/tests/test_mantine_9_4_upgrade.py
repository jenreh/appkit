"""Tests for the Mantine 9.4.1 upgrade — version pin, new props, new components.

Covers the props added in 9.3/9.4 on existing wrappers and the newly wrapped
components (Splitter, Menubar, ComboboxPopover, DataList, EmptyState and the
``@mantine/schedule`` resource/agenda views).
"""

from __future__ import annotations

import appkit_mantine as mn
from appkit_mantine.base import MANTINE_VERSION, MantineComponentBase


def _rendered(component) -> dict:
    return component.render()


def _prop_names(component) -> set[str]:
    """Return the JSX prop names emitted for a component."""
    props = _rendered(component).get("props", [])
    return {entry.split(":", 1)[0] for entry in props}


def _tag(component) -> str:
    return _rendered(component).get("name", "")


# ---------------------------------------------------------------------------
# Version pin
# ---------------------------------------------------------------------------


def test_mantine_version_is_9_4_1() -> None:
    assert MANTINE_VERSION == "9.4.1"


def test_core_library_pins_9_4_1() -> None:
    assert MantineComponentBase().library == "@mantine/core@9.4.1"


def test_schedule_library_pins_9_4_1() -> None:
    assert mn.schedule.day_view(events=[]).library == "@mantine/schedule@9.4.1"


# ---------------------------------------------------------------------------
# New props on already-wrapped components (snake_case -> camelCase)
# ---------------------------------------------------------------------------


def test_input_success_prop() -> None:
    assert "success" in _prop_names(mn.text_input(success="Looks good"))


def test_text_and_blockquote_text_wrap() -> None:
    assert "textWrap" in _prop_names(mn.text("hi", text_wrap="balance"))
    assert "textWrap" in _prop_names(mn.blockquote("q", text_wrap="pretty"))


def test_textarea_bottom_section() -> None:
    assert "bottomSection" in _prop_names(mn.textarea(bottom_section="0/100"))


def test_combobox_floating_height() -> None:
    for factory in (mn.select, mn.autocomplete):
        assert "floatingHeight" in _prop_names(
            factory(data=["a"], floating_height="viewport")
        )
    assert "floatingHeight" in _prop_names(mn.tags_input(floating_height="viewport"))


def test_pagination_responsive_layout() -> None:
    assert "layout" in _prop_names(mn.pagination(total=10, layout="responsive"))


def test_overflow_list_collapse_from() -> None:
    assert "collapseFrom" in _prop_names(
        mn.overflow_list(data=[1, 2], collapse_from="start")
    )


def test_menu_align_items_labels() -> None:
    assert "alignItemsLabels" in _prop_names(mn.menu(align_items_labels=True))


def test_timepicker_close_dropdown_on_preset_select() -> None:
    assert "closeDropdownOnPresetSelect" in _prop_names(
        mn.time_picker(close_dropdown_on_preset_select=True)
    )


def test_pie_chart_labels_type_name() -> None:
    assert "labelsType" in _prop_names(mn.pie_chart(data=[], labels_type="name"))


def test_schedule_view_flags() -> None:
    day = mn.schedule.day_view(with_sub_hour_grid_lines=True, with_agenda=True)
    assert {"withSubHourGridLines", "withAgenda"} <= _prop_names(day)
    month = mn.schedule.month_view(with_weekend_days=False, with_agenda=True)
    assert {"withWeekendDays", "withAgenda"} <= _prop_names(month)


# ---------------------------------------------------------------------------
# New components — correct tag, key props, top-level export
# ---------------------------------------------------------------------------


def test_splitter_component() -> None:
    assert _tag(mn.splitter(reset_on_double_click=True, h=200)) == "Splitter"
    assert _tag(mn.splitter.pane("x", default_size="30%")) == "Splitter.Pane"
    assert "resetOnDoubleClick" in _prop_names(mn.splitter(reset_on_double_click=True))


def test_menu_new_subcomponents() -> None:
    assert _tag(mn.menu.search(placeholder="f")) == "Menu.Search"
    assert _tag(mn.menu.checkbox_item("a", checked=True)) == "Menu.CheckboxItem"
    assert _tag(mn.menu.radio_group()) == "Menu.RadioGroup"
    assert _tag(mn.menu.radio_item("a", value="a")) == "Menu.RadioItem"
    assert _tag(mn.menu.context_menu()) == "Menu.ContextMenu"


def test_menubar_components() -> None:
    assert _tag(mn.menubar()) == "Menubar"
    assert _tag(mn.menubar.menu()) == "Menubar.Menu"
    assert _tag(mn.menubar.target("File")) == "Menubar.Target"
    assert _tag(mn.menubar.dropdown()) == "Menubar.Dropdown"


def test_popover_context_menu() -> None:
    assert _tag(mn.popover.context_menu()) == "Popover.ContextMenu"


def test_combobox_popover() -> None:
    assert _tag(mn.combobox_popover(data=["a"])) == "ComboboxPopover"
    assert _tag(mn.combobox_popover.target(mn.button("x"))) == "ComboboxPopover.Target"
    assert "nothingFoundMessage" in _prop_names(
        mn.combobox_popover(data=[], nothing_found_message="none")
    )


def test_data_list_components() -> None:
    assert _tag(mn.data_list(with_divider=True)) == "DataList"
    assert _tag(mn.data_list.item()) == "DataList.Item"
    assert _tag(mn.data_list.item_label("Name")) == "DataList.ItemLabel"
    assert _tag(mn.data_list.item_value("Jane")) == "DataList.ItemValue"


def test_empty_state_components() -> None:
    assert _tag(mn.empty_state(title="No data")) == "EmptyState"
    assert "withIndicatorBackground" in _prop_names(
        mn.empty_state(with_indicator_background=True)
    )
    assert _tag(mn.empty_state.actions()) == "EmptyState.Actions"


def test_resources_schedule_views() -> None:
    resources = [{"id": "a", "label": "A"}]
    day = mn.resources_day_view(resources=resources, start_time="08:00:00")
    assert _tag(day) == "ResourcesDayView"
    assert {"resources", "startTime"} <= _prop_names(day)
    assert _tag(mn.resources_week_view(resources=resources)) == "ResourcesWeekView"
    month = mn.resources_month_view(resources=resources, with_weekend_days=False)
    assert _tag(month) == "ResourcesMonthView"
    assert "withWeekendDays" in _prop_names(month)
    sched = mn.resources_schedule(resources=resources, view="week")
    assert _tag(sched) == "ResourcesSchedule"


def test_agenda_view() -> None:
    agenda = mn.agenda_view(range_start="2026-07-01", range_end="2026-07-08")
    assert _tag(agenda) == "AgendaView"
    assert {"rangeStart", "rangeEnd"} <= _prop_names(agenda)


def test_resource_view_event_triggers_registered() -> None:
    triggers = mn.resources_day_view(resources=[]).get_event_triggers()
    for handler in ("on_event_click", "on_date_change", "on_time_slot_click"):
        assert handler in triggers


def test_new_components_exported_from_package() -> None:
    for name in (
        "splitter",
        "menubar",
        "combobox_popover",
        "data_list",
        "empty_state",
        "resources_day_view",
        "resources_week_view",
        "resources_month_view",
        "resources_schedule",
        "agenda_view",
    ):
        assert name in mn.__all__
        assert hasattr(mn, name)
