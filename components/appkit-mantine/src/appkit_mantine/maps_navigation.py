"""Real-routing navigation components for MapCN maps.

``MapNavigation`` fetches turn-by-turn driving/walking/cycling directions
from an OSRM-compatible routing API (default: the public
`router.project-osrm.org` demo server — replace ``routing_url`` with your
own OSRM/Valhalla-compatible instance for production use), draws the
resulting route(s) on the map, and publishes the fetched data via context.
``MapDirectionsPanel`` reads that shared context and renders a summary +
turn-by-turn panel; it does not need to be nested inside ``MapNavigation``,
only used as another child of the same ``Map``.

Example::

    mn.map(
        mn.map.controls(show_zoom=True),
        mn.map.navigation(
            start_lat=40.7128,
            start_long=-74.006,
            end_lat=42.3601,
            end_long=-71.0589,
            profiles=["driving", "walking", "cycling"],
            alternatives=True,
        ),
        mn.map.directions_panel(title="Directions", show_steps=True),
        center=[-72.5, 41.5],
        zoom=6.5,
    )
"""

from __future__ import annotations

from typing import Literal

from reflex.vars.base import Var

from appkit_mantine.maps_base import MapConfigNode, MapControlPosition


class MapNavigation(MapConfigNode):
    """Navigation route config node consumed by ``Map``.

    Fetches route(s) between two coordinates from an OSRM-compatible
    routing API and renders them as line layers on the map.
    """

    tag = "VoyagerMapLibreNavigation"

    _rename_props = {
        "start_lat": "startLat",
        "start_long": "startLong",
        "end_lat": "endLat",
        "end_long": "endLong",
        "routing_url": "routingUrl",
        "line_color": "lineColor",
        "line_width": "lineWidth",
        "line_opacity": "lineOpacity",
        "line_dasharray": "lineDasharray",
        "fit_bounds": "fitBounds",
        "fit_bounds_padding": "fitBoundsPadding",
        "fit_bounds_max_zoom": "fitBoundsMaxZoom",
        "fit_bounds_duration_ms": "fitBoundsDurationMs",
        "continue_straight": "continueStraight",
        "include_steps": "includeSteps",
        "include_geometry": "includeGeometry",
        "show_end_markers": "showEndMarkers",
        "start_marker_color": "startMarkerColor",
        "end_marker_color": "endMarkerColor",
        "marker_radius": "markerRadius",
    }

    start_lat: Var[float | int]
    """Latitude of the route start point."""

    start_long: Var[float | int]
    """Longitude of the route start point."""

    end_lat: Var[float | int]
    """Latitude of the route end point."""

    end_long: Var[float | int]
    """Longitude of the route end point."""

    profile: Var[Literal["driving", "walking", "cycling"] | None] = Var.create(None)
    """Single routing profile (default: ``"driving"``).

    Ignored if ``profiles`` is set.
    """

    profiles: Var[list[Literal["driving", "walking", "cycling"]] | None] = Var.create(
        None
    )
    """Multiple profiles to fetch; lets ``MapDirectionsPanel`` offer a mode switch."""

    routing_url: Var[str | None] = Var.create(None)
    """Base URL of an OSRM-compatible routing API.

    Defaults to the public ``https://router.project-osrm.org`` demo server.
    """

    alternatives: Var[bool | None] = Var.create(None)
    """Request alternative routes for the active profile (OSRM ``alternatives``)."""

    overview: Var[Literal["full", "simplified", "false"] | None] = Var.create(None)
    """Geometry overview detail level (OSRM ``overview``, default: ``"full"``)."""

    geometries: Var[Literal["geojson", "polyline", "polyline6"] | None] = Var.create(
        None
    )
    """Geometry encoding requested from the routing API (default: ``"geojson"``)."""

    steps: Var[bool | None] = Var.create(None)
    """Request turn-by-turn step data from the routing API (OSRM ``steps``)."""

    line_color: Var[str | None] = Var.create(None)
    """Color of the selected route line (default: ``"#4285F4"``)."""

    line_width: Var[float | int | None] = Var.create(None)
    """Width of the selected route line in pixels (default: 5)."""

    line_opacity: Var[float | int | None] = Var.create(None)
    """Opacity of the selected route line (default: 0.85)."""

    line_dasharray: Var[list[float] | None] = Var.create(None)
    """Dash pattern ``[dash length, gap length]`` for the route line."""

    fit_bounds: Var[bool | None] = Var.create(None)
    """Fit the map viewport to the route bounds once loaded (default: True)."""

    fit_bounds_padding: Var[float | int | None] = Var.create(None)
    """Padding in pixels applied when fitting bounds (default: 48)."""

    fit_bounds_max_zoom: Var[float | int | None] = Var.create(None)
    """Maximum zoom level to fit bounds to."""

    fit_bounds_duration_ms: Var[float | int | None] = Var.create(None)
    """Animation duration in milliseconds for the fit-bounds transition."""

    continue_straight: Var[bool | None] = Var.create(None)
    """Forces the route to continue straight at the start point (OSRM option)."""

    annotations: Var[
        bool
        | list[
            Literal[
                "duration",
                "distance",
                "speed",
                "nodes",
                "datasources",
                "weight",
            ]
        ]
        | None
    ] = Var.create(None)
    """Additional per-segment metadata to request from the routing API."""

    exclude: Var[list[str] | None] = Var.create(None)
    """Road classes to exclude from routing.

    E.g. ``["motorway"]``; supported values are profile-dependent.
    """

    include_steps: Var[bool | None] = Var.create(None)
    """Keep turn-by-turn steps in the published navigation state (default: True)."""

    include_geometry: Var[bool | None] = Var.create(None)
    """Keep full route geometry in the published navigation state (default: True)."""

    show_end_markers: Var[bool | None] = Var.create(None)
    """Render start/end markers at the route endpoints (default: True)."""

    start_marker_color: Var[str | None] = Var.create(None)
    """Color of the start marker (default: ``"#22c55e"``)."""

    end_marker_color: Var[str | None] = Var.create(None)
    """Color of the end marker (default: ``"#ef4444"``)."""

    marker_radius: Var[float | int | None] = Var.create(None)
    """Radius (size) of the start/end markers (default: 8)."""


