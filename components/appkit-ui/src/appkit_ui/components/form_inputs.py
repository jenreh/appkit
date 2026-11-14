import reflex as rx

import appkit_mantine as mn


def hidden_field(
    **kwargs,
) -> rx.Component:
    """Creates a hidden input field."""
    return rx.el.input(
        type="hidden",
        **kwargs,
    )


def form_field(
    icon: str,
    label: str,
    hint: str = "",
    validation_error: str | None = None,
    **kwargs,
) -> rx.Component:
    if "value" in kwargs:
        kwargs["default_value"] = None
    elif "default_value" in kwargs:
        kwargs["value"] = None

    return mn.form.wrapper(
        mn.form.input(
            **kwargs,
            left_section=rx.cond(icon, rx.icon(icon, size=17, stroke_width=1.5), None),
        ),
        label=label,
        description=hint,
        error=validation_error,
        required=kwargs.get("required", False),
        width="100%",
        my="3px",
    )
