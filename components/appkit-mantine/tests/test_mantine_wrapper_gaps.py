"""Mantine 9.7.3 props and events that previously needed ``custom_attrs``.

Reflex 0.10 turns undeclared keyword props into CSS, so every prop here must
reach the JSX under its camelCase name and never end up in ``css``.
"""

from __future__ import annotations

from pathlib import Path

import reflex as rx

import appkit_mantine as mn


class _GapState(rx.State):
    selected: list[str] = []
    checked: list[str] = []
    time: str = ""
    masked: str = ""

    @rx.event
    def set_selected(self, value: list[str]) -> None:
        self.selected = value

    @rx.event
    def set_checked(self, value: list[str]) -> None:
        self.checked = value

    @rx.event
    def set_time(self, value: str) -> None:
        self.time = value

    @rx.event
    def set_masked(self, value: str) -> None:
        self.masked = value


def _rendered(component: rx.Component) -> dict[str, str]:
    props = component.render().get("props", [])
    return dict(p.split(":", 1) if ":" in p else (p, "") for p in props)


def _assert_props(component: rx.Component, *names: str) -> dict[str, str]:
    props = _rendered(component)
    missing = set(names) - set(props)
    assert not missing, f"missing {missing} in {sorted(props)}"
    css = props.get("css", "")
    for name in names:
        assert name not in css, f"{name} leaked into css: {css}"
    return props


def test_time_grid_props_and_change_event() -> None:
    comp = mn.time_grid(
        data=["10:00", "11:00"],
        value=_GapState.time,
        default_value="10:00",
        allow_deselect=True,
        disabled=False,
        min_time="09:00",
        max_time="18:00",
        disable_time=["12:00"],
        format="12h",
        with_seconds=False,
        am_pm_labels={"am": "am", "pm": "pm"},
        simple_grid_props={"cols": 4, "spacing": "xs"},
        radius="md",
        size="sm",
        on_change=_GapState.set_time,
    )
    _assert_props(
        comp,
        "value",
        "defaultValue",
        "allowDeselect",
        "disabled",
        "minTime",
        "maxTime",
        "disableTime",
        "format",
        "withSeconds",
        "amPmLabels",
        "simpleGridProps",
        "radius",
        "size",
        "onChange",
    )


def test_tree_select_and_check_events() -> None:
    comp = mn.tree(
        data=[{"label": "A", "value": "a"}],
        with_checkbox=True,
        multiple=True,
        initial_selected_state=["a"],
        initial_checked_state=["a"],
        initial_expanded_state={"a": True},
        check_strictly=True,
        on_select=_GapState.set_selected,
        on_check=_GapState.set_checked,
    )
    _assert_props(
        comp,
        "multiple",
        "initialSelectedState",
        "initialCheckedState",
        "initialExpandedState",
        "checkStrictly",
        "onSelect",
        "onCheck",
    )
    triggers = comp.get_event_triggers()
    assert {"on_select", "on_check", "on_expand", "on_collapse"} <= set(triggers)


def test_tree_wrapper_uses_controller_callbacks() -> None:
    import appkit_mantine

    source = (Path(appkit_mantine.__file__).parent / "tree_advanced.jsx").read_text()
    for name in ("useTree", "onSelectedStateChange", "onCheckedStateChange"):
        assert name in source


def test_table_variant() -> None:
    props = _assert_props(mn.table(variant="vertical"), "variant")
    assert props["variant"] == '"vertical"'


def test_close_button_variant() -> None:
    _assert_props(mn.close_button(variant="transparent"), "variant")


def test_hover_card_positioning_props() -> None:
    comp = mn.hover_card(
        position="top",
        offset=8,
        with_arrow=True,
        transition_props={"transition": "pop", "duration": 150},
    )
    _assert_props(comp, "position", "offset", "withArrow", "transitionProps")


def test_popover_advanced_props() -> None:
    comp = mn.popover(
        transition_props={"transition": "pop"},
        portal_props={"target": "#root"},
        middlewares={"flip": True, "shift": True, "inline": False},
        click_outside_events=["mouseup", "touchend"],
        prevent_position_change_when_visible=True,
    )
    _assert_props(
        comp,
        "transitionProps",
        "portalProps",
        "middlewares",
        "clickOutsideEvents",
        "preventPositionChangeWhenVisible",
    )


def test_date_picker_input_presets_and_formatter() -> None:
    comp = mn.date_picker_input(
        presets=[{"value": "2026-01-01", "label": "New year"}],
        value_formatter=rx.Var("({ date }) => String(date)"),
    )
    _assert_props(comp, "presets", "valueFormatter")


def test_time_picker_presets() -> None:
    _assert_props(mn.time_picker(presets=["09:00", "12:00"]), "presets")


def test_mask_input_options_and_complete_event() -> None:
    comp = mn.masked_input(
        mask="(999) 999-9999",
        always_show_mask=True,
        show_mask_on_focus=False,
        auto_clear=True,
        separate=True,
        on_complete=_GapState.set_masked,
    )
    _assert_props(
        comp,
        "alwaysShowMask",
        "showMaskOnFocus",
        "autoClear",
        "separate",
        "onComplete",
    )


def test_angle_slider_format_label() -> None:
    comp = mn.angle_slider(format_label=rx.Var("(v) => `${v}°`"))
    _assert_props(comp, "formatLabel")


def test_light_dark_hidden_style_props() -> None:
    _assert_props(mn.box(light_hidden=True), "lightHidden")
    _assert_props(mn.group(dark_hidden=True), "darkHidden")