class MapDirectionsPanel(MapConfigNode):
    """Directions panel config node consumed by ``Map``.

    Reads the navigation state published by a sibling ``MapNavigation`` and
    renders a route summary, profile/alternative switcher, and optional
    turn-by-turn step list as an overlay on the map.
    """

    tag = "VoyagerMapLibreDirectionsPanel"

    _rename_props = {
        "empty_text": "emptyText",
        "show_summary": "showSummary",
        "show_steps": "showSteps",
        "max_height": "maxHeight",
        "offset_top": "offsetTop",
        "offset_left": "offsetLeft",
        "dock_below_zoom_controls": "dockBelowZoomControls",
        "zoom_controls_gap_rem": "zoomControlsGapRem",
        "initially_collapsed": "initiallyCollapsed",
        "collapse_direction": "collapseDirection",
    }

    title: Var[str | None] = Var.create(None)
    """Panel header title (default: ``"Directions"``)."""

    empty_text: Var[str | None] = Var.create(None)
    """Text shown while no navigation state is available yet."""

    show_summary: Var[bool | None] = Var.create(None)
    """Show the duration/distance summary for the selected route (default: True)."""

    show_steps: Var[bool | None] = Var.create(None)
    """Show the turn-by-turn step list for the selected route (default: True)."""

    max_height: Var[float | int | None] = Var.create(None)
    """Maximum height in pixels of the scrollable panel body."""

    width: Var[float | int | str | None] = Var.create(None)
    """Panel width (number treated as pixels, or any CSS size string)."""

    offset_top: Var[float | int | None] = Var.create(None)
    """Explicit top offset in pixels, overriding the default corner position."""

    offset_left: Var[float | int | None] = Var.create(None)
    """Explicit left offset in pixels, overriding the default corner position."""

    dock_below_zoom_controls: Var[bool | None] = Var.create(None)
    """Position the panel just below the zoom controls instead of a fixed offset."""

    zoom_controls_gap_rem: Var[float | int | None] = Var.create(None)
    """Gap in rem between the zoom controls and the panel when docked."""

    collapsible: Var[bool | None] = Var.create(None)
    """Allow collapsing the panel body via its header (default: True)."""

    initially_collapsed: Var[bool | None] = Var.create(None)
    """Whether the panel body starts collapsed."""

    collapse_direction: Var[Literal["top", "bottom"] | None] = Var.create(None)
    """Direction the collapse chevron points when expanded."""

    position: Var[MapControlPosition | None] = Var.create(None)
    """Corner of the map to anchor the panel to (default: ``"top-left"``)."""
