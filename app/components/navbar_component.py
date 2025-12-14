import logging

import reflex as rx

import appkit_mantine as mn
from appkit_assistant.state.thread_state import ThreadListState
from appkit_ui.global_states import LoadingState
from appkit_user.authentication.components.components import requires_admin
from appkit_user.authentication.states import LoginState

logger = logging.getLogger(__name__)

accent_bg_color = rx.color("accent", 3)
gray_bg_color = rx.color("gray", 3)

accent_color = rx.color("accent", 3)
text_color = rx.color("gray", 11)
accent_text_color = rx.color("accent", 9)

border = f"1px solid {rx.color('gray', 5)}"
border_radius = "var(--radius-2)"

box_shadow_right_light = "inset -5px -5px 15px -5px rgba(0, 0, 0, 0.1)"
box_shadow_right_dark = "inset -5px -5px 15px -5px rgba(0.9, 0.9, 0.9, 0.1)"

sidebar_width = "375px"


sub_heading_styles = {
    "text_transform": "uppercase",
    "letter_spacing": "1px",
    "font-weight": "bold",
    "font-size": "0.8rem",
    "padding": "0.35em",
    "margin_top": "1em",
    "color": rx.color("gray", 10),
}


def admin_sidebar_item(
    label: str, icon: str, url: str, svg: str | None = None
) -> rx.Component:
    active = (rx.State.router.page.path == url.lower()) | (
        (rx.State.router.page.path == "/") & label == "Overview"
    )

    return rx.link(
        rx.hstack(
            rx.box(width="16px"),
            rx.cond(
                svg,
                rx.image(svg, height="16px", width="16px", fill="var(--gray-9)"),
                rx.icon(icon, size=15, color="var(--gray-9)"),
            ),
            rx.text(label, size="2", weight="regular"),
            color=rx.cond(
                active,
                accent_text_color,
                text_color,
            ),
            background_color=rx.cond(active, accent_bg_color, "transparent"),
            style={
                "_hover": {
                    "background_color": rx.cond(
                        active,
                        accent_bg_color,
                        gray_bg_color,
                    ),
                    "color": rx.cond(
                        active,
                        accent_text_color,
                        text_color,
                    ),
                    "opacity": "1",
                },
                "opacity": rx.cond(
                    active,
                    "1",
                    "0.95",
                ),
            },
            align="center",
            border_radius=border_radius,
            width="100%",
            padding="3px",
        ),
        on_click=[
            LoadingState.set_is_loading(True),
        ],
        underline="none",
        href=url,
        width="100%",
    )


def sidebar_item(label: str, icon: str, url: str) -> rx.Component:
    active = (rx.State.router.page.path == url.lower()) | (
        (rx.State.router.page.path == "/") & label == "Overview"
    )

    return rx.link(
        rx.hstack(
            rx.cond(icon == "", rx.spacer(), rx.icon(icon, size=17)),
            rx.text(label, size="3", weight="regular"),
            color=rx.cond(
                active,
                accent_text_color,
                text_color,
            ),
            background_color=rx.cond(active, accent_bg_color, "transparent"),
            style={
                "_hover": {
                    "background_color": rx.cond(
                        active,
                        accent_bg_color,
                        gray_bg_color,
                    ),
                    "color": rx.cond(
                        active,
                        accent_text_color,
                        text_color,
                    ),
                    "opacity": "1",
                },
                "opacity": rx.cond(
                    active,
                    "1",
                    "0.95",
                ),
            },
            align="center",
            border_radius=border_radius,
            width="100%",
            spacing="2",
            padding="0.35em",
        ),
        on_click=[
            LoadingState.set_is_loading(True),
        ],
        underline="none",
        href=url,
        width="100%",
    )


