import logging

import reflex as rx
from pydantic import BaseModel

import appkit_mantine as mn

logger = logging.getLogger(__name__)


class SelectItem(BaseModel):
    label: str
    value: str


def hidden_field(
    **kwargs,
) -> rx.Component:
    """Creates a hidden input field."""
    return rx.el.input(
        type="hidden",
        **kwargs,
    )


def inline_form_field(
    icon: str,
    label: str,
    hint: str = "",
    **kwargs,
) -> rx.Component:
    if "value" in kwargs:
        kwargs["default_value"] = None
    elif "default_value" in kwargs:
        kwargs["value"] = None

    minlength = kwargs.get("min_length", 0)
    maxlength = kwargs.get("max_length", 0)
    pattern = kwargs.get("pattern", "")

    logger.debug(
        "Creating form field: %s, minlength=%s, maxlength=%s, pattern=%s",
        label,
        minlength,
        maxlength,
        pattern,
    )

    return rx.form.field(
        rx.flex(
            rx.hstack(
                rx.icon(icon, size=17, stroke_width=1.5),
                rx.form.label(label),
                class_name="label",
            ),
            rx.hstack(
                rx.cond(
                    hint,
                    rx.form.message(
                        hint,
                        color="gray",
                        class_name="hint",
                    ),
                ),
                rx.form.control(
                    rx.input(
                        **kwargs,
                    ),
                    as_child=True,
                ),
                rx.cond(
                    kwargs.get("required", False),
                    rx.form.message(
                        f"{label} ist ein Pflichtfeld.",
                        name=kwargs.get("name", ""),
                        color="red",
                        class_name="error required",
                    ),
                ),
                rx.cond(
                    minlength > 0,
                    rx.form.message(
                        f"{label} muss mindestens {minlength} Zeichen enthalten.",
                        name=kwargs.get("name", ""),
                        color="red",
                        class_name="error minlength",
                    ),
                ),
                rx.cond(
                    maxlength > 0,
                    rx.form.message(
                        f"{label} darf maximal {maxlength} Zeichen enthalten.",
                        name=kwargs.get("name", ""),
                        color="red",
                        class_name="error maxlength",
                    ),
                ),
                rx.cond(
                    pattern,
                    rx.form.message(
                        f"{label} entspricht nicht dem geforderten Format: {pattern}",
                        name=kwargs.get("name", ""),
                        color="red",
                        class_name="error pattern",
                    ),
                ),
                direction="column",
                spacing="0",
            ),
        ),
        width="100%",
        class_name="form-group",
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

    if "size" in kwargs:
        # convert to mantine size "xs", "sm", "md", "lg", "xl"
        size_map = {"1": "xs", "2": "sm", "3": "md", "4": "lg", "5": "xl"}
        kwargs["size"] = size_map.get(kwargs["size"], "md")

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
    )


def form_inline_field(
    icon: str,
    **kwargs,
) -> rx.Component:
    if kwargs.get("width") is None:
        kwargs["width"] = "100%"
    if kwargs.get("size") is None:
        kwargs["size"] = "3"

    return rx.form.field(
        rx.input(
            rx.input.slot(rx.icon(icon)),
            **kwargs,
        ),
        class_name="form-group",
        width="100%",
    )


def form_textarea(
    *components,
    name: str,
    icon: str,
    label: str,
    hint: str = "",
    monospace: bool = True,
    **kwargs,
) -> rx.Component:
    if "value" in kwargs:
        kwargs["default_value"] = None
    elif "default_value" in kwargs:
        kwargs["value"] = None

    minlength = kwargs.get("min_length", 0)
    maxlength = kwargs.get("max_length", 0)

    logger.debug(
        "Creating form textarea: %s, minlength=%s, maxlength=%s",
        label,
        minlength,
        maxlength,
    )

    return rx.flex(
        rx.form.field(
            rx.flex(
                rx.hstack(
                    rx.icon(icon, size=16, stroke_width=1.5),
                    rx.form.label(label),
                    class_name="label",
                ),
                rx.spacer(),
                *components,
                direction="row",
            ),
            rx.cond(
                hint,
                rx.form.message(
                    hint,
                    color="gray",
                    class_name="hint",
                ),
            ),
            rx.form.message(
                f"{label} ist ein Pflichtfeld.",
                name=name,
                color="red",
                class_name="error required",
            ),
            rx.cond(
                minlength > 0,
                rx.form.message(
                    f"{label} muss mindestens {minlength} Zeichen enthalten.",
                    name=name,
                    color="red",
                    match="tooShort",
                    class_name="error minlength",
                ),
            ),
            rx.cond(
                maxlength > 0,
                rx.form.message(
                    f"{label} darf maximal {maxlength} Zeichen enthalten.",
                    name=name,
                    color="red",
                    match="tooLong",
                    class_name="error maxlength",
                ),
            ),
            rx.text_area(
                name=name,
                id=name,
                font_family=rx.cond(
                    monospace,
                    "Consolas, Monaco, 'Courier New', monospace;",
                    "inherit",
                ),
                **kwargs,
            ),
            class_name="form-group",
        ),
        direction="column",
        spacing="0",
    )


