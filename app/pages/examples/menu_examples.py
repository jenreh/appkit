"""Menu component examples."""

from __future__ import annotations

import reflex as rx

import appkit_mantine as mn
from appkit_user.authentication.templates import navbar_layout

from app.components.navbar import app_navbar


class MenuExamplesState(rx.State):
    """State for menu examples."""

    last_clicked: str = "—"
    menu_opened: bool = False
    notifications_enabled: bool = True
    selected_view: str = "list"

    def set_clicked(self, item: str) -> None:
        self.last_clicked = item

    def set_menu_opened(self, opened: bool) -> None:
        self.menu_opened = opened

    @rx.event
    def set_notifications(self, checked: bool) -> None:
        self.notifications_enabled = checked

    @rx.event
    def set_selected_view(self, value: str) -> None:
        self.selected_view = value


def _section(heading: str, description: str, *content: rx.Component) -> rx.Component:
    """Helper to render a labelled example section."""
    return mn.stack(
        rx.heading(heading, size="6"),
        rx.text(description, size="2", color="gray"),
        mn.card(
            mn.group(*content, justify="center", wrap="wrap"),
            with_border=True,
            shadow="sm",
            padding="lg",
            radius="md",
            w="100%",
        ),
        w="100%",
        p="12px",
    )


@navbar_layout(
    route="/menu",
    title="Menu Examples",
    navbar=app_navbar(),
    with_header=False,
)
def menu_examples() -> rx.Component:
    return mn.container(
        mn.stack(
            rx.heading("Menu", size="8"),
            rx.text(
                "Dropdown menu for navigation and secondary actions.",
                size="3",
                color="gray",
            ),
            w="100%",
            p="12px",
        ),
        # ── Basic usage ──────────────────────────────────────────────────────
        _section(
            "Basic Menu",
            "Standard menu with labels, items, and a divider.",
            mn.menu(
                mn.menu.target(mn.button("Toggle menu")),
                mn.menu.dropdown(
                    mn.menu.label("Application"),
                    mn.menu.item(
                        "Settings",
                        left_section=rx.icon("settings", size=14),
                        on_click=MenuExamplesState.set_clicked("Settings"),
                    ),
                    mn.menu.item(
                        "Messages",
                        left_section=rx.icon("message-circle", size=14),
                        on_click=MenuExamplesState.set_clicked("Messages"),
                    ),
                    mn.menu.item(
                        "Gallery",
                        left_section=rx.icon("image", size=14),
                        on_click=MenuExamplesState.set_clicked("Gallery"),
                    ),
                    mn.menu.item(
                        "Search",
                        left_section=rx.icon("search", size=14),
                        right_section=mn.text("⌘K", size="xs", c="dimmed"),
                        on_click=MenuExamplesState.set_clicked("Search"),
                    ),
                    mn.menu.divider(),
                    mn.menu.label("Danger zone"),
                    mn.menu.item(
                        "Transfer my data",
                        left_section=rx.icon("arrow-left-right", size=14),
                        on_click=MenuExamplesState.set_clicked("Transfer"),
                    ),
                    mn.menu.item(
                        "Delete my account",
                        left_section=rx.icon("trash", size=14),
                        color="red",
                        on_click=MenuExamplesState.set_clicked("Delete"),
                    ),
                ),
                shadow="md",
                width=200,
            ),
            rx.text(
                "Last clicked: ",
                rx.text.span(
                    MenuExamplesState.last_clicked,
                    weight="bold",
                ),
                size="2",
            ),
        ),
        # ── Hover trigger ────────────────────────────────────────────────────
        _section(
            "Hover / Click-Hover Trigger",
            "Open menu on hover (desktop) or click (mobile).",
            mn.menu(
                mn.menu.target(mn.button("Hover me", variant="outline")),
                mn.menu.dropdown(
                    mn.menu.item("Profile"),
                    mn.menu.item("Account"),
                    mn.menu.item("Logout"),
                ),
                trigger="click-hover",
                open_delay=100,
                close_delay=400,
                shadow="md",
                width=160,
            ),
        ),
        # ── Disabled items ───────────────────────────────────────────────────
        _section(
            "Disabled Items",
            "Individual items can be disabled.",
            mn.menu(
                mn.menu.target(mn.button("Toggle menu", variant="light")),
                mn.menu.dropdown(
                    mn.menu.item(
                        "Search",
                        left_section=rx.icon("search", size=14),
                        disabled=True,
                    ),
                    mn.menu.item("Download", left_section=rx.icon("download", size=14)),
                    mn.menu.item(
                        "Upload",
                        left_section=rx.icon("upload", size=14),
                        disabled=True,
                    ),
                    mn.menu.item("Copy", left_section=rx.icon("copy", size=14)),
                ),
                shadow="md",
                width=180,
            ),
        ),
        # ── Dropdown position ────────────────────────────────────────────────
        _section(
            "Dropdown Positions",
            "Control where the dropdown appears relative to the target.",
            mn.menu(
                mn.menu.target(mn.button("Bottom (default)")),
                mn.menu.dropdown(
                    mn.menu.item("Item A"),
                    mn.menu.item("Item B"),
                ),
                position="bottom",
                shadow="md",
                width=160,
            ),
            mn.menu(
                mn.menu.target(mn.button("Top", variant="light")),
                mn.menu.dropdown(
                    mn.menu.item("Item A"),
                    mn.menu.item("Item B"),
                ),
                position="top",
                shadow="md",
                width=160,
            ),
            mn.menu(
                mn.menu.target(mn.button("Right", variant="outline")),
                mn.menu.dropdown(
                    mn.menu.item("Item A"),
                    mn.menu.item("Item B"),
                ),
                position="right",
                shadow="md",
                width=160,
            ),
            mn.menu(
                mn.menu.target(mn.button("With Arrow", variant="filled", color="teal")),
                mn.menu.dropdown(
                    mn.menu.item("Item A"),
                    mn.menu.item("Item B"),
                ),
                position="bottom",
                with_arrow=True,
                shadow="md",
                width=160,
            ),
        ),
        # ── Controlled ───────────────────────────────────────────────────────
        _section(
            "Controlled Open State",
            "Manage the open/close state from Python.",
            mn.stack(
                mn.menu(
                    mn.menu.target(mn.button("Controlled menu")),
                    mn.menu.dropdown(
                        mn.menu.item("Action 1"),
                        mn.menu.item("Action 2"),
                    ),
                    opened=MenuExamplesState.menu_opened,
                    on_change=MenuExamplesState.set_menu_opened,
                    shadow="md",
                    width=180,
                ),
                rx.text(
                    "Menu is: ",
                    rx.cond(
                        MenuExamplesState.menu_opened,
                        rx.text.span("open", color="green", weight="bold"),
                        rx.text.span("closed", color="gray"),
                    ),
                    size="2",
                ),
                align="center",
                gap="sm",
            ),
        ),
        # ── Sub-menus ─────────────────────────────────────────────────────────
        _section(
            "Sub-menus",
            "Nested menus for hierarchical navigation.",
            mn.menu(
                mn.menu.target(mn.button("Toggle Menu")),
                mn.menu.dropdown(
                    mn.menu.item("Dashboard"),
                    mn.menu.sub(
                        mn.menu.sub.target(mn.menu.sub.item("Products")),
                        mn.menu.sub.dropdown(
                            mn.menu.item("All products"),
                            mn.menu.item("Categories"),
                            mn.menu.item("Tags"),
                            mn.menu.item("Attributes"),
                        ),
                        open_delay=120,
                        close_delay=150,
                    ),
                    mn.menu.sub(
                        mn.menu.sub.target(mn.menu.sub.item("Orders")),
                        mn.menu.sub.dropdown(
                            mn.menu.item("Open"),
                            mn.menu.item("Completed"),
                            mn.menu.item("Cancelled"),
                        ),
                    ),
                    mn.menu.sub(
                        mn.menu.sub.target(mn.menu.sub.item("Settings")),
                        mn.menu.sub.dropdown(
                            mn.menu.item("Profile"),
                            mn.menu.item("Security"),
                            mn.menu.item("Notifications"),
                        ),
                    ),
                ),
                width=200,
                position="bottom-start",
                shadow="md",
            ),
        ),
        # ── Transitions ──────────────────────────────────────────────────────
        _section(
            "Custom Transition",
            "Animate the dropdown using Mantine's built-in transitions.",
            mn.menu(
                mn.menu.target(mn.button("rotate-right", variant="light")),
                mn.menu.dropdown(
                    mn.menu.item("Item A"),
                    mn.menu.item("Item B"),
                ),
                transition_props={"transition": "rotate-right", "duration": 200},
                shadow="md",
                width=180,
            ),
            mn.menu(
                mn.menu.target(mn.button("scale-y", variant="light")),
                mn.menu.dropdown(
                    mn.menu.item("Item A"),
                    mn.menu.item("Item B"),
                ),
                transition_props={"transition": "scale-y", "duration": 200},
                shadow="md",
                width=180,
            ),
        ),
        # ── Search, checkbox & radio items (Mantine 9.3) ─────────────────────
        _section(
            "Search, Checkbox & Radio Items",
            "Menu.Search filters items; Menu.CheckboxItem and Menu.RadioGroup /"
            " Menu.RadioItem provide selectable options inside the dropdown.",
            mn.menu(
                mn.menu.target(mn.button("Options")),
                mn.menu.dropdown(
                    mn.menu.search(placeholder="Search…"),
                    mn.menu.label("Preferences"),
                    mn.menu.checkbox_item(
                        "Enable notifications",
                        checked=MenuExamplesState.notifications_enabled,
                        on_change=MenuExamplesState.set_notifications,
                        close_menu_on_click=False,
                    ),
                    mn.menu.divider(),
                    mn.menu.label("View"),
                    mn.menu.radio_group(
                        mn.menu.radio_item("List", value="list"),
                        mn.menu.radio_item("Grid", value="grid"),
                        mn.menu.radio_item("Table", value="table"),
                        value=MenuExamplesState.selected_view,
                        on_change=MenuExamplesState.set_selected_view,
                    ),
                ),
                shadow="md",
                width=220,
                close_on_item_click=False,
            ),
            rx.text(
                "Notifications: ",
                rx.text.span(
                    rx.cond(MenuExamplesState.notifications_enabled, "on", "off"),
                    weight="bold",
                ),
                " · View: ",
                rx.text.span(MenuExamplesState.selected_view, weight="bold"),
                size="2",
            ),
        ),
        # ── Menubar (Mantine 9.4) ────────────────────────────────────────────
        _section(
            "Menubar",
            "Desktop-application style horizontal menu bar. Each Menubar.Menu has"
            " a top-level target and a dropdown of Menu.Item children.",
            mn.menubar(
                mn.menubar.menu(
                    mn.menubar.target("File"),
                    mn.menubar.dropdown(
                        mn.menu.item("New file"),
                        mn.menu.item("Open…"),
                        mn.menu.divider(),
                        mn.menu.item("Save"),
                    ),
                ),
                mn.menubar.menu(
                    mn.menubar.target("Edit"),
                    mn.menubar.dropdown(
                        mn.menu.item("Undo"),
                        mn.menu.item("Redo"),
                        mn.menu.item("Find…"),
                    ),
                ),
                mn.menubar.menu(
                    mn.menubar.target("View"),
                    mn.menubar.dropdown(
                        mn.menu.item("Zoom in"),
                        mn.menu.item("Zoom out"),
                        mn.menu.item("Reset zoom"),
                    ),
                ),
            ),
        ),
    )