def sidebar_icon_button(
    label: str,
    icon: str,
    url: str,
) -> rx.Component:
    active = (rx.State.router.page.path == url.lower()) | (
        (rx.State.router.page.path == "/") & label == "Overview"
    )

    return rx.link(
        rx.tooltip(
            rx.hstack(
                rx.icon(icon, size=17),
                color=rx.cond(
                    active,
                    accent_text_color,
                    text_color,
                ),
                background_color=rx.cond(active, accent_bg_color, "transparent"),
                style={
                    "_hover": {
                        "background_color": rx.cond(
                            active,
                            accent_bg_color,
                            gray_bg_color,
                        ),
                        "color": rx.cond(
                            active,
                            accent_text_color,
                            text_color,
                        ),
                        "opacity": "1",
                    },
                    "opacity": rx.cond(
                        active,
                        "1",
                        "0.95",
                    ),
                },
                padding="0.35em",
            ),
            content=label,
        ),
        on_click=[
            LoadingState.set_is_loading(True),
        ],
        underline="none",
        href=url,
    )


def logout_button() -> rx.Component:
    return rx.link(
        rx.tooltip(
            rx.hstack(
                rx.icon("log-out", size=18),
                color=text_color,
                style={
                    "_hover": {
                        "background_color": gray_bg_color,
                        "color": text_color,
                        "opacity": "1",
                    },
                    "opacity": "0.95",
                },
                padding="0.35em",
            ),
            content="Abmelden",
        ),
        underline="none",
        on_click=[
            ThreadListState.reset_on_logout,
            LoginState.terminate_session,
            LoginState.logout,
        ],
    )


def navbar_default_header() -> rx.Component:
    return rx.hstack(
        rx.color_mode_cond(
            rx.image("/img/logo.svg", height="56px", margin_top="1.25em"),
            rx.image("/img/logo_dark.svg", height="56px", margin_top="1.25em"),
        ),
        rx.spacer(),
        align="center",
        width="100%",
        padding="0.35em",
        margin_bottom="1em",
    )


def navbar_default_footer(version: str) -> rx.Component:
    return rx.vstack(
        rx.hstack(
            sidebar_icon_button(label="Profil", icon="user", url="/profile"),
            rx.color_mode.button(style={"opacity": "0.8", "scale": "0.95"}),
            rx.spacer(),
            logout_button(),
            wrap="nowrap",
            justify="center",
            align="center",
            width="100%",
        ),
        rx.text(
            f"Version {version}",
            size="1",
            width="100%",
            margin_left="3px",
            color=rx.color("gray", 7),
        ),
        justify="start",
        align="start",
        width="100%",
        padding="0.35em",
    )


def navbar(
    navbar_items: rx.Component,
    version: str,
    navbar_admin_items: rx.Component,
    navbar_header: rx.Component | None = None,
    navbar_footer: rx.Component | None = None,
    **kwargs,
) -> rx.Component:
    if navbar_header is None:
        navbar_header = navbar_default_header()

    if navbar_footer is None:
        navbar_footer = navbar_default_footer(version=version)

    return rx.flex(
        rx.vstack(
            navbar_header,
            rx.box(
                class_name=rx.cond(
                    LoadingState.is_loading, "rainbow-gradient-bar", "default-bar"
                ),
            ),
            mn.scroll_area.stateful(
                navbar_items,
                requires_admin(
                    navbar_admin_items,
                ),
                width="100%",
                type="hover",
                scrollbars="y",
                scrollbar_size="6px",
                show_controls=False,
                persist_key="navbar_scroll_area",
                # Allow the scroll area to grow and take available space
                flex="1",
                min_height="0",
                height="100%",
            ),
            navbar_footer,
            justify="end",
            align="end",
            width="18em",
            height="100dvh",
            padding="1em",
        ),
        max_width=sidebar_width,
        width="100%",
        height="100%",
        position="sticky",
        justify="end",
        top="0px",
        left="0px",
        flex="1",
        spacing="0",
        bg=rx.color("gray", 2),
        border_right=border,
        box_shadow=rx.color_mode_cond(
            light=box_shadow_right_light,
            dark=box_shadow_right_dark,
        ),
        **kwargs,
    )
