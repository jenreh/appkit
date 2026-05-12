import reflex as rx

import appkit_mantine as mn


def delete_dialog(
    title: str,
    content: str,
    on_click: rx.EventHandler,
    icon_button: bool = False,
    action_loading: bool = False,
    **kwargs,
) -> rx.Component:
    """Generic delete confirmation dialog.

    Args:
        title: Dialog title
        content: The name/identifier of the item to delete
        on_click: Event handler for delete action
        icon_button: If True, use action_icon instead of button for trigger
        **kwargs: Additional props for the trigger button
    """
    if icon_button:
        trigger = mn.action_icon(rx.icon("trash-2", size=19), m=0, **kwargs)
    else:
        trigger = mn.button(rx.icon("trash-2", size=19), **kwargs)

    return mn.alert_dialog.root(
        mn.alert_dialog.trigger(trigger),
        mn.alert_dialog.content(
            mn.alert_dialog.title(title),
            mn.alert_dialog.description(
                mn.text(
                    "Bist du sicher, dass du ",
                    rx.el.strong(content),
                    " löschen möchtest? ",
                    "Diese Aktion wird das ausgewählte Element und alle zugehörigen ",
                    "Daten dauerhaft löschen. Dieser Vorgang kann nicht rückgängig ",
                    "gemacht werden!",
                    size="sm",
                ),
            ),
            mn.alert_dialog.footer(
                action_label="Löschen",
                on_action=on_click,
                action_loading=action_loading,
            ),
        ),
        size="lg",
        centered=True,
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
