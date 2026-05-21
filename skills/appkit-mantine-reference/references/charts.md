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

All charts use `@mantine/charts@9.1.1` (Recharts under the hood).

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
`unit`, `with_right_y_axis`, `h`, `w`, `m*`, `p*`.

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
`value_label`, `enable_labels`.

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
`with_tooltip`, `legend_props`, `tooltip_props`, `radial_bar_props`,
`radial_bar_chart_props`, `h`, `w`.

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
