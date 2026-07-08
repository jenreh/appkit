"""MapCN data-layer components (routes, arcs, GeoJSON, clusters).

See https://mapcn.dev/docs/routes, /docs/arcs, /docs/geojson, /docs/clusters.

Used inside :class:`appkit_mantine.maps.Map` (typically with ``blank=True``
for choropleths / dot-map / arc visualizations) via the ``mn.map`` namespace::

    mn.map(
        blank=True,
        children=[
            mn.map.geojson(data=world_geojson),
            mn.map.arc(data=connections),
        ],
    )
"""

from __future__ import annotations

from typing import Any

import reflex as rx
from reflex.event import EventHandler
from reflex.vars.base import Var

from appkit_mantine.maps_base import MapComponentBase


class MapRoute(MapComponentBase):
    """A line/route on the map connecting coordinate points."""

    tag = "MapRoute"

    _rename_props = {
        "dash_array": "dashArray",
        "on_click": "onClick",
        "on_mouse_enter": "onMouseEnter",
        "on_mouse_leave": "onMouseLeave",
    }

    id: Var[str] = None
    """Optional unique identifier for the route layer. Auto-generated if omitted."""

    coordinates: Var[list[list[float]]]
    """Array of ``[longitude, latitude]`` coordinate pairs."""

    color: Var[str] = None
    """Line color as a CSS color value (default: ``"#4285F4"``)."""

    width: Var[int | float] = None
    """Line width in pixels (default: 3)."""

    opacity: Var[int | float] = None
    """Line opacity from 0 to 1 (default: 0.8)."""

    dash_array: Var[list[float]] = None
    """Dash pattern ``[dash length, gap length]`` for dashed lines."""

    interactive: Var[bool] = None
    """Whether the route responds to mouse events (default: True)."""

    on_click: EventHandler[rx.event.no_args_event_spec] = None
    on_mouse_enter: EventHandler[rx.event.no_args_event_spec] = None
    on_mouse_leave: EventHandler[rx.event.no_args_event_spec] = None


class MapArc(MapComponentBase):
    """Curved connection arcs between coordinate pairs (quadratic Bézier)."""

    tag = "MapArc"

    _rename_props = {
        "hover_paint": "hoverPaint",
        "before_id": "beforeId",
        "on_click": "onClick",
        "on_hover": "onHover",
    }

    data: Var[list[dict[str, Any]]]
    """Arcs to render.

    Each needs a unique ``id`` and ``from``/``to`` as ``[lng, lat]``.
    """

    id: Var[str] = None
    """Id prefix for the underlying source/layers. Auto-generated if omitted."""

    curvature: Var[int | float] = None
    """How far the arc bows away from a straight line (default: 0.2)."""

    samples: Var[int] = None
    """Points per arc. Higher = smoother (default: 64)."""

    paint: Var[dict[str, Any]] = None
    """MapLibre line-layer paint props, merged over sensible defaults."""

    layout: Var[dict[str, Any]] = None
    """MapLibre line-layer layout props (defaults to rounded joins/caps)."""

    hover_paint: Var[dict[str, Any]] = None
    """Paint overrides applied to the hovered arc via feature-state."""

    interactive: Var[bool] = None
    """Whether arcs respond to mouse events (default: True)."""

    before_id: Var[str] = None
    """Insert the arc layers before this MapLibre layer id."""

    on_click: EventHandler[lambda e: [e]] = None
    on_hover: EventHandler[lambda e: [e]] = None


class MapGeoJSON(MapComponentBase):
    """Renders arbitrary GeoJSON as fill + outline layers.

    Typically used inside a ``blank`` :class:`~appkit_mantine.maps.Map` for
    choropleths and region/data maps.
    """

    tag = "MapGeoJSON"

    _rename_props = {
        "promote_id": "promoteId",
        "fill_paint": "fillPaint",
        "line_paint": "linePaint",
        "fill_hover_paint": "fillHoverPaint",
        "before_id": "beforeId",
        "on_click": "onClick",
        "on_hover": "onHover",
    }

    data: Var[dict[str, Any] | str]
    """GeoJSON data (FeatureCollection, Feature, Geometry) or a URL to fetch it from."""

    id: Var[str] = None
    """Id prefix for the underlying source/layers. Auto-generated if omitted."""

    promote_id: Var[str] = None
    """Feature property to promote to the feature id.

    Required for hover feature-state (``fill_hover_paint``) and stable
    ``on_hover``/``on_click`` payloads.
    """

    fill_paint: Var[dict[str, Any] | bool] = None
    """Paint for the polygon fill layer. Pass ``False`` to omit the fill layer."""

    line_paint: Var[dict[str, Any] | bool] = None
    """Paint for the outline layer. Pass ``False`` to omit the outline layer."""

    fill_hover_paint: Var[dict[str, Any]] = None
    """Paint merged onto the fill layer for the hovered feature.

    Requires ``promote_id``.
    """

    interactive: Var[bool] = None
    """Whether features respond to mouse events (default: False)."""

    before_id: Var[str] = None
    """Insert the layers before this MapLibre layer id."""

    on_click: EventHandler[lambda e: [e]] = None
    on_hover: EventHandler[lambda e: [e]] = None


class MapClusterLayer(MapComponentBase):
    """Clustered point data using MapLibre GL's native clustering."""

    tag = "MapClusterLayer"

    _rename_props = {
        "cluster_max_zoom": "clusterMaxZoom",
        "cluster_radius": "clusterRadius",
        "cluster_colors": "clusterColors",
        "cluster_thresholds": "clusterThresholds",
        "point_color": "pointColor",
        "on_point_click": "onPointClick",
        "on_cluster_click": "onClusterClick",
    }

    data: Var[dict[str, Any] | str]
    """GeoJSON FeatureCollection data or a URL to fetch GeoJSON from."""

    cluster_max_zoom: Var[int] = None
    """Maximum zoom level to cluster points on (default: 14)."""

    cluster_radius: Var[int] = None
    """Radius of each cluster in pixels (default: 50)."""

    cluster_colors: Var[list[str]] = None
    """Colors for cluster circles: [small, medium, large].

    Default: green/yellow/red.
    """

    cluster_thresholds: Var[list[int]] = None
    """Point count thresholds for color/size steps: [medium, large].

    Default: [100, 750].
    """

    point_color: Var[str] = None
    """Color for unclustered individual points (default: ``"#3b82f6"``)."""

    on_point_click: EventHandler[
        lambda feature, coordinates: [feature, coordinates]
    ] = None
    on_cluster_click: EventHandler[
        lambda cluster_id, coordinates, point_count: [
            cluster_id,
            coordinates,
            point_count,
        ]
    ] = None
