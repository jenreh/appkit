"""Authenticated page decorator."""

from __future__ import annotations

from collections.abc import Callable

import reflex as rx

import appkit_mantine as mn
from appkit_user.authentication.components import default_fallback, session_monitor
from appkit_user.authentication.states import UserSession

# Meta tags for the app.
default_meta = [
    {
        "name": "viewport",
        "content": "width=device-width, shrink-to-fit=no, initial-scale=1",
    },
]


def _default_template(content: rx.Component) -> rx.Component:
    """Default page template: bare mn.app_shell with main content only."""
    return mn.app_shell(mn.app_shell.main(content))


def authenticated_page(
    route: str | None = None,
    title: str | None = None,
    description: str | None = None,
    template: Callable[[rx.Component], rx.Component] | None = None,
    admin_only: bool = False,
    meta: list[dict] | None = None,
    script_tags: list[rx.Component] | None = None,
    on_load: rx.EventHandler | list[rx.EventHandler] | None = None,
) -> Callable[[Callable[[], rx.Component]], rx.Component]:
    """Page decorator with authentication check and flexible layout.

    The ``template`` callable receives the page content as an ``rx.Component``
    and must return an ``rx.Component`` wrapping it.  When omitted,
    ``_default_template`` is used (bare ``mn.app_shell`` with no sections).

    Usage::

        @authenticated_page(route="/dashboard", title="Dashboard")
        def dashboard_page() -> rx.Component:
            return rx.box("Content")


        # With a custom layout template:
        def my_template(content: rx.Component) -> rx.Component:
            return mn.app_shell(
                mn.app_shell.navbar(app_navbar()),
                mn.app_shell.main(content),
                navbar={"width": 250, "breakpoint": "sm"},
            )


        @authenticated_page(route="/settings", title="Settings", template=my_template)
        def settings_page() -> rx.Component:
            return rx.box("Settings")

    Args:
        route: URL route for this page.
        title: Page title shown in the browser tab.
        description: Meta description for the page.
        template: Callable ``(content) -> rx.Component`` defining the layout.
            Defaults to a bare ``mn.app_shell``.
        admin_only: Restrict access to admin users only.
        meta: Additional meta tags to add to the page.
        script_tags: Script components to inject into the page.
        on_load: Additional handlers called on page load. The ``SessionFilter``
            middleware gates the route before any of them are dispatched.
    """
    resolved_template = template if template is not None else _default_template
    handlers = mn.with_loading_reset(on_load)

    def decorator(page_content: Callable[[], rx.Component]) -> rx.Component:
        all_meta = [*default_meta, *(meta or [])]
        is_admin: bool = UserSession.user.is_admin

        @rx.page(
            route=route,
            title=title,
            description=description,
            meta=all_meta,
            script_tags=script_tags,
            on_load=handlers,
        )
        def theme_wrap() -> rx.Component:
            default_page = mn.theme_wrapper(
                rx.fragment(
                    session_monitor(),
                    resolved_template(page_content()),
                )
            )
            no_permission_page = mn.theme_wrapper(
                rx.fragment(
                    session_monitor(),
                    resolved_template(default_fallback()),
                )
            )
            return rx.cond(
                admin_only,
                rx.cond(is_admin, default_page, no_permission_page),
                default_page,
            )

        return theme_wrap

    return decorator
