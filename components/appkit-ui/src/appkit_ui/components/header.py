import reflex as rx

import appkit_mantine as mn

SIDEBAR_WIDTH = "320px"


def header(text: str, header_items: rx.Component | None = None) -> rx.Component:
    return mn.group(
        mn.title(text, order=4),
        header_items,
        justify="space-between",
        align="center",
        wrap="nowrap",
        p="12px",
        pl="32px",
        ml="-32px",
        style={
            "position": "fixed",
            "top": "0",
            "left": f"calc({SIDEBAR_WIDTH} + 32px)",
            "right": "0",
            "z_index": "1000",
            "border_bottom": f"1px solid {rx.color('gray', 5)}",
            "background": rx.color("gray", 2),
            "transition": "colors 300ms",
        },
    )
