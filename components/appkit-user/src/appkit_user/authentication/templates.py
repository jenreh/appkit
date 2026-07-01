"""Common templates used between pages in the app."""

from __future__ import annotations

import logging
from collections.abc import Callable

import reflex as rx

import appkit_mantine as mn
from appkit_ui.global_states import LoadingState
from appkit_user.authentication.components import default_fallback, session_monitor
from appkit_user.authentication.states import LoginState, UserSession

logger = logging.getLogger(__name__)

# Meta tags for the app.
default_meta = [
    {
        "name": "viewport",
        "content": "width=device-width, shrink-to-fit=no, initial-scale=1",
    },
]


class ThemeState(rx.State):
    """The state for the theme of the app."""

    # accent_color: str = "crimson"
    gray_color: str = "gray"
    radius: str = "large"
    scaling: str = "100%"
    appearance: str = "inherit"


def theme_wrapper(content: rx.Component) -> rx.Component:
    return rx.theme(
        content,
        has_background=True,
        gray_color=ThemeState.gray_color,
        radius=ThemeState.radius,
        scaling=ThemeState.scaling,
        appearance=ThemeState.appearance,
        class_name=rx.cond(LoadingState.is_loading, "cursor-wait", ""),
    )


def default_layout(
    route: str | None = None,
    title: str | None = None,
    description: str | None = None,
    meta: str | None = None,
    script_tags: list[rx.Component] | None = None,
    on_load: rx.EventHandler | list[rx.EventHandler] | None = None,
) -> Callable[[Callable[[], rx.Component]], rx.Component]:
    """The template for each page of the app.

    Args:
        route: The route to reach the page.
        title: The title of the page.
        description: The description of the page.
        meta: Additionnal meta to add to the page.
        on_load: The event handler(s) called when the page load.
        script_tags: Scripts to attach to the page.

    Returns:
        The template with the page content.
    """

    def decorator(page_content: Callable[[], rx.Component]) -> rx.Component:
        all_meta = [*default_meta, *(meta or [])]

        def templated_page() -> rx.Component:
            return rx.center(
                page_content(),
                width="100%",
                height="100vh",
                class_name="splash-container",
            )

        @rx.page(
            route=route,
            title=title,
            description=description,
            meta=all_meta,
            script_tags=script_tags,
            on_load=on_load,
        )
        def theme_wrap() -> rx.Component:
            return rx.theme(
                templated_page(),
                has_background=True,
                appearance="dark",
            )

        return theme_wrap

    return decorator


def _render_layout(
    content: rx.Component,
    navbar_component: rx.Component,
    with_header: bool,
) -> rx.Component:
    """Shared layout renderer using Mantine Flex and Stack."""
    return mn.flex(
        navbar_component,
        mn.stack(
            content,
            w="100%",
            m=rx.cond(with_header, "48px 0 0 0", "0"),
            p=rx.cond(with_header, "0", "24px"),
            flex="1",
            min_w="0",
            h="100vh",
            style={"overflowY": "auto", "overflowX": "hidden"},
        ),
        w="100%",
        h="100vh",
        align="flex-start",
        pos="relative",
        p="0",
        style={"overflow": "hidden"},
    )


def _build_auth_handlers(
    on_load: rx.EventHandler | list[rx.EventHandler] | None,
) -> list[rx.EventHandler]:
    """Build on_load handlers: auth check first, loading state last."""
    handlers: list[rx.EventHandler] = [LoginState.check_auth]
    if on_load is None:
        handlers.append(LoadingState.set_is_loading(False))
    elif isinstance(on_load, list):
        handlers.extend(on_load)
        handlers.append(LoadingState.set_is_loading(False))
    else:
        handlers.extend([on_load, LoadingState.set_is_loading(False)])
    return handlers


