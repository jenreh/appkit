# Charts Reference

## Contents

- AreaChart
- BarChart
- LineChart
- CompositeChart
- DonutChart
- PieChart
- RadarChart
- ScatterChart
- BubbleChart
- Sparkline
- FunnelChart
- Heatmap
- Treemap
- RadialBarChart
- BarsList
- SankeyChart
- SunburstChart
- BulletChart
- ChartBrush
- GaugeChart
- WaffleChart
- MatrixChart
- CandlestickChart
- Reference areas & dots

All charts use the shared `appkit_mantine.base.MANTINE_VERSION` for
`@mantine/charts` (Recharts under the hood).

## Common props (categorical charts)

AreaChart, BarChart, LineChart, CompositeChart share:

```python
mn.bar_chart(
    data=[
        {"month": "Jan", "sales": 100, "expenses": 80},
        {"month": "Feb", "sales": 140, "expenses": 90},
    ],
    data_key="month",  # x-axis key
    series=[
        {"name": "sales", "color": "blue.6"},
        {"name": "expenses", "color": "red.6"},
    ],
    h=300,
    with_legend=True,
    with_tooltip=True,
    grid_axis="xy",
    with_x_axis=True,
    with_y_axis=True,
    x_axis_label="Month",
    y_axis_label="Amount ($)",
)
```

Common props: `data`, `data_key`, `series`, `with_legend`, `legend_props`,
`with_tooltip`, `tooltip_props`, `grid_axis`, `tick_line`, `with_x_axis`,
`x_axis_props`, `x_axis_label`, `with_y_axis`, `y_axis_props`, `y_axis_label`,
`unit`, `with_right_y_axis`, `accessibility_layer`, `h`, `w`, `m*`, `p*`.

### Accessibility layer and brush

- `accessibility_layer` (bool, `True` by default) — keyboard navigation via
  the Recharts accessibility layer. Available on all Recharts-based charts
  (AreaChart, BarChart, LineChart, CompositeChart, ScatterChart, BubbleChart,
  PieChart, DonutChart, RadarChart, RadialBarChart, FunnelChart).
- `with_brush` (bool, `False` by default) and `brush_props` (dict passed to
  the Recharts `Brush`) — range selector below the chart. Only on AreaChart,
  BarChart, LineChart, CompositeChart with horizontal orientation.

```python
mn.line_chart(
    data=data,
    data_key="date",
    series=[{"name": "value", "color": "indigo.6"}],
    h=300,
    with_brush=True,
    brush_props={"startIndex": 3, "endIndex": 10, "height": 30},
)
```

For full brush control, render `mn.chart_brush(...)` as a child instead of
`with_brush` (see ChartBrush below).

### Series format

```python
series = [
    {"name": "column_key", "color": "blue.6", "label": "Display Name"},
]
```

## AreaChart

```python
mn.area_chart(
    data=data,
    data_key="date",
    series=[{"name": "value", "color": "indigo.6"}],
    h=300,
    curve_type="natural",
    with_gradient=True,
    with_dots=False,
)
```

Extra props: `curve_type` (`"linear"`, `"natural"`, `"monotone"`, `"step"`, etc.),
`fill_opacity`, `with_dots`, `with_gradient`, `connect_nulls`, `stroke_width`,
`chart_type` (`"default"`, `"stacked"`, `"percent"`, `"split"`).

## BarChart

```python
mn.bar_chart(
    data=data,
    data_key="category",
    series=[{"name": "count", "color": "violet.6"}],
    h=300,
    chart_type="stacked",
    orientation="vertical",
)
```

Extra props: `chart_type` (`"default"`, `"stacked"`, `"percent"`, `"waterfall"`),
`orientation`, `max_bar_width`, `min_bar_size`, `fill_opacity`, `with_bar_value_label`.

## LineChart

```python
mn.line_chart(
    data=data,
    data_key="date",
    series=[
        {"name": "temperature", "color": "red.6"},
        {"name": "humidity", "color": "blue.6"},
    ],
    h=300,
    curve_type="monotone",
    with_dots=True,
)
```

Extra props: `curve_type`, `connect_nulls`, `stroke_width`, `with_dots`, `orientation`.

## CompositeChart

Mix bars and lines in one chart.

```python
mn.composite_chart(
    data=data,
    data_key="month",
    series=[
        {"name": "revenue", "color": "blue.6", "type": "bar"},
        {"name": "trend", "color": "red.6", "type": "line"},
    ],
    h=300,
)
```

Series `type` can be `"bar"`, `"line"`, or `"area"`.

