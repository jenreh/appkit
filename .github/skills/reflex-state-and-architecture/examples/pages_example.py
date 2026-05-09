"""
Page Factory — canonical pattern.

Derived from: knai-team pages.py + app/app.py registration.

Every feature package exports ONE factory function per page.
The factory accepts `navbar` (and optionally route/title overrides)
so that the app shell can inject its own navbar without the package
knowing how it was built.
"""

from collections.abc import Callable

import reflex as rx
from knai_myfeature.components.my_feature_components import my_feature_page_content
from knai_myfeature.state.my_feature_state import MyFeatureState

from appkit_ui.components.header import header
from appkit_user.authentication.templates import authenticated

# ─── Single-page factory ──────────────────────────────────────────────────────


def create_my_feature_page(
    navbar: rx.Component,
    route: str = "/my-feature",
    title: str = "My Feature",
    with_header: bool = True,
) -> Callable:
    """
    Register the feature page with Reflex and return the page function.

    Args:
        navbar:      Navbar component from the app shell (call app_navbar()).
        route:       URL path. Change to avoid collisions.
        title:       Page <title> and header text.
        with_header: Pass False to suppress the appkit_ui header bar.

    Usage in app/app.py:
        from knai_myfeature.pages import create_my_feature_page
        create_my_feature_page(app_navbar())
    """

    @authenticated(
        route=route,
        title=title,
        navbar=navbar,
        with_header=with_header,
        on_load=MyFeatureState.on_load,
        # Choose ONE of:
        admin_only=True,  # only admins
        # role="my-feature",         # specific role from app/roles.py
    )
    def my_feature_page() -> rx.Component:
        return rx.flex(
            header(title),
            my_feature_page_content(),
            direction="column",
            gap="4",
            w="100%",
            p="2rem",
            mb="4em",
        )

    return my_feature_page


# ─── Multi-page factory (when a package contributes several routes) ────────────


def create_my_feature_list_page(
    navbar: rx.Component,
    route: str = "/my-feature",
    title: str = "My Feature",
) -> Callable:
    """List / overview page."""

    @authenticated(
        route=route,
        title=title,
        navbar=navbar,
        on_load=MyFeatureState.on_load,
        role="my-feature",
    )
    def my_feature_list_page() -> rx.Component:
        return rx.flex(
            header(title),
            my_feature_page_content(),
            direction="column",
            gap="4",
            w="100%",
            p="2rem",
        )

    return my_feature_list_page


def create_my_feature_admin_page(
    navbar: rx.Component,
    route: str = "/admin/my-feature",
    title: str = "My Feature Admin",
) -> Callable:
    """Admin page for the same feature — different route, admin_only."""

    @authenticated(
        route=route,
        title=title,
        navbar=navbar,
        on_load=MyFeatureState.on_load,
        admin_only=True,
    )
    def my_feature_admin_page() -> rx.Component:
        return rx.flex(
            header(title),
            my_feature_page_content(),  # or a different admin component
            direction="column",
            gap="4",
            w="100%",
            p="2rem",
        )

    return my_feature_admin_page


# ─── Registration snippet (copy into app/app.py) ──────────────────────────────
#
# from knai_myfeature.pages import (
#     create_my_feature_list_page,
#     create_my_feature_admin_page,
# )
#
# # After all imports, at module level (not inside a function):
# create_my_feature_list_page(app_navbar())
# create_my_feature_admin_page(app_navbar())
#
# ─────────────────────────────────────────────────────────────────────────────
