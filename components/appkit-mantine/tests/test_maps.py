"""Tests for the MapCN (https://mapcn.dev) map component wrappers.

Covers component tags, prop aliasing (snake_case -> camelCase), namespace
factories (``mn.map``, ``mn.marker``), and event trigger wiring for the 11
MapCN components: Map, MapControls, MapMarker, MarkerContent, MarkerPopup,
MarkerTooltip, MarkerLabel, MapPopup, MapRoute, MapArc, MapGeoJSON, and
MapClusterLayer.
"""

from __future__ import annotations

import reflex as rx

import appkit_mantine as mn
from appkit_mantine.maps import Map, MapControls
from appkit_mantine.maps_base import (
    MAPLIBRE_GL_DEPENDENCY,
    MapComponentBase,
    MapConfigNode,
)
from appkit_mantine.maps_layers import MapArc, MapClusterLayer, MapGeoJSON, MapRoute
from appkit_mantine.maps_markers import MapMarker
from appkit_mantine.maps_navigation import MapDirectionsPanel, MapNavigation
from appkit_mantine.maps_popups import MapPopup


def _rendered(component) -> dict:
    return component.render()


def _prop_names(component) -> set[str]:
    """Return the JSX prop names emitted for a component."""
    props = _rendered(component).get("props", [])
    return {entry.split(":", 1)[0] for entry in props}


def _tag(component) -> str:
    return _rendered(component).get("name", "")


# ---------------------------------------------------------------------------
# Base plumbing
# ---------------------------------------------------------------------------


def test_map_component_base_uses_local_jsx_asset() -> None:
    library = MapComponentBase().library
    assert library is not None
    assert "maps.jsx" in library or library.startswith("$/public")


def test_map_component_base_depends_on_maplibre_gl() -> None:
    assert MAPLIBRE_GL_DEPENDENCY in MapComponentBase.lib_dependencies


# ---------------------------------------------------------------------------
# Map
# ---------------------------------------------------------------------------


def test_map_renders_with_default_props() -> None:
    component = mn.map(center=[-74.006, 40.7128], zoom=11)
    assert _tag(component) == "Map"
    assert {"center", "zoom"} <= _prop_names(component)


def test_map_class_name_prop_renamed() -> None:
    assert "className" in _prop_names(mn.map(class_name="custom-map"))


def test_map_blank_and_theme_props() -> None:
    props = _prop_names(mn.map(blank=True, theme="dark"))
    assert {"blank", "theme"} <= props


def test_map_viewport_control_props() -> None:
    props = _prop_names(mn.map(viewport={"center": [0, 0], "zoom": 2}))
    assert "viewport" in props


def test_map_on_viewport_change_event_trigger() -> None:
    triggers = Map.get_event_triggers()
    assert "on_viewport_change" in triggers


def test_map_on_viewport_change_prop_renamed() -> None:
    props = _prop_names(mn.map(on_viewport_change=rx.console_log("viewport changed")))
    assert "onViewportChange" in props


# ---------------------------------------------------------------------------
# MapControls
# ---------------------------------------------------------------------------


def test_map_controls_tag() -> None:
    assert _tag(mn.map.controls()) == "MapControls"


def test_map_controls_selective_visibility_props_renamed() -> None:
    props = _prop_names(
        mn.map.controls(
            show_zoom=True,
            show_compass=False,
            show_locate=True,
            show_fullscreen=True,
        )
    )
    assert {"showZoom", "showCompass", "showLocate", "showFullscreen"} <= props


def test_map_controls_position_prop() -> None:
    assert "position" in _prop_names(mn.map.controls(position="top-left"))


def test_map_controls_on_locate_event_trigger() -> None:
    assert "on_locate" in MapControls.get_event_triggers()


# ---------------------------------------------------------------------------
# MapMarker + marker sub-components
# ---------------------------------------------------------------------------


def test_map_marker_positioning() -> None:
    component = mn.map.marker(longitude=-74.006, latitude=40.7128)
    assert _tag(component) == "MapMarker"
    assert {"longitude", "latitude"} <= _prop_names(component)


def test_map_marker_event_props_renamed() -> None:
    props = _prop_names(
        mn.map.marker(
            longitude=0,
            latitude=0,
            on_click=rx.console_log("click"),
            on_drag_start=rx.console_log("drag start"),
            on_drag_end=rx.console_log("drag end"),
        )
    )
    assert {"onClick", "onDragStart", "onDragEnd"} <= props


def test_map_marker_event_triggers() -> None:
    triggers = set(MapMarker.get_event_triggers())
    expected = {
        "on_click",
        "on_mouse_enter",
        "on_mouse_leave",
        "on_drag",
        "on_drag_start",
        "on_drag_end",
    }
    assert expected <= triggers


