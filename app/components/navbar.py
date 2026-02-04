from typing import Final

import reflex as rx

from appkit_assistant.roles import ASSISTANT_ADMIN_ROLE
from appkit_commons.registry import service_registry
from appkit_user.authentication.components.components import requires_role

from app.components.navbar_component import (
    admin_sidebar_item,
    border_radius,
    navbar,
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
        rx.list.unordered(
            rx.list.item(rx.link("Inputs", href="/inputs")),
            rx.list.item(rx.link("TextInput", href="/text-input")),
            rx.list.item(rx.link("Password Input", href="/password")),
            rx.list.item(rx.link("Date Input", href="/date")),
            rx.list.item(rx.link("Number Input", href="/number")),
            rx.list.item(rx.link("Textarea", href="/textarea")),
            rx.list.item(rx.link("Json Input", href="/json-input")),
            rx.list.item(rx.link("Select", href="/select")),
            rx.list.item(rx.link("Rich Select", href="/rich_select")),
            rx.list.item(rx.link("MultiSelect", href="/multi-select")),
            rx.list.item(rx.link("TagsInput", href="/tags-input")),
            rx.list.item(rx.link("Autocomplete", href="/autocomplete")),
            rx.list.item(rx.link("Rich Text Editor (Tiptap)", href="/tiptap")),
        ),
        rx.text("Buttons", size="2", weight="bold", style=sub_heading_styles),
        rx.list.unordered(
            rx.list.item(rx.link("Action Icon (Group demo)", href="/action-icon")),
            rx.list.item(rx.link("Button", href="/button")),
        ),
        rx.text("Others", size="2", weight="bold", style=sub_heading_styles),
        rx.list.unordered(
            rx.list.item(rx.link("Markdown Preview", href="/markdown-preview")),
            rx.list.item(rx.link("Modal", href="/modal")),
            rx.list.item(rx.link("Navigation Progress", href="/nprogress")),
            rx.list.item(rx.link("Nav Link", href="/nav-link")),
            rx.list.item(rx.link("Number Formatter", href="/number-formatter")),
            rx.list.item(rx.link("ScrollArea", href="/scroll-area")),
            rx.list.item(rx.link("Auto Scroll", href="/auto-scroll")),
            rx.list.item(rx.link("Table", href="/table")),
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
