from typing import Final

import reflex as rx

from appkit_assistant.roles import ASSISTANT_ADMIN_ROLE
from appkit_commons.registry import service_registry
from appkit_user.authentication.components.components import requires_role

from app.components.navbar_component import (
    admin_sidebar_item,
    border_radius,
    navbar,
    sidebar_sub_item,
    sub_heading_styles,
)
from app.configuration import AppConfig

_config = service_registry().get(AppConfig)
VERSION: Final[str] = (
    f"{_config.version}-{_config.environment}"
    if _config.environment
    else _config.version
)


def navbar_header() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.image(
                "/img/logo.svg",
                class_name="h-[54px]",
                margin_top="1.2em",
                margin_left="0px",
            ),
            rx.heading("AppKit", size="8", margin_top="36px", margin_left="6px"),
            rx.spacer(),
            align="center",
            justify="start",
            width="100%",
            padding="0.35em",
            margin_bottom="0",
            margin_top="-0.5em",
        ),
    )


def navbar_admin_items() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.icon("settings", size=18),
            rx.text("Administration"),
            align="center",
            border_radius=border_radius,
            width="100%",
            spacing="2",
            padding="0.35em",
        ),
        admin_sidebar_item(
            label="Benutzer",
            icon="users",
            url="/admin/users",
        ),
        requires_role(
            admin_sidebar_item(
                label="Assistant",
                icon="bot",
                url="/admin/assistant",
            ),
            role=ASSISTANT_ADMIN_ROLE.name,
        ),
        width="95%",
        spacing="1",
    )


def navbar_items() -> rx.Component:
    return rx.vstack(
        rx.text("Inputs & Buttons", size="2", weight="bold", style=sub_heading_styles),
        rx.vstack(
            sidebar_sub_item(label="Buttons & Icons", icon="", url="/buttons"),
            sidebar_sub_item(label="Inputs", icon="", url="/inputs"),
            sidebar_sub_item(label="Comboboxes", icon="", url="/comboboxes"),
            sidebar_sub_item(label="Rich Text Editor (Tiptap)", icon="", url="/tiptap"),
            spacing="0",
            width="100%",
        ),
        rx.text("Data Display", size="2", weight="bold", style=sub_heading_styles),
        rx.vstack(
            sidebar_sub_item(label="Accordion", icon="", url="/accordion"),
            sidebar_sub_item(label="Avatar", icon="", url="/avatar"),
            sidebar_sub_item(label="Card", icon="", url="/card"),
            sidebar_sub_item(label="Image", icon="", url="/image"),
            sidebar_sub_item(label="Indicator", icon="", url="/indicator"),
            sidebar_sub_item(label="Timeline", icon="", url="/timeline"),
            spacing="0",
            width="100%",
        ),
        rx.text("Feedback", size="2", weight="bold", style=sub_heading_styles),
        rx.vstack(
            sidebar_sub_item(label="Alert", icon="", url="/alert"),
            sidebar_sub_item(label="Notification", icon="", url="/notification"),
            sidebar_sub_item(label="Progress", icon="", url="/progress"),
            sidebar_sub_item(label="Skeleton", icon="", url="/skeleton"),
            spacing="0",
            width="100%",
        ),
        rx.text("Navigation", size="2", weight="bold", style=sub_heading_styles),
        rx.vstack(
            sidebar_sub_item(label="Breadcrumbs", icon="", url="/breadcrumbs"),
            sidebar_sub_item(label="Pagination", icon="", url="/pagination"),
            sidebar_sub_item(label="Stepper", icon="", url="/stepper"),
            sidebar_sub_item(label="Tabs", icon="", url="/tabs"),
            sidebar_sub_item(label="Navigation Progress", icon="", url="/nprogress"),
            sidebar_sub_item(label="Nav Link", icon="", url="/nav-link"),
            spacing="0",
            width="100%",
        ),
        rx.text("Others", size="2", weight="bold", style=sub_heading_styles),
        rx.vstack(
            sidebar_sub_item(label="Overlay", icon="", url="/overlay"),
            sidebar_sub_item(
                label="Markdown Preview", icon="", url="/markdown-preview"
            ),
            sidebar_sub_item(label="Modal", icon="", url="/modal"),
            sidebar_sub_item(
                label="Number Formatter", icon="", url="/number-formatter"
            ),
            sidebar_sub_item(label="ScrollArea", icon="", url="/scroll-area"),
            sidebar_sub_item(label="Auto Scroll", icon="", url="/auto-scroll"),
            sidebar_sub_item(label="Table", icon="", url="/table"),
            spacing="0",
            width="100%",
        ),
        rx.spacer(min_height="1em"),
        spacing="1",
        width="95%",
    )


def app_navbar() -> rx.Component:
    return navbar(
        navbar_header=navbar_header(),
        navbar_items=navbar_items(),
        navbar_admin_items=navbar_admin_items(),
        version=VERSION,
    )
