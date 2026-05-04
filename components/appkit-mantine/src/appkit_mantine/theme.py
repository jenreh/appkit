"""Mantine theme helpers for AppKit.

Provides a Pythonic, reflex.dev-style API for configuring Mantine theming:

- :func:`create_theme` builds a theme override dictionary using snake_case
  kwargs (translated to the camelCase keys Mantine expects).
- :func:`set_app_theme` configures the theme used by the app-level
  ``MantineProvider`` that wraps every page automatically.
- :func:`get_app_theme` returns the currently configured app-level theme.

Page-level theming is available via ``mantine_provider(...)`` re-exported
from the package root.

References
----------
- https://mantine.dev/llms/theming-mantine-provider.md
- https://mantine.dev/llms/theming-theme-object.md
- https://mantine.dev/llms/theming-colors.md
- https://mantine.dev/llms/theming-color-schemes.md
- https://mantine.dev/llms/theming-typography.md
"""

from __future__ import annotations

from typing import Any, Literal

ThemeDict = dict[str, Any]

_app_theme: ThemeDict | None = None

_SNAKE_TO_CAMEL: dict[str, str] = {
    "primary_color": "primaryColor",
    "primary_shade": "primaryShade",
    "font_family": "fontFamily",
    "font_family_monospace": "fontFamilyMonospace",
    "font_sizes": "fontSizes",
    "line_heights": "lineHeights",
    "font_weights": "fontWeights",
    "font_smoothing": "fontSmoothing",
    "default_radius": "defaultRadius",
    "focus_ring": "focusRing",
    "auto_contrast": "autoContrast",
    "luminance_threshold": "luminanceThreshold",
    "cursor_type": "cursorType",
    "respect_reduced_motion": "respectReducedMotion",
    "default_gradient": "defaultGradient",
    "active_class_name": "activeClassName",
    "focus_class_name": "focusClassName",
    "variant_color_resolver": "variantColorResolver",
}


def create_theme(
    *,
    primary_color: str | None = None,
    primary_shade: int | dict[str, int] | None = None,
    colors: dict[str, list[str]] | None = None,
    white: str | None = None,
    black: str | None = None,
    font_family: str | None = None,
    font_family_monospace: str | None = None,
    headings: dict[str, Any] | None = None,
    font_sizes: dict[str, str] | None = None,
    line_heights: dict[str, str | int | float] | None = None,
    font_weights: dict[str, int | str] | None = None,
    font_smoothing: bool | None = None,
    radius: dict[str, str] | None = None,
    default_radius: str | int | None = None,
    spacing: dict[str, str] | None = None,
    breakpoints: dict[str, str] | None = None,
    shadows: dict[str, str] | None = None,
    focus_ring: Literal["auto", "always", "never"] | None = None,
    scale: float | None = None,
    auto_contrast: bool | None = None,
    luminance_threshold: float | None = None,
    cursor_type: Literal["default", "pointer"] | None = None,
    respect_reduced_motion: bool | None = None,
    default_gradient: dict[str, Any] | None = None,
    active_class_name: str | None = None,
    focus_class_name: str | None = None,
    components: dict[str, Any] | None = None,
    other: dict[str, Any] | None = None,
    **extra: Any,
) -> ThemeDict:
    """Build a Mantine theme override object from snake_case kwargs.

    Mirrors ``createTheme()`` from ``@mantine/core`` but accepts Pythonic
    snake_case parameters and emits the camelCase keys Mantine expects.

    Only the top-level keys are translated. Nested values (e.g. inside
    ``headings.sizes`` or ``default_gradient``) must already use Mantine's
    camelCase keys — pass them as plain dicts.

    Custom palettes in ``colors`` must define exactly 10 shades, ordered
    light → dark, per Mantine's color system.

    Example::

        theme = create_theme(
            primary_color="alloqWarm",
            primary_shade={"light": 5, "dark": 6},
            font_family="Roboto Flex",
            headings={"fontFamily": "Roboto Flex", "fontWeight": "600"},
            colors={
                "alloqWarm": [
                    "#fffef8",
                    "#fbf8ed",
                    "#f7efd1",
                    "#f8eaa8",
                    "#f6d94d",
                    "#f1ca45",
                    "#d99f18",
                    "#a97811",
                    "#6f4f0f",
                    "#3e2d0b",
                ],
            },
        )
    """
    candidates: dict[str, Any] = {
        "primary_color": primary_color,
        "primary_shade": primary_shade,
        "colors": colors,
        "white": white,
        "black": black,
        "font_family": font_family,
        "font_family_monospace": font_family_monospace,
        "headings": headings,
        "font_sizes": font_sizes,
        "line_heights": line_heights,
        "font_weights": font_weights,
        "font_smoothing": font_smoothing,
        "radius": radius,
        "default_radius": default_radius,
        "spacing": spacing,
        "breakpoints": breakpoints,
        "shadows": shadows,
        "focus_ring": focus_ring,
        "scale": scale,
        "auto_contrast": auto_contrast,
        "luminance_threshold": luminance_threshold,
        "cursor_type": cursor_type,
        "respect_reduced_motion": respect_reduced_motion,
        "default_gradient": default_gradient,
        "active_class_name": active_class_name,
        "focus_class_name": focus_class_name,
        "components": components,
        "other": other,
    }

    theme: ThemeDict = {}
    for key, value in candidates.items():
        if value is None:
            continue
        theme[_SNAKE_TO_CAMEL.get(key, key)] = value
    theme.update(extra)
    return theme


def set_app_theme(theme: ThemeDict | None) -> None:
    """Configure the global Mantine theme used by the app-level provider.

    Call this once before instantiating ``rx.App(...)``. The theme is
    forwarded to the root ``MantineProvider`` automatically registered as an
    app-wrap component by every Mantine component.

    Pass ``None`` to clear a previously configured theme.

    Example::

        import appkit_mantine as am

        am.set_app_theme(
            am.create_theme(
                primary_color="blue",
                font_family="Roboto Flex",
            )
        )

        app = rx.App(...)
    """
    global _app_theme  # noqa: PLW0603 — module-level config set at import time
    _app_theme = theme


def get_app_theme() -> ThemeDict | None:
    """Return the theme configured via :func:`set_app_theme`, if any."""
    return _app_theme
