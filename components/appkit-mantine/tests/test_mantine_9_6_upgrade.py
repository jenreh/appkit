"""Tests for the Mantine 9.6 features — new components and props."""

from __future__ import annotations

import pytest

import appkit_mantine as mn
from appkit_mantine.dropzone import REACT_DROPZONE_LIBRARY
from appkit_mantine.lightbox import LIGHTBOX_LIBRARY
from appkit_mantine.tiptap import RichTextEditor, ToolbarControlGroup


def _props(component) -> set[str]:
    return {e.split(":", 1)[0] for e in component.render().get("props", [])}


def _tag(component) -> str:
    return component.render().get("name", "")


@pytest.mark.parametrize(
    ("factory", "tag", "props"),
    [
        (
            lambda: mn.gauge_chart(value=72, target=80, sections=[], round_caps=True),
            "GaugeChart",
            {"value", "target", "sections", "roundCaps"},
        ),
        (
            lambda: mn.waffle_chart(data=[], fill_direction="top-to-bottom"),
            "WaffleChart",
            {"data", "fillDirection"},
        ),
        (
            lambda: mn.matrix_chart(data=[], y_labels=["a"], with_y_labels=True),
            "MatrixChart",
            {"data", "yLabels", "withYLabels"},
        ),
        (
            lambda: mn.candlestick_chart(
                data=[], data_key="date", up_color="teal", reference_dots=[]
            ),
            "CandlestickChart",
            {"data", "dataKey", "upColor", "referenceDots"},
        ),
    ],
)
def test_new_charts(factory, tag: str, props: set[str]) -> None:
    comp = factory()
    assert comp.library == "@mantine/charts@9.7.3"
    assert _tag(comp) == tag
    assert props <= _props(comp)


@pytest.mark.parametrize(
    "factory",
    [mn.area_chart, mn.bar_chart, mn.line_chart, mn.composite_chart, mn.scatter_chart],
)
def test_reference_annotations(factory) -> None:
    comp = factory(
        data=[],
        reference_lines=[{"y": 1}],
        reference_areas=[{"x1": "a", "x2": "b", "label": "Weekend"}],
        reference_dots=[{"x": "a", "y": 1}],
    )
    assert {"referenceLines", "referenceAreas", "referenceDots"} <= _props(comp)


def test_area_chart_stream_type() -> None:
    assert 'type:"stream"' in mn.area_chart(chart_type="stream").render()["props"]


def test_action_bar_tree() -> None:
    comp = mn.action_bar(
        mn.text("2 selected"),
        mn.action_bar.divider(),
        mn.action_bar.close_button(),
        opened=True,
        shadow="md",
    )
    assert _tag(comp) == "ActionBar"
    assert {"opened", "shadow"} <= _props(comp)
    assert "on_close" in comp.get_event_triggers()
    assert _tag(mn.action_bar.divider()) == "ActionBar.Divider"
    assert _tag(mn.action_bar.close_button()) == "ActionBar.CloseButton"


def test_lightbox_controlled_and_provider() -> None:
    comp = mn.lightbox(
        opened=True, slides=[{"src": "a.png"}], current_index=0, with_thumbnails=True
    )
    assert comp.library == LIGHTBOX_LIBRARY == "@mantine/lightbox@9.7.3"
    assert _tag(comp) == "Lightbox"
    assert {"opened", "slides", "currentIndex", "withThumbnails"} <= _props(comp)
    assert {"on_close", "on_index_change"} <= set(comp.get_event_triggers())
    assert _tag(mn.lightbox.provider(with_zoom=True)) == "Lightbox.Provider"
    assert "embla-carousel-react@^8.5.2" in comp.lib_dependencies
    assert "window.mantineLightbox" in comp._get_custom_code()


def test_lightbox_api_scripts() -> None:
    spec = mn.lightbox_api.open([{"src": "a.png"}], start_index=2)
    script = str(spec.args[0][1])
    assert "mantineLightbox.open(" in script
    assert "startIndex" in script
    for spec in (
        mn.lightbox_api.close(),
        mn.lightbox_api.next(),
        mn.lightbox_api.prev(),
        mn.lightbox_api.set_index(3),
    ):
        assert "mantineLightbox." in str(spec.args[0][1])


def test_stepper_label_position() -> None:
    comp = mn.stepper(label_position="bottom", icon_position="right")
    assert {"labelPosition", "iconPosition"} <= _props(comp)


@pytest.mark.parametrize(
    "factory",
    [
        mn.schedule.day_view,
        mn.schedule.week_view,
        mn.resources_day_view,
        mn.resources_week_view,
    ],
)
def test_schedule_drag_resize_intervals(factory) -> None:
    comp = factory(
        events=[],
        event_drag_interval=15,
        event_resize_interval=15,
        with_interactive_background_events=True,
    )
    assert {
        "eventDragInterval",
        "eventResizeInterval",
        "withInteractiveBackgroundEvents",
    } <= _props(comp)


@pytest.mark.parametrize("factory", [mn.schedule.month_view, mn.schedule])
def test_schedule_interactive_background_events(factory) -> None:
    comp = factory(events=[], with_interactive_background_events=True)
    assert "withInteractiveBackgroundEvents" in _props(comp)


def test_notifications_render_notification_prop() -> None:
    comp = mn.notifications_provider(layout="stacked", render_notification=None)
    assert "layout" in _props(comp)
    assert "render_notification" in mn.notifications_provider().get_fields()


def test_dropzone_react_dropzone_20() -> None:
    assert REACT_DROPZONE_LIBRARY == "react-dropzone@20.1.2"


def test_tiptap_new_control_groups() -> None:
    assert "tableInsert" in ToolbarControlGroup.TABLE.value
    assert ToolbarControlGroup.DETAILS.value == ["details"]
    assert ToolbarControlGroup.INVISIBLE_CHARACTERS.value == ["invisibleCharacters"]
    assert {"tableSplitCell", "details", "invisibleCharacters"} <= set(
        ToolbarControlGroup.ALL.value
    )
    deps = RichTextEditor.lib_dependencies
    for package in ("table", "details", "invisible-characters"):
        assert any(d.startswith(f"@tiptap/extension-{package}@") for d in deps)
