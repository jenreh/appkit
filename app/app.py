"""Welcome to Reflex! This file outlines the steps to create a basic app."""

from collections.abc import AsyncGenerator
from contextlib import AsyncExitStack, asynccontextmanager

import reflex as rx
from fastapi import FastAPI
from starlette.types import ASGIApp

from appkit_assistant.backend.ai_model_registry import ai_model_registry
from appkit_assistant.backend.api.mcp_apps_api import (
    router as mcp_apps_router,
)
from appkit_assistant.backend.services.file_cleanup_service import FileCleanupService
from appkit_assistant.pages import mcp_oauth_callback_page  # noqa: F401
from appkit_commons.middleware import ForceHTTPSMiddleware
from appkit_commons.registry import service_registry
from appkit_commons.scheduler import PGQueuerScheduler
from appkit_imagecreator.backend.generator_registry import generator_registry
from appkit_imagecreator.backend.image_api import router as image_api_router
from appkit_imagecreator.backend.services.image_cleanup_service import (
    ImageCleanupService,
)
from appkit_mcp_bpmn.server import create_bpmn_mcp_server
from appkit_mcp_charts.server import create_charts_mcp_server
from appkit_mcp_image.auth import verifier
from appkit_mcp_image.configuration import MCPImageGeneratorConfig
from appkit_mcp_image.server import (
    create_image_mcp_server,
    init_generators,
)
from appkit_mcp_user.server import create_user_mcp_server
from appkit_user.authentication.backend.services import (
    SessionCleanupService,
)
from appkit_user.authentication.pages import (  # noqa: F401
    azure_oauth_callback_page,
    github_oauth_callback_page,
)
from appkit_user.user_management.pages import (
    create_login_page,
    create_password_reset_confirm_page,
    create_password_reset_request_page,
    create_profile_page,
)

from app.components.navbar import app_navbar

# Import pages to ensure they are registered
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
from app.pages.index import index  # noqa: F401
from app.pages.users import users_page  # noqa: F401

# Register Authentication & User Management Pages
create_login_page()
create_profile_page(
    app_navbar(),
    class_name="w-full gap-6 max-w-[800px]",
    padding="2rem",
)
create_password_reset_request_page()
create_password_reset_confirm_page()


base_stylesheets = [
    "https://fonts.googleapis.com/css2?family=Roboto+Flex:wght@400;500;600;700;800&display=swap",
    "https://fonts.googleapis.com/css2?family=Audiowide&family=Honk:SHLN@5&family=Major+Mono+Display&display=swap",
    "css/appkit.css",
    "css/react-zoom.css",
]

base_style = {
    "font_family": "Roboto Flex",
    rx.icon: {
        "stroke_width": "1.5px",
    },
}


def init_mcp_apps() -> dict[str, ASGIApp]:
    """Initialize MCP servers and return their ASGI apps."""
    # Standard MCP servers
    servers = {
        "/user": create_user_mcp_server(),
        "/charts": create_charts_mcp_server(),
        "/bpmn": create_bpmn_mcp_server(),
    }

    # Image MCP server specific setup
    image_mcp_config = service_registry().get(MCPImageGeneratorConfig)
    generators = init_generators(image_mcp_config)
    servers["/image"] = create_image_mcp_server(
        generators[image_mcp_config.generator],
        verifier,
    )

    # Convert to ASGI apps using streamable-http transport for SSE support
    return {
        path: server.http_app(path="/mcp", transport="streamable-http")
        for path, server in servers.items()
    }


# Initialize MCP apps
_mcp_apps = init_mcp_apps()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:  # noqa: ARG001
    """Handle application lifespan events (startup and shutdown)."""
    async with AsyncExitStack() as stack:
        # Register MCP server lifespans
        for mcp_app in _mcp_apps.values():
            await stack.enter_async_context(mcp_app.router.lifespan_context(mcp_app))

        # Initialize registries
        await ai_model_registry.initialize()
        await generator_registry.initialize()

        # Start job scheduler
        scheduler = PGQueuerScheduler()
        scheduler.add_service(FileCleanupService())
        scheduler.add_service(SessionCleanupService(interval_minutes=30))
        scheduler.add_service(ImageCleanupService())
        await scheduler.start()

        yield

        await scheduler.shutdown()


# Create FastAPI app for custom API routes
# NOTE: Do NOT add CORSMiddleware here. See App._add_cors() in Reflex.
api_app = FastAPI(title="AppKit API")
api_app.include_router(image_api_router)
api_app.include_router(mcp_apps_router)

# Mount MCP apps
for path, mcp_app in _mcp_apps.items():
    api_app.mount(path, mcp_app)


def add_https_middleware(asgi_app: ASGIApp) -> ASGIApp:
    """Wrap the ASGI app with HTTPS redirect middleware."""
    return ForceHTTPSMiddleware(asgi_app)


app = rx.App(
    stylesheets=base_stylesheets,
    style=base_style,
    api_transformer=[api_app, add_https_middleware],
)
app.register_lifespan_task(lifespan)
