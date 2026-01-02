import logging

from google import genai
from google.genai import types

from appkit_imagecreator.backend.models import (
    GeneratedImageData,
    GenerationInput,
    ImageGenerator,
    ImageGeneratorResponse,
    ImageResponseState,
)

logger = logging.getLogger(__name__)


class GoogleImageGenerator(ImageGenerator):
    """Generator for the Google Imagen API."""

    def __init__(
        self,
        api_key: str,
        label: str = "Google Imagen 4",
        id: str = "imagen-4",  # noqa: A002
        model: str = "imagen-4.0-generate-preview-06-06",
        supports_edit: bool = True,
    ) -> None:
        super().__init__(
            id=id,
            label=label,
            model=model,
            api_key=api_key,
            supports_edit=supports_edit,
        )
        self.client = genai.Client(api_key=self.api_key)

    def _enhance_prompt(self, prompt: str) -> str:
        response = self.client.models.generate_content(
            model="gemini-2.0-flash-001",
            contents=(
                "You are an image generation assistant specialized in "
                "optimizing user prompts. Ensure content "
                "compliance rules are followed. Do not ask followup "
                "questions, just generate the plain, raw, optimized prompt "
                "withoud any additional text, headlines or questions."
                f"Enhance this prompt for image generation or image editing: {prompt}"
            ),
        )

        prompt = response.text.strip()
        logger.debug("Enhanced prompt for image generation: %s", prompt)
        return prompt

    async def _perform_generation(
        self, input_data: GenerationInput
    ) -> ImageGeneratorResponse:
        prompt = self._format_prompt(input_data.prompt, input_data.negative_prompt)
        original_prompt = prompt

        if input_data.enhance_prompt:
            prompt = self._enhance_prompt(prompt)

        enhanced_prompt = prompt if input_data.enhance_prompt else original_prompt

        response = self.client.models.generate_images(
            model=self.model,
            prompt=prompt,
            config=genai.types.GenerateImagesConfig(
                number_of_images=input_data.n,
                aspect_ratio=self._aspect_ratio(input_data.width, input_data.height),
            ),
        )

        output_format = "jpeg"
        content_type = f"image/{output_format}"
        generated_images = [
            self._create_generated_image_data(img.image.image_bytes, content_type)
            for img in response.generated_images
        ]

        return ImageGeneratorResponse(
            state=ImageResponseState.SUCCEEDED,
            generated_images=generated_images,
            enhanced_prompt=enhanced_prompt,
        )

    async def _perform_edit(
        self,
        input_data: GenerationInput,
        reference_images: list[tuple[bytes, str]],
    ) -> ImageGeneratorResponse:
        """Edit images using Google's generate_content API with reference images.

        Args:
            input_data: Generation parameters including prompt
            reference_images: List of (image_bytes, content_type) tuples

        Returns:
            ImageGeneratorResponse with edited images
        """

        prompt = self._format_prompt(input_data.prompt, input_data.negative_prompt)
        original_prompt = prompt

        if input_data.enhance_prompt:
            prompt = self._enhance_prompt(prompt)

        enhanced_prompt = prompt if input_data.enhance_prompt else original_prompt

        logger.info(
            "Editing with %d reference image(s) using model %s",
            len(reference_images),
            self.model,
        )

        try:
            # Build contents array with reference images and prompt
            contents = []
            for img_bytes, content_type in reference_images:
                contents.append(
                    types.Part.from_bytes(data=img_bytes, mime_type=content_type)
                )
            contents.append(prompt)

            # Use generate_content with multimodal input
            response = self.client.models.generate_content(
                model=self.model,
                contents=contents,
                config=types.GenerateContentConfig(response_modalities=["IMAGE"]),
            )

            output_format = "png"
            content_type = f"image/{output_format}"
            generated_images: list[GeneratedImageData] = []

            # Extract images from response
            if response.candidates:
                for candidate in response.candidates:
                    if candidate.content and candidate.content.parts:
                        for part in candidate.content.parts:
                            if hasattr(part, "inline_data") and part.inline_data:
                                generated_images.append(  # noqa: PERF401
                                    self._create_generated_image_data(
                                        part.inline_data.data, content_type
                                    )
                                )

            if not generated_images:
                logger.warning("No edited images generated by %s", self.model)
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

        except Exception as e:
            logger.exception(
                "Error editing image with %s model %s", self.id, self.model
            )
            return ImageGeneratorResponse(
                state=ImageResponseState.FAILED,
                generated_images=[],
                error=str(e),
                enhanced_prompt=enhanced_prompt,
            )
