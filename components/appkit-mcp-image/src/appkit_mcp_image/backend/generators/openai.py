import logging
from typing import Any, Final

from openai import AsyncAzureOpenAI

from appkit_mcp_image.backend.image_processor import ImageProcessor
from appkit_mcp_image.backend.models import (
    EditImageInput,
    GenerationInput,
    ImageGenerator,
    ImageGeneratorResponse,
    ImageResponseState,
)

logger = logging.getLogger(__name__)

# API Configuration
TMP_IMG_FILE: Final[str] = "gpt-image"
API_VERSION: Final[str] = "2025-04-01-preview"


class OpenAIPromptEnhancer:
    """Encapsulates prompt enhancement logic."""

    def __init__(self, client: AsyncAzureOpenAI, prompt_optimizer_model: str):
        self.client = client
        self.model = prompt_optimizer_model

    async def enhance(self, prompt: str) -> str:
        """Enhance prompt for better image generation results."""
        logger.debug("Starting prompt enhancement")
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
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
                            f"Enhance this prompt for image generation: {prompt}"
                        ),
                    },
                ],
            )
            if result := response.choices[0].message.content.strip():
                logger.info("Prompt enhanced successfully")
                return result

            logger.warning("Prompt enhancement returned empty, using original")
            return prompt
        except Exception:
            logger.exception("Prompt enhancement failed")
            return prompt


class OpenAIImageGenerator(ImageGenerator):
    """Generator for the OpenAI DALL-E API.

    Uses composition pattern with specialized helper classes for:
    - Image loading/processing (ImageProcessor)
    - Prompt enhancement (PromptEnhancer)
    """

    def __init__(
        self,
        api_key: str,
        id: str = "gpt-image-1",  # noqa: A002
        label: str = "OpenAI GPT-Image-1",
        model: str = "gpt-image-1",
        prompt_optimizer_model: str = "gpt-5-mini",
        backend_server: str | None = None,
        base_url: str | None = None,
    ) -> None:
        super().__init__(
            id=id,
            label=label,
            model=model,
            optimizer_model=prompt_optimizer_model,
            api_key=api_key,
            base_url=base_url,
            backend_server=backend_server,
        )
        self.client = AsyncAzureOpenAI(
            api_version=API_VERSION,
            azure_endpoint=base_url,
            api_key=api_key,
        )
        self.prompt_enhancer = OpenAIPromptEnhancer(self.client, prompt_optimizer_model)
        self.image_processor = ImageProcessor(self)

    async def _perform_generation(
        self, input_data: GenerationInput
    ) -> ImageGeneratorResponse:
        """Generate images using gpt-image-1 model."""
        logger.debug("Starting image generation: size=%s", input_data.size)

        # Prepare prompt
        prompt_to_use = self._format_prompt(input_data.prompt, "")

        if input_data.enhance_prompt:
            logger.debug("Prompt enhancement requested")
            prompt_to_use = await self.prompt_enhancer.enhance(prompt_to_use)

        # Call API
        try:
            logger.debug("Calling OpenAI API")
            response = await self.client.images.generate(
                model=self.model,
                prompt=prompt_to_use,
                size=input_data.size,
                output_format=input_data.output_format,
                background=input_data.background,
            )
            logger.info("OpenAI API response received: %d images", len(response.data))
            return await self._process_response(
                response.data, input_data.output_format, prompt_to_use
            )
        except Exception as e:
            logger.exception("OpenAI API call failed")
            return ImageGeneratorResponse(
                state=ImageResponseState.FAILED,
                images=[],
                enhanced_prompt=prompt_to_use,
                error=f"API call failed: {e!s}",
            )

    async def _perform_edit(self, input_data: EditImageInput) -> ImageGeneratorResponse:
        """Edit images using gpt-image-1 model."""
        logger.debug("Starting image editing: size=%s", input_data.size)

        try:
            # Prepare images and mask
            image_files = await self.image_processor.prepare_images_for_editing(
                input_data.image_paths, input_data.output_format
            )

            mask_file = None
            if input_data.mask_path:
                mask_file = await self.image_processor.load_image(input_data.mask_path)
                logger.debug("Loaded mask image: %d bytes", len(mask_file))

            # Call API
            logger.debug("Calling OpenAI edit API")
            api_kwargs = {
                "model": self.model,
                "image": image_files,
                "prompt": self._format_prompt(input_data.prompt, ""),
                "size": input_data.size,
                "output_format": input_data.output_format,
                "background": input_data.background,
            }
            if mask_file:
                api_kwargs["mask"] = mask_file

            response = await self.client.images.edit(**api_kwargs)
            logger.debug(
                "OpenAI edit API response received: %d images", len(response.data)
            )
            return await self._process_response(response.data, input_data.output_format)

        except Exception as e:
            error_msg = f"Edit failed: {e!s}"
            logger.exception(error_msg)
            return ImageGeneratorResponse(
                state=ImageResponseState.FAILED,
                images=[],
                error=error_msg,
            )

    async def _process_response(
        self,
        response_data: list[Any],
        output_format: str,
        enhanced_prompt: str | None = None,
    ) -> ImageGeneratorResponse:
        """Process API response images and return structured result."""
        self.clean_tmp_path(TMP_IMG_FILE)
        try:
            images = await self.image_processor.save_and_return_images(
                response_data, output_format
            )
            logger.debug("Successfully processed %d images", len(images))
            return ImageGeneratorResponse(
                state=ImageResponseState.SUCCEEDED,
                images=images,
                enhanced_prompt=enhanced_prompt,
            )
        except Exception as e:
            logger.exception("Failed to process generated images")
            return ImageGeneratorResponse(
                state=ImageResponseState.FAILED,
                images=[],
                enhanced_prompt=enhanced_prompt,
                error=f"Failed to process images: {e!s}",
            )
