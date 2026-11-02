"""Tests for the Mantine 9.7.3 upgrade — version pin, new props, new components.

Covers the props added in 9.5.0/9.5.1 on existing wrappers and the newly
wrapped components (Cascader, SunburstChart, BulletChart, ChartBrush and
``FloatingWindow.ResizeHandle``).

Written tests-first: the component-import tests stay red until the new
wrappers land in their modules.
"""

from __future__ import annotations

import reflex as rx

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


def test_mantine_version_is_9_7_3() -> None:
    assert MANTINE_VERSION == "9.7.3"


def test_core_library_pins_9_7_3() -> None:
    assert MantineComponentBase().library == "@mantine/core@9.7.3"


def test_schedule_library_pins_9_7_3() -> None:
    assert mn.schedule.day_view(events=[]).library == "@mantine/schedule@9.7.3"


# ---------------------------------------------------------------------------
# New components (Mantine 9.5.0) — imported directly from their modules so
# these tests go green as soon as each wrapper lands, before integration.
# ---------------------------------------------------------------------------


def test_cascader_component() -> None:
    from appkit_mantine.combobox import Cascader, cascader

    component = cascader(data=[])
    assert isinstance(component, Cascader)
    assert _tag(component) == "Cascader"


def test_sunburst_chart_component() -> None:
    from appkit_mantine.charts import SunburstChart, sunburst_chart

    component = sunburst_chart(data=[])
    assert isinstance(component, SunburstChart)
    assert _tag(component) == "SunburstChart"


def test_bullet_chart_component() -> None:
    from appkit_mantine.charts import BulletChart, bullet_chart

    component = bullet_chart(value=75, ranges=[{"value": 100, "color": "gray"}])
    assert isinstance(component, BulletChart)
    assert _tag(component) == "BulletChart"


def test_chart_brush_component() -> None:
    from appkit_mantine.charts import ChartBrush, chart_brush

    component = chart_brush()
    assert isinstance(component, ChartBrush)
    assert _tag(component) == "ChartBrush"


def test_floating_window_resize_handle_component() -> None:
    from appkit_mantine.layout import FloatingWindowResizeHandle

    component = FloatingWindowResizeHandle.create()
    assert _tag(component) == "FloatingWindow.ResizeHandle"


# ---------------------------------------------------------------------------
# New props on already-wrapped components (snake_case -> camelCase)
# ---------------------------------------------------------------------------


def test_tooltip_interactive() -> None:
    assert "interactive" in _prop_names(mn.tooltip(label="hint", interactive=True))


def test_accordion_disable_collapse() -> None:
    assert "disableCollapse" in _prop_names(mn.accordion(disable_collapse=True))


def test_timeline_item_opposite_and_alternate() -> None:
    item = mn.timeline.item(opposite="14:00", alternate=True)
    assert {"opposite", "alternate"} <= _prop_names(item)


def test_scroll_area_vertical_scrollbar_position() -> None:
    assert "verticalScrollbarPosition" in _prop_names(
        mn.scroll_area(vertical_scrollbar_position="left")
    )


def test_heatmap_month_labels_position() -> None:
    assert "monthLabelsPosition" in _prop_names(
        mn.heatmap(data={}, month_labels_position="bottom")
    )


def test_date_pickers_with_native_level_select() -> None:
    for factory in (
        mn.date_picker,
        mn.date_picker_input,
        mn.month_picker,
        mn.year_picker,
        mn.date_time_picker,
    ):
        assert "withNativeLevelSelect" in _prop_names(
            factory(with_native_level_select=True)
        )


def test_categorical_charts_with_brush() -> None:
    for factory in (mn.area_chart, mn.bar_chart, mn.line_chart, mn.composite_chart):
        chart = factory(
            data=[],
            data_key="date",
            series=[],
            with_brush=True,
            brush_props={"height": 40},
        )
        assert {"withBrush", "brushProps"} <= _prop_names(chart)


def test_charts_accessibility_layer() -> None:
    area = mn.area_chart(data=[], data_key="date", series=[], accessibility_layer=True)
    assert "accessibilityLayer" in _prop_names(area)
    scatter = mn.scatter_chart(data=[], accessibility_layer=True)
    assert "accessibilityLayer" in _prop_names(scatter)


def test_color_input_full_width() -> None:
    assert "fullWidth" in _prop_names(mn.color_input(full_width=True))


def test_floating_window_resize_props() -> None:
    window = mn.floating_window(
        dimensions={"initialWidth": 400, "minWidth": 200, "maxWidth": 800},
        on_size_change=rx.console_log("resized"),
        on_resize_start=rx.console_log("resize started"),
    )
    assert {"dimensions", "onSizeChange", "onResizeStart"} <= _prop_names(window)


# ---------------------------------------------------------------------------
# Props added in Mantine 9.5.1
# ---------------------------------------------------------------------------


def test_password_input_visibility_toggle_focusable() -> None:
    assert "visibilityToggleFocusable" in _prop_names(
        mn.password_input(visibility_toggle_focusable=True)
    )


def test_scatter_chart_right_y_axis() -> None:
    chart = mn.scatter_chart(
        data=[],
        with_right_y_axis=True,
        right_y_axis_label="Volume",
        right_y_axis_props={"width": 60},
    )
    assert {
        "withRightYAxis",
        "rightYAxisLabel",
        "rightYAxisProps",
    } <= _prop_names(chart)


def test_year_view_render_day_and_weekend_days() -> None:
    view = mn.schedule.year_view(
        render_day=rx.Var("(date, dayEvents) => null"),
        with_weekend_days=False,
    )
    assert {"renderDay", "withWeekendDays"} <= _prop_names(view)


def test_resources_month_view_event_resize() -> None:
    view = mn.resources_month_view(
        resources=[],
        with_event_resize=True,
        on_event_resize=rx.console_log("resized"),
    )
    assert {"withEventResize", "onEventResize"} <= _prop_names(view)
