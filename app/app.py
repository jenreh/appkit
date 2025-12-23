"""Welcome to Reflex! This file outlines the steps to create a basic app."""

import logging

import reflex as rx
from fastapi import FastAPI
from starlette.types import ASGIApp

from appkit_commons.middleware import ForceHTTPSMiddleware
from appkit_imagecreator.backend.image_api import router as image_api_router
from appkit_user.authentication.pages import (  # noqa: F401
    azure_oauth_callback_page,
    github_oauth_callback_page,
)
from appkit_user.authentication.templates import navbar_layout
from appkit_user.user_management.pages import (  # noqa: F401
    create_login_page,
    create_profile_page,
)

from app.components.navbar import app_navbar
from app.pages.assistant.admin_assistant import admin_assistant_page  # noqa: F401
from app.pages.assistant.assistant import assistant_page  # noqa: F401

# from app.pages.assitant.assistant import assistant_page  # noqa: F401
from app.pages.examples.action_icon_examples import action_icon_examples  # noqa: F401
from app.pages.examples.auto_scroll_examples import auto_scroll_examples  # noqa: F401
from app.pages.examples.autocomplete_examples import autocomplete_examples  # noqa: F401
from app.pages.examples.button_examples import button_examples  # noqa: F401
from app.pages.examples.date_input_examples import (
    date_input_examples_page,  # noqa: F401
)
from app.pages.examples.input_examples import form_inputs_showcase  # noqa: F401
from app.pages.examples.json_input_examples import json_input_examples  # noqa: F401
from app.pages.examples.markdown_preview_examples import (
    markdown_preview_examples,  # noqa: F401
)
from app.pages.examples.multi_select_examples import multi_select_examples  # noqa: F401
from app.pages.examples.nav_link_examples import nav_link_examples  # noqa: F401
from app.pages.examples.nprogress_examples import nprogress_examples_page  # noqa: F401
from app.pages.examples.number_formatter_examples import (
    number_formatter_examples,  # noqa: F401
)
from app.pages.examples.number_input_examples import (
    number_input_examples_page,  # noqa: F401
)
from app.pages.examples.password_input_examples import (
    password_input_examples_page,  # noqa: F401
)
from app.pages.examples.rich_select_examples import rich_select_example  # noqa: F401
from app.pages.examples.scroll_area_examples import scroll_area_examples  # noqa: F401
from app.pages.examples.select_examples import select_examples  # noqa: F401
from app.pages.examples.table_examples import table_examples  # noqa: F401
from app.pages.examples.tags_input_examples import tags_input_examples  # noqa: F401
from app.pages.examples.textarea_examples import textarea_examples_page  # noqa: F401
from app.pages.examples.tiptap_examples import tiptap_page  # noqa: F401
from app.pages.image_creator import image_gallery  # noqa: F401
from app.pages.users import users_page  # noqa: F401

logging.basicConfig(level=logging.DEBUG)
create_login_page(header="AppKit")
create_profile_page(app_navbar())


@navbar_layout(
    route="/index",
    title="Home",
    description="A demo page for the appkit components",
    navbar=app_navbar(),
    with_header=False,
)
def index() -> rx.Component:
    return rx.container(
        rx.vstack(
            rx.heading("Welcome to appkit!", size="9"),
            rx.text(
                "A component library for ",
                rx.link("Reflex.dev", href="https://reflex.dev/", is_external=True),
                " based on ",
                rx.link("Mantine UI", href="https://mantine.dev/", is_external=True),
                margin_bottom="24px",
            ),
            rx.text.strong("AI Tools:", size="3"),
            rx.list.unordered(
                rx.list.item(rx.link("Image Generator", href="/image-gallery")),
                rx.list.item(rx.link("Assistant", href="/assistant")),
            ),
            rx.text.strong("Inputs:", size="3"),
            rx.list.unordered(
                rx.list.item(rx.link("Text Inputs", href="/inputs")),
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
            rx.text.strong("Buttons:", size="3"),
            rx.list.unordered(
                rx.list.item(rx.link("Action Icon (Group demo)", href="/action-icon")),
                rx.list.item(rx.link("Button", href="/button")),
            ),
            rx.text.strong("Others:", size="3"),
            rx.list.unordered(
                rx.list.item(rx.link("Markdown Preview", href="/markdown-preview")),
                rx.list.item(rx.link("Navigation Progress", href="/nprogress")),
                rx.list.item(rx.link("Nav Link", href="/nav-link")),
                rx.list.item(rx.link("Number Formatter", href="/number-formatter")),
                rx.list.item(rx.link("ScrollArea", href="/scroll-area")),
                rx.list.item(rx.link("Table", href="/table")),
            ),
            spacing="2",
            justify="center",
            margin_top="0",
        ),
    )


base_stylesheets = [
    "https://fonts.googleapis.com/css2?family=Roboto+Flex:wght@400;500;600;700;800&display=swap",
    "https://fonts.googleapis.com/css2?family=Audiowide&family=Honk:SHLN@5&family=Major+Mono+Display&display=swap",
    "css/appkit.css",
    #    "css/styles.css",
    "css/react-zoom.css",
]

base_style = {
    "font_family": "Roboto Flex",
    rx.icon: {
        "stroke_width": "1.5px",
    },
}

# Create FastAPI app for custom API routes
api_app = FastAPI(title="AppKit API")
api_app.include_router(image_api_router)


# Middleware transformer for HTTPS redirect
def add_https_middleware(asgi_app: ASGIApp) -> ASGIApp:
    """Wrap the ASGI app with HTTPS redirect middleware."""
    return ForceHTTPSMiddleware(asgi_app)


app = rx.App(
    stylesheets=base_stylesheets,
    style=base_style,
    api_transformer=[api_app, add_https_middleware],
)
