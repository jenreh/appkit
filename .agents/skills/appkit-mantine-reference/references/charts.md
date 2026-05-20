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

All charts use `@mantine/charts@8.3.10` (Recharts under the hood).

## Common props (categorical charts)

AreaChart, BarChart, LineChart, CompositeChart share:

```python
mn.bar_chart(
    data=[
        {"month": "Jan", "sales": 100, "expenses": 80},
        {"month": "Feb", "sales": 140, "expenses": 90},
    ],
    data_key="month",       # x-axis key
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
series=[
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
