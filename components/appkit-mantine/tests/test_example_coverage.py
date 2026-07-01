from __future__ import annotations

import re
from pathlib import Path

from appkit_mantine.base import MANTINE_VERSION
from appkit_mantine.charts import (
    MANTINE_CHARTS_LIBRARY,
    RECHARTS_LIBRARY,
    MantineChartComponentBase,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
EXAMPLES_DIR = REPO_ROOT / "app" / "pages" / "examples"
NAVBAR_FILE = REPO_ROOT / "app" / "components" / "navbar.py"

REQUIRED_COMPONENT_EXAMPLES = (
    "agenda_view",
    "anchor",
    "background_image",
    "bars_list",
    "burger",
    "close_button",
    "color_swatch",
    "collapse",
    "combobox_popover",
    "data_list",
    "dialog",
    "day_view",
    "empty_state",
    "menubar",
    "floating_indicator",
    "floating_window",
    "inline_date_time_picker",
    "kbd",
    "loading_overlay",
    "marquee",
    "mobile_month_view",
    "month_view",
    "overflow_list",
    "overlay",
    "pill",
    "pills_input",
    "popover",
    "radial_bar_chart",
    "resources_day_view",
    "resources_month_view",
    "resources_schedule",
    "resources_week_view",
    "rolling_number",
    "sankey_chart",
    "schedule",
    "scroller",
    "splitter",
    "spoiler",
    "table_of_contents",
    "theme_icon",
    "transition",
    "tree_select",
    "unstyled_button",
    "week_view",
    "year_view",
)


def _read_example_sources() -> str:
    return "\n".join(path.read_text() for path in EXAMPLES_DIR.glob("*_examples.py"))


def test_required_components_have_examples() -> None:
    example_sources = _read_example_sources()

    # Accept both top-level (``mn.day_view(``) and namespaced
    # (``mn.schedule.day_view(``) factory usage.
    missing_components = [
        component
        for component in REQUIRED_COMPONENT_EXAMPLES
        if f".{component}(" not in example_sources
    ]

    assert missing_components == []


def test_example_routes_are_linked_in_navbar() -> None:
    route_pattern = re.compile(r'route="([^"]+)"')
    nav_pattern = re.compile(r'url="([^"]+)"')

    example_routes = {
        route
        for path in EXAMPLES_DIR.glob("*_examples.py")
        for route in route_pattern.findall(path.read_text())
    }
    navbar_urls = set(nav_pattern.findall(NAVBAR_FILE.read_text()))

    assert sorted(example_routes - navbar_urls) == []


def test_charts_package_uses_current_mantine_version() -> None:
    assert MANTINE_CHARTS_LIBRARY == f"@mantine/charts@{MANTINE_VERSION}"


def test_charts_pin_vite_compatible_recharts_dependencies() -> None:
    assert RECHARTS_LIBRARY == "recharts@3.8.1"
    assert MantineChartComponentBase.lib_dependencies == [
        RECHARTS_LIBRARY,
    ]
