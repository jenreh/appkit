"""
UI Components — canonical appkit_mantine patterns.

Derived from:
  - alloq-team components.py, app/components/stat_card.py
  - https://github.com/jenreh/appkit/tree/main/app/pages/examples
    (button_examples.py, input_examples.py, modal_examples.py,
     table_examples.py, date_examples.py, overlay_examples.py)

Rules:
  - Use mn.* for all visible UI (layout, typography, inputs, feedback).
  - rx.cond / rx.foreach / rx.icon are fine anywhere.
  - Never use rx.vstack, rx.hstack, rx.box where a Mantine equivalent exists.
  - Before using a component not shown here, look it up via Context7 MCP:
      resolve-library-id("mantine") → get-library-docs(id, topic="<component>")
"""

import reflex as rx
from knai_myfeature.state.my_feature_state import MyFeatureState

import appkit_mantine as mn

# ─── Atom components ──────────────────────────────────────────────────────────


def stat_card(
    title: str,
    value: rx.Var | str | int,
    icon: str,
    color: str = "blue",
) -> rx.Component:
    """Single KPI card with icon and value. Pass state vars for reactivity."""
    return mn.card(
        mn.group(
            mn.action_icon(
                rx.icon(tag=icon, size=22, color="white"),
                variant="filled",
                color=color,
                size="xl",
                radius="md",
            ),
            mn.stack(
                mn.text(title, size="2", c="dimmed"),
                mn.heading(value, size="6", fw="bold"),
                gap="2",
            ),
            gap="md",
            align="center",
        ),
        shadow="sm",
        padding="md",
        radius="md",
        with_border=True,
        w="100%",
    )


def badge_status(label: str, color: str = "blue") -> rx.Component:
    """Inline status badge."""
    return mn.badge(label, color=color, variant="light", size="sm")


def section_heading(title: str, subtitle: str = "") -> rx.Component:
    """Section title block."""
    return mn.stack(
        mn.heading(title, size="4", fw=600),
        mn.text(subtitle, size="2", c="dimmed") if subtitle else rx.fragment(),
        gap="1",
    )


# ─── Filter bar ───────────────────────────────────────────────────────────────


def _filter_bar() -> rx.Component:
    """Search input + year/month selects + clear button."""
    return mn.group(
        mn.text_input(
            value=MyFeatureState.search_query,
            on_change=MyFeatureState.set_search_query,
            placeholder="Suchen...",
            left_section=rx.icon(tag="search", size=16),
            w=240,
        ),
        mn.select(
            data=[str(y) for y in range(2024, 2029)],
            value=MyFeatureState.selected_year_str,
            on_change=MyFeatureState.set_year,
            w=100,
        ),
        mn.select(
            data=[
                {"value": str(m), "label": name}
                for m, name in [
                    (1, "Jan"),
                    (2, "Feb"),
                    (3, "Mär"),
                    (4, "Apr"),
                    (5, "Mai"),
                    (6, "Jun"),
                    (7, "Jul"),
                    (8, "Aug"),
                    (9, "Sep"),
                    (10, "Okt"),
                    (11, "Nov"),
                    (12, "Dez"),
                ]
            ],
            value=MyFeatureState.selected_month_str,
            on_change=MyFeatureState.set_month,
            w=100,
        ),
        mn.button(
            "Zurücksetzen",
            on_click=MyFeatureState.load_items,
            variant="subtle",
            size="2",
        ),
        gap="sm",
        align="center",
        wrap="wrap",
    )


# ─── Data table ───────────────────────────────────────────────────────────────


def _table_row(item) -> rx.Component:
    """One row in the items table."""
    return mn.table.tr(
        mn.table.td(mn.text(item.name, size="2")),
        mn.table.td(mn.text(item.formatted_date, size="2", c="dimmed")),
        mn.table.td(
            badge_status(item.status, item.status_color),
        ),
        mn.table.td(
            mn.group(
                mn.action_icon(
                    rx.icon(tag="pencil", size=16),
                    variant="subtle",
                    on_click=MyFeatureState.select_item(item.id),
                ),
                mn.action_icon(
                    rx.icon(tag="trash-2", size=16),
                    variant="subtle",
                    color="red",
                    on_click=MyFeatureState.delete_item(item.id),
                ),
                gap="xs",
            ),
        ),
    )


