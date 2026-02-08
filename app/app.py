"""Welcome to Reflex! This file outlines the steps to create a basic app."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import reflex as rx
from fastapi import FastAPI
from starlette.types import ASGIApp

from appkit_assistant.backend.services.file_cleanup_service import (
    start_scheduler,
    stop_scheduler,
)
from appkit_assistant.pages import mcp_oauth_callback_page  # noqa: F401
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
from app.pages.examples.auto_scroll_examples import auto_scroll_examples  # noqa: F401
from app.pages.examples.button_examples import button_examples  # noqa: F401
from app.pages.examples.combobox_examples import combobox_examples  # noqa: F401
from app.pages.examples.data_display_examples import (
    accordion_examples,  # noqa: F401
    avatar_examples,  # noqa: F401
    card_examples,  # noqa: F401
    image_examples,  # noqa: F401
    indicator_examples,  # noqa: F401
    timeline_examples,  # noqa: F401
)
from app.pages.examples.feedback_examples import (
    alert_examples,  # noqa: F401
    notification_examples,  # noqa: F401
    progress_examples,  # noqa: F401
    skeleton_examples,  # noqa: F401
)
from app.pages.examples.input_examples import input_examples_page  # noqa: F401
from app.pages.examples.markdown_preview_examples import (
    markdown_preview_examples,  # noqa: F401
)
from app.pages.examples.modal_examples import modal_examples  # noqa: F401
from app.pages.examples.nav_link_examples import nav_link_examples  # noqa: F401
from app.pages.examples.navigation_examples import (
    breadcrumbs_examples,  # noqa: F401
    pagination_examples,  # noqa: F401
    stepper_examples,  # noqa: F401
    tabs_examples,  # noqa: F401
)
from app.pages.examples.nprogress_examples import nprogress_examples_page  # noqa: F401
from app.pages.examples.number_formatter_examples import (
    number_formatter_examples,  # noqa: F401
)
from app.pages.examples.overlay_examples import (
    overlay_examples,  # noqa: F401
)
from app.pages.examples.scroll_area_examples import scroll_area_examples  # noqa: F401
from app.pages.examples.table_examples import table_examples  # noqa: F401
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
                rx.list.item(rx.link("Input Components", href="/inputs")),
                rx.list.item(rx.link("Password Input", href="/password")),
                rx.list.item(rx.link("Date Input", href="/date")),
                rx.list.item(rx.link("Select", href="/select")),
                rx.list.item(rx.link("Rich Select", href="/rich_select")),
                rx.list.item(rx.link("MultiSelect", href="/multi-select")),
                rx.list.item(rx.link("Autocomplete", href="/autocomplete")),
                rx.list.item(rx.link("Rich Text Editor (Tiptap)", href="/tiptap")),
            ),
            rx.text.strong("Buttons:", size="3"),
            rx.list.unordered(
                rx.list.item(rx.link("Action Icon (Group demo)", href="/action-icon")),
                rx.list.item(rx.link("Button", href="/button")),
            ),
            rx.text.strong("Data Display:", size="3"),
            rx.list.unordered(
                rx.list.item(rx.link("Accordion", href="/accordion")),
                rx.list.item(rx.link("Avatar", href="/avatar")),
                rx.list.item(rx.link("Card", href="/card")),
                rx.list.item(rx.link("Image", href="/image")),
                rx.list.item(rx.link("Indicator", href="/indicator")),
                rx.list.item(rx.link("Timeline", href="/timeline")),
            ),
            rx.text.strong("Feedback:", size="3"),
            rx.list.unordered(
                rx.list.item(rx.link("Alert", href="/alert")),
                rx.list.item(rx.link("Notification", href="/notification")),
                rx.list.item(rx.link("Progress", href="/progress")),
                rx.list.item(rx.link("Skeleton", href="/skeleton")),
            ),
            rx.text.strong("Navigation:", size="3"),
            rx.list.unordered(
                rx.list.item(rx.link("Breadcrumbs", href="/breadcrumbs")),
                rx.list.item(rx.link("Pagination", href="/pagination")),
                rx.list.item(rx.link("Stepper", href="/stepper")),
                rx.list.item(rx.link("Tabs", href="/tabs")),
            ),
            rx.text.strong("Overlay:", size="3"),
            rx.list.unordered(
                rx.list.item(rx.link("HoverCard", href="/hover-card")),
                rx.list.item(rx.link("Tooltip", href="/tooltip")),
            ),
            rx.text.strong("Others:", size="3"),
            rx.list.unordered(
                rx.list.item(rx.link("Markdown Preview", href="/markdown-preview")),
                rx.list.item(rx.link("Modal", href="/modal")),
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


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:  # noqa: ARG001
    """Handle application lifespan events (startup and shutdown)."""
    # Startup
    start_scheduler()
    yield
    # Shutdown
    stop_scheduler()


# Create FastAPI app for custom API routes
api_app = FastAPI(title="AppKit API", lifespan=lifespan)
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
