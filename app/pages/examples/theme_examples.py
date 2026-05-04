"""Mantine theme examples — demonstrates per-page theming.

Wraps the page content in :func:`mantine_provider` with a custom theme built
via :func:`create_theme`. The same components on other pages keep using the
app-level theme configured in ``app.py``; only this subtree is overridden.
"""

from __future__ import annotations

import reflex as rx

import appkit_mantine as mn
from appkit_user.authentication.templates import navbar_layout

from app.components.examples import example_box
from app.components.navbar import app_navbar

# 10-shade palette, ordered light → dark, per Mantine's color system.
GRAPE_GLOW = [
    "#fdf4ff",
    "#fae8ff",
    "#f5d0fe",
    "#f0abfc",
    "#e879f9",
    "#d946ef",
    "#c026d3",
    "#a21caf",
    "#86198f",
    "#701a75",
]

# Shade index at which background becomes dark enough for white text.
DARK_TEXT_BREAKPOINT = 5

PAGE_THEME = mn.create_theme(
    primary_color="grapeGlow",
    primary_shade={"light": 5, "dark": 7},
    default_radius="lg",
    font_family="Roboto Flex",
    headings={
        "fontFamily": "Audiowide, Roboto Flex, sans-serif",
        "fontWeight": "500",
        "sizes": {
            "h1": {"fontSize": "2.5rem", "lineHeight": "1.2"},
            "h2": {"fontSize": "1.75rem", "lineHeight": "1.3"},
        },
    },
    colors={"grapeGlow": GRAPE_GLOW},
    cursor_type="pointer",
    auto_contrast=True,
)


def _theme_demo() -> rx.Component:
    """Components that visibly react to theme changes."""
    return mn.stack(
        mn.title("Theme Examples", order=1),
        mn.text(
            "This page is wrapped in mantine_provider(...) with a custom "
            "theme. Compare the buttons, inputs and badges with the rest of "
            "the app — primary color, default radius and heading font are "
            "overridden here only.",
            size="md",
            c="dimmed",
        ),
        mn.simple_grid(
            example_box(
                "Primary color (grapeGlow)",
                mn.group(
                    mn.button("Default", variant="filled"),
                    mn.button("Light", variant="light"),
                    mn.button("Outline", variant="outline"),
                    mn.button("Subtle", variant="subtle"),
                ),
            ),
            example_box(
                "Default radius (lg)",
                mn.group(
                    mn.paper(
                        mn.text("Paper"),
                        with_border=True,
                        p="md",
                    ),
                    mn.button("Button"),
                    mn.text_input(placeholder="Input"),
                ),
            ),
            cols=2,
            spacing="md",
        ),
        mn.simple_grid(
            example_box(
                "Headings (Audiowide font)",
                mn.stack(
                    mn.title("Heading 1", order=1),
                    mn.title("Heading 2", order=2),
                    mn.title("Heading 3", order=3),
                ),
            ),
            example_box(
                "Auto contrast on filled badges",
                mn.group(
                    mn.badge("Default"),
                    mn.badge("Light", variant="light"),
                    mn.badge("Outline", variant="outline"),
                    mn.badge("Color 9", color="grapeGlow.9"),
                    mn.badge("Color 3", color="grapeGlow.3"),
                ),
            ),
            cols=2,
            spacing="md",
        ),
        example_box(
            "Full palette",
            mn.group(
                *[
                    mn.paper(
                        mn.text(
                            str(i),
                            c="white" if i >= DARK_TEXT_BREAKPOINT else "black",
                            fw=600,
                        ),
                        bg=GRAPE_GLOW[i],
                        w=48,
                        h=48,
                        radius="md",
                        style={
                            "display": "flex",
                            "alignItems": "center",
                            "justifyContent": "center",
                        },
                    )
                    for i in range(10)
                ],
                gap="xs",
            ),
        ),
        gap="lg",
    )


@navbar_layout(
    route="/examples/theme",
    title="Theme",
    navbar=app_navbar(),
    with_header=False,
)
def theme_examples() -> rx.Component:
    """Theme example page wrapped in a custom MantineProvider."""
    return mn.container(
        mn.mantine_provider(
            _theme_demo(),
            theme=PAGE_THEME,
        ),
        size="lg",
        py="xl",
    )
