# Maps Reference

MapCN-ported MapLibre GL map ([mapcn.dev](https://mapcn.dev)), bundled as a
local JSX asset. Not part of `@mantine/core` — powered by `maplibre-gl`, but
styled to match the rest of `appkit_mantine`.

## Contents

- `mn.map` — root map container
- `mn.map.controls` — zoom/compass/locate/fullscreen controls
- `mn.map.marker` + `mn.marker.*` — markers with content/popup/tooltip/label
- `mn.map.popup` — standalone popup at a coordinate (not attached to a marker)
- `mn.map.route` — polyline route
- `mn.map.arc` — animated great-circle arcs (data viz)
- `mn.map.geojson` — arbitrary GeoJSON fill/line layer
- `mn.map.cluster` — clustered point layer
- `mn.map.navigation` — real driving/walking/cycling routing (OSRM)
- `mn.map.directions_panel` — turn-by-turn directions overlay

## Important: sizing

Unlike other `appkit_mantine` components, `Map` does **not** accept Mantine
layout props (`w`, `h`, ...). Size it by wrapping it in a container with an
explicit height:

```python
rx.box(
    mn.map(center=[-74.006, 40.7128], zoom=11),
    height="420px",
    w="100%",
    style={"borderRadius": "8px", "overflow": "hidden"},
)
```

## `mn.map` (root)

```python
mn.map(
    mn.map.controls(show_zoom=True, show_compass=True),
    center=[-74.006, 40.7128],  # [longitude, latitude]
    zoom=11,
    theme="dark",  # "dark" | "light" — auto-detects if unset
)
```

Props: `theme` (`"dark"|"light"`), `styles` (`{"light": ..., "dark": ...}` —
style URL or MapLibre style spec, overrides default Carto tiles), `blank`
(transparent tile-less basemap for pure data viz — draw your own layers on
top; ignored when `styles` is set), `projection` (`{"type": "globe"}` for 3D
globe), `center` (`[lng, lat]`), `zoom`, `viewport` (controlled
`{center, zoom, bearing, pitch}` — use with `on_viewport_change` for full
State control), `loading` (show loading indicator).

Events: `on_click`, `on_viewport_change` (fired continuously while
panning/zooming/rotating), plus standard pointer/focus events.

## `mn.map.controls`

```python
mn.map.controls(
    position="bottom-right",  # "top-left" | "top-right" | "bottom-left" | "bottom-right"
    show_zoom=True,
    show_compass=True,
    show_locate=True,
    show_fullscreen=True,
    on_locate=State.set_last_located,  # receives user's coordinates
)
```

## Markers — `mn.map.marker` + `mn.marker.*`

`mn.map.marker` positions a marker on the map; its children come from the
separate `mn.marker` namespace (`content`, `popup`, `tooltip`, `label`).

```python
mn.map.marker(
    mn.marker.content(),  # default dot marker
    mn.marker.label("NYC", position="top"),  # always-visible label
    mn.marker.popup(mn.text("New York City"), close_button=True),  # click to open
    mn.marker.tooltip(mn.text("Hover me")),  # hover-only
    longitude=-74.006,
    latitude=40.7128,
    draggable=True,
    on_click=State.select_marker("nyc"),
    on_drag_end=State.on_marker_moved,
)
```

`mn.map.marker` props: `longitude`, `latitude`, `draggable`, `offset`
(`[x, y]` px), `rotation` (degrees), `rotation_alignment`
(`"auto"|"horizon"|"map"|"viewport"`), `pitch_alignment`
(`"auto"|"map"|"viewport"`). Events: `on_click`, `on_drag_start`, `on_drag`,
`on_drag_end`, `on_mouse_enter`, `on_mouse_leave`.

`mn.marker.content(...)` — the visual marker itself (defaults to a dot);
pass any component (e.g. `rx.box` circle, `rx.icon`) as children for a custom
marker.

`mn.marker.label(...)` — always-visible text label. Prop: `position`
(`"top"|"bottom"`, default `"top"`). Renders alongside `content`, not inside
it — a marker using a custom `content` still needs the label added
separately.

`mn.marker.popup(...)` — opens on click. Props: `close_button` (default
`False`), `offset`, `max_width`.

`mn.marker.tooltip(...)` — opens on hover. Props: `offset`, `max_width`.

## `mn.map.popup` (standalone)

A popup anchored to a coordinate directly, not attached to a marker:

```python
mn.map.popup(
    mn.text("Standalone popup"),
    longitude=-74.006,
    latitude=40.7128,
    close_button=True,
    on_close=State.on_popup_closed,
)
```

Props: `longitude`, `latitude`, `close_button`, `offset`, `max_width`. Event:
`on_close`.

## `mn.map.route`

Static polyline (e.g. precomputed geometry):

```python
mn.map.route(
    coordinates=[[-74.006, 40.7128], [-87.6298, 41.8781], [-118.24, 34.05]],
    color="#4285F4",  # default
    width=3,  # default
    opacity=0.8,  # default
    dash_array=[4, 2],
    interactive=True,  # default — respond to mouse events
    on_click=State.on_route_click,
)
```

## `mn.map.arc`

Animated great-circle arcs — ideal for "connections between places" data viz:

```python
mn.map.arc(
    data=[{"id": "nyc-la", "from": [-74.006, 40.7128], "to": [-118.24, 34.05]}],
    curvature=0.25,  # default 0.2 — how far the arc bows
    samples=64,  # default — points per arc, higher = smoother
    hover_paint={"line-color": "#ef4444"},
    interactive=True,
    on_hover=State.on_arc_hover,
    on_click=State.on_arc_click,
)
```

Props: `data` (list of `{id, from: [lng,lat], to: [lng,lat], ...}`),
`curvature`, `samples`, `paint` (MapLibre line-layer paint, merged over
defaults), `layout` (MapLibre line-layer layout), `hover_paint` (feature-state
paint override), `interactive`, `before_id` (insert before this layer id).

## `mn.map.geojson`

Render arbitrary GeoJSON (polygons/lines):

```python
mn.map.geojson(
    data=geojson_dict,  # FeatureCollection/Feature/Geometry, or URL string
    promote_id="GEOID",  # required for hover feature-state
    fill_paint={"fill-color": "#3b82f6", "fill-opacity": 0.4},
    line_paint={"line-color": "#1d4ed8", "line-width": 1},
    fill_hover_paint={"fill-opacity": 0.7},  # requires promote_id
    interactive=True,
    on_hover=State.on_region_hover,
    on_click=State.on_region_click,
)
```

Pass `fill_paint=False` / `line_paint=False` to omit that layer entirely
(e.g. outline-only or fill-only).

## `mn.map.cluster`

Clustered point layer (auto-clusters at low zoom, expands at high zoom):

```python
mn.map.cluster(
    data=geojson_points,  # FeatureCollection or URL
    cluster_max_zoom=14,  # default
    cluster_radius=50,  # default, px
    cluster_colors=["#22c55e", "#eab308", "#ef4444"],  # small/medium/large
    cluster_thresholds=[100, 750],  # point-count steps for color/size
    point_color="#3b82f6",  # unclustered points
    on_cluster_click=State.on_cluster_click,
    on_point_click=State.on_point_click,
)
```

## `mn.map.navigation` + `mn.map.directions_panel`

Real turn-by-turn routing via an OSRM-compatible API (defaults to the public
`https://router.project-osrm.org` demo server). `MapNavigation` is a
config-only node (renders nothing itself but publishes route state consumed
by `MapDirectionsPanel` and used to draw the route line + endpoint markers).

```python
mn.map(
    mn.map.controls(show_zoom=True),
    mn.map.navigation(
        start_lat=40.7128,
        start_long=-74.006,
        end_lat=42.3601,
        end_long=-71.0589,
        profiles=["driving", "walking", "cycling"],  # profile switcher
        alternatives=True,
        line_color="#4285F4",
        fit_bounds=True,  # default — auto-fit viewport to route
        show_end_markers=True,  # default
    ),
    mn.map.directions_panel(
        title="Directions",
        show_summary=True,  # default
        show_steps=True,  # default
        width=260,
        position="top-left",  # default
        collapsible=True,  # default
    ),
    center=[-72.5, 41.5],
    zoom=6.5,
)
```

`mn.map.navigation` key props: `start_lat`/`start_long`/`end_lat`/`end_long`,
`profile` (single: `"driving"|"walking"|"cycling"`) or `profiles` (list —
adds a switcher), `routing_url` (custom OSRM-compatible endpoint),
`alternatives`, `overview` (`"false"|"full"|"simplified"`), `steps`,
`line_color`/`line_width`/`line_opacity`/`line_dasharray`, `fit_bounds` +
`fit_bounds_padding`/`fit_bounds_max_zoom`/`fit_bounds_duration_ms`,
`show_end_markers`, `start_marker_color`, `end_marker_color`, `exclude`
(road classes, e.g. `["motorway"]`).

`mn.map.directions_panel` key props: `title`, `empty_text`, `show_summary`,
`show_steps`, `max_height`, `width`, `position`
(`"top-left"|"top-right"|"bottom-left"|"bottom-right"`), `offset_top`,
`offset_left`, `dock_below_zoom_controls`, `collapsible`,
`initially_collapsed`, `collapse_direction` (`"top"|"bottom"`).

## Full example (markers + popups + custom content)

```python
def marker_dot(color: str = "#3b82f6", size: str = "14px") -> rx.Component:
    return rx.box(
        width=size,
        height=size,
        border_radius="50%",
        border="2px solid white",
        background=color,
        box_shadow="0 1px 3px rgba(0, 0, 0, 0.3)",
    )


rx.box(
    mn.map(
        mn.map.controls(show_zoom=True),
        rx.foreach(
            State.markers,
            lambda m: mn.map.marker(
                mn.marker.content(marker_dot(), mn.marker.label(m["label"])),
                mn.marker.popup(
                    mn.text(m["label"], fw=600, size="sm"), close_button=True
                ),
                longitude=m["lng"],
                latitude=m["lat"],
                draggable=True,
                on_click=State.select_marker(m["label"]),
            ),
        ),
        center=[-95.0, 39.0],
        zoom=3,
    ),
    height="420px",
    w="100%",
    style={"borderRadius": "8px", "overflow": "hidden"},
)
```

> Reference implementation: [app/pages/examples/map_examples.py](../../../app/pages/examples/map_examples.py)
> Source: [components/appkit-mantine/src/appkit_mantine/maps.py](../../../components/appkit-mantine/src/appkit_mantine/maps.py)
> Original design: [mapcn.dev](https://mapcn.dev)