def form_checkbox(
    name: str,
    label: str,
    hint: str | None = None,
    **kwargs,
) -> rx.Component:
    return rx.form.field(
        rx.hstack(
            rx.switch(
                name=name,
                margin_top="8px",
                margin_right="9px",
                **kwargs,
            ),
            rx.flex(
                rx.form.label(label, padding_bottom="3px"),
                rx.cond(
                    hint,
                    rx.form.message(
                        hint, color="gray", margin_top="-10px", class_name="hint"
                    ),
                ),
                direction="column",
            ),
            spacing="2",
            align="start",
            justify="start",
            margin_top="1em",
        ),
        name=name,
        width="100%",
        class_name="form-group",
    )


def render_select_item(option: SelectItem) -> rx.Component:
    return rx.select.item(
        rx.hstack(
            rx.text(option.label),
        ),
        value=option.value,
    )


def form_select(
    *components,
    options: list[SelectItem],
    icon: str = "circle-dot",
    label: str = "",
    hint: str = "",
    placeholder: str = "",
    on_change: rx.EventHandler | None = None,
    with_label: bool = True,
    column_width: str = "100%",
    **kwargs,
) -> rx.Component:
    if "value" in kwargs:
        kwargs["default_value"] = None
    elif "default_value" in kwargs:
        kwargs["value"] = None

    if on_change is not None:
        kwargs["on_change"] = on_change

    classes = "rt-SelectTrigger"
    if "size" in kwargs:
        classes += f" rt-r-size-{kwargs['size']}"
    else:
        classes += " rt-r-size-2"

    if "variant" in kwargs:
        classes += f" rt-variant-{kwargs['variant'].lower()}"
    else:
        classes += " rt-variant-surface"

    return rx.flex(
        rx.form.field(
            rx.cond(
                with_label,
                rx.hstack(
                    rx.icon(icon, size=16, stroke_width=1.5),
                    rx.form.label(label),
                    class_name="label",
                ),
            ),
            rx.cond(
                hint,
                rx.form.message(
                    hint,
                    color="gray",
                    class_name="hint",
                ),
            ),
            rx.hstack(
                rx.el.select(
                    rx.cond(placeholder, rx.el.option(placeholder, value="")),
                    rx.foreach(
                        options.to(list[SelectItem]),
                        lambda option: rx.el.option(
                            label=option.label,
                            value=option.value,
                            class_name="rt-SelectItem",
                        ),
                    ),
                    appearance="base-select",
                    class_name=classes,
                    **kwargs,
                ),
                *components,
            ),
            rx.form.message(
                f"{label} darf nicht leer sein.",
                name=kwargs.get("name", ""),
                color="red",
                class_name="error required",
            ),
            spacing="2",
            margin_bottom="0.75em",
            class_name="form-group",
        ),
        width=column_width,
        flex_grow="1",
    )


def form_text_editor(
    icon: str,
    label: str,
    name: str = "editor",
    hint: str = "",
    on_blur: rx.EventHandler | None = None,
    **kwargs,
) -> rx.Component:
    if kwargs.get("width") is None:
        kwargs["width"] = "100%"

    if on_blur is not None:
        kwargs["on_blur"] = on_blur

    return rx.vstack(
        rx.form.field(
            rx.hstack(
                rx.icon(icon, size=16, stroke_width=1.5),
                rx.form.label(label),
                class_name="label",
            ),
            rx.cond(
                hint,
                rx.form.message(
                    hint,
                    color="gray",
                    class_name="hint",
                ),
            ),
            margin_bottom="-12px",
        ),
        mn.rich_text_editor(
            id=name,
            toolbar_config=mn.EditorToolbarConfig(
                control_groups=[
                    ["bold", "italic", "underline"],
                    ["h1", "h2", "h3"],
                    ["bulletList", "orderedList", "blockquote", "code"],
                    ["alignLeft", "alignCenter", "alignRight", "alignJustify"],
                    ["link", "unlink"],
                    ["image"],
                ]
            ),
            variant="subtle",
            **kwargs,
        ),
        width="100%",
        class_name="form-group",
    )
