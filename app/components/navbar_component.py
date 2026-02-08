import logging

import reflex as rx

import appkit_mantine as mn
from appkit_assistant.state.thread_list_state import ThreadListState
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


def admin_sidebar_item(
    label: str, icon: str, url: str, svg: str | None = None
) -> rx.Component:
    active = (rx.State.router.page.path == url.lower()) | (
        (rx.State.router.page.path == "/") & label == "Overview"
    )

    return rx.link(
        mn.box(
            mn.group(
                rx.cond(
                    svg,
                    rx.image(svg, height="16px", width="16px", fill="var(--gray-9)"),
                    rx.icon(
                        icon,
                        size=15,
                        color=rx.cond(
                            active,
                            accent_text_color,
                            text_color,
                        ),
                    ),
                ),
                mn.text(
                    label,
                    size="sm",
                ),
                style={
                    "background_color": rx.cond(
                        active,
                        accent_bg_color,
                        "transparent",
                    ),
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
                    "border_radius": border_radius,
                },
                align="center",
                width="100%",
                p="3px 9px",
            ),
            padding="3px 9px",
            ml="15px",
        ),
        on_click=[
            LoadingState.set_is_loading(True),
        ],
        underline="none",
        href=url,
        width="100%",
        margin="0",
        color=rx.cond(
            active,
            accent_text_color,
            text_color,
        ),
    )


def sidebar_item(label: str, icon: str, url: str) -> rx.Component:
    active = (rx.State.router.page.path == url.lower()) | (
        (rx.State.router.page.path == "/") & label == "Overview"
    )

    return rx.link(
        mn.group(
            rx.cond(
                icon == "", rx.spacer(), rx.icon(icon, size=17, margin_right="6px")
            ),
            mn.text(
                label,
                size="md",
                fw="regular",
                style={
                    "color": rx.cond(
                        active,
                        accent_text_color,
                        text_color,
                    ),
                },
            ),
            style={
                "background_color": rx.cond(
                    active,
                    accent_bg_color,
                    "transparent",
                ),
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
                "border_radius": border_radius,
            },
            align="center",
            w="100%",
            gap="3px",
            p="0.35em",
        ),
        on_click=[
            LoadingState.set_is_loading(True),
        ],
        underline="none",
        href=url,
        width="100%",
    )


def sidebar_sub_item(
    label: str,
    icon: str,  # noqa: ARG001
    url: str,
    svg: str | None = None,  # noqa: ARG001
) -> rx.Component:
    active = (rx.State.router.page.path == url.lower()) | (
        (rx.State.router.page.path == "/") & label == "Overview"
    )

    return rx.link(
        rx.box(
            mn.group(
                mn.text(
                    label,
                    size="sm",
                    fw="regular",
                ),
                style={
                    "color": rx.cond(
                        active,
                        accent_text_color,
                        text_color,
                    ),
                    "background_color": rx.cond(
                        active,
                        accent_bg_color,
                        "transparent",
                    ),
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
                width="90%",
                p="3px 9px",
                ml="6px",
            ),
            border_left=f"1px solid {rx.color('gray', 7)}",
            padding="3px",
        ),
        on_click=[
            LoadingState.set_is_loading(True),
        ],
        underline="none",
        href=url,
        width="100%",
        padding="0",
        margin="0 0 0 13px",
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
            mn.group(
                rx.icon(icon, size=17),
                style={
                    "color": rx.cond(
                        active,
                        accent_text_color,
                        text_color,
                    ),
                    "background_color": rx.cond(
                        active,
                        accent_bg_color,
                        "transparent",
                    ),
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
                    "border_radius": border_radius,
                },
                p="0.35em",
                br=border_radius,
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
            mn.group(
                rx.icon("log-out", size=18),
                style={
                    "color": text_color,
                    "_hover": {
                        "background_color": gray_bg_color,
                        "color": text_color,
                        "opacity": "1",
                    },
                    "opacity": "0.95",
                    "border_radius": border_radius,
                },
                p="0.35em",
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
    return mn.group(
        rx.color_mode_cond(
            rx.image("/img/logo.svg", height="56px", margin_top="1.25em"),
            rx.image("/img/logo_dark.svg", height="56px", margin_top="1.25em"),
        ),
        rx.spacer(),
        align="center",
        width="100%",
        p="0.35em",
        mb="1em",
    )


def navbar_default_footer(version: str) -> rx.Component:
    return mn.stack(
        mn.group(
            sidebar_icon_button(label="Profil", icon="user", url="/profile"),
            rx.color_mode.button(style={"opacity": "0.8", "scale": "0.95"}),
            rx.spacer(),
            logout_button(),
            wrap="nowrap",
            justify="center",
            align="center",
            w="100%",
        ),
        mn.text(
            f"Version {version}",
            size="xs",
            w="100%",
            ml="3px",
            c="gray",
            # color=rx.color("gray", 7),
        ),
        justify="start",
        align="start",
        width="100%",
        p="0.35em",
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
        rx.box(
            class_name=rx.cond(
                LoadingState.is_loading, "rainbow-gradient-bar", "default-bar"
            ),
        ),
        mn.stack(
            navbar_header,
            mn.stack(
                sidebar_item(
                    label="Assistent",
                    icon="bot-message-square",
                    url="/assistant",
                ),
                sidebar_item(
                    label="Bildgenerator",
                    icon="image",
                    url="/image-gallery",
                ),
                align="start",
                w="100%",
                gap="2px",
            ),
            mn.scroll_area.stateful(
                navbar_items,
                w="100%",
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
            mn.stack(
                requires_admin(
                    navbar_admin_items,
                ),
                align="start",
                w="100%",
                gap="0",
            ),
            navbar_footer,
            justify="end",
            align="end",
            w="18em",
            h="100dvh",
            p="1em",
            gap="6px",
        ),
        max_width=sidebar_width,
        width="100%",
        height="100vh",
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
