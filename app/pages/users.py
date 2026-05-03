from collections.abc import Callable

import reflex as rx

import appkit_mantine as mn
from appkit_ui.components.header import header
from appkit_user.authentication.components.components import requires_admin
from appkit_user.authentication.templates import authenticated
from appkit_user.user_management.components.user import users_table
from appkit_user.user_management.states.user_states import UserState

from app.components.navbar import app_navbar
from app.roles import ALL_ROLES


def users_view(**kwargs) -> rx.Component:
    additional_components = kwargs.get("additional_components", [])

    return mn.stack(
        header("Benutzer"),
        mn.stack(
            users_table(additional_components=additional_components),
            max_width="1200px",
            width="100%",
        ),
        width="100%",
        padding="2rem",
    )


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


def create_users_page(
    navbar: rx.Component,
    route: str = "/admin/users",
    title: str = "Benutzer",
    **kwargs,
) -> Callable:
    """Create the users page with authentication.

    Args:
        navbar: The navigation bar to use in the page.

    Returns:
        The users page component.
    """

    @authenticated(
        route=route,
        title=title,
        navbar=navbar,
    )
    def _users_page() -> rx.Component:
        """The users page.

        Returns:
            The UI for the profile page.
        """
        return users_view(**kwargs)

    return _users_page
