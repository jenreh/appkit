import reflex as rx

import appkit_mantine as mn


class DeleteDialog(rx.ComponentState):
    is_open: bool = False

    def toggle(self) -> None:
        self.is_open = not self.is_open

    # Map legacy Radix variant names to Mantine equivalents
    _VARIANT_MAP: dict[str, str] = {
        "ghost": "subtle",
        "soft": "light",
        "surface": "default",
        "classic": "filled",
    }

    @classmethod
    def get_component(
        cls,
        title: str,
        content: str,
        on_click: rx.EventHandler,
        icon_button: bool = False,
        class_name: str = "dialog",
        action_loading: bool = False,
        **kwargs,
    ) -> rx.Component:
        # Map legacy variant names to Mantine equivalents
        if "variant" in kwargs:
            kwargs["variant"] = cls._VARIANT_MAP.get(
                kwargs["variant"], kwargs["variant"]
            )

        # Defaults
        kwargs.setdefault("color", "red")

        if icon_button:
            kwargs.setdefault("variant", "subtle")
            icon = kwargs.pop("icon", None) or rx.icon("trash-2", size=18)

            trigger = mn.action_icon(
                icon,
                on_click=cls.toggle,
                **kwargs,
            )
        else:
            kwargs.setdefault("variant", "light")
            kwargs.setdefault("left_section", rx.icon("trash-2", size=16))

            trigger = mn.button(
                "Löschen",
                on_click=cls.toggle,
                **kwargs,
            )

        return rx.fragment(
            trigger,
            mn.modal(
                rx.flex(
                    rx.text(
                        "Bist du sicher, dass du ",
                        rx.text.strong(content, font_weight="600"),
                        " löschen möchtest? ",
                        "Diese Aktion wird das ausgewählte Element und "
                        "alle zugehörigen ",
                        "Daten dauerhaft löschen. Dieser Vorgang kann nicht "
                        "rückgängig ",
                        "gemacht werden!",
                        margin_bottom="24px",
                    ),
                    rx.flex(
                        mn.button(
                            "Abbrechen",
                            variant="subtle",
                            color="gray",
                            on_click=cls.toggle,
                        ),
                        mn.button(
                            "Löschen",
                            color="red",
                            on_click=[on_click, cls.toggle],
                            loading=action_loading,
                        ),
                        justify="end",
                        gap="9px",
                    ),
                    direction="column",
                ),
                opened=cls.is_open,
                on_close=cls.toggle,
                title=title,
                z_index=1500,
                centered=True,
                class_name=class_name,
            ),
        )


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
        class_name: CSS class for the dialog content
        action_loading: If True, show loading state on the delete button
        **kwargs: Additional props for the trigger button
    """
    return DeleteDialog.create(
        title=title,
        content=content,
        on_click=on_click,
        icon_button=icon_button,
        class_name=class_name,
        action_loading=action_loading,
        **kwargs,
    )


def dialog_header(icon: str, title: str, description: str) -> rx.Component:
    """Reusable dialog header component."""
    return rx.hstack(
        rx.badge(
            rx.icon(tag=icon, size=34),
            color_scheme="grass",
            radius="full",
            padding="0.65rem",
        ),
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
