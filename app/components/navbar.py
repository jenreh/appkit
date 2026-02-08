from typing import Final

import reflex as rx

import appkit_mantine as mn
from appkit_assistant.roles import ASSISTANT_ADMIN_ROLE
from appkit_commons.registry import service_registry
from appkit_user.authentication.components.components import requires_role

from app.components.navbar_component import (
    admin_sidebar_item,
    border_radius,
    navbar,
    sidebar_sub_item,
)
from app.configuration import AppConfig

_config = service_registry().get(AppConfig)
VERSION: Final[str] = (
    f"{_config.version}-{_config.environment}"
    if _config.environment
    else _config.version
)


def sub_heading(label: str) -> rx.Component:
    return mn.text(
        label,
        text_transform="uppercase",
        letter_spacing="1px",
        fw="bold",
        size="0.75rem",
        p="0.35rem 0.1rem !important",
        margin="3px 0 0 6px !important",
        c="dimmed",
    )


def navbar_header() -> rx.Component:
    return mn.stack(
        mn.group(
            rx.image(
                "/img/logo.svg",
                class_name="h-[54px]",
                margin_top="1.2em",
                margin_left="0px",
            ),
            mn.title("AppKit", order=1, mt="xl", ml="sm"),
            rx.spacer(),
            align="center",
            justify="start",
            w="100%",
            p="sm",
            mb="0",
            mt="-sm",
        ),
    )


def navbar_admin_items() -> rx.Component:
    return mn.stack(
        mn.group(
            rx.icon("settings", size=18),
            mn.text("Administration"),
            align="center",
            br=border_radius,
            w="100%",
            gap="sm",
            p="sm",
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
        w="95%",
        gap="2px",
    )


def navbar_items() -> rx.Component:
    return mn.stack(
        sub_heading("Components"),
        mn.stack(
            sidebar_sub_item(label="Buttons & Icons", icon="", url="/buttons"),
            sidebar_sub_item(label="Inputs", icon="", url="/inputs"),
            sidebar_sub_item(label="Comboboxes", icon="", url="/comboboxes"),
            sidebar_sub_item(label="Rich Text Editor (Tiptap)", icon="", url="/tiptap"),
            gap="0",
            w="100%",
        ),
        sub_heading("Data Display"),
        mn.stack(
            sidebar_sub_item(label="Accordion", icon="", url="/accordion"),
            sidebar_sub_item(label="Avatar", icon="", url="/avatar"),
            sidebar_sub_item(label="Card", icon="", url="/card"),
            sidebar_sub_item(label="Image", icon="", url="/image"),
            sidebar_sub_item(label="Indicator", icon="", url="/indicator"),
            sidebar_sub_item(label="Timeline", icon="", url="/timeline"),
            gap="0",
            w="100%",
        ),
        sub_heading("Navigation"),
        mn.stack(
            sidebar_sub_item(label="Breadcrumbs", icon="", url="/breadcrumbs"),
            sidebar_sub_item(label="Pagination", icon="", url="/pagination"),
            sidebar_sub_item(label="Stepper", icon="", url="/stepper"),
            sidebar_sub_item(label="Tabs", icon="", url="/tabs"),
            sidebar_sub_item(label="Navigation Progress", icon="", url="/nprogress"),
            sidebar_sub_item(label="Nav Link", icon="", url="/nav-link"),
            gap="0",
            w="100%",
        ),
        sub_heading("Others"),
        mn.stack(
            sidebar_sub_item(label="Feedback", icon="", url="/feedback"),
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
            gap="0",
            w="100%",
        ),
        rx.spacer(min_height="1em"),
        gap="sm",
        w="95%",
    )


def app_navbar() -> rx.Component:
    return navbar(
        navbar_header=navbar_header(),
        navbar_items=navbar_items(),
        navbar_admin_items=navbar_admin_items(),
        version=VERSION,
    )