def test_marker_content_default_and_class_name() -> None:
    assert _tag(mn.marker.content()) == "MarkerContent"
    assert "className" in _prop_names(mn.marker.content(class_name="dot"))


def test_marker_popup_close_button_prop() -> None:
    component = mn.marker.popup(mn.text("hi"), close_button=True)
    assert _tag(component) == "MarkerPopup"
    assert "closeButton" in _prop_names(component)


def test_marker_tooltip_tag() -> None:
    assert _tag(mn.marker.tooltip(mn.text("tip"))) == "MarkerTooltip"


def test_marker_label_position_prop() -> None:
    component = mn.marker.label("NYC", position="bottom")
    assert _tag(component) == "MarkerLabel"
    assert "position" in _prop_names(component)


# ---------------------------------------------------------------------------
# MapPopup
# ---------------------------------------------------------------------------


def test_map_popup_tag_and_props() -> None:
    component = mn.map.popup(longitude=-74.0, latitude=40.7, close_button=True)
    assert _tag(component) == "MapPopup"
    assert {"longitude", "latitude", "closeButton"} <= _prop_names(component)


def test_map_popup_on_close_event_trigger() -> None:
    assert "on_close" in MapPopup.get_event_triggers()


# ---------------------------------------------------------------------------
# MapRoute
# ---------------------------------------------------------------------------


def test_map_route_coordinates_and_defaults() -> None:
    component = mn.map.route(coordinates=[[-74.0, 40.7], [-73.9, 40.6]])
    assert _tag(component) == "MapRoute"
    assert "coordinates" in _prop_names(component)


def test_map_route_dash_array_renamed() -> None:
    props = _prop_names(mn.map.route(coordinates=[[0, 0], [1, 1]], dash_array=[2, 4]))
    assert "dashArray" in props


def test_map_route_event_triggers() -> None:
    triggers = MapRoute.get_event_triggers()
    assert {"on_click", "on_mouse_enter", "on_mouse_leave"} <= set(triggers)


# ---------------------------------------------------------------------------
# MapArc
# ---------------------------------------------------------------------------


def test_map_arc_data_prop() -> None:
    data = [{"id": 1, "from": [-74.0, 40.7], "to": [-118.2, 34.0]}]
    component = mn.map.arc(data=data)
    assert _tag(component) == "MapArc"
    assert "data" in _prop_names(component)


def test_map_arc_hover_paint_and_before_id_renamed() -> None:
    props = _prop_names(
        mn.map.arc(data=[], hover_paint={"line-color": "#fff"}, before_id="water")
    )
    assert {"hoverPaint", "beforeId"} <= props


def test_map_arc_event_triggers() -> None:
    assert {"on_click", "on_hover"} <= set(MapArc.get_event_triggers())


# ---------------------------------------------------------------------------
# MapGeoJSON
# ---------------------------------------------------------------------------


def test_map_geojson_data_prop() -> None:
    data = {"type": "FeatureCollection", "features": []}
    component = mn.map.geojson(data=data)
    assert _tag(component) == "MapGeoJSON"
    assert "data" in _prop_names(component)


def test_map_geojson_paint_props_renamed() -> None:
    props = _prop_names(
        mn.map.geojson(
            data="https://example.com/data.geojson",
            promote_id="code",
            fill_paint={"fill-color": "#000"},
            line_paint=False,
            fill_hover_paint={"fill-color": "#fff"},
        )
    )
    assert {"promoteId", "fillPaint", "linePaint", "fillHoverPaint"} <= props


def test_map_geojson_event_triggers() -> None:
    assert {"on_click", "on_hover"} <= set(MapGeoJSON.get_event_triggers())


# ---------------------------------------------------------------------------
# MapClusterLayer
# ---------------------------------------------------------------------------


def test_map_cluster_layer_data_prop() -> None:
    data = {"type": "FeatureCollection", "features": []}
    component = mn.map.cluster(data=data)
    assert _tag(component) == "MapClusterLayer"
    assert "data" in _prop_names(component)


def test_map_cluster_layer_props_renamed() -> None:
    props = _prop_names(
        mn.map.cluster(
            data={"type": "FeatureCollection", "features": []},
            cluster_max_zoom=10,
            cluster_radius=40,
            cluster_colors=["#0f0", "#ff0", "#f00"],
            cluster_thresholds=[50, 500],
            point_color="#123456",
        )
    )
    assert {
        "clusterMaxZoom",
        "clusterRadius",
        "clusterColors",
        "clusterThresholds",
        "pointColor",
    } <= props


def test_map_cluster_layer_event_triggers() -> None:
    assert {"on_point_click", "on_cluster_click"} <= set(
        MapClusterLayer.get_event_triggers()
    )


# ---------------------------------------------------------------------------
# MapNavigation / MapDirectionsPanel (real routing via OSRM-compatible API)
# ---------------------------------------------------------------------------


