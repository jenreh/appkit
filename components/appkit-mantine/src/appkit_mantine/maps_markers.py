"""MapCN marker sub-components (https://mapcn.dev/docs/markers).

``MapMarker`` is a positioning container; its children compose the marker's
visual appearance and interactions:

- :class:`MarkerContent` — the visual marker (defaults to a blue dot).
- :class:`MarkerPopup` — a popup shown on click.
- :class:`MarkerTooltip` — a tooltip shown on hover.
- :class:`MarkerLabel` — a text label above/below the marker (used inside
  ``MarkerContent``).

Use via the ``mn.map`` / ``mn.marker`` namespaces::

    mn.map.marker(
        longitude=-74.006,
        latitude=40.7128,
        children=[
            mn.marker.content(),
            mn.marker.popup(children=[mn.marker.label("NYC")]),
        ],
    )
"""

from __future__ import annotations

from typing import Literal

import reflex as rx
from reflex.event import EventHandler
from reflex.vars.base import Var

from appkit_mantine.maps_base import MapComponentBase


class MapMarker(MapComponentBase):
    """A positioned marker container. Provides context for its children.

    Extends MapLibre GL's ``MarkerOptions`` (excluding ``element``).
    """

    tag = "MapMarker"

    _rename_props = {
        "on_click": "onClick",
        "on_mouse_enter": "onMouseEnter",
        "on_mouse_leave": "onMouseLeave",
        "on_drag_start": "onDragStart",
        "on_drag": "onDrag",
        "on_drag_end": "onDragEnd",
    }

    longitude: Var[int | float]
    """Longitude coordinate for marker position."""

    latitude: Var[int | float]
    """Latitude coordinate for marker position."""

    draggable: Var[bool] = None
    """Whether the marker can be dragged."""

    offset: Var[list[float]] = None
    """Marker offset as ``[x, y]`` pixels."""

    rotation: Var[int | float] = None
    """Marker rotation in degrees."""

    rotation_alignment: Var[Literal["map", "viewport", "horizon", "auto"]] = None
    pitch_alignment: Var[Literal["map", "viewport", "auto"]] = None

    on_click: EventHandler[lambda e: [e]] = None
    on_mouse_enter: EventHandler[lambda e: [e]] = None
    on_mouse_leave: EventHandler[lambda e: [e]] = None
    on_drag_start: EventHandler[lambda lng_lat: [lng_lat]] = None
    on_drag: EventHandler[lambda lng_lat: [lng_lat]] = None
    on_drag_end: EventHandler[lambda lng_lat: [lng_lat]] = None


class MarkerContent(MapComponentBase):
    """Visual content of a marker. Must be used inside :class:`MapMarker`.

    Renders a default blue dot if no children are provided.
    """

    tag = "MarkerContent"

    _rename_props = {"class_name": "className"}

    class_name: Var[str] = None
    """Additional CSS class for the marker container."""


class MarkerPopup(MapComponentBase):
    """Popup attached to a marker, opens on click.

    Extends MapLibre GL's ``PopupOptions`` (excluding ``className`` and
    ``closeButton``, which are exposed via this component's own props).
    """

    tag = "MarkerPopup"

    _rename_props = {"class_name": "className"}

    class_name: Var[str] = None
    """Additional CSS class for the popup container."""

    close_button: Var[bool] = None
    """Show a close button in the popup (default: False)."""

    offset: Var[float | list[float]] = None
    max_width: Var[str] = None


class MarkerTooltip(MapComponentBase):
    """Tooltip shown on hover. Must be used inside :class:`MapMarker`."""

    tag = "MarkerTooltip"

    _rename_props = {"class_name": "className"}

    class_name: Var[str] = None
    """Additional CSS class for the tooltip container."""

    offset: Var[float | list[float]] = None
    max_width: Var[str] = None


class MarkerLabel(MapComponentBase):
    """Text label above or below a marker. Must be used inside ``MarkerContent``."""

    tag = "MarkerLabel"

    _rename_props = {"class_name": "className"}

    class_name: Var[str] = None
    """Additional CSS class for the label."""

    position: Var[Literal["top", "bottom"]] = None
    """Position of the label relative to the marker (default: ``"top"``)."""


class MarkerNamespace(rx.ComponentNamespace):
    """Namespace for marker sub-components: ``mn.marker.content(...)``, etc."""

    content = staticmethod(MarkerContent.create)
    popup = staticmethod(MarkerPopup.create)
    tooltip = staticmethod(MarkerTooltip.create)
    label = staticmethod(MarkerLabel.create)


marker = MarkerNamespace()

__all__: list[str] = [
    "MapMarker",
    "MarkerContent",
    "MarkerLabel",
    "MarkerNamespace",
    "MarkerPopup",
    "MarkerTooltip",
    "marker",
]
