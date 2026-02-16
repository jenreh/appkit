"""Table component for displaying image generator models."""

import reflex as rx

import appkit_mantine as mn
from appkit_imagecreator.admin_state import ImageGeneratorAdminState
from appkit_imagecreator.backend.models import ImageGeneratorModel
from appkit_imagecreator.components.image_generator_dialogs import (
    ImageGeneratorValidationState,
    add_image_generator_button,
    add_image_generator_modal,
    delete_image_generator_dialog,
    edit_image_generator_modal,
)


def _processor_short_name(processor_type: str) -> str:
    """Extract short class name from fully-qualified path."""
    if "." in processor_type:
        return processor_type.rsplit(".", 1)[-1]
    return processor_type


def image_generator_table_row(
    generator: ImageGeneratorModel,
) -> rx.Component:
    """Render a single image generator as a table row."""
    return mn.table.tr(
        mn.table.td(
            mn.text(
                generator.label,
                size="sm",
                fw="500",
                style={"whiteSpace": "nowrap"},
            ),
            min_width="160px",
        ),
        mn.table.td(
            mn.text(
                generator.model_id,
                size="sm",
                c="dimmed",
                style={"whiteSpace": "nowrap"},
            ),
            width="1%",
            style={"whiteSpace": "nowrap"},
        ),
        # Role column — inline select with spinner
        mn.table.td(
            mn.group(
                mn.select(
                    value=generator.required_role,
                    data=ImageGeneratorAdminState.available_roles,
                    placeholder="nicht eingeschränkt",
                    size="xs",
                    clearable=True,
                    check_icon_position="right",
                    on_change=lambda val: (
                        ImageGeneratorAdminState.update_generator_role(
                            generator.id, val
                        )
                    ),
                    w="160px",
                ),
                mn.box(
                    rx.cond(
                        ImageGeneratorAdminState.updating_role_generator_id
                        == generator.id,
                        rx.spinner(size="1"),
                    ),
                    width="16px",
                    display="flex",
                    align_items="center",
                    justify_content="center",
                    flex_shrink="0",
                ),
                align="center",
                gap="xs",
                wrap="nowrap",
            ),
            width="1%",
            style={"whiteSpace": "nowrap"},
        ),
        # Active column — switch with spinner
        mn.table.td(
            mn.group(
                mn.switch(
                    checked=generator.active,
                    on_change=lambda checked: (
                        ImageGeneratorAdminState.toggle_generator_active(
                            generator.id, checked
                        )
                    ),
                    size="sm",
                ),
                mn.box(
                    rx.cond(
                        ImageGeneratorAdminState.updating_active_generator_id
                        == generator.id,
                        rx.spinner(size="1"),
                    ),
                    width="16px",
                    display="flex",
                    align_items="center",
                    justify_content="center",
                    flex_shrink="0",
                ),
                align="center",
                gap="xs",
                wrap="nowrap",
            ),
            width="1%",
            style={"whiteSpace": "nowrap"},
        ),
        # Actions column
        mn.table.td(
            mn.group(
                rx.icon_button(
                    rx.icon("square-pen", size=19),
                    variant="ghost",
                    on_click=[
                        lambda: ImageGeneratorAdminState.get_generator(generator.id),
                        ImageGeneratorValidationState.initialize(generator),
                        ImageGeneratorAdminState.open_edit_modal,
                    ],
                    margin="0",
                ),
                delete_image_generator_dialog(generator),
                align="center",
                gap="xs",
                wrap="nowrap",
            ),
            width="1%",
            style={"whiteSpace": "nowrap"},
        ),
    )


def image_generators_table(
    role_labels: dict[str, str] | None = None,
    available_roles: list[dict[str, str]] | None = None,
) -> rx.Component:
    """Admin table for managing image generator models."""
    if role_labels is None:
        role_labels = {}
    if available_roles is None:
        available_roles = []

    return mn.stack(
        add_image_generator_modal(),
        edit_image_generator_modal(),
        rx.flex(
            add_image_generator_button(),
            mn.text_input(
                placeholder="Generator filtern...",
                left_section=rx.icon("search", size=16),
                left_section_pointer_events="none",
                value=ImageGeneratorAdminState.search_filter,
                on_change=ImageGeneratorAdminState.set_search_filter,
                size="sm",
                w="18rem",
            ),
            rx.spacer(),
            width="100%",
            margin_bottom="md",
            gap="12px",
            align="center",
        ),
        mn.table(
            mn.table.thead(
                mn.table.tr(
                    mn.table.th(mn.text("Label", size="sm", fw="700")),
                    mn.table.th(mn.text("Modell-ID", size="sm", fw="700")),
                    mn.table.th(mn.text("Rolle", size="sm", fw="700")),
                    mn.table.th(mn.text("Aktiv", size="sm", fw="700")),
                    mn.table.th(mn.text("", size="sm")),
                ),
            ),
            mn.table.tbody(
                rx.foreach(
                    ImageGeneratorAdminState.filtered_generators,
                    image_generator_table_row,
                )
            ),
            striped=False,
            highlight_on_hover=True,
            highlight_on_hover_color=rx.color_mode_cond(
                light="gray.0",
                dark="dark.8",
            ),
            w="100%",
        ),
        w="100%",
        on_mount=[
            ImageGeneratorAdminState.set_available_roles(available_roles, role_labels),
            ImageGeneratorAdminState.load_generators_with_toast,
        ],
    )
