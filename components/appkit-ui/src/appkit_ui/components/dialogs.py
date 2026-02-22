import reflex as rx

import appkit_mantine as mn


def delete_dialog(
    title: str,
    content: str,
    on_click: rx.EventHandler,
    icon_button: bool = False,
    class_name: str = "dialog",
    action_loading: bool = False,
    **kwargs,
) -> rx.Component:
    """Generic delete confirmation dialog.

    Args:
        title: Dialog title
        content: The name/identifier of the item to delete
        on_click: Event handler for delete action
        icon_button: If True, use icon_button instead of button for trigger
        **kwargs: Additional props for the trigger button
    """
    # Create the appropriate trigger based on icon_button parameter
    if icon_button:
        trigger = mn.action_icon(rx.icon("trash-2", size=19), m=0, **kwargs)
    else:
        trigger = mn.button(rx.icon("trash-2", size=19), **kwargs)

    return rx.alert_dialog.root(
        rx.alert_dialog.trigger(trigger),
        rx.alert_dialog.content(
            rx.alert_dialog.title(title),
            rx.alert_dialog.description(
                rx.text(
                    "Bist du sicher, dass du ",
                    rx.text.strong(content),
                    " löschen möchtest? ",
                    "Diese Aktion wird das ausgewählte Element und alle zugehörigen ",
                    "Daten dauerhaft löschen. Dieser Vorgang kann nicht rückgängig ",
                    "gemacht werden!",
                ),
                class_name="mb-4",
            ),
            rx.flex(
                rx.alert_dialog.cancel(
                    rx.button(
                        "Abbrechen",
                        class_name=(
                            "bg-gray-100 dark:bg-neutral-700 text-gray-700 "
                            "dark:text-neutral-300 hover:bg-gray-200 "
                            "dark:hover:bg-neutral-600 px-4 py-2 rounded"
                        ),
                    ),
                ),
                rx.alert_dialog.action(
                    rx.button(
                        "Löschen",
                        class_name=(
                            "bg-red-500 text-white hover:bg-red-600 px-4 py-2 rounded"
                        ),
                        loading=action_loading,
                        on_click=on_click,
                    )
                ),
                class_name="justify-end gap-3",
            ),
            class_name=class_name,
        ),
    )


def dialog_header(
    title: str,
    description: str,
    icon: str | None = None,
) -> rx.Component:
    """Reusable dialog header component."""
    icon_badge = rx.cond(
        icon,
        rx.badge(
            rx.icon(tag=icon if icon else "activity", size=18),
            color_scheme="grass",
            radius="full",
            padding="0.65rem",
        ),
        rx.fragment(),
    )

    return rx.hstack(
        icon_badge,
        rx.vstack(
            rx.dialog.title(
                title,
                weight="bold",
                margin="0",
            ),
            rx.dialog.description(description),
            spacing="1",
            height="100%",
            align_items="start",
        ),
        height="100%",
        spacing="4",
        margin_bottom="1.5em",
        align_items="center",
        width="100%",
    )


def dialog_buttons(
    submit_text: str, spacing: str = "3", has_errors: bool = False
) -> rx.Component:
    """Reusable dialog action buttons."""
    return rx.flex(
        rx.dialog.close(
            rx.button(
                "Abbrechen",
                class_name=(
                    "bg-gray-100 dark:bg-neutral-700 text-gray-700 "
                    "dark:text-neutral-300 hover:bg-gray-200 "
                    "dark:hover:bg-neutral-600 px-4 py-2 rounded"
                ),
            ),
        ),
        rx.form.submit(
            rx.dialog.close(
                rx.button(
                    submit_text,
                    class_name="px-4 py-2 rounded",
                    disabled=has_errors,
                ),
            ),
            as_child=True,
        ),
        class_name=f"pt-8 gap-{spacing} mt-4 justify-end",
    )
