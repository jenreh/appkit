"""MapCN root Map + Controls components (https://mapcn.dev).

MapCN is a MapLibre GL-powered map library. These wrappers port
https://mapcn.dev's React components as Reflex components, bundled as a
local JSX asset (see ``maps.jsx``).

Compose a map from the ``mn.map`` namespace::

    mn.map(
        center=[-74.006, 40.7128],
        zoom=11,
        children=[
            mn.map.controls(show_zoom=True, show_compass=True),
            mn.map.marker(
                longitude=-74.006,
                latitude=40.7128,
                children=[
                    mn.marker.content(),
                    mn.marker.popup(children=[mn.marker.label("NYC")]),
                ],
            ),
        ],
    )

Sub-components are exposed as namespace attributes:

- ``mn.map.controls`` — :class:`MapControls`
- ``mn.map.marker`` — :class:`~appkit_mantine.maps_markers.MapMarker`
- ``mn.map.popup`` — :class:`~appkit_mantine.maps_popups.MapPopup`
- ``mn.map.route`` — :class:`~appkit_mantine.maps_layers.MapRoute`
- ``mn.map.arc`` — :class:`~appkit_mantine.maps_layers.MapArc`
- ``mn.map.geojson`` — :class:`~appkit_mantine.maps_layers.MapGeoJSON`
- ``mn.map.cluster`` — :class:`~appkit_mantine.maps_layers.MapClusterLayer`
- ``mn.map.navigation`` — :class:`~appkit_mantine.maps_navigation.MapNavigation`
  (real driving/walking/cycling routing via an OSRM-compatible API)
- ``mn.map.directions_panel`` —
  :class:`~appkit_mantine.maps_navigation.MapDirectionsPanel`

Marker sub-components use the separate ``mn.marker`` namespace (``content``,
``popup``, ``tooltip``, ``label``).

Note:
    Unlike most ``appkit_mantine`` components, ``Map`` does not accept
    Mantine layout props (``w``, ``h``, ...). Size it by wrapping it in a
    container with an explicit height, matching mapcn's own usage pattern::

        rx.box(mn.map(center=[...], zoom=11), height="400px", width="100%")
"""

from __future__ import annotations

from typing import Any, Literal

import reflex as rx
from reflex.event import EventHandler
from reflex.vars.base import Var

from appkit_mantine.maps_base import MapComponentBase, MapControlPosition
from appkit_mantine.maps_layers import MapArc, MapClusterLayer, MapGeoJSON, MapRoute
from appkit_mantine.maps_markers import MapMarker
from appkit_mantine.maps_navigation import MapDirectionsPanel, MapNavigation
from appkit_mantine.maps_popups import MapPopup


class Map(MapComponentBase):
    """Root container. Initializes MapLibre GL and provides context to children.

    Automatically handles theme switching between light and dark modes.
    """

    tag = "Map"

    _rename_props = {
        "class_name": "className",
        "on_viewport_change": "onViewportChange",
    }

    class_name: Var[str] = None
    """Additional CSS class for the map container."""

    theme: Var[Literal["light", "dark"]] = None
    """Theme for the map.

    Auto-detects from document class or system preference if unset.
    """

    styles: Var[dict[str, Any]] = None
    """Custom map styles for light/dark themes: ``{"light": ..., "dark": ...}``.

    Overrides the default Carto base map tiles. Values may be a style URL or
    a MapLibre style spec dict.
    """

    blank: Var[bool] = None
    """Use a transparent, tile-less basemap instead of the default Carto basemap.

    Renders nothing on its own — add layers (``MapGeoJSON``, ``MapArc``,
    markers) on top. Ideal for data visualizations. Ignored when ``styles``
    is provided.
    """

    projection: Var[dict[str, Any]] = None
    """Map projection. Use ``{"type": "globe"}`` for a 3D globe view."""

    center: Var[list[float]] = None
    """Initial/controlled center coordinate as ``[longitude, latitude]``."""

    zoom: Var[int | float] = None
    """Initial/controlled zoom level."""

    viewport: Var[dict[str, Any]] = None
    """Controlled viewport state (``center``, ``zoom``, ``bearing``, ``pitch``).

    Used together with ``on_viewport_change`` to fully control the map from
    Reflex State.
    """

    loading: Var[bool] = None
    """Show a loading indicator on the map."""

    on_viewport_change: EventHandler[lambda viewport: [viewport]] = None
    """Fired continuously as the viewport changes (pan, zoom, rotate, pitch)."""


class MapControls(MapComponentBase):
    """Zoom, compass, locate, and fullscreen control buttons.

    Must be used inside ``Map``.
    """

    tag = "MapControls"

    _rename_props = {
        "class_name": "className",
        "show_zoom": "showZoom",
        "show_compass": "showCompass",
        "show_locate": "showLocate",
        "show_fullscreen": "showFullscreen",
        "on_locate": "onLocate",
    }

    position: Var[MapControlPosition] = None
    """Position of the controls on the map (default: ``"bottom-right"``)."""

    show_zoom: Var[bool] = None
    """Show zoom in/out buttons (default: True)."""

    show_compass: Var[bool] = None
    """Show compass button to reset bearing (default: False)."""

    show_locate: Var[bool] = None
    """Show locate button to find the user's location (default: False)."""

    show_fullscreen: Var[bool] = None
    """Show fullscreen toggle button (default: False)."""

    class_name: Var[str] = None
    """Additional CSS class for the controls container."""

    on_locate: EventHandler[lambda coords: [coords]] = None
    """Fired with the user's coordinates when located."""


class MapNamespace(rx.ComponentNamespace):
    """Namespace for MapCN map components.

    ``mn.map(...)`` renders the root :class:`Map`; sub-attributes render the
    remaining MapCN components (controls, markers, popups, routes, arcs,
    GeoJSON layers, and clusters).
    """

    __call__ = staticmethod(Map.create)
    controls = staticmethod(MapControls.create)
    marker = staticmethod(MapMarker.create)
    popup = staticmethod(MapPopup.create)
    route = staticmethod(MapRoute.create)
    arc = staticmethod(MapArc.create)
    geojson = staticmethod(MapGeoJSON.create)
    cluster = staticmethod(MapClusterLayer.create)
    navigation = staticmethod(MapNavigation.create)
    directions_panel = staticmethod(MapDirectionsPanel.create)


map = MapNamespace()  # noqa: A001
