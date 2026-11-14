import reflex as rx

from appkit_mantine.alert_dialog import alert_dialog
from appkit_mantine.button import action_icon, button
from appkit_mantine.typography import text

sticky_header_style = {
    "zIndex": "10",
    "position": "relative",
    "boxShadow": (
        "0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03)"
    ),
    "clipPath": "inset(0 0 -10px 0)",
}


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
        trigger = action_icon(rx.icon("trash-2", size=19), m=0, **kwargs)
    else:
        trigger = button(rx.icon("trash-2", size=19), **kwargs)

    return alert_dialog.root(
        alert_dialog.trigger(trigger),
        alert_dialog.content(
            alert_dialog.title(title),
            alert_dialog.description(
                text(
                    "Bist du sicher, dass du ",
                    rx.el.strong(content),
                    " löschen möchtest? ",
                    "Diese Aktion wird das ausgewählte Element und alle zugehörigen ",
                    "Daten dauerhaft löschen. Dieser Vorgang kann nicht rückgängig ",
                    "gemacht werden!",
                    size="sm",
                ),
            ),
            alert_dialog.footer(
                action_label="Löschen",
                on_action=on_click,
                action_loading=action_loading,
            ),
        ),
        size="lg",
        centered=True,
    )
