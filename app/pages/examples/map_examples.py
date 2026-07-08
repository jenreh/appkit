"""Examples demonstrating MapCN (https://mapcn.dev) map components in Reflex.

Showcases the ``mn.map`` / ``mn.marker`` namespaces: a basic map with
controls, draggable markers with popups, a route line, curved arcs, a
GeoJSON choropleth-style layer, and clustered points — all wired to Reflex
State for controlled viewport + marker management.
"""

from __future__ import annotations

from typing import Any

import reflex as rx

import appkit_mantine as mn
from appkit_user.authentication.templates import navbar_layout

from app.components.examples import example_box
from app.components.navbar import app_navbar

NYC: dict[str, Any] = {
    "id": 1,
    "lng": -74.006,
    "lat": 40.7128,
    "label": "New York City",
}
LA: dict[str, Any] = {"id": 2, "lng": -118.2437, "lat": 34.0522, "label": "Los Angeles"}
CHICAGO: dict[str, Any] = {"id": 3, "lng": -87.6298, "lat": 41.8781, "label": "Chicago"}

WORLD_GEOJSON_URL = (
    "https://cdn.jsdelivr.net/gh/nvkelso/natural-earth-vector@v5.1.2/"
    "geojson/ne_110m_admin_0_countries.geojson"
)

PLACES: list[dict[str, Any]] = [
    {
        "id": 1,
        "name": "The Metropolitan Museum of Art",
        "category": "Museum",
        "rating": 4.8,
        "reviews": 12453,
        "hours": "10:00 AM - 5:00 PM",
        "image": "https://images.unsplash.com/photo-1575223970966-76ae61ee7838?w=300&h=200&fit=crop",
        "lng": -73.9632,
        "lat": 40.7794,
    },
    {
        "id": 2,
        "name": "Brooklyn Bridge",
        "category": "Landmark",
        "rating": 4.9,
        "reviews": 8234,
        "hours": "Open 24 hours",
        "image": "https://images.unsplash.com/photo-1496588152823-86ff7695e68f?w=300&h=200&fit=crop",
        "lng": -73.9969,
        "lat": 40.7061,
    },
]

# Real driving/walking/cycling directions between New York and Boston,
# fetched live from an OSRM-compatible routing API by `mn.map.navigation`.
ROUTE_START: dict[str, Any] = {"name": "New York", "lng": -74.006, "lat": 40.7128}
ROUTE_END: dict[str, Any] = {"name": "Boston", "lng": -71.0589, "lat": 42.3601}


class MapExamplesState(rx.State):
    """State for the map component examples page."""

    viewport: dict = {
        "center": [-96.0, 38.0],
        "zoom": 3,
        "bearing": 0,
        "pitch": 0,
    }
    markers: list[dict] = [NYC, LA, CHICAGO]
    last_clicked_marker: str = ""
    popup_open_id: int = 0
    route_click_count: int = 0
    last_located: str = ""

    @rx.event
    def set_viewport(self, viewport: dict) -> None:
        self.viewport = viewport

    @rx.event
    def add_marker(self, coords: dict) -> None:
        next_id = max((m["id"] for m in self.markers), default=0) + 1
        self.markers.append(
            {
                "id": next_id,
                "lng": coords["longitude"],
                "lat": coords["latitude"],
                "label": f"Marker {next_id}",
            }
        )

    @rx.event
    def select_marker(self, label: str) -> None:
        self.last_clicked_marker = label

    @rx.event
    def increment_route_clicks(self) -> None:
        self.route_click_count += 1

    @rx.event
    def set_last_located(self, coords: dict) -> None:
        self.last_located = f"{coords['latitude']:.4f}, {coords['longitude']:.4f}"


ARC_DATA: list[dict[str, Any]] = [
    {"id": "nyc-la", "from": [NYC["lng"], NYC["lat"]], "to": [LA["lng"], LA["lat"]]},
    {
        "id": "nyc-chi",
        "from": [NYC["lng"], NYC["lat"]],
        "to": [CHICAGO["lng"], CHICAGO["lat"]],
    },
]

_CLUSTER_POINTS = [
    (-74.0 + i * 0.05, 40.7 + j * 0.05) for i in range(-3, 4) for j in range(-3, 4)
]

CLUSTER_DATA: dict[str, Any] = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {},
            "geometry": {"type": "Point", "coordinates": [lng, lat]},
        }
        for lng, lat in _CLUSTER_POINTS
    ],
}


