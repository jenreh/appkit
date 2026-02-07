import base64
import logging

import httpx
from openai import AsyncAzureOpenAI

from appkit_imagecreator.backend.models import (
    GeneratedImageData,
    GenerationInput,
    ImageGenerator,
    ImageGeneratorResponse,
    ImageModel,
    ImageResponseState,
)

logger = logging.getLogger(__name__)

GPT_IMAGE_1_5 = ImageModel(
    id="gpt-image-1.5",
    model="gpt-image-1.5",
    label="OpenAI GPT-Image-1.5 (Azure)",
    config={
        "moderation": "low",
        # "input_fidelity": "high",
        "output_compression": 95,
        "output_format": "jpeg",
        "quality": "high",
        "background": "auto",
    },
)

GPT_IMAGE_1_MINI = ImageModel(
    id="gpt-image-1-mini",
    model="gpt-image-1-mini",
    label="OpenAI GPT-Image-1 mini (Azure)",
    config={
        "moderation": "low",
        # "input_fidelity": "high",
        "output_compression": 90,
        "output_format": "jpeg",
        "quality": "high",
        "background": "auto",
    },
)


class OpenAIImageGenerator(ImageGenerator):
    """Generator for the OpenAI DALL-E API."""

    base_url: str | None

    def __init__(
        self,
        model: ImageModel,
        api_key: str,
        base_url: str | None = None,
        supports_edit: bool = True,
    ) -> None:
        super().__init__(
            model=model,
            api_key=api_key,
            supports_edit=supports_edit,
        )
        self.base_url = base_url

        self.client = AsyncAzureOpenAI(
            api_version="2025-04-01-preview",
            azure_endpoint=base_url,
            api_key=api_key,
        )

    def _build_api_params(self, **overrides: any) -> dict:
        """Build API parameters from model config with overrides.

        Args:
            **overrides: Parameters that override model config defaults

        Returns:
            Dict of API parameters to use
        """
        params = {}
        if self.model.config:
            params.update(self.model.config)
        params.update(overrides)
        return params

    def _get_content_type(self, params: dict) -> str:
        """Get content type from output_format parameter.

        Args:
            params: API parameters dict containing output_format

        Returns:
            MIME type string
        """
        output_format = params.get("output_format", "jpeg")
        return f"image/{output_format}"

    async def _process_response_images(
        self, response_data: list, content_type: str
    ) -> list[GeneratedImageData]:
        """Process API response data (base64 or URL) into GeneratedImageData objects."""
        generated_images: list[GeneratedImageData] = []

        for img in response_data:
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
                        generated_images.append(
                            self._create_generated_image_data(
                                resp.content, content_type
                            )
                        )
                except httpx.HTTPError as e:
                    logger.warning("Failed to fetch image from URL %s: %s", img.url, e)
            else:
                logger.warning("Image data from OpenAI is neither b64_json nor a URL.")

        return generated_images

    async def _enhance_prompt(self, prompt: str) -> str:
        try:
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
                        "content": (
                            "Enhance this prompt for image generation or "
                            f"image editing: {prompt}"
                        ),
                    },
                ],
            )

            result = response.choices[0].message.content.strip()
            if not result:
                result = prompt

            logger.debug("Enhanced prompt for image generation: %s", result)
            return result
        except Exception as e:
            logger.error("Failed to enhance prompt: %s", e)
            return prompt

    async def _perform_generation(
        self, input_data: GenerationInput
    ) -> ImageGeneratorResponse:
        prompt = self._format_prompt(input_data.prompt, input_data.negative_prompt)
        original_prompt = prompt

        if input_data.enhance_prompt:
            prompt = await self._enhance_prompt(prompt)

        enhanced_prompt = prompt if input_data.enhance_prompt else original_prompt

        api_params = self._build_api_params(
            model=self.model.model,
            prompt=prompt,
            n=input_data.n,
        )
        response = await self.client.images.generate(**api_params)
        content_type = self._get_content_type(api_params)
        generated_images = await self._process_response_images(
            response.data, content_type
        )

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
        type_map = {
            "image/png": ("png", "image/png"),
            "image/jpeg": ("jpg", "image/jpeg"),
            "image/jpg": ("jpg", "image/jpeg"),
            "image/webp": ("webp", "image/webp"),
        }

        image_files = []
        for idx, (img_bytes, content_type) in enumerate(reference_images):
            ext, mime_type = type_map.get(content_type, ("jpg", "image/jpeg"))

            if content_type not in type_map:
                logger.warning(
                    "Unknown content type '%s' for reference image %d, using jpeg",
                    content_type,
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
    ) -> list[GeneratedImageData]:
        """Call OpenAI edit API and process response."""
        api_params = self._build_api_params(
            model=self.model.model,
            image=image_files,
            prompt=prompt,
            n=input_data.n,
        )
        response = await self.client.images.edit(**api_params)
        content_type = self._get_content_type(api_params)

        return await self._process_response_images(response.data, content_type)

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
        enhanced_prompt = input_data.prompt
        image_files = self._prepare_image_files(reference_images)

        logger.debug(
            "Editing %d reference image(s)",
            len(image_files),
        )

        # Call OpenAI images.edit API
        generated_images = await self._call_edit_api(
            enhanced_prompt, image_files, input_data
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
