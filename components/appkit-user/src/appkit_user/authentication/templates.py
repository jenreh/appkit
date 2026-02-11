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

        def templated_page():
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
        def theme_wrap():
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
        style={"overflow": "hidden"},
    )


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
        on_load.append(LoadingState.set_is_loading(False))
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
        def theme_wrap():
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

    # Build on_load handlers with auth check FIRST
    handlers = [LoginState.check_auth]

    if on_load is None:
        handlers.append(LoadingState.set_is_loading(False))
    elif isinstance(on_load, list):
        handlers.extend(on_load)
        handlers.append(LoadingState.set_is_loading(False))
    elif isinstance(on_load, rx.EventHandler):
        handlers.extend([on_load, LoadingState.set_is_loading(False)])

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
        def theme_wrap():
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
