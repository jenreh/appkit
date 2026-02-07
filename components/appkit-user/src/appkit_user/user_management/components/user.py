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
    icon_size: int = 19,
    **kwargs,
) -> rx.Component:
    return rx.dialog.root(
        rx.dialog.trigger(
            rx.button(
                rx.icon(icon, size=icon_size),
                rx.text(label, display=["none", "none", "block"]),
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
    icon_size: int = 19,
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
            rx.cond(user.name, user.name, ""),
            class_name="whitespace-nowrap",
        ),
        mn.table.td(
            rx.cond(user.email, user.email, ""),
            class_name="whitespace-nowrap",
        ),
        mn.table.td(
            rx.cond(
                user.is_active,
                rx.icon("user-check", color="green", size=21),
                rx.icon("user-x", color="crimson", size=21),
            ),
            class_name="text-center",
        ),
        mn.table.td(
            rx.cond(
                user.is_verified,
                rx.icon("user-check", color="green", size=21),
                rx.icon("user-x", color="crimson", size=21),
            ),
            class_name="text-center",
        ),
        mn.table.td(
            rx.cond(
                user.is_admin,
                rx.icon("user-check", color="green", size=21),
                rx.icon("user-x", color="crimson", size=21),
            ),
            class_name="text-center",
        ),
        mn.table.td(
            rx.hstack(
                *rendered_additional_components,
                update_user_button(user=user, variant="surface"),
                delete_user_button(user=user, variant="subtle"),
                class_name="whitespace-nowrap",
            ),
        ),
        class_name="justify-center items-center",
        # style={"_hover": {"bg": rx.color("gray", 2)}},
    )


def loading() -> rx.Component:
    """Loading indicator for the users table."""
    return mn.table.tr(
        mn.table.td(
            rx.hstack(
                rx.spinner(size="3"),
                rx.text("Lade Benutzer...", size="3"),
            ),
            col_span=6,
            class_name="text-center justify-center",
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

    return rx.fragment(
        rx.flex(
            add_user_button(),
            rx.spacer(),
        ),
        mn.table(
            mn.table.thead(
                mn.table.tr(
                    mn.table.th("Name"),
                    mn.table.th("Email", width="auto"),
                    mn.table.th("Aktiv", width="90px"),
                    mn.table.th("Verifiziert", width="90px"),
                    mn.table.th("Admin", width="90px"),
                    mn.table.th("", width="110px"),
                ),
            ),
            rx.cond(
                UserState.is_loading,
                mn.table.tbody(loading()),
                mn.table.tbody(
                    rx.foreach(
                        UserState.users,
                        render_user_row,
                    )
                ),
            ),
            highlight_on_hover=True,
            sticky_header=True,
            class_name="w-full",
            on_mount=UserState.load_users,
        ),
    )
