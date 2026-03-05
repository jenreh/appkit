from collections.abc import Callable

import reflex as rx

import appkit_mantine as mn


def collapsible(
    *children: rx.Component,
    title: str,
    info_text: str = "",
    show_condition: bool | rx.Var[bool] = True,
    expanded: bool | rx.Var[bool] = False,
    on_toggle: Callable | None = None,
    **props,
) -> rx.Component:
    """
    Erstellt eine Collapsible Komponente mit beliebig vielen Child-Komponenten

    Args:
        *children: Beliebige Anzahl von Reflex Komponenten als positionale Argumente
        title: Titel der Collapsible Sektion
        info_text: Info-Text rechts neben dem Titel
        show_condition: Bedingung, wann die Komponente angezeigt wird
        expanded: Zustand, ob die Komponente erweitert ist
        on_toggle: Event handler für das Umschalten
        **props: Zusätzliche Props für das Container-Element
    """
    return mn.stack(
        mn.stack(
            mn.group(
                rx.icon(
                    tag=rx.cond(
                        expanded,
                        "chevron-down",
                        "chevron-right",
                    ),
                    size=16,
                ),
                mn.text(
                    title,
                    size="xs",
                    fw="500",
                    c="gray.7",
                    style={"flexGrow": "1"},
                ),
                mn.text(
                    info_text,
                    size="xs",
                    c="dimmed",
                    ta="right",
                    w="40%",
                ),
                gap="xs",
                align="flex-start",
                w="100%",
            ),
            on_click=on_toggle,
            p="xs",
            w="100%",
            style={
                "cursor": "pointer",
                "border_radius": "6px",
            },
            _hover={
                "bg": rx.color_mode_cond(
                    light="var(--mantine-color-gray-1)",
                    dark="var(--mantine-color-dark-8)",
                ),
            },
        ),
        rx.cond(
            expanded,
            mn.stack(*children, gap="sm"),
        ),
        # Container Styling with Mantine colors that auto-adapt to theme
        gap="xs",
        w="calc(90% + 18px)",
        bd=rx.color_mode_cond(
            light="1px solid gray.3",
            dark="1px solid gray.7",
        ),
        # bg="gray.0",
        style={
            "border_radius": "8px",
            "opacity": rx.cond(show_condition, "1", "0"),
            "transform": rx.cond(show_condition, "translateY(0)", "translateY(-20px)"),
            "height": rx.cond(show_condition, "auto", "0"),
            "max_height": rx.cond(show_condition, "500px", "0"),
            "padding": rx.cond(show_condition, "3px", "0"),
            "margin_top": rx.cond(show_condition, "16px", "-16px"),
            "overflow": "hidden",
            "pointer_events": rx.cond(show_condition, "auto", "none"),
            "transition": "all 0.2s ease",
        },
        **props,
    )
