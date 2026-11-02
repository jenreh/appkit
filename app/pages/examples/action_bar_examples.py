"""ActionBar examples (Mantine 9.6)."""

from __future__ import annotations

import reflex as rx

import appkit_mantine as mn
from appkit_user.authentication.templates import navbar_layout

from app.components.examples import example_box
from app.components.navbar import app_navbar

ELEMENTS = [
    {"position": 6, "mass": 12.011, "symbol": "C", "name": "Carbon"},
    {"position": 7, "mass": 14.007, "symbol": "N", "name": "Nitrogen"},
    {"position": 39, "mass": 88.906, "symbol": "Y", "name": "Yttrium"},
    {"position": 56, "mass": 137.33, "symbol": "Ba", "name": "Barium"},
    {"position": 58, "mass": 140.12, "symbol": "Ce", "name": "Cerium"},
]


class ActionBarExamplesState(rx.State):
    """State for ActionBar examples."""

    selection: list[int] = []
    last_action: str = ""

    @rx.var
    def selected_count(self) -> int:
        return len(self.selection)

    @rx.var
    def all_selected(self) -> bool:
        return len(self.selection) == len(ELEMENTS)

    @rx.var
    def some_selected(self) -> bool:
        return 0 < len(self.selection) < len(ELEMENTS)

    @rx.event
    def toggle_row(self, position: int) -> None:
        if position in self.selection:
            self.selection = [p for p in self.selection if p != position]
        else:
            self.selection = [*self.selection, position]

    @rx.event
    def toggle_all(self) -> None:
        if len(self.selection) == len(ELEMENTS):
            self.selection = []
        else:
            self.selection = [el["position"] for el in ELEMENTS]

    @rx.event
    def clear(self) -> None:
        self.selection = []

    @rx.event
    def run_action(self, action: str) -> None:
        self.last_action = f"{action}: {len(self.selection)} element(s)"
        self.selection = []


def _row(element: dict) -> rx.Component:
    position = element["position"]
    selected = ActionBarExamplesState.selection.contains(position)
    return mn.table.tr(
        mn.table.td(
            mn.checkbox(
                aria_label="Select row",
                checked=selected,
                on_change=lambda _checked: ActionBarExamplesState.toggle_row(position),
            )
        ),
        mn.table.td(position),
        mn.table.td(element["name"]),
        mn.table.td(element["symbol"]),
        mn.table.td(element["mass"]),
        bg=rx.cond(selected, "var(--mantine-color-blue-light)", None),
    )


def _action_button(label: str) -> rx.Component:
    return mn.button(
        label,
        variant="default",
        size="compact-sm",
        on_click=ActionBarExamplesState.run_action(label),
    )


@navbar_layout(
    route="/examples/action-bar",
    title="ActionBar",
    navbar=app_navbar(),
    with_header=False,
)
def action_bar_examples() -> rx.Component:
    """ActionBar examples page."""
    return mn.container(
        mn.stack(
            mn.title("ActionBar", order=1, size="xl"),
            mn.text(
                "Fixed bottom bar for bulk actions. Select table rows to open it; "
                "press Escape or the close button to clear the selection.",
                size="md",
                c="dimmed",
            ),
            example_box(
                "Table selection",
                mn.stack(
                    mn.table(
                        mn.table.thead(
                            mn.table.tr(
                                mn.table.th(
                                    mn.checkbox(
                                        aria_label="Select all",
                                        checked=ActionBarExamplesState.all_selected,
                                        indeterminate=ActionBarExamplesState.some_selected,
                                        on_change=lambda _checked: (
                                            ActionBarExamplesState.toggle_all()
                                        ),
                                    )
                                ),
                                mn.table.th("Position"),
                                mn.table.th("Name"),
                                mn.table.th("Symbol"),
                                mn.table.th("Atomic mass"),
                            )
                        ),
                        mn.table.tbody(rx.foreach(ELEMENTS, _row)),
                    ),
                    rx.cond(
                        ActionBarExamplesState.last_action != "",
                        mn.text(
                            "Last action — " + ActionBarExamplesState.last_action,
                            size="sm",
                            c="dimmed",
                        ),
                    ),
                ),
            ),
            mn.action_bar(
                mn.text(
                    ActionBarExamplesState.selected_count.to_string() + " selected",
                    size="sm",
                ),
                mn.action_bar.divider(),
                _action_button("Delete"),
                _action_button("Move"),
                _action_button("Archive"),
                mn.action_bar.close_button(),
                opened=ActionBarExamplesState.selected_count > 0,
                on_close=ActionBarExamplesState.clear,
                shadow="md",
                aria_label="Bulk actions",
            ),
            spacing="md",
            w="100%",
            mb="6rem",
        ),
        size="lg",
        w="100%",
    )