def _items_table() -> rx.Component:
    """Full table with sticky header."""
    return mn.scroll_area(
        mn.table(
            mn.table.thead(
                mn.table.tr(
                    mn.table.th("Name"),
                    mn.table.th("Datum"),
                    mn.table.th("Status"),
                    mn.table.th(""),
                ),
            ),
            mn.table.tbody(
                rx.foreach(MyFeatureState.filtered_items, _table_row),
            ),
            striped=True,
            highlight_on_hover=True,
            w="100%",
        ),
        h=480,
        type="auto",
    )


def _empty_state() -> rx.Component:
    return mn.card(
        mn.stack(
            rx.icon(tag="inbox", size=40, color="gray"),
            mn.text("Keine Einträge gefunden", size="3", c="dimmed"),
            align="center",
            gap="sm",
        ),
        padding="xl",
        radius="md",
        w="100%",
    )


# ─── Charts ───────────────────────────────────────────────────────────────────


def monthly_bar_chart() -> rx.Component:
    """Stacked bar chart for monthly data."""
    return mn.card(
        mn.stack(
            section_heading("Monatsübersicht"),
            mn.bar_chart(
                data=MyFeatureState.chart_data,
                data_key="month",
                series=[
                    {"name": "Billable", "color": "blue.5"},
                    {"name": "Intern", "color": "gray.4"},
                ],
                chart_type="stacked",
                with_legend=True,
                with_tooltip=True,
                h=260,
                w="100%",
            ),
            gap="md",
        ),
        shadow="sm",
        padding="lg",
        radius="md",
        with_border=True,
    )


# ─── KPI grid ─────────────────────────────────────────────────────────────────


def _kpi_grid() -> rx.Component:
    """Responsive grid of stat cards."""
    return mn.simple_grid(
        stat_card("Einträge", MyFeatureState.total_count, "list", "blue"),
        stat_card("Aktiv", MyFeatureState.active_count, "check-circle", "green"),
        stat_card("Ausstehend", MyFeatureState.pending_count, "clock", "orange"),
        cols={"base": 1, "sm": 3},
        spacing="md",
        w="100%",
    )


# ─── Tabs ─────────────────────────────────────────────────────────────────────


def feature_tabs() -> rx.Component:
    """Tabbed layout. Tab selection persisted via LocalStorage in state."""
    return mn.tabs(
        mn.tabs.list(
            mn.tabs.tab("Übersicht", value="overview"),
            mn.tabs.tab("Analyse", value="analysis"),
        ),
        mn.tabs.panel(
            overview_content(),
            value="overview",
            pt="md",
        ),
        mn.tabs.panel(
            analysis_content(),
            value="analysis",
            pt="md",
        ),
        value=MyFeatureState.selected_tab,
        on_change=MyFeatureState.set_selected_tab,
    )


# ─── Top-level page content ───────────────────────────────────────────────────


def overview_content() -> rx.Component:
    return mn.stack(
        _kpi_grid(),
        _filter_bar(),
        rx.cond(
            MyFeatureState.is_loading,
            mn.center(mn.loader(size="lg"), h=300),
            rx.cond(
                MyFeatureState.items,
                _items_table(),
                _empty_state(),
            ),
        ),
        gap="md",
        w="100%",
    )


def analysis_content() -> rx.Component:
    return mn.stack(
        monthly_bar_chart(),
        gap="md",
        w="100%",
    )


def my_feature_page_content() -> rx.Component:
    """Root component for the feature page. Import this in pages.py."""
    return mn.stack(
        feature_tabs(),
        gap="md",
        w="100%",
    )


# ─── Rule: never use bare Python if in components ────────────────────────────
# Always use rx.cond / rx.foreach — Python if evaluates at import time,
# not reactively.
#
# CORRECT:
#   rx.cond(ListState.is_empty, mn.text("No items"), rx.foreach(ListState.items, render_item))
#
# WRONG (won't react to state changes):
#   if ListState.is_empty: return mn.text("No items")


