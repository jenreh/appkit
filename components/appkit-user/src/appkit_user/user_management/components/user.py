import reflex as rx

import appkit_mantine as mn
from appkit_ui.components.dialogs import (
    delete_dialog,
    dialog_buttons,
    dialog_header,
)
from appkit_ui.components.form_inputs import form_field, hidden_field
from appkit_user.authentication.backend.models import User
from appkit_user.user_management.states.user_states import UserState


def role_checkbox(
    user: User, role: dict[str, str], is_edit_mode: bool = False
) -> rx.Component:
    """Checkbox for a role in the user form."""
    name = role.get("name")

    return rx.cond(
        name,
        rx.box(
            rx.tooltip(
                rx.checkbox(
                    role.get("label"),
                    name=f"role_{name}",
                    default_checked=(
                        user.roles.contains(name)
                        if is_edit_mode and user.roles is not None
                        else False
                    ),
                ),
                content=role.get("description", ""),
            ),
            class_name="w-[30%] max-w-[30%] flex-grow",
        ),
        rx.fragment(),
    )


def user_form_fields(user: User | None = None) -> rx.Component:
    """Reusable form fields for user add/update dialogs."""
    is_edit_mode = user is not None

    # Basic user fields
    basic_fields = [
        hidden_field(
            name="user_id",
            default_value=user.user_id.to_string() if is_edit_mode else "",
        ),
        form_field(
            name="name",
            icon="user",
            label="Name",
            type="text",
            default_value=user.name if is_edit_mode else "",
            required=True,
        ),
        form_field(
            name="email",
            icon="mail",
            label="Email",
            hint="Die E-Mail-Adresse des Benutzers, wird für die Anmeldung verwendet.",
            type="email",
            default_value=user.email if is_edit_mode else "",
            required=True,
            pattern=r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$",
        ),
        form_field(
            name="password",
            icon="lock",
            label="Initiales Passwort" if not is_edit_mode else "Passwort",
            type="password",
            hint="Leer lassen, um das aktuelle Passwort beizubehalten",
            default_value="",
            required=False,
        ),
    ]

    # Status switches (only for edit mode)
    status_fields = []
    if is_edit_mode:
        status_fields = [
            rx.vstack(
                rx.flex(
                    rx.box(
                        rx.hstack(
                            rx.switch(
                                name="is_active",
                                default_checked=(
                                    user.is_active
                                    if user.is_active is not None
                                    else False
                                ),
                            ),
                            rx.text("Aktiv", size="2"),
                            spacing="2",
                        ),
                        class_name="w-[30%] max-w-[30%] flex-grow",
                    ),
                    rx.box(
                        rx.hstack(
                            rx.switch(
                                name="is_verified",
                                default_checked=(
                                    user.is_verified
                                    if user.is_verified is not None
                                    else False
                                ),
                            ),
                            rx.text("Verifiziert", size="2"),
                            spacing="2",
                        ),
                        class_name="w-[30%] max-w-[30%] flex-grow",
                    ),
                    rx.box(
                        rx.hstack(
                            rx.switch(
                                name="is_admin",
                                default_checked=(
                                    user.is_admin
                                    if user.is_admin is not None
                                    else False
                                ),
                            ),
                            rx.text("Superuser", size="2"),
                            spacing="2",
                        ),
                        class_name="w-[30%] max-w-[30%] flex-grow",
                    ),
                    class_name="w-full flex-wrap gap-2",
                ),
                spacing="1",
                margin="4px 0",
                width="100%",
            ),
        ]

    # Role fields (available for both add and edit modes)
    def render_role_group(group_name: str, roles: list[dict[str, str]]) -> rx.Component:
        """Render a group of roles with a headline."""
        return rx.vstack(
            rx.text(group_name, size="1", weight="bold", color="gray"),
            rx.flex(
                rx.foreach(
                    roles,
                    lambda role: role_checkbox(
                        user=user, role=role, is_edit_mode=is_edit_mode
                    ),
                ),
                class_name="w-full flex-wrap gap-2",
            ),
            spacing="1",
            margin="4px 0",
            width="100%",
        )

    role_fields = [
        rx.vstack(
            rx.text("Berechtigungen", size="2", weight="bold"),
            rx.foreach(
                UserState.sorted_group_names,
                lambda group_name: render_role_group(
                    group_name,
                    UserState.grouped_roles[group_name],
                ),
            ),
            spacing="2",
            margin="6px 0",
            width="100%",
        ),
    ]

    # Combine all fields
    all_fields = basic_fields + status_fields + role_fields

    return rx.flex(
        *all_fields,
        # class_name=rx.cond(is_edit_mode, "flex-col gap-3", "flex-col gap-0"),
        class_name="flex-col gap-3" if is_edit_mode else "flex-col gap-2",
    )


def add_user_button(
    label: str = "Benutzer hinzufügen",
    icon: str = "plus",
    icon_size: int = 16,
    **kwargs,
) -> rx.Component:
    return rx.dialog.root(
        rx.dialog.trigger(
            mn.button(
                label,
                left_section=rx.icon(icon, size=icon_size),
                **kwargs,
            ),
        ),
        rx.dialog.content(
            dialog_header(
                icon="users",
                title="Benutzer hinzufügen",
                description="Bitte füllen Sie das Formular mit den Benutzerdaten aus.",
            ),
            rx.flex(
                rx.form.root(
                    user_form_fields(),
                    dialog_buttons(
                        submit_text="Benutzer speichern",
                    ),
                    on_submit=UserState.create_user,
                    reset_on_submit=False,
                ),
                class_name="w-full flex-col gap-4",
            ),
            class_name="dialog",
        ),
    )