def test_map_navigation_is_a_config_node() -> None:
    assert issubclass(MapNavigation, MapConfigNode)
    assert issubclass(MapDirectionsPanel, MapConfigNode)


def test_map_navigation_tag_and_required_props() -> None:
    component = mn.map.navigation(
        start_lat=40.7128, start_long=-74.006, end_lat=42.3601, end_long=-71.0589
    )
    assert _tag(component) == "VoyagerMapLibreNavigation"
    props = _prop_names(component)
    assert {"startLat", "startLong", "endLat", "endLong"} <= props


def test_map_navigation_props_renamed_to_camel_case() -> None:
    component = mn.map.navigation(
        start_lat=40.7128,
        start_long=-74.006,
        end_lat=42.3601,
        end_long=-71.0589,
        routing_url="https://osrm.example.com",
        line_color="#6366f1",
        line_width=5,
        line_opacity=0.9,
        line_dasharray=[2, 4],
        fit_bounds=True,
        fit_bounds_padding=48,
        fit_bounds_max_zoom=14,
        fit_bounds_duration_ms=800,
        continue_straight=True,
        include_steps=True,
        include_geometry=True,
        show_end_markers=True,
        start_marker_color="#22c55e",
        end_marker_color="#ef4444",
        marker_radius=8,
    )
    props = _prop_names(component)
    assert {
        "routingUrl",
        "lineColor",
        "lineWidth",
        "lineOpacity",
        "lineDasharray",
        "fitBounds",
        "fitBoundsPadding",
        "fitBoundsMaxZoom",
        "fitBoundsDurationMs",
        "continueStraight",
        "includeSteps",
        "includeGeometry",
        "showEndMarkers",
        "startMarkerColor",
        "endMarkerColor",
        "markerRadius",
    } <= props


def test_map_navigation_profiles_and_alternatives() -> None:
    component = mn.map.navigation(
        start_lat=40.7128,
        start_long=-74.006,
        end_lat=42.3601,
        end_long=-71.0589,
        profiles=["driving", "walking", "cycling"],
        alternatives=True,
    )
    props = _prop_names(component)
    assert {"profiles", "alternatives"} <= props


def test_map_directions_panel_tag_and_defaults() -> None:
    component = mn.map.directions_panel()
    assert _tag(component) == "VoyagerMapLibreDirectionsPanel"


def test_map_directions_panel_props_renamed_to_camel_case() -> None:
    component = mn.map.directions_panel(
        title="Directions",
        empty_text="No route yet",
        show_summary=True,
        show_steps=True,
        max_height=320,
        width=280,
        offset_top=16,
        offset_left=16,
        dock_below_zoom_controls=True,
        zoom_controls_gap_rem=6,
        collapsible=True,
        initially_collapsed=False,
        collapse_direction="bottom",
        position="top-left",
    )
    props = _prop_names(component)
    assert {
        "emptyText",
        "showSummary",
        "showSteps",
        "maxHeight",
        "offsetTop",
        "offsetLeft",
        "dockBelowZoomControls",
        "zoomControlsGapRem",
        "initiallyCollapsed",
        "collapseDirection",
        "position",
    } <= props


def test_map_navigation_and_directions_panel_compose_inside_map() -> None:
    component = mn.map(
        mn.map.navigation(
            start_lat=40.7128,
            start_long=-74.006,
            end_lat=42.3601,
            end_long=-71.0589,
            profiles=["driving", "walking"],
            alternatives=True,
        ),
        mn.map.directions_panel(title="Directions", show_steps=True),
        center=[-72.5, 41.5],
        zoom=6.5,
    )
    assert _tag(component) == "Map"
    tags = {_tag(child) for child in component.children}
    assert {"VoyagerMapLibreNavigation", "VoyagerMapLibreDirectionsPanel"} <= tags


# ---------------------------------------------------------------------------
# Full composition (no exceptions during construction)
# ---------------------------------------------------------------------------


def test_full_map_composition_renders() -> None:
    component = mn.map(
        mn.map.controls(show_zoom=True, show_compass=True),
        mn.map.marker(
            mn.marker.content(),
            mn.marker.popup(mn.marker.label("NYC")),
            longitude=-74.006,
            latitude=40.7128,
        ),
        mn.map.route(coordinates=[[-74.0, 40.7], [-73.9, 40.6]]),
        mn.map.arc(data=[{"id": 1, "from": [-74.0, 40.7], "to": [-118.2, 34.0]}]),
        mn.map.geojson(data={"type": "FeatureCollection", "features": []}),
        mn.map.cluster(data={"type": "FeatureCollection", "features": []}),
        mn.map.popup(mn.text("hi"), longitude=-74.0, latitude=40.7),
        center=[-74.006, 40.7128],
        zoom=11,
    )
    rendered = _rendered(component)
    assert rendered["name"] == "Map"
