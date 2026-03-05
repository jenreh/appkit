import json
import logging
from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from fastmcp.server.apps import AppConfig
from fastmcp.server.auth.auth import AuthProvider
from pydantic import Field

from appkit_mcp_image.backend.generators import (
    GoogleImageGenerator,
    OpenAIImageGenerator,
)
from appkit_mcp_image.backend.image_service import edit_image_impl, generate_image_impl
from appkit_mcp_image.backend.models import (
    EditImageInput,
    GenerationInput,
    ImageGenerator,
    ImageResult,
)
from appkit_mcp_image.configuration import MCPImageGeneratorConfig
from appkit_mcp_image.resources.image_viewer import IMAGE_VIEWER_HTML, VIEW_URI

logger = logging.getLogger(__name__)

_generators: dict[str, ImageGenerator] = {}


def _success_result(
    image_url: str,
    prompt: str,
    *,
    enhanced_prompt: str | None = None,
    model: str | None = None,
    size: str | None = None,
) -> str:
    """Return a JSON success response for the MCP-App UI."""
    result = ImageResult(
        success=True,
        image_url=image_url,
        prompt=prompt,
        enhanced_prompt=enhanced_prompt,
        model=model,
        size=size,
    )
    return json.dumps(result.model_dump(), default=str)


def _error_result(message: str) -> str:
    """Return a JSON error response."""
    result = ImageResult(success=False, error=message)
    return json.dumps(result.model_dump(), default=str)


def init_generators(config: MCPImageGeneratorConfig) -> dict[str, ImageGenerator]:
    """Initialize generators from environment variables."""
    if _generators:
        return _generators  # Already initialized

    openai_key = (
        config.azure_api_key.get_secret_value() if config.azure_api_key else None
    )
    openai_base_url = (
        config.azure_base_url.get_secret_value() if config.azure_base_url else None
    )
    backend_server = config.backend_server

    if openai_key and openai_base_url:
        _generators["azure"] = OpenAIImageGenerator(
            api_key=openai_key,
            base_url=openai_base_url,
            model=config.azure_image_model,
            prompt_optimizer_model=config.azure_prompt_optimizer,
            backend_server=backend_server,
        )
        logger.info("Initialized Azure image generator")

    if config.google_api_key:
        _generators["google"] = GoogleImageGenerator(
            api_key=config.google_api_key.get_secret_value(),
            model=config.google_image_model,
            prompt_optimizer_model=config.google_prompt_optimizer,
            backend_server=backend_server,
        )
        logger.info("Initialized Google image generator")

    if not _generators:
        logger.warning("✗ No generators initialized - check environment variables")

    return _generators


def create_image_mcp_server(
    generator: ImageGenerator,
    auth: AuthProvider | None = None,
    *,
    name: str = "appkit-image-generator",
) -> FastMCP[Any]:
    mcp = FastMCP(
        name=name,
        instructions=(
            "This server allows the creation of new images and the editing "
            "of existing images. When the user uses this service, the user expects "
            "that the generated answer is shown directly to the user and not "
            "processed any further by additional reasoning steps."
        ),
        auth=auth,
    )

    @mcp.resource(
        VIEW_URI,
        app=AppConfig(prefers_border=False),
    )
    def image_view() -> str:
        """Image viewer that displays generated images with prompt info."""
        return IMAGE_VIEWER_HTML

    @mcp.tool(
        name="generate_image",
        tags={"image", "generation"},
        description=(
            "Create an image based on the prompt. "
            "The generated answer must be shown directly to the user."
        ),
        app=AppConfig(resource_uri=VIEW_URI),
    )
    async def generate_image(
        prompt: Annotated[
            str,
            Field(
                description="Text description of the desired image (max 32000 chars)"
            ),
        ],
        size: Annotated[
            Literal["1024x1024", "1536x1024", "1024x1536", "auto"],
            Field(
                description=(
                    "Image dimensions: 1024x1024 (square), "
                    "1536x1024 (landscape), 1024x1536 (portrait), or auto"
                )
            ),
        ] = "1024x1024",
        background: Annotated[
            Literal["transparent", "opaque", "auto"],
            Field(description="Background transparency setting"),
        ] = "auto",
        seed: Annotated[
            int,
            Field(description="Random seed for reproducibility (0 = random)"),
        ] = 0,
        enhance_prompt: Annotated[
            bool,
            Field(description="Auto-enhance prompt for better results"),
        ] = True,
        output_format: Annotated[
            Literal["png", "jpeg", "webp"],
            Field(description="Output image format"),
        ] = "jpeg",
    ) -> str:
        """Generate image from text prompt using gpt-image-1 or FLUX.1-Kontext-pro.

        Returns a JSON result rendered by the image viewer app.

        Supported models:
        - gpt-image-1: OpenAI's latest image generation model
        - FLUX.1-Kontext-pro: Black Forrest Labs model, preferred for
          photorealistic images
        """
        input_data = GenerationInput(
            prompt=prompt,
            size=size,
            output_format=output_format,
            background=background,
            seed=seed,
            enhance_prompt=enhance_prompt,
        )
        try:
            image_url, enhanced_prompt = await generate_image_impl(
                input_data, generator
            )
        except ValueError as exc:
            return _error_result(str(exc))

        return _success_result(
            image_url,
            prompt,
            enhanced_prompt=enhanced_prompt,
            model=generator.model,
            size=size,
        )

    @mcp.tool(
        name="edit_image",
        tags={"image", "editing"},
        description=(
            "Edit existing images based on the prompt and the list of image URLs. "
            "The generated answer must be shown directly to the user."
        ),
        app=AppConfig(resource_uri=VIEW_URI),
    )
    async def edit_image(
        prompt: Annotated[
            str,
            Field(
                description="Text description of the desired edits (max 32000 chars)"
            ),
        ],
        image_paths: Annotated[
            list[str],
            Field(
                description=(
                    "List of image URLs, file paths, or base64 data URLs "
                    "to edit. Supports up to 4 images. "
                    "Formats: PNG, JPEG, WEBP (each <20MB)."
                )
            ),
        ],
        size: Annotated[
            Literal["1024x1024", "1536x1024", "1024x1536", "auto"],
            Field(description="Output image dimensions"),
        ] = "auto",
        output_format: Annotated[
            Literal["png", "jpeg", "webp"],
            Field(description="Output image format"),
        ] = "jpeg",
    ) -> str:
        """Edit existing images with text prompts and optional masks.

        Returns a JSON result rendered by the image viewer app.

        Supports:
        - Multi-image editing (up to 16 images)
        - Inpainting with mask (transparent areas indicate edit zones)
        - Various output formats (PNG, JPEG, WEBP)

        Note: Only gpt-image-1 supports image editing.
        """
        input_data = EditImageInput(
            prompt=prompt,
            image_paths=image_paths,
            size=size,
            output_format=output_format,
        )
        try:
            image_url = await edit_image_impl(input_data, generator)
        except ValueError as exc:
            return _error_result(str(exc))

        return _success_result(
            image_url,
            prompt,
            model=generator.model,
            size=size,
        )

    return mcp
