from typing import Final

import reflex as rx

import appkit_mantine as mn
from appkit_assistant.roles import ASSISTANT_ADMIN_ROLE
from appkit_commons.configuration.configuration import Environment
from appkit_commons.public_path import public_path
from appkit_commons.registry import service_registry
from appkit_imagecreator.roles import IMAGE_GEN_ADMIN_ROLE
from appkit_user.authentication.components.components import requires_role

from app.components.navbar_component import (
    admin_sidebar_item,
    navbar,
    sidebar_sub_item,
)
from app.configuration import AppConfig

_config = service_registry().get(AppConfig)
VERSION: Final[str] = (
    f"{_config.version}-{_config.environment}"
    if _config.environment and _config.environment != Environment.production
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
        rx.color_mode_cond(
            rx.image(
                public_path("/img/appkit_logo.svg"),
                class_name="h-[60px]",
                margin="1em 0 1em -9px",
            ),
            rx.image(
                public_path("/img/appkit_logo_dark.svg"),
                class_name="h-[60px]",
                margin="1em 0 1em -9px",
            ),
        ),
        align="start",
        justify="start",
        w="95%",
    )


def navbar_admin_items() -> rx.Component:
    return mn.stack(
        mn.group(
            rx.icon("settings", size=17, margin_right="6px"),
            mn.text("Administration", size="md", fw="regular"),
            align="center",
            w="100%",
            gap="3px",
            p="0.35em",
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
        requires_role(
            admin_sidebar_item(
                label="Bildgenerator",
                icon="image",
                url="/admin/image-generators",
            ),
            role=IMAGE_GEN_ADMIN_ROLE.name,
        ),
        w="95%",
        gap="0px",
    )


def navbar_items() -> rx.Component:
    return mn.stack(
        sub_heading("Components"),
        mn.stack(
            sidebar_sub_item(label="Buttons & Icons", url="/examples/buttons"),
            sidebar_sub_item(label="Comboboxes", url="/examples/comboboxes"),
            sidebar_sub_item(label="Date & Time", url="/examples/date"),
            sidebar_sub_item(label="Extension Components", url="/examples/extensions"),
            sidebar_sub_item(label="Schedule", url="/examples/schedule"),
            sidebar_sub_item(
                label="Resources Schedule", url="/examples/resources-schedule"
            ),
            sidebar_sub_item(label="Maps", url="/examples/maps"),
            sidebar_sub_item(label="Inputs", url="/examples/inputs"),
            sidebar_sub_item(label="Advanced Inputs", url="/examples/inputs-advanced"),
            sidebar_sub_item(label="Menu", url="/examples/menu"),
            sidebar_sub_item(label="Rich Text Editor (Tiptap)", url="/examples/tiptap"),
            gap="0",
            w="100%",
        ),
        sub_heading("Navigation"),
        mn.stack(
            sidebar_sub_item(label="Navigation", url="/examples/navigation"),
            sidebar_sub_item(label="Navigation Progress", url="/examples/nprogress"),
            sidebar_sub_item(label="Nav Link", url="/examples/nav-link"),
            gap="0",
            w="100%",
        ),
        sub_heading("Page Templates"),
        mn.stack(
            sidebar_sub_item(label="Header + Navbar", url="/examples/template-header"),
            sidebar_sub_item(label="Navbar + Aside", url="/examples/template-aside"),
            gap="0",
            w="100%",
        ),
        sub_heading("Others"),
        mn.stack(
            sidebar_sub_item(label="Alert Dialog", url="/examples/alert-dialog"),
            sidebar_sub_item(label="Charts", url="/examples/charts"),
            sidebar_sub_item(label="Data Display", url="/examples/data-display"),
            sidebar_sub_item(label="Data List", url="/examples/data-list"),
            sidebar_sub_item(label="Empty State", url="/examples/empty-state"),
            sidebar_sub_item(label="Feedback", url="/examples/feedback"),
            sidebar_sub_item(label="Layout", url="/examples/layout"),
            sidebar_sub_item(label="Splitter", url="/examples/splitter"),
            sidebar_sub_item(
                label="Markdown Preview", url="/examples/markdown-preview"
            ),
            sidebar_sub_item(label="Modal", url="/examples/modal"),
            sidebar_sub_item(
                label="Number Formatter", url="/examples/number-formatter"
            ),
            sidebar_sub_item(label="Overlay", url="/examples/overlay"),
            sidebar_sub_item(label="ScrollArea", url="/examples/scroll-area"),
            sidebar_sub_item(label="Auto Scroll", url="/examples/auto-scroll"),
            sidebar_sub_item(label="Table", url="/examples/table"),
            sidebar_sub_item(label="Theme", url="/examples/theme"),
            sidebar_sub_item(label="Typography", url="/examples/typography"),
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
