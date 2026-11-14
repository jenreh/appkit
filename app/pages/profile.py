from typing import Any

import reflex as rx

from appkit_user.user_management.components.user_profile import user_profile_view

from app.components.templates import authenticated


def create_profile_page(
    navbar: rx.Component,
    route: str = "/profile",
    title: str = "Profil",
    **kwargs: Any,
) -> rx.Component:
    """Create the profile page with authentication.

    Args:
        navbar: The navigation bar to use in the page.

    Returns:
        The profile page component.
    """

    @authenticated(
        route=route,
        title=title,
        navbar=navbar,
    )
    def _profile_page() -> rx.Component:
        """The profile page.

        Returns:
            The UI for the profile page.
        """
        return user_profile_view(**kwargs)

    return _profile_page
