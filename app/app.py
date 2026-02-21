"""Welcome to Reflex! This file outlines the steps to create a basic app."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import reflex as rx
from fastapi import FastAPI
from starlette.types import ASGIApp

import appkit_mantine as mn
from appkit_assistant.backend.ai_model_registry import ai_model_registry
from appkit_assistant.backend.services.file_cleanup_service import FileCleanupService
from appkit_assistant.pages import mcp_oauth_callback_page  # noqa: F401
from appkit_commons.middleware import ForceHTTPSMiddleware
from appkit_commons.scheduler import PGQueuerScheduler
from appkit_imagecreator.backend.generator_registry import generator_registry
from appkit_imagecreator.backend.image_api import router as image_api_router
from appkit_imagecreator.backend.services.image_cleanup_service import (
    ImageCleanupService,
)
from appkit_user.authentication.backend.services.session_cleanup_service import (
    SessionCleanupService,
)
from appkit_user.authentication.pages import (  # noqa: F401
    azure_oauth_callback_page,
    github_oauth_callback_page,
)
from appkit_user.authentication.templates import navbar_layout
from appkit_user.user_management.pages import (  # noqa: F401
    create_login_page,
    create_password_reset_confirm_page,
    create_password_reset_request_page,
    create_profile_page,
)

from app.components.navbar import app_navbar
from app.pages.assistant.admin_assistant import admin_assistant_page  # noqa: F401
from app.pages.assistant.assistant import assistant_page  # noqa: F401
from app.pages.examples.auto_scroll_examples import auto_scroll_examples  # noqa: F401
from app.pages.examples.button_examples import button_examples  # noqa: F401
from app.pages.examples.charts_examples import charts_examples  # noqa: F401
from app.pages.examples.combobox_examples import combobox_examples  # noqa: F401
from app.pages.examples.data_display_examples import (
    data_display_examples,  # noqa: F401
)
from app.pages.examples.date_examples import date_examples_page  # noqa: F401
from app.pages.examples.feedback_examples import feedback_examples  # noqa: F401
from app.pages.examples.input_examples import input_examples_page  # noqa: F401
from app.pages.examples.markdown_preview_examples import (
    markdown_preview_examples,  # noqa: F401
)
from app.pages.examples.modal_examples import modal_examples  # noqa: F401
from app.pages.examples.nav_link_examples import nav_link_examples  # noqa: F401
from app.pages.examples.navigation_examples import navigation_examples  # noqa: F401
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
from app.pages.image_generators import image_generators_page  # noqa: F401
from app.pages.users import users_page  # noqa: F401

create_login_page()
create_profile_page(
    app_navbar(),
    class_name="w-full gap-6 max-w-[800px]",
    padding="2rem",
)
create_password_reset_request_page()
create_password_reset_confirm_page()


@navbar_layout(
    route="/index",
    title="Home",
    description="A demo page for the appkit components",
    navbar=app_navbar(),
    with_header=False,
)
def index() -> rx.Component:
    return mn.container(
        mn.stack(
            mn.title("Welcome to appkit!", order=1, size="xl"),
            mn.text(
                "A component library for ",
                rx.link("Reflex.dev", href="https://reflex.dev/", is_external=True),
                " based on ",
                rx.link("Mantine UI", href="https://mantine.dev/", is_external=True),
                mb="lg",
            ),
            mn.simple_grid(
                # Left column
                mn.stack(
                    mn.text("AI Tools:", fw="bold", size="md"),
                    mn.list_(
                        mn.list_.item(rx.link("Assistant", href="/assistant")),
                        mn.list_.item(
                            rx.link("Image Generator", href="/image-gallery")
                        ),
                        list_style_type="disc",
                        type="unordered",
                    ),
                    mn.text("Inputs:", fw="bold", size="md"),
                    mn.list_(
                        mn.list_.item(rx.link("Buttons & Icons", href="/buttons")),
                        mn.list_.item(rx.link("Input Components", href="/inputs")),
                        mn.list_.item(rx.link("Comboboxes", href="/comboboxes")),
                        mn.list_.item(
                            rx.link("Rich Text Editor (Tiptap)", href="/tiptap")
                        ),
                        list_style_type="disc",
                        type="unordered",
                    ),
                    mn.text("Data Display:", fw="bold", size="md"),
                    mn.list_(
                        mn.list_.item(rx.link("Data Display", href="/data-display")),
                        type="unordered",
                        list_style_type="disc",
                    ),
                ),
                # Right column
                mn.stack(
                    mn.text("Navigation:", fw="bold", size="md"),
                    mn.list_(
                        mn.list_.item(rx.link("Navigation", href="/navigation")),
                        mn.list_.item(
                            rx.link("Navigation Progress", href="/nprogress")
                        ),
                        mn.list_.item(rx.link("Nav Link", href="/nav-link")),
                        type="unordered",
                        list_style_type="disc",
                    ),
                    mn.text("Overlay:", fw="bold", size="md"),
                    mn.list_(
                        mn.list_.item(rx.link("HoverCard", href="/hover-card")),
                        mn.list_.item(rx.link("Tooltip", href="/tooltip")),
                        type="unordered",
                        list_style_type="disc",
                    ),
                    mn.text("Others:", fw="bold", size="md"),
                    mn.list_(
                        mn.list_.item(rx.link("Feedback Components", href="/feedback")),
                        mn.list_.item(
                            rx.link("Markdown Preview", href="/markdown-preview")
                        ),
                        mn.list_.item(rx.link("Modal", href="/modal")),
                        mn.list_.item(
                            rx.link("Navigation Progress", href="/nprogress")
                        ),
                        mn.list_.item(rx.link("Nav Link", href="/nav-link")),
                        mn.list_.item(
                            rx.link("Number Formatter", href="/number-formatter")
                        ),
                        mn.list_.item(rx.link("ScrollArea", href="/scroll-area")),
                        mn.list_.item(rx.link("Table", href="/table")),
                        type="unordered",
                        list_style_type="disc",
                    ),
                ),
                cols=2,
                spacing="md",
            ),
            spacing="md",
            mt="0",
            w="100%",
        ),
        size="lg",
        w="100%",
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
    await ai_model_registry.initialize()
    await generator_registry.initialize()

    scheduler = PGQueuerScheduler()
    scheduler.add_service(FileCleanupService())
    scheduler.add_service(SessionCleanupService(interval_minutes=30))
    scheduler.add_service(ImageCleanupService())
    await scheduler.start()

    yield

    await scheduler.shutdown()


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
app.register_lifespan_task(lifespan)
