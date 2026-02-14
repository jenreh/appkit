import reflex as rx

import appkit_mantine as mn
from appkit_ui.components.header import header
from appkit_user.authentication.components.components import requires_admin
from appkit_user.authentication.templates import authenticated
from appkit_user.user_management.components.user import users_table
from appkit_user.user_management.states.user_states import UserState

from app.components.navbar import app_navbar
from app.roles import ALL_ROLES


@authenticated(
    route="/admin/users",
    title="Users",
    navbar=app_navbar(),
    admin_only=True,
    on_load=[UserState.set_available_roles(ALL_ROLES)],
)
def users_page() -> rx.Component:
    additional_components = []

    return requires_admin(
        mn.stack(
            header("Benutzer"),
            mn.stack(
                users_table(additional_components=additional_components),
                max_width="1200px",
                width="100%",
            ),
            width="100%",
            padding="2rem",
        )
    )
