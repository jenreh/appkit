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
        rx.text("Inputs", size="2", weight="bold", style=sub_heading_styles),
        rx.vstack(
            sidebar_sub_item(label="Inputs", icon="", url="/inputs"),
            sidebar_sub_item(label="TextInput", icon="", url="/text-input"),
            sidebar_sub_item(label="Password Input", icon="", url="/password"),
            sidebar_sub_item(label="Date Input", icon="", url="/date"),
            sidebar_sub_item(label="Number Input", icon="", url="/number"),
            sidebar_sub_item(label="Textarea", icon="", url="/textarea"),
            sidebar_sub_item(label="Json Input", icon="", url="/json-input"),
            sidebar_sub_item(label="Select", icon="", url="/select"),
            sidebar_sub_item(label="Rich Select", icon="", url="/rich_select"),
            sidebar_sub_item(label="MultiSelect", icon="", url="/multi-select"),
            sidebar_sub_item(label="TagsInput", icon="", url="/tags-input"),
            sidebar_sub_item(label="Autocomplete", icon="", url="/autocomplete"),
            sidebar_sub_item(label="Rich Text Editor (Tiptap)", icon="", url="/tiptap"),
            spacing="0",
            width="100%",
        ),
        rx.text("Buttons", size="2", weight="bold", style=sub_heading_styles),
        rx.vstack(
            sidebar_sub_item(
                label="Action Icon (Group demo)", icon="", url="/action-icon"
            ),
            sidebar_sub_item(label="Button", icon="", url="/button"),
            spacing="0",
            width="100%",
        ),
        rx.text("Others", size="2", weight="bold", style=sub_heading_styles),
        rx.vstack(
            sidebar_sub_item(
                label="Markdown Preview", icon="", url="/markdown-preview"
            ),
            sidebar_sub_item(label="Modal", icon="", url="/modal"),
            sidebar_sub_item(label="Navigation Progress", icon="", url="/nprogress"),
            sidebar_sub_item(label="Nav Link", icon="", url="/nav-link"),
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