# ─── Inputs ───────────────────────────────────────────────────────────────────
# Source: https://github.com/jenreh/appkit/blob/main/app/pages/examples/input_examples.py


def text_input_examples() -> rx.Component:
    """
    mn.text_input — controlled vs uncontrolled.

    Controlled: value= + on_change=  (state updated on every keystroke)
    Uncontrolled: default_value= + on_blur=  (state updated when focus leaves)
    Use the error= prop to show inline validation messages.
    """
    return mn.stack(
        # Controlled — bind to state
        mn.text_input(
            label="Name",
            value=MyFeatureState.search_query,
            on_change=MyFeatureState.set_search_query,
            placeholder="Search...",
            left_section=rx.icon("search", size=16),
        ),
        # Uncontrolled with on_blur (cheaper — no DB hit on every keystroke)
        mn.text_input(
            label="Bio",
            description="Saved when you leave the field",
            default_value="",
            on_blur=MyFeatureState.set_search_query,
        ),
        # With validation error
        mn.text_input(
            label="E-Mail",
            placeholder="user@example.com",
            error=MyFeatureState.search_query,  # bind error var here
            left_section=rx.icon("at-sign", size=16),
        ),
        gap="md",
    )


def number_input_examples() -> rx.Component:
    """
    mn.number_input — on_change receives float | str.
    Always guard against empty string in the setter:
        def set_hours(self, val: float | str) -> None:
            self.hours = str(val)  # keep as str; parse in validate/submit
    """
    return mn.stack(
        mn.number_input(
            label="Hours per week",
            min=0,
            max=80,
            step=0.5,
            default_value=40,
        ),
        mn.number_input(
            label="Price",
            prefix="€",
            decimal_scale=2,
            fixed_decimal_scale=True,
            default_value=9.99,
        ),
        mn.number_input(
            label="Percentage",
            suffix="%",
            min=0,
            max=100,
            default_value=50,
        ),
        gap="md",
    )


def textarea_example() -> rx.Component:
    """mn.textarea — use autosize for growing inputs."""
    return mn.textarea(
        label="Notes",
        placeholder="Type here...",
        autosize=True,
        min_rows=3,
        max_rows=8,
        resize="none",
    )


def tags_input_example() -> rx.Component:
    """mn.tags_input — controlled multi-value input."""
    return mn.stack(
        # Free-entry tags
        mn.tags_input(
            label="Skills",
            placeholder="Add skill",
        ),
        # Restricted to a predefined list
        mn.tags_input(
            label="Color",
            data=["Red", "Green", "Blue", "Yellow"],
            placeholder="Pick a color",
            max_tags=3,
            allow_new=False,
        ),
        gap="md",
    )


def password_input_example() -> rx.Component:
    """mn.password_input — with visibility toggle and error."""
    return mn.password_input(
        label="Password",
        description="Minimum 8 characters",
        left_section=rx.icon("lock", size=16),
        error="",  # bind error var
    )


def slider_examples() -> rx.Component:
    """mn.slider / mn.range_slider / mn.switch."""
    return mn.stack(
        mn.slider(
            default_value=40,
            min=0,
            max=100,
            step=5,
            marks=[
                {"value": 0, "label": "0%"},
                {"value": 50, "label": "50%"},
                {"value": 100, "label": "100%"},
            ],
        ),
        mn.range_slider(
            default_value=[20, 80],
            min=0,
            max=100,
            min_range=10,
        ),
        mn.switch(
            label="Enable feature",
            default_checked=False,
            on_label="ON",
            off_label="OFF",
        ),
        gap="xl",
    )


# ─── Modal ────────────────────────────────────────────────────────────────────
# Source: https://github.com/jenreh/appkit/blob/main/app/pages/examples/modal_examples.py


def simple_modal_example(opened: rx.Var, on_close: rx.EventSpec) -> rx.Component:
    """
    Simple modal — most common pattern.
    opened= binds to a bool state var; on_close= calls the close handler.
    """
    return mn.modal(
        mn.stack(
            mn.text("Modal content goes here."),
            mn.button("Close", on_click=on_close, variant="outline"),
            gap="md",
        ),
        title="My Modal",
        opened=opened,
        on_close=on_close,
        centered=True,
        size="md",  # xs | sm | md | lg | xl | "70%" | "100%"
    )


