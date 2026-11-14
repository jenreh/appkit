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
