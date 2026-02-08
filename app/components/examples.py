import reflex as rx

import appkit_mantine as mn


def example_box(
    title: str, component: rx.Component, state_value: rx.Var | None = None
) -> rx.Component:
    """Helper to render a consistent example box."""
    return mn.card(
        mn.title(title, order=5, mb="sm"),
        component,
        rx.cond(
            state_value,
            mn.text(
                "Selected: ",
                mn.text(state_value, display="inline", fw="bold"),
                c="gray",
                size="sm",
                mt="md",
            ),
            rx.fragment(),
        ),
        shadow="sm",
        with_border=True,
        radius="md",
        padding="lg",
    )
