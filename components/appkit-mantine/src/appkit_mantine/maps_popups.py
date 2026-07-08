"""MapCN standalone popup component (https://mapcn.dev/docs/popups).

A popup that can be placed anywhere on the map, not attached to a marker.
Used via ``mn.map.popup(...)``.
"""

from __future__ import annotations

import reflex as rx
from reflex.event import EventHandler
from reflex.vars.base import Var

from appkit_mantine.maps_base import MapComponentBase


class MapPopup(MapComponentBase):
    """A standalone popup placed at a coordinate. Must be used inside ``Map``."""

    tag = "MapPopup"

    _rename_props = {
        "class_name": "className",
        "close_button": "closeButton",
        "max_width": "maxWidth",
        "on_close": "onClose",
    }

    longitude: Var[int | float]
    """Longitude coordinate for popup position."""

    latitude: Var[int | float]
    """Latitude coordinate for popup position."""

    class_name: Var[str] = None
    """Additional CSS class for the popup container."""

    close_button: Var[bool] = None
    """Show a close button in the popup (default: False)."""

    offset: Var[float | list[float]] = None
    max_width: Var[str] = None

    on_close: EventHandler[rx.event.no_args_event_spec] = None
    """Called when the popup is closed."""