def update_user_button(
    user: User,
    icon: str = "square-pen",
    icon_size: int = 16,
    **kwargs,
) -> rx.Component:
    return rx.dialog.root(
        rx.dialog.trigger(
            rx.icon_button(
                rx.icon(icon, size=icon_size),
                on_click=lambda: UserState.select_user(user.user_id),
                **kwargs,
            ),
        ),
        rx.dialog.content(
            dialog_header(
                icon="users",
                title="Benutzer bearbeiten",
                description="Aktualisieren Sie die Benutzerdaten",
            ),
            rx.flex(
                rx.form.root(
                    user_form_fields(user=user),
                    dialog_buttons(
                        submit_text="Benutzer aktualisieren",
                    ),
                    on_submit=UserState.update_user,
                    reset_on_submit=False,
                ),
                direction="column",
                spacing="4",
            ),
            class_name="dialog",
        ),
        width="660px",
    )


def delete_user_button(user: User, **kwargs) -> rx.Component:
    """Use the generic delete dialog component."""
    return delete_dialog(
        title="Löschen bestätigen",
        content=rx.cond(user.email, user.email, "Unbekannter Benutzer"),
        on_click=lambda: UserState.delete_user(user.user_id),
        icon_button=True,
        color_scheme="red",
        **kwargs,
    )


def users_table_row(
    user: User, additional_components: list | None = None
) -> rx.Component:
    """Show a customer in a table row.

    Args:
        user: The user object to display
        roles: List of available roles
        additional_components: Optional list of component functions that will be
                              called with (user=user, roles=roles) and rendered
                              to the left of the edit button
    """
    if additional_components is None:
        additional_components = []

    # Generate additional components with the same parameters as edit/delete buttons
    rendered_additional_components = [
        component_func(user=user) for component_func in additional_components
    ]

    return mn.table.tr(
        mn.table.td(
            mn.text(user.name, size="sm", fw="500", style={"whiteSpace": "nowrap"}),
        ),
        mn.table.td(
            mn.text(user.email, size="sm", c="dimmed", style={"whiteSpace": "nowrap"}),
        ),
        mn.table.td(
            rx.center(
                rx.cond(
                    user.is_active,
                    rx.icon("check", color="green", size=18),
                    rx.icon("x", color="red", size=18),
                )
            ),
            width="1%",
        ),
        mn.table.td(
            rx.center(
                rx.cond(
                    user.is_verified,
                    rx.icon("check", color="green", size=18),
                    rx.icon("x", color="red", size=18),
                )
            ),
            width="1%",
        ),
        mn.table.td(
            rx.center(
                rx.cond(
                    user.is_admin,
                    rx.icon("check", color="green", size=18),
                    rx.icon("x", color="red", size=18),
                )
            ),
            width="1%",
        ),
        mn.table.td(
            mn.group(
                *rendered_additional_components,
                update_user_button(user=user, variant="ghost"),
                delete_user_button(
                    user=user,
                    variant="ghost",
                ),
                gap="xs",
                wrap="nowrap",
                align="center",
            ),
            width="1%",
            style={"whiteSpace": "nowrap"},
        ),
    )


def loading() -> rx.Component:
    """Loading indicator for the users table."""
    return mn.table.tr(
        mn.table.td(
            rx.hstack(
                rx.spinner(size="3"),
                mn.text("Lade Benutzer...", size="sm"),
                align="center",
                justify="center",
                spacing="3",
            ),
            col_span=6,
            style={"textAlign": "center"},
        ),
    )


def users_table(additional_components: list | None = None) -> rx.Component:
    """Create a users table with optional additional components.

    Args:
        roles: List of available roles for user management
        additional_components: Optional list of component functions that will be
                              rendered to the left of the edit button for each user.
                              Each function will be called with (user=user, roles=roles)
    """
    if additional_components is None:
        additional_components = []

    # Solution 1: Store in component props instead of capturing
    def render_user_row(user: User) -> rx.Component:
        """Render a single user row - avoids capturing in lambda."""
        return users_table_row(
            user=user,
            additional_components=additional_components,
        )

    return mn.stack(
        rx.flex(
            add_user_button(),
            rx.spacer(),
            width="100%",
            margin_bottom="md",
            gap="12px",
            align="center",
        ),
        mn.table(
            mn.table.thead(
                mn.table.tr(
                    mn.table.th(mn.text("Name", size="sm", fw="700")),
                    mn.table.th(mn.text("Email", size="sm", fw="700")),
                    mn.table.th(
                        mn.text("Aktiv", size="sm", fw="700"),
                        style={"textAlign": "center"},
                    ),
                    mn.table.th(
                        mn.text("Verifiziert", size="sm", fw="700"),
                        style={"textAlign": "center"},
                    ),
                    mn.table.th(
                        mn.text("Admin", size="sm", fw="700"),
                        style={"textAlign": "center"},
                    ),
                    mn.table.th(mn.text("", size="sm")),
                ),
            ),
            mn.table.tbody(
                rx.cond(
                    UserState.is_loading,
                    loading(),
                    rx.foreach(
                        UserState.users,
                        render_user_row,
                    ),
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
        on_mount=UserState.load_users,
    )
