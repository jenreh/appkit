"""App page layouts: splash pages and pages with a navbar."""

from __future__ import annotations

from collections.abc import Callable

import reflex as rx

import appkit_mantine as mn
from appkit_user.authentication.components import default_fallback, session_monitor
from appkit_user.authentication.states import UserSession
from appkit_user.authentication.templates import default_meta


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
    """The template for each page of the app that requires authentication.

    Authentication is enforced by the
    :class:`appkit_user.authentication.session_filter.SessionFilter`
    middleware, which gates the route before any ``on_load`` handler is
    dispatched — an unauthenticated visitor never reaches the page handlers.
    ``admin_only`` additionally gates rendering, but that is a render-layer
    check only — enforce admin-only *events* with the
    :func:`appkit_user.authentication.decorators.requires_admin` decorator.
    """
    handlers = mn.with_loading_reset(on_load)

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
            # Create navbar component if provided
            navbar_component = navbar if navbar else rx.fragment()
            default_page = mn.theme_wrapper(
                rx.fragment(
                    session_monitor(),
                    templated_page(page_content, navbar_component),
                )
            )
            no_permission_page = mn.theme_wrapper(
                rx.fragment(
                    session_monitor(),
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
    handlers = mn.with_loading_reset(on_load)

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
            default_page = mn.theme_wrapper(
                rx.fragment(
                    session_monitor(),  # Inject session monitor for timeout detection
                    templated_page(
                        page_content,
                        navbar_component,
                    ),
                )
            )
            no_permission_page = mn.theme_wrapper(
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