def marker_dot(color: str = "#3b82f6", size: str = "16px") -> rx.Component:
    """A small circular marker dot.

    ``MarkerContent`` only renders its built-in default dot when given no
    children, so any marker that also needs a ``MarkerLabel`` (or other
    content) must render its own dot explicitly alongside it.
    """
    return rx.box(
        width=size,
        height=size,
        border_radius="50%",
        border="2px solid white",
        background=color,
        box_shadow="0 1px 3px rgba(0, 0, 0, 0.3)",
    )


def basic_map_example() -> rx.Component:
    return rx.box(
        mn.map(
            mn.map.controls(
                show_zoom=True,
                show_compass=True,
                show_locate=True,
                show_fullscreen=True,
                on_locate=MapExamplesState.set_last_located,
            ),
            center=[-74.006, 40.7128],
            zoom=10,
        ),
        height="420px",
        w="100%",
        style={"borderRadius": "8px", "overflow": "hidden"},
    )


def markers_and_popups_example() -> rx.Component:
    return rx.box(
        mn.map(
            mn.map.controls(show_zoom=True),
            rx.foreach(
                MapExamplesState.markers,
                lambda m: mn.map.marker(
                    mn.marker.content(marker_dot(), mn.marker.label(m["label"])),
                    mn.marker.popup(
                        mn.text(m["label"], fw=600, size="sm"),
                        close_button=True,
                    ),
                    longitude=m["lng"],
                    latitude=m["lat"],
                    draggable=True,
                    on_click=MapExamplesState.select_marker(m["label"]),
                ),
            ),
            center=[-95.0, 39.0],
            zoom=3,
        ),
        height="420px",
        w="100%",
        style={"borderRadius": "8px", "overflow": "hidden"},
    )


def route_and_arc_example() -> rx.Component:
    return rx.box(
        mn.map(
            mn.map.controls(show_zoom=True),
            mn.map.route(
                coordinates=[
                    [NYC["lng"], NYC["lat"]],
                    [CHICAGO["lng"], CHICAGO["lat"]],
                    [LA["lng"], LA["lat"]],
                ],
                color="#4285F4",
                width=4,
                on_click=MapExamplesState.increment_route_clicks,
            ),
            mn.map.arc(
                data=ARC_DATA,
                curvature=0.25,
                hover_paint={"line-color": "#ef4444"},
            ),
            mn.map.marker(
                mn.marker.content(), longitude=NYC["lng"], latitude=NYC["lat"]
            ),
            mn.map.marker(mn.marker.content(), longitude=LA["lng"], latitude=LA["lat"]),
            mn.map.marker(
                mn.marker.content(), longitude=CHICAGO["lng"], latitude=CHICAGO["lat"]
            ),
            center=[-95.0, 39.0],
            zoom=3,
        ),
        height="420px",
        w="100%",
        style={"borderRadius": "8px", "overflow": "hidden"},
    )


def _place_popup_card(place: dict[str, Any]) -> rx.Component:
    return mn.stack(
        rx.image(
            src=place["image"],
            height="110px",
            width="100%",
            style={"objectFit": "cover", "borderRadius": "6px"},
        ),
        mn.badge(place["category"], size="xs", variant="light", color="pink"),
        mn.text(place["name"], fw=600, size="sm"),
        mn.group(
            rx.icon("star", size=14, color="#f59e0b"),
            mn.text(str(place["rating"]), fw=600, size="xs"),
            mn.text(f"({place['reviews']:,})", c="gray", size="xs"),
            gap="4px",
        ),
        mn.group(
            rx.icon("clock", size=14),
            mn.text(place["hours"], size="xs", c="gray"),
            gap="4px",
        ),
        mn.button(
            rx.icon("navigation", size=14),
            "Directions",
            size="xs",
            width="100%",
            mt="4px",
        ),
        gap="6px",
    )


def custom_popup_example() -> rx.Component:
    """Rich, custom-styled popups (image, category, rating, actions)."""
    return rx.box(
        mn.map(
            mn.map.controls(show_zoom=True),
            *[
                mn.map.marker(
                    mn.marker.content(marker_dot(color="#f43f5e", size="18px")),
                    mn.marker.popup(_place_popup_card(place), close_button=True),
                    longitude=place["lng"],
                    latitude=place["lat"],
                )
                for place in PLACES
            ],
            center=[-73.98, 40.74],
            zoom=12,
        ),
        height="420px",
        w="100%",
        style={"borderRadius": "8px", "overflow": "hidden"},
    )


