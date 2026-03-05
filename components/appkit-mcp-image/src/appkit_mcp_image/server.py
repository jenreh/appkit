import logging
from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from fastmcp.server.auth.auth import AuthProvider
from fastmcp.utilities.types import Image
from pydantic import Field

from appkit_commons.registry import service_registry
from appkit_mcp_image.backend.generators import (
    GoogleImageGenerator,
    OpenAIImageGenerator,
)
from appkit_mcp_image.backend.image_service import edit_image_impl, generate_image_impl
from appkit_mcp_image.backend.models import (
    EditImageInput,
    GenerationInput,
    ImageGenerator,
)
from appkit_mcp_image.backend.utils import url_to_bytes
from appkit_mcp_image.configuration import MCPImageGeneratorConfig

logger = logging.getLogger(__name__)

_generators: dict[str, ImageGenerator] = {}
config: MCPImageGeneratorConfig = service_registry().get(MCPImageGeneratorConfig)


async def _generate_response(
    image_url: str,
    prompt: str,
    response_format: Literal["image", "markdown", "url"] = "url",
    output_format: Literal["png", "jpeg", "webp"] = "jpeg",
) -> str | Image:
    """Generate response based on requested format.

    Args:
        image_url: URL of the generated/edited image
        response_format: "image", "markdown", or "url"
        prompt: Original prompt (used for markdown)
        output_format: Image format (png, jpeg, webp)

    Returns:
        MCP Image object, markdown string, or URL string

    Raises:
        ValueError: If image URL conversion fails
    """
    if response_format == "image":
        try:
            image_bytes = await url_to_bytes(image_url)
            return Image(data=image_bytes, format=output_format)
        except Exception as e:
            logger.error("Failed to create Image object from URL: %s", str(e))
            raise ValueError(f"Failed to convert image URL to MCP Image: {e}") from e

    if response_format == "url":
        return image_url

    if response_format == "markdown":
        return f"![Generated Image]({image_url})\n\n**Prompt:** {prompt}"

    raise ValueError(f"Unknown response format: {response_format}")


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

    @mcp.tool(
        name="generate_image",
        tags={"image", "generation"},
        description=(
            "Create an image based on the prompt. "
            "The generated answer must be shown directly to the user."
        ),
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
        response_format: Annotated[
            Literal["image", "markdown", "adaptive_card"],
            Field(
                description=(
                    "Output format: 'image' for MCP Image objects, "
                    "'markdown' for markdown string with image link, "
                    "'adaptive_card' for Microsoft Adaptive Card JSON"
                )
            ),
        ] = config.default_response_format,
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
    ) -> str | Image:
        """Generate image from text prompt using gpt-image-1 or FLUX.1-Kontext-pro.

        Returns the URL of the generated image.

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
            response_format=response_format,
            seed=seed,
            enhance_prompt=enhance_prompt,
        )
        image_url, enhanced_prompt = await generate_image_impl(input_data, generator)

        return await _generate_response(
            image_url, enhanced_prompt, response_format, output_format
        )

    @mcp.tool(
        name="edit_image",
        tags={"image", "editing"},
        description=(
            "Edit existing images based on the prompt and the list of image URLs. "
            "The generated answer must be shown directly to the user."
        ),
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
        response_format: Annotated[
            Literal["image", "markdown", "adaptive_card"],
            Field(
                description=(
                    "Output format: 'image' for MCP Image objects, "
                    "'markdown' for markdown string with image link, "
                    "'adaptive_card' for Microsoft Adaptive Card JSON"
                )
            ),
        ] = config.default_response_format,
    ) -> str | Image:
        """Edit existing images with text prompts and optional masks.

        Returns the URL of the edited image.

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
        image_url = await edit_image_impl(input_data, generator)

        return await _generate_response(
            image_url, prompt, response_format, output_format
        )

    return mcp
