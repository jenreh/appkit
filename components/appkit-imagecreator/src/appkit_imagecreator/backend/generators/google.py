import logging
from typing import ClassVar

from google import genai
from google.genai import types

from appkit_imagecreator.backend.models import (
    GeneratedImageData,
    GenerationInput,
    ImageGenerator,
    ImageGeneratorResponse,
    ImageModel,
    ImageResponseState,
)

logger = logging.getLogger(__name__)


class GoogleImageGenerator(ImageGenerator):
    """Generator for the Google Imagen API."""

    ENHANCEMENT_MODEL: ClassVar[str] = "gemini-2.0-flash-001"

    def __init__(
        self,
        model: ImageModel,
        api_key: str,
        supports_edit: bool = True,
    ) -> None:
        super().__init__(
            model=model,
            api_key=api_key,
            supports_edit=supports_edit,
        )
        self.client = genai.Client(api_key=self.api_key)

    def _aspect_ratio(self, width: int, height: int) -> str:
        """Calculate the closest supported aspect ratio based on width and height."""
        ratios = {
            "21:9": 21 / 9,
            "16:9": 16 / 9,
            "9:16": 9 / 16,
            "5:4": 5 / 4,
            "4:5": 4 / 5,
            "4:3": 4 / 3,
            "3:4": 3 / 4,
            "3:2": 3 / 2,
            "2:3": 2 / 3,
            "1:1": 1.0,
        }

        current_ratio = width / height
        ratio = min(ratios, key=lambda k: abs(ratios[k] - current_ratio))
        logger.debug(
            "Calculated aspect ratio %s for dimensions %dx%d", ratio, width, height
        )
        return ratio

    def _enhance_prompt(self, input_data: GenerationInput) -> str:
        """Format and optionally enhance the prompt."""
        prompt = self._format_prompt(input_data.prompt, input_data.negative_prompt)

        if not input_data.enhance_prompt:
            return prompt

        try:
            instruction = (
                "You are an image generation assistant specialized in optimizing "
                "user prompts. Ensure content compliance rules are followed. "
                "Do not ask followup questions, just generate the plain, raw, "
                "optimized prompt without any additional text, headlines or questions."
            )

            response = self.client.models.generate_content(
                model=self.ENHANCEMENT_MODEL,
                contents=(
                    f"{instruction} Enhance this prompt for image "
                    f"generation or image editing: {prompt}"
                ),
            )

            enhanced = response.text.strip()
            logger.debug("Enhanced prompt: %s", enhanced)
            return enhanced
        except Exception as e:
            logger.error("Failed to enhance prompt: %s", e)
            return prompt

    async def _perform_generation(
        self, input_data: GenerationInput
    ) -> ImageGeneratorResponse:
        prompt = self._enhance_prompt(input_data)

        try:
            # self.model is the ImageModel object; self.model.model is the ID string
            response = self.client.models.generate_images(
                model=self.model.model,
                prompt=prompt,
                config=types.GenerateImagesConfig(
                    number_of_images=input_data.n,
                    aspect_ratio=self._aspect_ratio(
                        input_data.width, input_data.height
                    ),
                ),
            )

            # Google Imagen generated images are typically JPEG or match request
            content_type = "image/jpeg"
            generated_images: list[GeneratedImageData] = [
                self._create_generated_image_data(img.image.image_bytes, content_type)
                for img in response.generated_images
            ]

            return ImageGeneratorResponse(
                state=ImageResponseState.SUCCEEDED,
                generated_images=generated_images,
                enhanced_prompt=prompt,
            )
        except Exception as e:
            logger.exception(
                "Generation failed with model %s (%s)", self.model.id, self.model.model
            )
            return ImageGeneratorResponse(
                state=ImageResponseState.FAILED,
                generated_images=[],
                error=str(e),
                enhanced_prompt=prompt,
            )

    async def _perform_edit(
        self,
        input_data: GenerationInput,
        reference_images: list[tuple[bytes, str]],
    ) -> ImageGeneratorResponse:
        """Edit images using Google's generate_content API with reference images."""
        prompt = self._enhance_prompt(input_data)

        logger.debug(
            "Editing with %d reference image(s) using model %s",
            len(reference_images),
            self.model.id,
        )

        try:
            contents = [
                types.Part.from_bytes(data=img, mime_type=mime)
                for img, mime in reference_images
            ]
            contents.append(prompt)

            response = self.client.models.generate_content(
                model=self.model.model,
                contents=contents,
                config=types.GenerateContentConfig(response_modalities=["IMAGE"]),
            )

            generated_images: list[GeneratedImageData] = []
            content_type = "image/png"  # Edit mode typically returns PNG

            if response.candidates:
                for candidate in response.candidates:
                    if not (candidate.content and candidate.content.parts):
                        continue

                    generated_images.extend(
                        self._create_generated_image_data(
                            part.inline_data.data, content_type
                        )
                        for part in candidate.content.parts
                        if hasattr(part, "inline_data") and part.inline_data
                    )

            if not generated_images:
                logger.warning("No edited images generated by %s", self.model.id)
                return ImageGeneratorResponse(
                    state=ImageResponseState.FAILED,
                    generated_images=[],
                    error="Es wurden keine bearbeiteten Bilder generiert.",
                    enhanced_prompt=prompt,
                )

            return ImageGeneratorResponse(
                state=ImageResponseState.SUCCEEDED,
                generated_images=generated_images,
                enhanced_prompt=prompt,
            )

        except Exception as e:
            logger.exception(
                "Error editing image with %s model %s", self.model.id, self.model.model
            )
            return ImageGeneratorResponse(
                state=ImageResponseState.FAILED,
                generated_images=[],
                error=str(e),
                enhanced_prompt=prompt,
            )