def navbar_layout(
    route: str | None = None,
    title: str | None = None,
    description: str | None = None,
    navbar: rx.Component | None = None,
    with_header: bool = False,
    admin_only: bool = False,
    meta: list[dict] | None = None,  # Updated type hint
    script_tags: list[rx.Component] | None = None,
    on_load: rx.EventHandler | list[rx.EventHandler] | None = None,
) -> Callable[[Callable[[], rx.Component]], rx.Component]:
    """The template for each page of the app that requires authentication."""
    if on_load is None:
        on_load = [LoadingState.set_is_loading(False)]
    elif isinstance(on_load, list):
        on_load = [*on_load, LoadingState.set_is_loading(False)]
    elif isinstance(on_load, rx.EventHandler):
        on_load = [on_load, LoadingState.set_is_loading(False)]

    def decorator(page_content: Callable[[], rx.Component]) -> rx.Component:
        all_meta = [*default_meta, *(meta or [])]
        is_admin: bool = UserSession.user.is_admin

        def templated_page(
            content: Callable[[], rx.Component],
            navbar_component: rx.Component,
        ) -> rx.Component:
            return _render_layout(content(), navbar_component, with_header)

        @rx.page(
            route=route,
            title=title,
            description=description,
            meta=all_meta,
            script_tags=script_tags,
            on_load=on_load,
        )
        def theme_wrap() -> rx.Component:
            # Create navbar component if provided
            navbar_component = navbar if navbar else rx.fragment()
            default_page = theme_wrapper(templated_page(page_content, navbar_component))
            no_permission_page = theme_wrapper(
                templated_page(
                    lambda: rx.center(
                        rx.heading(
                            "Sie haben nicht die notwendigen Berechtigungen um auf diese Seite zuzugreifen.",  # noqa
                            size="4",
                        ),
                        width="100%",
                        margin_top="10em",
                    ),
                    navbar_component,
                )
            )

            return rx.cond(
                admin_only,
                rx.cond(
                    is_admin,
                    default_page,
                    no_permission_page,
                ),
                default_page,
            )

        return theme_wrap

    return decorator


def authenticated(
    route: str | None = None,
    title: str | None = None,
    description: str | None = None,
    navbar: rx.Component | None = None,
    with_header: bool = True,
    admin_only: bool = False,
    meta: list[dict] | None = None,
    script_tags: list[rx.Component] | None = None,
    on_load: rx.EventHandler | list[rx.EventHandler] | None = None,
) -> Callable[[Callable[[], rx.Component]], rx.Component]:
    """The template for each page of the app that requires authentication."""
    handlers = _build_auth_handlers(on_load)

    def decorator(page_content: Callable[[], rx.Component]) -> rx.Component:
        all_meta = [*default_meta, *(meta or [])]
        is_admin: bool = UserSession.user.is_admin

        def templated_page(
            content: Callable[[], rx.Component],
            navbar_component: rx.Component,
        ) -> rx.Component:
            return _render_layout(content(), navbar_component, with_header)

        @rx.page(
            route=route,
            title=title,
            description=description,
            meta=all_meta,
            script_tags=script_tags,
            on_load=handlers,
        )
        def theme_wrap() -> rx.Component:
            navbar_component = navbar if navbar else rx.fragment()
            default_page = theme_wrapper(
                rx.fragment(
                    session_monitor(),  # Inject session monitor for timeout detection
                    templated_page(
                        page_content,
                        navbar_component,
                    ),
                )
            )
            no_permission_page = theme_wrapper(
                rx.fragment(
                    session_monitor(),  # Also monitor on permission denied pages
                    templated_page(
                        default_fallback,
                        navbar_component,
                    ),
                )
            )

            return rx.cond(
                admin_only,
                rx.cond(
                    is_admin,
                    default_page,
                    no_permission_page,
                ),
                default_page,
            )

        return theme_wrap

    return decorator


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
        on_load: Additional handlers called on page load. Auth check always runs first.
    """
    resolved_template = template if template is not None else _default_template
    handlers = _build_auth_handlers(on_load)

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
            default_page = theme_wrapper(
                rx.fragment(
                    session_monitor(),
                    resolved_template(page_content()),
                )
            )
            no_permission_page = theme_wrapper(
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
