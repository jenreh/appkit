import reflex as rx

import appkit_mantine as mn
from appkit_ui.components.dialogs import (
    delete_dialog,
)
from appkit_ui.components.form_inputs import hidden_field
from appkit_ui.styles import sticky_header_style
from appkit_user.authentication.backend.models import User
from appkit_user.user_management.states.user_states import UserState


def role_checkbox(
    user: User, role: dict[str, str], is_edit_mode: bool = False
) -> rx.Component:
    """Checkbox for a role in the user form."""
    name = role.get("name")
    label = role.get("label", "")
    description = role.get("description", "")

    chk = mn.checkbox(
        label=label,
        name=f"role_{name}",
        default_checked=(
            user.roles.contains(name)
            if is_edit_mode and user.roles is not None
            else False
        ),
        size="sm",
    )

    return rx.cond(
        name,
        mn.box(
            rx.cond(
                description & (description != ""),
                mn.tooltip(
                    chk,
                    label=description,
                ),
                chk,
            ),
            w="100%",
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
        mn.text_input(
            name="name",
            label="Name",
            default_value=user.name if is_edit_mode else "",
            required=True,
            left_section=rx.icon("user", size=16),
        ),
        mn.text_input(
            name="email",
            label="Email",
            description="Die E-Mail-Adresse des Benutzers, wird für die Anmeldung verwendet.",  # noqa: E501
            default_value=user.email if is_edit_mode else "",
            required=True,
            left_section=rx.icon("mail", size=16),
            type="email",
            # pattern matches what was in form_field
            pattern=r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$",
        ),
        mn.password_input(
            name="password",
            label="Passwort" if is_edit_mode else "Initiales Passwort",
            description="Leer lassen, um das aktuelle Passwort beizubehalten",
            default_value="",
            required=False,
            left_section=rx.icon("lock", size=16),
        ),
    ]

    # Status switches (default active for new users)
    # They should be visible in both Add and Edit modes
    status_fields = [
        mn.stack(
            mn.divider(label="Status", size="xs", width="100%", my="xs"),
            mn.flex(
                mn.box(
                    mn.switch(
                        label="Aktiv",
                        name="is_active",
                        default_checked=(
                            user.is_active
                            if is_edit_mode and user.is_active is not None
                            else True  # Default True for new users
                        ),
                        size="sm",
                    ),
                    class_name="w-[50%] max-w-[50%] flex-grow",
                ),
                mn.box(
                    mn.switch(
                        label="Verifiziert",
                        name="is_verified",
                        default_checked=(
                            user.is_verified
                            if is_edit_mode and user.is_verified is not None
                            else True  # Default True for new users created by admin
                        ),
                        size="sm",
                    ),
                    class_name="w-[50%] max-w-[50%] flex-grow",
                ),
                mn.box(
                    mn.switch(
                        label="Superuser",
                        name="is_admin",
                        default_checked=(
                            user.is_admin
                            if is_edit_mode and user.is_admin is not None
                            else False
                        ),
                        size="sm",
                    ),
                    class_name="w-[50%] max-w-[50%] flex-grow",
                ),
                class_name="w-full flex-wrap gap-2",
            ),
            align="stretch",
            gap="xs",
            my="4px",
            w="100%",
        ),
    ]

    # Role fields (available for both add and edit modes)
    def render_role_group(group_name: str, roles: list[dict[str, str]]) -> rx.Component:
        """Render a group of roles with a headline."""
        return mn.stack(
            mn.divider(
                label=group_name,
                size="xs",
                width="100%",
                my="3px",
            ),
            rx.foreach(
                roles,
                lambda role: role_checkbox(
                    user=user, role=role, is_edit_mode=is_edit_mode
                ),
            ),
            gap="xs",
            my="4px",
            w="100%",
        )

    role_fields = [
        mn.stack(
            rx.foreach(
                UserState.sorted_group_names,
                lambda group_name: render_role_group(
                    group_name,
                    UserState.grouped_roles[group_name],
                ),
            ),
            gap="xs",
            my="6px",
            w="100%",
        ),
    ]

    # Combine all fields
    left_fields = basic_fields + status_fields

    return mn.flex(
        # Left column: inputs and status (non-scrolling)
        mn.box(
            mn.flex(
                *left_fields,
                direction="column",
                gap="md" if is_edit_mode else "sm",
                width="100%",
            ),
            flex="1",
            min_width="0",
            overflow="hidden",
        ),
        mn.box(
            mn.text("Berechtigungen", size="sm", fw="500", mt="3px"),
            mn.scroll_area.autosize(
                *role_fields,
                max_height="60vh",
                width="100%",
                type="always",
                offset_scrollbars=True,
                padding="0",
            ),
            flex="1",
            min_width="0",
            height="100%",
            overflow="hidden",
        ),
        direction="row",
        gap="md",
        width="100%",
        height="100%",
        align="flex-start",
    )


def _modal_footer(
    submit_label: str,
    on_cancel: rx.EventHandler,
) -> rx.Component:
    """Footer buttons for add/edit modals."""
    return rx.flex(
        mn.button(
            "Abbrechen",
            variant="subtle",
            on_click=on_cancel,
        ),
        mn.button(
            submit_label,
            type="submit",
            loading=UserState.is_loading,
        ),
        direction="row",
        gap="9px",
        justify_content="end",
        padding="16px",
        border_top="1px solid var(--mantine-color-default-border)",
        background="var(--mantine-color-body)",
        width="100%",
    )


def _user_modal(
    title: str,
    opened: bool | rx.Var,
    on_close: rx.EventHandler,
    on_submit: rx.EventHandler,
    submit_label: str,
    content: rx.Component,
) -> rx.Component:
    """Shared modal structure for add/edit user."""
    return mn.modal(
        rx.form.root(
            rx.flex(
                rx.box(
                    content,
                    flex="1",
                    min_height="0",
                    width="100%",
                    gap="md",
                ),
                _modal_footer(submit_label, on_close),
                direction="column",
                height="100%",
                width="100%",
            ),
            on_submit=on_submit,
            reset_on_submit=False,
            height="100%",
        ),
        title=title,
        opened=opened,
        on_close=on_close,
        size="lg",
        centered=True,
        overlay_props={"backgroundOpacity": 0.5, "blur": 4},
    )


def add_user_modal() -> rx.Component:
    """Modal for adding a new user."""
    return _user_modal(
        title="Benutzer hinzufügen",
        opened=UserState.add_modal_open,
        on_close=UserState.close_add_modal,
        on_submit=UserState.create_user,
        submit_label="Benutzer speichern",
        content=user_form_fields(),
    )


def edit_user_modal() -> rx.Component:
    """Modal for editing an existing user."""
    return _user_modal(
        title="Benutzer bearbeiten",
        opened=UserState.edit_modal_open,
        on_close=UserState.close_edit_modal,
        on_submit=UserState.update_user,
        submit_label="Benutzer aktualisieren",
        content=user_form_fields(user=UserState.selected_user),
    )


def add_user_button(
    label: str = "Benutzer hinzufügen",
    icon: str = "plus",
    icon_size: int = 16,
    **kwargs,
) -> rx.Component:
    return mn.button(
        label,
        left_section=rx.icon(icon, size=icon_size),
        on_click=UserState.open_add_modal,
        **kwargs,
    )


def update_user_button(
    user: User,
    icon: str = "square-pen",
    icon_size: int = 16,
    **kwargs,
) -> rx.Component:
    return rx.icon_button(
        rx.icon(icon, size=icon_size),
        on_click=lambda: UserState.select_user_and_open_edit(user.user_id),
        **kwargs,
    )


def delete_user_button(user: User, **kwargs) -> rx.Component:
    """Use the generic delete dialog component."""
    return delete_dialog(
        title="Löschen bestätigen",
        content=rx.cond(user.email, user.email, "Unbekannter Benutzer"),
        on_click=lambda: UserState.delete_user(user.user_id),
        icon_button=True,
        color="red",
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
            width="72px",
        ),
        mn.table.td(
            rx.center(
                rx.cond(
                    user.is_verified,
                    rx.icon("check", color="green", size=18),
                    rx.icon("x", color="red", size=18),
                )
            ),
            width="72px",
        ),
        mn.table.td(
            rx.center(
                rx.cond(
                    user.is_admin,
                    rx.icon("check", color="green", size=18),
                    rx.icon("x", color="red", size=18),
                )
            ),
            width="72px",
        ),
        mn.table.td(
            mn.group(
                *rendered_additional_components,
                update_user_button(user=user, variant="ghost"),
                delete_user_button(
                    user=user,
                    variant="subtle",
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
        add_user_modal(),
        edit_user_modal(),
        rx.flex(
            add_user_button(),
            mn.text_input(
                placeholder="Benutzer suchen...",
                left_section=rx.icon("search", size=16),
                left_section_pointer_events="none",
                value=UserState.search_filter,
                on_change=UserState.set_search_filter,
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
                    style=sticky_header_style,
                ),
            ),
            mn.table.tbody(
                rx.cond(
                    UserState.is_loading,
                    loading(),
                    rx.foreach(
                        UserState.filtered_users,
                        render_user_row,
                    ),
                )
            ),
            sticky_header=True,
            sticky_header_offset="0px",
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