def route_planning_example() -> rx.Component:
    """Real driving/walking/cycling directions via ``mn.map.navigation``.

    Fetches live routes (with alternatives) from the public OSRM demo
    routing API and renders a turn-by-turn ``mn.map.directions_panel``
    overlay. See https://www.mapcn.dev/docs/routes#route-planning for the
    original mapcn demo this is modeled after — here the routing and
    directions UI are reusable ``Map`` config nodes instead of hand-rolled
    per-page logic.
    """
    return rx.box(
        mn.map(
            mn.map.controls(show_zoom=True),
            mn.map.navigation(
                start_lat=ROUTE_START["lat"],
                start_long=ROUTE_START["lng"],
                end_lat=ROUTE_END["lat"],
                end_long=ROUTE_END["lng"],
                profiles=["driving", "walking", "cycling"],
                alternatives=True,
            ),
            mn.map.directions_panel(
                title="Directions",
                show_steps=True,
                width=260,
            ),
            mn.map.marker(
                mn.marker.content(marker_dot(color="#22c55e")),
                mn.marker.label(ROUTE_START["name"], position="top"),
                longitude=ROUTE_START["lng"],
                latitude=ROUTE_START["lat"],
            ),
            mn.map.marker(
                mn.marker.content(marker_dot(color="#ef4444")),
                mn.marker.label(ROUTE_END["name"], position="bottom"),
                longitude=ROUTE_END["lng"],
                latitude=ROUTE_END["lat"],
            ),
            center=[-72.5, 41.5],
            zoom=6.5,
        ),
        height="420px",
        w="100%",
        style={"borderRadius": "8px", "overflow": "hidden", "position": "relative"},
    )


def geojson_example() -> rx.Component:
    return rx.box(
        mn.map(
            mn.map.controls(show_zoom=True),
            mn.map.geojson(
                data=WORLD_GEOJSON_URL,
                interactive=True,
                fill_hover_paint={"fill-color": "#4285F4"},
            ),
            blank=True,
            center=[10.0, 20.0],
            zoom=1,
        ),
        height="420px",
        w="100%",
        style={"borderRadius": "8px", "overflow": "hidden"},
    )


def clusters_example() -> rx.Component:
    return rx.box(
        mn.map(
            mn.map.controls(show_zoom=True),
            mn.map.cluster(
                data=CLUSTER_DATA,
                cluster_radius=40,
                point_color="#4285F4",
            ),
            center=[-74.0, 40.7],
            zoom=9,
        ),
        height="420px",
        w="100%",
        style={"borderRadius": "8px", "overflow": "hidden"},
    )


@navbar_layout(
    route="/maps",
    title="Maps",
    navbar=app_navbar(),
    with_header=False,
)
def map_examples() -> rx.Component:
    """Page demonstrating MapCN map components."""
    return mn.container(
        mn.stack(
            mn.title("Maps", order=1),
            mn.text(
                "MapCN (mapcn.dev) MapLibre GL components wrapped for Reflex.",
                size="md",
                c="gray",
            ),
            rx.link("← Back to Home", href="/", size="3"),
            mn.simple_grid(
                example_box(
                    "Basic Map + Controls",
                    mn.stack(
                        basic_map_example(),
                        mn.text(
                            "Located at: ",
                            mn.text(
                                MapExamplesState.last_located,
                                span=True,
                                display="inline",
                                fw="bold",
                            ),
                            c="gray",
                            size="sm",
                        ),
                        gap="sm",
                    ),
                ),
                example_box(
                    "Markers + Popups (draggable)",
                    mn.stack(
                        markers_and_popups_example(),
                        mn.text(
                            "Last clicked: ",
                            mn.text(
                                MapExamplesState.last_clicked_marker,
                                span=True,
                                display="inline",
                                fw="bold",
                            ),
                            c="gray",
                            size="sm",
                        ),
                        gap="sm",
                    ),
                ),
                example_box(
                    "Routes + Arcs",
                    mn.stack(
                        route_and_arc_example(),
                        mn.text(
                            "Route clicks: ",
                            mn.text(
                                MapExamplesState.route_click_count,
                                span=True,
                                display="inline",
                                fw="bold",
                            ),
                            c="gray",
                            size="sm",
                        ),
                        gap="sm",
                    ),
                ),
                example_box("Custom Popups (rich content)", custom_popup_example()),
                example_box(
                    "Route Planning (2 alternatives)", route_planning_example()
                ),
                example_box("GeoJSON Choropleth (blank basemap)", geojson_example()),
                example_box("Clustered Points", clusters_example()),
                cols=1,
                spacing="lg",
            ),
            gap="lg",
            w="100%",
        ),
        py="xl",
        w="100%",
    )
