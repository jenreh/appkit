"""Mantine Menu component wrapper for Reflex.

A dropdown menu component for navigation and secondary actions. Menu follows
WAI-ARIA recommendations and supports keyboard navigation out of the box.

Key Features:
    - Click, hover, and click-hover trigger modes
    - Sub-menus (nested dropdowns)
    - Controlled and uncontrolled open state
    - Left/right sections on items (icons, shortcuts)
    - Disabled items and colored items
    - Arrow, transitions, and positioning options
    - Full accessibility support (WAI-ARIA menu button pattern)

Documentation: https://mantine.dev/core/menu/

Example:
    ```python
    import reflex as rx
    import appkit_mantine as mn


    class State(rx.State):
        clicked: str = ""

        def on_click_settings(self):
            self.clicked = "settings"


    def my_menu():
        return mn.menu(
            mn.menu.target(mn.button("Open Menu")),
            mn.menu.dropdown(
                mn.menu.label("Application"),
                mn.menu.item("Settings", on_click=State.on_click_settings),
                mn.menu.item("Messages"),
                mn.menu.divider(),
                mn.menu.label("Danger zone"),
                mn.menu.item("Delete account", color="red"),
            ),
            shadow="md",
            width=200,
        )
    ```
"""

from __future__ import annotations

from typing import Any, Literal

import reflex as rx
from reflex.event import EventHandler
from reflex.vars.base import Var

from appkit_mantine.base import MantineComponentBase, MantineLayoutComponentBase

# ============================================================================
# Menu Component
# ============================================================================


class Menu(MantineLayoutComponentBase):
    """Mantine Menu component - dropdown menu for navigation and secondary actions.

    Based on: https://mantine.dev/core/menu/
    """

    tag = "Menu"

    _rename_props = {
        "open_delay": "openDelay",
        "close_delay": "closeDelay",
        "close_on_item_click": "closeOnItemClick",
        "close_on_escape": "closeOnEscape",
        "close_on_click_outside": "closeOnClickOutside",
        "click_outside_events": "clickOutsideEvents",
        "default_opened": "defaultOpened",
        "with_arrow": "withArrow",
        "arrow_offset": "arrowOffset",
        "arrow_position": "arrowPosition",
        "arrow_radius": "arrowRadius",
        "arrow_size": "arrowSize",
        "within_portal": "withinPortal",
        "portal_props": "portalProps",
        "trap_focus": "trapFocus",
        "menu_item_tab_index": "menuItemTabIndex",
        "transition_props": "transitionProps",
        "z_index": "zIndex",
        "keep_mounted": "keepMounted",
        "with_initial_focus_placeholder": "withInitialFocusPlaceholder",
        "with_overlay": "withOverlay",
        "overlay_props": "overlayProps",
        "floating_strategy": "floatingStrategy",
        "return_focus": "returnFocus",
        "hide_detached": "hideDetached",
        "prevent_position_change_when_visible": "preventPositionChangeWhenVisible",
    }

    # Open/close state
    opened: Var[bool]
    default_opened: Var[bool]
    disabled: Var[bool]

    # Trigger mode
    trigger: Var[Literal["click", "hover", "click-hover"]]
    open_delay: Var[int]
    close_delay: Var[int]

    # Close behaviour
    close_on_item_click: Var[bool]
    close_on_escape: Var[bool]
    close_on_click_outside: Var[bool]
    click_outside_events: Var[list[str]]

    # Positioning
    position: Var[str]
    offset: Var[int | dict[str, Any]]

    # Dimensions
    width: Var[str | int]

    # Arrow
    with_arrow: Var[bool]
    arrow_offset: Var[int]
    arrow_position: Var[Literal["center", "side"]]
    arrow_radius: Var[int]
    arrow_size: Var[int]

    # Appearance
    shadow: Var[str]
    radius: Var[str | int]

    # Transitions
    transition_props: Var[dict[str, Any]]

    # Accessibility / focus
    trap_focus: Var[bool]
    loop: Var[bool]
    menu_item_tab_index: Var[Literal[0, -1]]
    with_initial_focus_placeholder: Var[bool]
    return_focus: Var[bool]

    # Portal / overlay
    within_portal: Var[bool]
    portal_props: Var[dict[str, Any]]
    with_overlay: Var[bool]
    overlay_props: Var[dict[str, Any]]
    keep_mounted: Var[bool]
    hide_detached: Var[bool]
    floating_strategy: Var[str]
    prevent_position_change_when_visible: Var[bool]
    z_index: Var[int | str]

    # Events
    on_change: EventHandler[lambda opened: [opened]]
    on_open: EventHandler[rx.event.no_args_event_spec]
    on_close: EventHandler[rx.event.no_args_event_spec]
    on_dismiss: EventHandler[rx.event.no_args_event_spec]


# ============================================================================
# Menu.Target
# ============================================================================


class MenuTarget(MantineComponentBase):
    """Mantine Menu.Target component - wraps the element that opens the menu."""

    tag = "Menu.Target"

    ref_prop: Var[str]


# ============================================================================
# Menu.Dropdown
# ============================================================================


class MenuDropdown(MantineLayoutComponentBase):
    """Mantine Menu.Dropdown component - the dropdown panel."""

    tag = "Menu.Dropdown"


# ============================================================================
# Menu.Item
# ============================================================================


