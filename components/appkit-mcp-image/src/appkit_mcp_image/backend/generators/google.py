import logging
from typing import Any, Final

from google import genai
from google.genai import types

from appkit_commons.registry import service_registry
from appkit_mcp_image.backend.image_processor import ImageProcessor
from appkit_mcp_image.backend.models import (
    EditImageInput,
    GenerationInput,
    ImageGenerator,
    ImageGeneratorResponse,
    ImageResponseState,
)
from appkit_mcp_image.configuration import MCPImageGeneratorConfig

config = service_registry().get(MCPImageGeneratorConfig)
logger = logging.getLogger(__name__)

TMP_IMG_FILE: Final[str] = "nano-image"


class GooglePromptEnhancer:
    """Encapsulates prompt enhancement logic for Google models."""

    def __init__(self, client: genai.Client, model: str):
        self.client = client
        self.model = model

    def enhance(self, prompt: str) -> str:
        """Enhance prompt using Google's generative model."""
        logger.debug("Starting prompt enhancement")
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=(
                    "You are an image generation assistant specialized in "
                    "optimizing user prompts. Ensure content "
                    "compliance rules are followed. Do not ask followup "
                    "questions, just generate the plain, raw, optimized prompt "
                    "without any additional text, headlines or questions."
                    f"Enhance this prompt for image generation: {prompt}"
                ),
            )
            if result := response.text.strip():
                logger.info("Prompt enhanced successfully")
                return result

            logger.warning("Prompt enhancement returned empty, using original")
            return prompt
        except Exception:
            logger.exception("Prompt enhancement failed")
            return prompt


class GoogleImageGenerator(ImageGenerator):
    """Generator for the Google Imagen API.

    Uses composition pattern with specialized helper classes for:
    - Prompt enhancement (GooglePromptEnhancer)
    - Image processing (ImageProcessor)
    """

    def __init__(
        self,
        api_key: str,
        label: str = "Google Imagen 4",
        id: str = "imagen-4",  # noqa: A002
        model: str = "imagen-4.0-generate-preview-06-06",
        prompt_optimizer_model: str = "gemini-2.0-flash-001",
        backend_server: str | None = None,
    ) -> None:
        super().__init__(
            id=id,
            label=label,
            model=model,
            optimizer_model=prompt_optimizer_model,
            api_key=api_key,
            backend_server=backend_server,
        )
        self.client = genai.Client(api_key=self.api_key)
        self.prompt_enhancer = GooglePromptEnhancer(self.client, prompt_optimizer_model)
        self.image_processor = ImageProcessor(self)

    def _parse_size(self, size: str) -> tuple[int, int]:
        """Parse size string 'WxH' into (width, height)."""
        if size == "auto" or "x" not in size:
            return 1024, 1024
        try:
            width, height = map(int, size.split("x"))
            return width, height
        except ValueError:
            logger.warning("Invalid size format '%s', defaulting to 1024x1024", size)
            return 1024, 1024

    async def _process_response(
        self,
        response: Any,
        output_format: str,
        enhanced_prompt: str,
    ) -> ImageGeneratorResponse:
        """Process API response and save images."""
        self.clean_tmp_path(TMP_IMG_FILE)
        images: list[str] = []
        fmt = output_format or "jpeg"  # Default to jpeg per spec if None

        try:
            if not response.candidates:
                return self._create_failed_response(
                    "No candidates returned", enhanced_prompt
                )

            for candidate in response.candidates:
                if not (candidate.content and candidate.content.parts):
                    continue

                for part in candidate.content.parts:
                    if not (hasattr(part, "inline_data") and part.inline_data):
                        continue

                    image_url = await self.save_image(
                        image_bytes=part.inline_data.data,
                        tmp_file_prefix=TMP_IMG_FILE,
                        output_format=fmt,
                    )
                    images.append(image_url)

            if not images:
                return self._create_failed_response(
                    "No image data found in response", enhanced_prompt
                )

            logger.debug("Successfully generated %d images", len(images))
            return ImageGeneratorResponse(
                state=ImageResponseState.SUCCEEDED,
                images=images,
                enhanced_prompt=enhanced_prompt,
            )

        except Exception as e:
            logger.exception("Failed to process generated images")
            return self._create_failed_response(
                f"Processing failed: {e!s}", enhanced_prompt
            )

    def _create_failed_response(
        self, error: str, prompt: str
    ) -> ImageGeneratorResponse:
        """Helper to create failed response."""
        return ImageGeneratorResponse(
            state=ImageResponseState.FAILED,
            images=[],
            error=error,
            enhanced_prompt=prompt,
        )

    async def _perform_generation(
        self, input_data: GenerationInput
    ) -> ImageGeneratorResponse:
        """Generate images using generate_content API with IMAGE modality."""
        logger.debug("Starting image generation: size=%s", input_data.size)

        # Prepare prompt
        prompt_to_use = self._format_prompt(input_data.prompt, "")

        if input_data.enhance_prompt:
            prompt_to_use = self.prompt_enhancer.enhance(prompt_to_use)

        try:
            # Configure generation
            width, height = self._parse_size(input_data.size)
            aspect_ratio = self._aspect_ratio(width, height)

            image_config = types.ImageConfig(aspect_ratio=aspect_ratio)
            content_config = types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=image_config,
            )

            # Call API
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt_to_use,
                config=content_config,
            )
            return await self._process_response(
                response, input_data.output_format, prompt_to_use
            )

        except Exception as e:
            logger.exception("Google API call failed")
            return self._create_failed_response(
                f"API call failed: {e!s}", prompt_to_use
            )

    async def _perform_edit(self, input_data: EditImageInput) -> ImageGeneratorResponse:
        """Edit images using Google's generate_content API."""
        logger.debug("Starting image editing: size=%s", input_data.size)

        try:
            # Load and prepare images
            image_files = await self.image_processor.prepare_images_for_editing(
                input_data.image_paths, input_data.output_format
            )

            # Prepare prompt
            prompt = self._format_prompt(input_data.prompt, "")

            logger.debug("Calling Google API for editing")
            contents = [
                types.Part.from_bytes(data=img_bytes, mime_type=mime)
                for _, img_bytes, mime in image_files
            ]
            contents.append(prompt)

            response = self.client.models.generate_content(
                model=self.model,
                contents=contents,
                config=types.GenerateContentConfig(response_modalities=["IMAGE"]),
            )
            logger.debug("Google API response received")
            return await self._process_response(
                response, input_data.output_format, prompt
            )

        except Exception as e:
            logger.exception("Google editing failed")
            return self._create_failed_response(
                f"Edit failed: {e!s}", self._format_prompt(input_data.prompt, "")
            )
