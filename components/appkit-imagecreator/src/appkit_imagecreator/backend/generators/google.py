import logging

from google import genai

from appkit_imagecreator.backend.models import (
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
    ) -> None:
        super().__init__(
            id=id,
            label=label,
            model=model,
            api_key=api_key,
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
                f"Enhance this prompt for image generation: {prompt}"
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
