# components/appkit-mantine/src/appkit_mantine/rich_select.py

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any, Literal

import reflex as rx
from reflex.event import EventHandler
from reflex.vars.base import Var

from appkit_mantine.base import MantineInputComponentBase

# Lokales Asset (kein npm "rich_select" mehr!)
_JSX = rx.asset("rich_select.jsx", shared=True)


logger = logging.getLogger(__name__)

"""Mantine Combobox (RichSelect) wrapper for Reflex.

This module exposes a comprehensive set of props that map to Mantine's
`Combobox` / `useCombobox` options and Combobox subcomponents. See:
https://mantine.dev/core/combobox/

Notes:
- Python prop names use snake_case and map to Mantine camelCase props.
- `store` is exposed as a passthrough Var[Any] so callers can provide a JS
  combobox store created via Mantine's `useCombobox` hook.
"""


class RichSelect(MantineInputComponentBase):
    """Reflex wrapper um die JSX-Komponente (Mantine Combobox mapping).

    Mantine prop -> Python mapping examples:
    - defaultOpened -> default_opened
    - onDropdownOpen -> on_dropdown_open
    - classNames -> class_names
    """

    library = f"$/public{_JSX}"
    tag = "RichSelect"

    # Core props (existing)
    nothing_found: Var[str] = "Nothing found"

    # Search and clear
    searchable: Var[bool] = True
    clearable: Var[bool] = False
    search_placeholder: Var[str] = "Search..."
    search_value: Var[str] | None = None

    # Dropdown control (useCombobox options)
    default_opened: Var[bool]
    opened: Var[bool]
    loop: Var[bool]
    scroll_behavior: Var[Literal["auto", "instant", "smooth"]]

    # Store passthrough - allows passing Mantine's useCombobox store from JS
    store: Var[Any]

    # Popover/dropdown passthroughs
    position: (
        Var[
            Literal[
                "top",
                "bottom",
                "left",
                "right",
                "top-start",
                "top-end",
                "bottom-start",
                "bottom-end",
                "left-start",
                "left-end",
                "right-start",
                "right-end",
            ]
        ]
        | None
    ) = None
    middlewares: Var[list[Any] | None] = None
    hidden: Var[bool]

    # Dropdown sizing
    max_dropdown_height: Var[int] = 280
    max_height: Var[str | int]
    min_height: Var[str | int]
    height: Var[str | int]

    # Styles API / appearance
    class_names: Var[dict[str, str] | None] = None
    styles: Var[dict[str, Any] | None] = None
    unstyled: Var[bool] = False

    # Creatable / new option support
    creatable: Var[bool] = False

    # Multiselect (optional)
    values: Var[list[str] | None] = None

    # Events
    on_create: EventHandler[lambda value: [value]]
    """Called when a new option is created (receives created value)."""

    on_change: EventHandler[lambda value: [value]]
    """Called when value changes (receives selected value or list of values)."""

    on_search_change: EventHandler[lambda value: [value]]
    """Called when search value changes."""

    on_clear: EventHandler[list]
    """Called when the clear button is clicked."""

    on_option_submit: EventHandler[lambda value: [value]]
    """Called when option is submitted from dropdown."""

    on_opened_change: EventHandler[lambda opened: [opened]]
    """Called when opened state changes."""

    on_dropdown_close: EventHandler[lambda source: [source]]
    """Called when dropdown is closed."""

    on_dropdown_open: EventHandler[lambda source: [source]]
    """Called when dropdown is opened or closed."""
    # Extra props passthrough - JS side expects `extra_props` dict for safe
    # forwarding of nested props (combobox, input_base, search, nothing_found).
    extra_props: Var[dict[str, Any] | None] = None

    def get_event_triggers(self) -> dict[str, Any]:
        """Transform events to work with Reflex state system."""

        def _on_change(value: Var) -> list[Var]:
            return [value]

        return {
            **super().get_event_triggers(),
            "on_change": _on_change,
        }


class RichSelectItem(rx.Component):
    """Virtuelles Kind - trägt die Daten + Renderer-Node."""

    library = f"$/public{_JSX}"
    tag = "RichSelectItem"

    # value can be None when the source data doesn't provide a value.
    # Mark as optional to avoid compile-time warnings when None is passed.
    value: Var[str | None] = None
    option: Var[Any]
    disabled: Var[bool | None] = False
    keywords: Var[list[str] | None]
    payload: Var[dict[str, Any] | None]
    active: Var[bool] | None = None
    group: Var[str] | None = None


class RichSelectNamespace(rx.ComponentNamespace):
    __call__ = staticmethod(RichSelect.create)
    item = staticmethod(RichSelectItem.create)

    @staticmethod
    def map(
        data: Any,
        renderer: Callable[[Any], rx.Component] | None = None,
        *,
        value: Callable[[Any], str] | None = None,
        value_key: str = "value",
        disabled: Callable[[Any], bool] | None = None,
        keywords: Callable[[Any], list[str] | None] | None = None,
        payload: Callable[[Any], dict[str, Any] | None] | None = None,
        **kwargs,
    ) -> rx.Component:
        if renderer is None and "renderer" in kwargs:
            renderer = kwargs.pop("renderer")
        if renderer is None:
            raise ValueError("rich_select.map(...): 'renderer' ist erforderlich.")

        def _is_reflex_var(obj: Any) -> bool:
            """Check if object is a Reflex Var (state variable or expression)."""
            return isinstance(obj, Var)

        def _safe_get(obj: Any, key: str, default: Any) -> Any:
            """Safely get attribute/key from object with fallbacks.

            For Reflex Vars, returns a Var expression instead of trying to
            extract Python values. For Python objects, tries dict then attribute
            access, with graceful fallback to default.

            Args:
                obj: Object to extract from (Var or Python object)
                key: Key or attribute name
                default: Default value if extraction fails

            Returns:
                Extracted value, Var expression, or default
            """
            # If it's a Reflex Var, create a Var accessor instead of extracting
            if _is_reflex_var(obj):
                try:
                    # Use getattr on Var to create a property accessor expression
                    return getattr(obj, key)
                except Exception as exc:
                    logger.debug(
                        "Failed to access attribute '%s' on Var: %s",
                        key,
                        exc,
                    )
                    return default

            try:
                return obj[key]
            except (KeyError, TypeError, AttributeError):
                pass

            try:
                return getattr(obj, key, default)
            except Exception as exc:
                logger.debug(
                    "Failed to access attribute '%s' from object: %s",
                    key,
                    exc,
                )

            # Return default if all extraction methods fail
            return default

        def _mapper(row: Any, index: int) -> rx.Component:
            value_var = (
                value(row) if value is not None else _safe_get(row, value_key, row)
            )

            disabled_var = (
                disabled(row)
                if disabled is not None
                else _safe_get(row, "disabled", False)
            )

            keywords_var = (
                keywords(row)
                if keywords is not None
                else _safe_get(row, "keywords", None)
            )

            payload_var = payload(row) if payload is not None else None
            key_str = f"rs-{index}"

            return RichSelectItem.create(
                value=value_var,
                option=renderer(row),
                disabled=disabled_var,
                keywords=keywords_var,
                payload=payload_var,
                key=key_str,
            )

        return rx.foreach(data, _mapper)


rich_select = RichSelectNamespace()
