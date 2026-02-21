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
            style={"cursor": "pointer"},
            _hover={"background_color": "var(--mantine-color-gray-1)"},
        ),
        rx.cond(
            expanded,
            mn.stack(*children, gap="sm"),
        ),
        # Container Styling
        gap="xs",
        w="calc(90% + 18px)",
        bg="gray.0",
        style={
            "border": "1px solid var(--mantine-color-gray-3)",  # gray 6 roughly
            "border_radius": "8px",
            "opacity": rx.cond(show_condition, "1", "0"),
            "transform": rx.cond(show_condition, "translateY(0)", "translateY(-20px)"),
            "height": rx.cond(show_condition, "auto", "0"),
            "max_height": rx.cond(show_condition, "500px", "0"),
            "padding": rx.cond(show_condition, "3px", "0"),
            "margin_top": rx.cond(show_condition, "16px", "-16px"),
            "overflow": "hidden",
            "pointer_events": rx.cond(show_condition, "auto", "none"),
            # transition="all 1s ease-out",
        },
        **props,
    )
