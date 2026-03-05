"""Image editing tool for FastMCP server.

Handles image editing and inpainting using OpenAI's gpt-image-1 model.
"""

import logging

from appkit_mcp_image.backend.models import (
    EditImageInput,
    GenerationInput,
    ImageGenerator,
    ImageResponseState,
)

logger = logging.getLogger(__name__)


async def edit_image_impl(
    input_data: EditImageInput,
    generator: ImageGenerator,
) -> str:
    """Edit existing images with text prompts and optional masks.

    Supports multi-image editing and inpainting with masks.

    Args:
        input_data: Edit image input model with prompt, image_paths, and parameters
        generator: OpenAI image generator instance

    Returns:
        URL of the edited image

    Raises:
        ValueError: If model doesn't support editing or generation fails
    """
    logger.debug(
        "Editing images - images: %d, mask: %s",
        len(input_data.image_paths),
        input_data.mask_path is not None,
    )

    response = await generator.edit(input_data)

    if response.state == ImageResponseState.FAILED:
        logger.error("Image editing failed: %s", response.error)
        raise ValueError(f"Image editing failed: {response.error}")

    # Return the first edited image URL
    image_url = response.images[0]
    logger.debug("Successfully edited image ")
    return image_url


async def generate_image_impl(
    input_data: GenerationInput,
    generator: ImageGenerator,
) -> tuple[str, str | None]:
    """Generate images from text prompts using specified model.

    Returns URL of the generated image.

    Args:
        input_data: Generation input model with prompt and parameters
        generator: OpenAI image generator instance

    Returns:
        Tuple of (image URL, enhanced prompt)

    Raises:
        ValueError: If generation fails
    """
    logger.debug(
        "Generating image - size: %s",
        input_data.size,
    )

    response = await generator.generate(input_data)
    enhanced_prompt = response.enhanced_prompt

    if response.state == ImageResponseState.FAILED:
        logger.error("Image generation failed: %s", response.error)
        raise ValueError(f"Image generation failed: {response.error}")

    # Return the first generated image URL and enhanced prompt
    image_url = response.images[0]
    logger.debug("Successfully generated image")
    return image_url, enhanced_prompt