def compound_modal_example(opened: rx.Var, on_close: rx.EventSpec) -> rx.Component:
    """
    Compound modal — use when you need full control over header/body structure.
    mn.modal.root → mn.modal.overlay + mn.modal.content
                      → mn.modal.header (mn.modal.title + mn.modal.close_button)
                      → mn.modal.body
    """
    return mn.modal.root(
        mn.modal.overlay(),
        mn.modal.content(
            mn.modal.header(
                mn.modal.title("Custom Header"),
                mn.modal.close_button(),
            ),
            mn.modal.body(
                mn.stack(
                    mn.text("Full control over structure."),
                    mn.button("Close", on_click=on_close),
                    gap="md",
                ),
            ),
        ),
        opened=opened,
        on_close=on_close,
    )


# ─── Table ────────────────────────────────────────────────────────────────────
# Source: https://github.com/jenreh/appkit/blob/main/app/pages/examples/table_examples.py


def data_table_example() -> rx.Component:
    """
    mn.table — sticky header, hover highlight, scroll area.
    Sub-components: mn.table.thead / mn.table.tbody / mn.table.tr / mn.table.th / mn.table.td
    """

    def _row(item: dict) -> rx.Component:
        return mn.table.tr(
            mn.table.td(mn.text(item["name"], size="2")),
            mn.table.td(mn.text(item["value"], size="2", c="dimmed")),
            mn.table.td(
                mn.action_icon(
                    rx.icon("trash-2", size=16),
                    variant="subtle",
                    color="red",
                    on_click=MyFeatureState.delete_item(item["id"]),
                ),
            ),
        )

    return mn.scroll_area(
        mn.table(
            mn.table.thead(
                mn.table.tr(
                    mn.table.th("Name"),
                    mn.table.th("Value"),
                    mn.table.th(""),
                ),
            ),
            mn.table.tbody(
                rx.foreach(MyFeatureState.items, _row),
            ),
            sticky_header=True,
            with_table_border=True,
            highlight_on_hover=True,
            striped=True,
            w="100%",
        ),
        max_height="400px",
        w="100%",
    )


# ─── Date inputs ─────────────────────────────────────────────────────────────
# Source: https://github.com/jenreh/appkit/blob/main/app/pages/examples/date_examples.py
# State values are ISO strings (e.g. "2026-05-03"); on_change receives the ISO string.


def date_input_examples() -> rx.Component:
    """
    Date input components.
    All on_change handlers receive an ISO date string.
    Use clearable=True for optional fields.
    """
    return mn.stack(
        # Single date via text input with calendar popup
        mn.date_input(
            label="Start Date",
            placeholder="Pick a date",
            clearable=True,
        ),
        # Date range picker (type="range")
        mn.date_picker_input(
            label="Date Range",
            placeholder="Pick range",
            type="range",
            clearable=True,
        ),
        # Date + time
        mn.date_time_picker(
            label="Appointment",
            placeholder="Pick date and time",
            clearable=True,
        ),
        # Month only
        mn.month_picker_input(label="Month", placeholder="Pick a month"),
        # Time only
        mn.time_input(label="Time", with_seconds=False),
        gap="md",
    )


# ─── Tooltip & HoverCard ─────────────────────────────────────────────────────
# Source: https://github.com/jenreh/appkit/blob/main/app/pages/examples/overlay_examples.py


def tooltip_examples() -> rx.Component:
    """mn.tooltip wraps any element. label= is the tooltip text."""
    return mn.group(
        mn.tooltip(
            mn.button("Hover me", variant="outline"),
            label="Tooltip content",
        ),
        mn.tooltip(
            mn.button("With arrow", variant="outline"),
            label="Appears below",
            position="bottom",
            with_arrow=True,
        ),
        mn.tooltip(
            mn.button("Multiline", variant="outline"),
            label="A longer explanation that wraps across multiple lines",
            multiline=True,
            w="200px",
        ),
        gap="sm",
    )