class MenuItem(MantineLayoutComponentBase):
    """Mantine Menu.Item component - a single action item in the menu."""

    tag = "Menu.Item"

    _rename_props = {
        "left_section": "leftSection",
        "right_section": "rightSection",
        "close_menu_on_click": "closeMenuOnClick",
    }

    color: Var[str]
    disabled: Var[bool]
    left_section: Var[Any]
    right_section: Var[Any]
    close_menu_on_click: Var[bool]

    on_click: EventHandler[rx.event.no_args_event_spec]


# ============================================================================
# Menu.Label
# ============================================================================


class MenuLabel(MantineLayoutComponentBase):
    """Mantine Menu.Label component - a section label."""

    tag = "Menu.Label"


# ============================================================================
# Menu.Divider
# ============================================================================


class MenuDivider(MantineComponentBase):
    """Mantine Menu.Divider component - a horizontal separator."""

    tag = "Menu.Divider"


# ============================================================================
# Menu.Sub  (submenu)
# ============================================================================


class MenuSub(MantineLayoutComponentBase):
    """Mantine Menu.Sub component - a nested submenu."""

    tag = "Menu.Sub"

    _rename_props = {
        "open_delay": "openDelay",
        "close_delay": "closeDelay",
        "with_arrow": "withArrow",
        "arrow_offset": "arrowOffset",
        "arrow_position": "arrowPosition",
        "arrow_radius": "arrowRadius",
        "arrow_size": "arrowSize",
        "within_portal": "withinPortal",
        "portal_props": "portalProps",
        "transition_props": "transitionProps",
        "z_index": "zIndex",
        "keep_mounted": "keepMounted",
        "with_overlay": "withOverlay",
        "overlay_props": "overlayProps",
        "floating_strategy": "floatingStrategy",
        "return_focus": "returnFocus",
        "hide_detached": "hideDetached",
        "prevent_position_change_when_visible": "preventPositionChangeWhenVisible",
    }

    disabled: Var[bool]
    position: Var[str]
    offset: Var[int | dict[str, Any]]
    width: Var[str | int]
    with_arrow: Var[bool]
    arrow_offset: Var[int]
    arrow_position: Var[Literal["center", "side"]]
    arrow_radius: Var[int]
    arrow_size: Var[int]
    shadow: Var[str]
    radius: Var[str | int]
    open_delay: Var[int]
    close_delay: Var[int]
    transition_props: Var[dict[str, Any]]
    within_portal: Var[bool]
    portal_props: Var[dict[str, Any]]
    with_overlay: Var[bool]
    overlay_props: Var[dict[str, Any]]
    keep_mounted: Var[bool]
    hide_detached: Var[bool]
    floating_strategy: Var[str]
    prevent_position_change_when_visible: Var[bool]
    z_index: Var[int | str]
    return_focus: Var[bool]

    on_change: EventHandler[lambda opened: [opened]]
    on_open: EventHandler[rx.event.no_args_event_spec]
    on_close: EventHandler[rx.event.no_args_event_spec]
    on_dismiss: EventHandler[rx.event.no_args_event_spec]


# ============================================================================
# Menu.Sub.Target
# ============================================================================


class MenuSubTarget(MantineComponentBase):
    """Mantine Menu.Sub.Target component - trigger for a submenu."""

    tag = "Menu.Sub.Target"

    ref_prop: Var[str]


# ============================================================================
# Menu.Sub.Dropdown
# ============================================================================


class MenuSubDropdown(MantineLayoutComponentBase):
    """Mantine Menu.Sub.Dropdown component - the submenu dropdown panel."""

    tag = "Menu.Sub.Dropdown"


# ============================================================================
# Menu.Sub.Item  (alias: Menu.SubItem)
# ============================================================================


class MenuSubItem(MantineLayoutComponentBase):
    """Mantine Menu.Sub.Item component - trigger item that opens a submenu."""

    tag = "Menu.Sub.Item"

    _rename_props = {
        "left_section": "leftSection",
        "right_section": "rightSection",
        "close_menu_on_click": "closeMenuOnClick",
    }

    color: Var[str]
    disabled: Var[bool]
    left_section: Var[Any]
    right_section: Var[Any]
    close_menu_on_click: Var[bool]


# ============================================================================
# Namespace factory
# ============================================================================


class MenuSubNamespace(rx.ComponentNamespace):
    """Namespace for Menu.Sub compound components."""

    __call__ = staticmethod(MenuSub.create)
    target = staticmethod(MenuSubTarget.create)
    dropdown = staticmethod(MenuSubDropdown.create)
    item = staticmethod(MenuSubItem.create)


class MenuNamespace(rx.ComponentNamespace):
    """Namespace for Menu compound components.

    Usage::

        mn.menu(
            mn.menu.target(mn.button("Open")),
            mn.menu.dropdown(
                mn.menu.label("Section"),
                mn.menu.item("Action", left_section=rx.icon("settings")),
                mn.menu.divider(),
                mn.menu.item("Delete", color="red"),
            ),
            shadow="md",
            width=200,
        )
    """

    __call__ = staticmethod(Menu.create)
    target = staticmethod(MenuTarget.create)
    dropdown = staticmethod(MenuDropdown.create)
    item = staticmethod(MenuItem.create)
    label = staticmethod(MenuLabel.create)
    divider = staticmethod(MenuDivider.create)
    sub = MenuSubNamespace()


menu = MenuNamespace()