## DonutChart

```python
mn.donut_chart(
    data=[
        {"name": "USA", "value": 400, "color": "indigo.6"},
        {"name": "UK", "value": 300, "color": "yellow.6"},
        {"name": "Germany", "value": 200, "color": "teal.6"},
    ],
    size=200,
    thickness=30,
    with_labels=True,
    with_tooltip=True,
    chart_label="Total: 900",
)
```

Props: `data` (list of `{name, value, color}`), `size`, `thickness`, `padding_angle`,
`with_labels`, `with_labels_line`, `with_tooltip`, `chart_label`, `start_angle`,
`end_angle`, `labels_type` (`"value"`, `"percent"`).

## PieChart

Same API as DonutChart but renders full pie (no inner hole by default).

```python
mn.pie_chart(
    data=[{"name": "A", "value": 40, "color": "blue"}, ...],
    with_labels=True,
)
```

## RadarChart

```python
mn.radar_chart(
    data=[
        {"skill": "JS", "level": 80},
        {"skill": "Python", "level": 90},
        {"skill": "Go", "level": 60},
    ],
    data_key="skill",
    series=[{"name": "level", "color": "blue.4", "opacity": 0.2}],
    h=300,
    with_polar_grid=True,
    with_polar_angle_axis=True,
)
```

Props: `data_key`, `series`, `with_polar_grid`, `with_polar_angle_axis`,
`with_polar_radius_axis`, `with_legend`.

## ScatterChart

```python
mn.scatter_chart(
    data=[{"x": 10, "y": 20}, {"x": 30, "y": 40}],
    data_key={"x": "x", "y": "y"},
    h=300,
)
```

Second y axis: set `with_right_y_axis=True` (plus optional
`right_y_axis_label` / `right_y_axis_props`) and bind a series to it with
`"yAxisId": "right"` inside the `data` object — series without `yAxisId`
stay on the left axis.

```python
mn.scatter_chart(
    data=scatter_data,  # series dicts may carry "yAxisId": "right"
    data_key={"x": "month", "y": "value"},
    h=300,
    with_right_y_axis=True,
    right_y_axis_label="Conversion rate",
    right_y_axis_props={"unit": "%"},
)
```

## BubbleChart

```python
mn.bubble_chart(
    data=[{"x": 10, "y": 20, "z": 5}],
    data_key={"x": "x", "y": "y", "z": "z"},
    range=[5, 20],
    h=300,
)
```

## Sparkline

Inline mini chart.

```python
mn.sparkline(
    data=[10, 20, 15, 30, 25, 40],
    w=200,
    h=60,
    color="blue.6",
    curve_type="natural",
    with_gradient=True,
    trend_colors={"positive": "teal.6", "negative": "red.6", "neutral": "gray.5"},
)
```

## FunnelChart

```python
mn.funnel_chart(
    data=[
        {"name": "Visits", "value": 5000, "color": "indigo.6"},
        {"name": "Leads", "value": 3000, "color": "blue.6"},
        {"name": "Sales", "value": 1000, "color": "teal.6"},
    ],
    with_labels=True,
    with_tooltip=True,
)
```

## Heatmap

```python
mn.heatmap(
    data=heatmap_data,
    start_date="2024-01-01",
    end_date="2024-12-31",
    color_scale=["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"],
)
```

Props: `data`, `start_date`, `end_date`, `min`, `max`, `color_scale`,
`value_label`, `enable_labels`, `with_legend`, `legend_labels`,
`month_labels_position` (`"top"` default, `"bottom"`).

## Treemap

Hierarchical proportional area chart. Each leaf node is sized by its `value`.

```python
treemap_data = [
    {
        "name": "Frontend",
        "children": [
            {"name": "React", "value": 400},
            {"name": "CSS", "value": 150},
        ],
    },
    {
        "name": "Backend",
        "children": [
            {"name": "Python", "value": 600},
            {"name": "SQL", "value": 200},
        ],
    },
]

mn.treemap(
    data=treemap_data,
    h=300,
    w="100%",
)
```

Props: `data` (hierarchical list of dicts with `name`, `value`, `children`), `w`, `h`.

