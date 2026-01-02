import base64
import logging

import httpx
from openai import AsyncAzureOpenAI

from appkit_imagecreator.backend.models import (
    GeneratedImageData,
    GenerationInput,
    ImageGenerator,
    ImageGeneratorResponse,
    ImageResponseState,
)

logger = logging.getLogger(__name__)


class OpenAIImageGenerator(ImageGenerator):
    """Generator for the OpenAI DALL-E API."""

    def __init__(
        self,
        api_key: str,
        id: str = "gpt-image-1",  # noqa: A002
        label: str = "OpenAI GPT-Image-1",
        model: str = "gpt-image-1",
        base_url: str | None = None,
        supports_edit: bool = True,
    ) -> None:
        super().__init__(
            id=id,
            label=label,
            model=model,
            api_key=api_key,
            supports_edit=supports_edit,
        )

        self.client = AsyncAzureOpenAI(
            api_version="2025-04-01-preview",
            azure_endpoint=base_url,
            api_key=api_key,
        )

    async def _enhance_prompt(self, prompt: str) -> str:
        response = await self.client.chat.completions.create(
            model="gpt-4.1-mini",
            stream=False,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an image generation assistant specialized in "
                        "optimizing user prompts. Ensure content "
                        "compliance rules are followed. Do not ask followup "
                        "questions, just generate the optimized prompt."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Enhance this prompt for image generation or image editing: {prompt}",
                },
            ],
        )

        result = response.choices[0].message.content.strip()
        if not result:
            result = prompt

        logger.debug("Enhanced prompt for image generation: %s", result)
        return result

    async def _perform_generation(
        self, input_data: GenerationInput
    ) -> ImageGeneratorResponse:
        output_format = "jpeg"
        prompt = self._format_prompt(input_data.prompt, input_data.negative_prompt)
        original_prompt = prompt

        if input_data.enhance_prompt:
            prompt = await self._enhance_prompt(prompt)

        enhanced_prompt = prompt if input_data.enhance_prompt else original_prompt

        response = await self.client.images.generate(
            model=self.model,
            prompt=prompt,
            n=input_data.n,
            moderation="low",
            output_format=output_format,
            output_compression=95,
        )

        generated_images: list[GeneratedImageData] = []
        content_type = f"image/{output_format}"

        for img in response.data:
            if img.b64_json:
                # Prefer base64 data - decode and return bytes directly
                image_bytes = base64.b64decode(img.b64_json)
                generated_images.append(
                    self._create_generated_image_data(image_bytes, content_type)
                )
            elif img.url:
                # Fetch image from URL and return bytes
                try:
                    async with httpx.AsyncClient() as client:
                        resp = await client.get(img.url, timeout=60.0)
                        resp.raise_for_status()
                        img_data = self._create_generated_image_data(
                            resp.content, content_type
                        )
                        generated_images.append(img_data)
                except httpx.HTTPError as e:
                    logger.warning("Failed to fetch image from URL %s: %s", img.url, e)
            else:
                logger.warning("Image data from OpenAI is neither b64_json nor a URL.")

        if not generated_images:
            logger.error(
                "No images were successfully processed or retrieved from OpenAI."
            )
            return ImageGeneratorResponse(
                state=ImageResponseState.FAILED,
                generated_images=[],
                error="Es wurden keine Bilder generiert oder von der API abgerufen.",
                enhanced_prompt=enhanced_prompt,
            )

        return ImageGeneratorResponse(
            state=ImageResponseState.SUCCEEDED,
            generated_images=generated_images,
            enhanced_prompt=enhanced_prompt,
        )

    def _prepare_image_files(
        self, reference_images: list[tuple[bytes, str]]
    ) -> list[tuple[str, bytes, str]]:
        """Prepare image data with proper file format and MIME types.

        Args:
            reference_images: List of (image_bytes, content_type) tuples

        Returns:
            List of (filename, bytes, mime_type) tuples for OpenAI API
        """
        image_files = []
        for idx, (img_bytes, img_content_type) in enumerate(reference_images):
            # Determine file extension and normalize MIME type
            if img_content_type == "image/png":
                ext, mime_type = "png", "image/png"
            elif img_content_type in {"image/jpeg", "image/jpg"}:
                ext, mime_type = "jpg", "image/jpeg"
            elif img_content_type == "image/webp":
                ext, mime_type = "webp", "image/webp"
            else:
                # Default to jpeg if unknown
                ext, mime_type = "jpg", "image/jpeg"
                logger.warning(
                    "Unknown content type '%s' for reference image %d, using jpeg",
                    img_content_type,
                    idx,
                )

            filename = f"reference_{idx}.{ext}"
            image_files.append((filename, img_bytes, mime_type))

        return image_files

    async def _call_edit_api(
        self,
        prompt: str,
        image_files: list[tuple[str, bytes, str]],
        input_data: GenerationInput,
        output_format: str,
    ) -> list[GeneratedImageData]:
        """Call OpenAI edit API and process response."""
        response = await self.client.images.edit(
            model=self.model,
            image=image_files,
            prompt=prompt,
            n=input_data.n,
            output_format=output_format,
            output_compression=95,
            input_fidelity="high",
        )

        generated_images: list[GeneratedImageData] = []
        content_type = f"image/{output_format}"

        for img in response.data:
            if img.b64_json:
                image_bytes = base64.b64decode(img.b64_json)
                generated_images.append(
                    self._create_generated_image_data(image_bytes, content_type)
                )
            elif img.url:
                try:
                    async with httpx.AsyncClient() as client:
                        resp = await client.get(img.url, timeout=60.0)
                        resp.raise_for_status()
                        img_data = self._create_generated_image_data(
                            resp.content, content_type
                        )
                        generated_images.append(img_data)
                except httpx.HTTPError as e:
                    logger.warning(
                        "Failed to fetch edited image from URL %s: %s", img.url, e
                    )

        return generated_images

    async def _perform_edit(
        self,
        input_data: GenerationInput,
        reference_images: list[tuple[bytes, str]],
    ) -> ImageGeneratorResponse:
        """Edit images using OpenAI's images.edit API.

        For style_transfer mode: Uses minimal prompt to maintain original content.
        For edit mode: Uses full prompt to guide modifications.

        Args:
            input_data: Generation parameters including prompt and edit mode
            reference_images: List of (image_bytes, content_type) tuples (max 16)

        Returns:
            ImageGeneratorResponse with edited images
        """

        output_format = "jpeg"
        enhanced_prompt = input_data.prompt
        image_files = self._prepare_image_files(reference_images)

        logger.info(
            "Editing %d reference image(s)",
            len(image_files),
        )

        # Call OpenAI images.edit API
        generated_images = await self._call_edit_api(
            enhanced_prompt, image_files, input_data, output_format
        )

        if not generated_images:
            logger.error("No edited images were successfully processed.")
            return ImageGeneratorResponse(
                state=ImageResponseState.FAILED,
                generated_images=[],
                error="Es wurden keine bearbeiteten Bilder generiert.",
                enhanced_prompt=enhanced_prompt,
            )

        return ImageGeneratorResponse(
            state=ImageResponseState.SUCCEEDED,
            generated_images=generated_images,
            enhanced_prompt=enhanced_prompt,
        )
