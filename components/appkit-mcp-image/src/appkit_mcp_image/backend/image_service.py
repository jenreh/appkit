"""Image service — adapts MCP tool calls to appkit-imagecreator generators.

Converts MCP-specific input models to imagecreator GenerationInput,
invokes the imagecreator generator, persists results to the database,
and returns image URLs via the existing image API.
"""

import logging

from appkit_commons.database.session import get_asyncdb_session
from appkit_imagecreator.backend.models import (
    GeneratedImage,
    GeneratedImageData,
    ImageGenerator,
    ImageGeneratorResponse,
    ImageResponseState,
    get_image_api_base_url,
)
from appkit_imagecreator.backend.models import (
    GenerationInput as ICGenerationInput,
)
from appkit_imagecreator.backend.repository import image_repo
from appkit_mcp_image.backend.image_loaders import ImageLoaderFactory
from appkit_mcp_image.backend.image_processor import ImageProcessor
from appkit_mcp_image.backend.models import EditImageInput, GenerationInput

logger = logging.getLogger(__name__)


def _parse_size(size: str) -> tuple[int, int]:
    """Parse a 'WxH' size string into (width, height)."""
    if size == "auto":
        return 1024, 1024
    parts = size.split("x")
    return int(parts[0]), int(parts[1])


def _to_ic_input(input_data: GenerationInput | EditImageInput) -> ICGenerationInput:
    """Convert an MCP input model to an imagecreator GenerationInput."""
    width, height = _parse_size(input_data.size)
    seed = input_data.seed if isinstance(input_data, GenerationInput) else 0
    enhance = (
        input_data.enhance_prompt if isinstance(input_data, GenerationInput) else True
    )
    return ICGenerationInput(
        prompt=input_data.prompt,
        width=width,
        height=height,
        seed=seed,
        enhance_prompt=enhance,
    )


async def _get_image_bytes(img_data: GeneratedImageData) -> bytes | None:
    """Extract raw bytes from a GeneratedImageData response."""
    if img_data.image_bytes:
        return img_data.image_bytes
    if img_data.external_url:
        try:
            loader = ImageLoaderFactory().create(img_data.external_url)
            return await loader.load(img_data.external_url)
        except Exception:
            logger.exception("Failed to download external image")
    return None


async def _save_image(
    user_id: int,
    image_bytes: bytes,
    response: ImageGeneratorResponse,
    ic_input: ICGenerationInput,
    content_type: str,
    model_name: str,
) -> str:
    """Persist a generated image to the database and return its API URL."""
    async with get_asyncdb_session() as session:
        new_image = GeneratedImage(
            user_id=user_id,
            prompt=ic_input.prompt,
            model=model_name,
            image_data=image_bytes,
            content_type=content_type,
            width=ic_input.width,
            height=ic_input.height,
            enhanced_prompt=response.enhanced_prompt or ic_input.prompt,
            config={"size": f"{ic_input.width}x{ic_input.height}"},
        )
        saved = await image_repo.create(session, new_image)
        saved_id = saved.id

    base_url = get_image_api_base_url()
    return f"{base_url}/api/images/{saved_id}"


async def generate_image_impl(
    input_data: GenerationInput,
    generator: ImageGenerator,
    user_id: int,
) -> tuple[str, str | None]:
    """Generate an image, persist it, and return (image_url, enhanced_prompt).

    Raises:
        ValueError: If generation fails or produces no images.
    """
    ic_input = _to_ic_input(input_data)

    response = await generator.generate(ic_input)

    if response.state != ImageResponseState.SUCCEEDED:
        raise ValueError(f"Image generation failed: {response.error}")

    if not response.generated_images:
        raise ValueError("No images generated")

    img_data = response.generated_images[0]
    image_bytes = await _get_image_bytes(img_data)
    if not image_bytes:
        raise ValueError("Could not retrieve image bytes from generator response")

    image_url = await _save_image(
        user_id=user_id,
        image_bytes=image_bytes,
        response=response,
        ic_input=ic_input,
        content_type=img_data.content_type,
        model_name=generator.model.model,
    )

    return image_url, response.enhanced_prompt or None


async def edit_image_impl(
    input_data: EditImageInput,
    generator: ImageGenerator,
    user_id: int,
) -> str:
    """Edit images, persist the result, and return the image URL.

    Raises:
        ValueError: If editing fails or produces no images.
    """
    ic_input = _to_ic_input(input_data)

    # Load reference images from URLs/paths/base64
    processor = ImageProcessor()
    reference_images = await processor.prepare_images_for_editing(
        input_data.image_paths, input_data.output_format
    )

    # Load mask if provided
    if input_data.mask_path:
        mask_bytes = await processor.load_image(input_data.mask_path)
        reference_images.append((mask_bytes, f"image/{input_data.output_format}"))

    response = await generator.edit(ic_input, reference_images)

    if response.state != ImageResponseState.SUCCEEDED:
        raise ValueError(f"Image editing failed: {response.error}")

    if not response.generated_images:
        raise ValueError("No images produced by editing")

    img_data = response.generated_images[0]
    image_bytes = await _get_image_bytes(img_data)
    if not image_bytes:
        raise ValueError("Could not retrieve image bytes from edit response")

    return await _save_image(
        user_id=user_id,
        image_bytes=image_bytes,
        response=response,
        ic_input=ic_input,
        content_type=img_data.content_type,
        model_name=generator.model.model,
    )