> [Mantine docs — Charts](https://mantine.dev/charts/getting-started/)

## RadialBarChart

Polar bar chart — bars laid out around a circle.

```python
mn.radial_bar_chart(
    data=[
        {"name": "Mobile", "value": 60, "color": "blue.6"},
        {"name": "Desktop", "value": 35, "color": "teal.6"},
        {"name": "Tablet", "value": 12, "color": "yellow.6"},
    ],
    data_key="value",
    h=300,
    bar_size=20,
    start_angle=90,
    end_angle=-270,
    with_legend=True,
    with_tooltip=True,
    with_labels=True,
    with_background=True,
)
```

Props: `data`, `data_key`, `bar_size`, `start_angle`, `end_angle`,
`empty_background_color`, `with_background`, `with_labels`, `with_legend`,
`with_tooltip`, `legend_props`, `tooltip_props`, `accessibility_layer`, `h`, `w`.

> [Mantine docs — RadialBarChart](https://mantine.dev/charts/radial-bar-chart/)

## BarsList

Lightweight horizontal-bars list (not a Recharts chart) — useful for ranked metric
displays inside cards.

```python
mn.bars_list(
    data=[
        {"label": "Frontend", "value": 4200, "color": "blue"},
        {"label": "Backend", "value": 3100, "color": "teal"},
        {"label": "DevOps", "value": 1800, "color": "orange"},
    ],
    bar_height=10,
    bar_gap=6,
    auto_contrast=True,
)
```

Props: `data`, `bar_color`, `bar_gap`, `bar_height`, `bar_text_color`,
`bars_label`, `min_bar_size`, `value_label`, `auto_contrast`.

> [Mantine docs — BarsList](https://mantine.dev/charts/bars-list/)

## SankeyChart

Flow diagram showing weighted links between nodes.

```python
mn.sankey_chart(
    data={
        "nodes": [
            {"name": "Visitors"},
            {"name": "Signups"},
            {"name": "Activated"},
            {"name": "Paid"},
        ],
        "links": [
            {"source": 0, "target": 1, "value": 400},
            {"source": 1, "target": 2, "value": 250},
            {"source": 2, "target": 3, "value": 80},
        ],
    },
    h=300,
    colors=["blue.5", "teal.5", "orange.5", "grape.5"],
    node_padding=20,
    node_width=14,
    link_opacity=0.4,
    with_tooltip=True,
)
```

Props: `data` (`{nodes: [{name}], links: [{source, target, value}]}`), `height`,
`colors`, `iterations`, `link_color`, `link_curvature`, `link_opacity`,
`node_color`, `node_padding`, `node_width`, `text_color`, `with_tooltip`,
`tooltip_animation_duration`, `tooltip_props`, `w`, `h`.

> [Mantine docs — SankeyChart](https://mantine.dev/charts/sankey-chart/)

## SunburstChart

Hierarchical data as concentric rings — a treemap in polar coordinates.
Same data shape as Treemap: leaf nodes carry `value`,
parents carry `children`.

```python
mn.sunburst_chart(
    data=[
        {
            "name": "Frontend",
            "color": "blue.6",
            "children": [
                {"name": "React", "value": 400},
                {"name": "Vue", "value": 200},
            ],
        },
        {
            "name": "Backend",
            "color": "teal.6",
            "children": [{"name": "Python", "value": 250}],
        },
    ],
    size=260,
    with_labels=True,
    with_tooltip=True,
)
```

Props: `data`, `data_key`, `size`, `gap`, `inner_radius`, `start_angle`,
`end_angle`, `stroke_color`, `with_labels`, `with_tooltip`,
`tooltip_animation_duration`, `tooltip_props`, `sunburst_chart_props`,
`w`, `h`.

> [Mantine docs — SunburstChart](https://mantine.dev/charts/sunburst-chart/)

## BulletChart

Compact KPI chart — a value bar against a target marker and qualitative
range bands. Required props: `value`, `ranges`.

```python
mn.bullet_chart(
    value=230,
    target=250,
    ranges=[
        {"value": 150, "color": "red.8", "label": "Low"},
        {"value": 225, "color": "yellow.8", "label": "Medium"},
        {"value": 300, "color": "teal.8", "label": "High"},
    ],
    label="Revenue",
    bar_color="blue.6",
    with_tooltip=True,
)
```

Props: `value`, `ranges` (`[{value, color, label?}]`, rendered back-to-front),
`target`, `label`, `orientation` (`"horizontal"` default, `"vertical"` needs
`h`), `size` (track height), `bar_size`, `bar_color`, `target_color`,
`target_ratio`, `target_size`, `with_tooltip`, `w`, `h`.

> [Mantine docs — BulletChart](https://mantine.dev/charts/bullet-chart/)

## ChartBrush

Themed Recharts `Brush`. Render as a child of AreaChart,
BarChart, LineChart, or CompositeChart for full control over the brush —
use instead of `with_brush`, not together with it.

```python
mn.area_chart(
    mn.chart_brush(data_key="date", height=24, start_index=0, end_index=10),
    data=data,
    data_key="date",
    series=[{"name": "value", "color": "indigo.6"}],
    h=300,
)
```

Props: `data_key`, `start_index`, `end_index`, `height`. Accepts recharts
`Brush` props in general (Mantine applies its theming).

> [Mantine docs — Brush](https://mantine.dev/charts/area-chart/)

## GaugeChart

Radial gauge for a single KPI. Required prop: `value`.

```python
mn.gauge_chart(
    value=72,
    target=85,
    sections=[
        {"value": 40, "color": "red.6"},
        {"value": 70, "color": "yellow.6"},
        {"value": 100, "color": "teal.6"},
    ],
    size=220,
    thickness=14,
    label="72% uptime",
    round_caps=True,
)
```

Props: `value`, `min`, `max`, `target`, `sections` (`[{value, color}]`),
`thickness`, `size`, `start_angle`, `end_angle`, `label`, `value_formatter`
(JS function), `track_color`, `filled_color`, `target_color`, `target_size`,
`round_caps`.

> [Mantine docs — GaugeChart](https://mantine.dev/charts/gauge-chart/)

## WaffleChart

Part-to-whole grid of colored cells.

```python
mn.waffle_chart(
    data=[
        {"name": "Chrome", "value": 65, "color": "blue"},
        {"name": "Safari", "value": 19, "color": "teal"},
        {"name": "Other", "value": 16, "color": "gray"},
    ],
    with_tooltip=True,
    with_legend=True,
    legend_position="right",
)
```

Props: `data` (`[{name, value, color}]`), `rows`, `columns`, `total`, `gap`,
`cell_radius`, `empty_color`, `with_tooltip`, `get_tooltip_label`,
`with_legend`, `legend_position`, `fill_direction`, `size`.

> [Mantine docs — WaffleChart](https://mantine.dev/charts/waffle-chart/)

## MatrixChart

Heatmap with categorical x/y axes. Cells are
`{x, y, value}`; `value` may be `None`.

```python
mn.matrix_chart(
    data=[{"x": "1", "y": "James", "value": 7}, ...],
    y_labels=["James", "Mary"],
    with_y_labels=True,
    with_tooltip=True,
    with_legend=True,
    cell_size=14,
)
```

Props: `data`, `x_labels`, `y_labels`, `domain`, `colors`, `cell_size`,
`gap`, `cell_radius`, `with_tooltip`, `get_tooltip_label`, `tooltip_props`,
`get_cell_props`, `y_labels_width`, `x_labels_height`, `x_labels_position`,
`font_size`, `empty_color`, `with_legend`, `legend_labels`, `with_x_labels`,
`with_y_labels`, `x_labels_rotation`. The chart has a fixed pixel size
(`cell_size` × columns), so shrink `cell_size` for narrow containers.

> [Mantine docs — MatrixChart](https://mantine.dev/charts/matrix-chart/)

## CandlestickChart

Financial OHLC chart. Rows need `open`, `high`, `low`,
`close` keys (rename with `data_keys`).

```python
mn.candlestick_chart(
    h=300,
    data=[{"date": "Mar 01", "open": 136, "high": 142, "low": 133, "close": 140}],
    data_key="date",
    with_tooltip=True,
    reference_lines=[{"y": 140, "label": "Support"}],
)
```

Props: `data`, `data_key`, `data_keys`, `labels`, `up_color`, `down_color`,
`max_candle_width`, `candle_stroke_width`, axis/grid/tooltip props as on
categorical charts, `reference_lines`, `reference_areas`, `reference_dots`.

> [Mantine docs — CandlestickChart](https://mantine.dev/charts/candlestick-chart/)

## Reference areas & dots

AreaChart, BarChart, LineChart, CompositeChart and ScatterChart accept
`reference_lines`, `reference_areas` and `reference_dots`.

```python
mn.area_chart(
    data=data,
    data_key="date",
    series=[{"name": "Apples", "color": "indigo.6"}],
    reference_areas=[
        {"x1": "Mar 23", "x2": "Mar 25", "color": "red.6", "label": "Weekend"}
    ],
    reference_dots=[{"x": "Mar 25", "y": 3470, "color": "red.6", "label": "Peak"}],
)
```

Areas take `x1`/`x2` and/or `y1`/`y2` (omit a pair to span the full axis).
`mn.area_chart(chart_type="stream")` renders a streamgraph; its y axis is
hidden by default.
