import base64
import logging
from typing import Final

from openai import AsyncAzureOpenAI

from appkit_imagecreator.backend.models import (
    GenerationInput,
    ImageGenerator,
    ImageGeneratorResponse,
    ImageResponseState,
)

logger = logging.getLogger(__name__)

TMP_IMG_FILE: Final[str] = "gpt-image"


class OpenAIImageGenerator(ImageGenerator):
    """Generator for the OpenAI DALL-E API."""

    def __init__(
        self,
        api_key: str,
        id: str = "gpt-image-1",  # noqa: A002
        label: str = "OpenAI GPT-Image-1",
        model: str = "gpt-image-1",
        backend_server: str | None = None,
        base_url: str | None = None,
    ) -> None:
        super().__init__(
            id=id,
            label=label,
            model=model,
            api_key=api_key,
            backend_server=backend_server,
        )
        # self.client = AsyncOpenAI(api_key=self.api_key)

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
                    "content": f"Enhance this prompt for image generation: {prompt}",
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

        self.clean_tmp_path(TMP_IMG_FILE)

        images = []
        for img in response.data:
            if img.url:
                images.append(img.url)
            elif img.b64_json:
                image_bytes = base64.b64decode(img.b64_json)
                image_url = await self._save_image_to_tmp_and_get_url(
                    image_bytes=image_bytes,
                    tmp_file_prefix=TMP_IMG_FILE,
                    output_format=output_format,
                )
                images.append(image_url)
            else:
                logger.warning("Image data from OpenAI is neither b64_json nor a URL.")

        if not images:
            logger.error(
                "No images were successfully processed or retrieved from OpenAI."
            )
            return ImageGeneratorResponse(
                state=ImageResponseState.FAILED,
                images=[],
                error="Es wurden keine Bilder generiert oder von der API abgerufen.",
                enhanced_prompt=enhanced_prompt,
            )

        return ImageGeneratorResponse(
            state=ImageResponseState.SUCCEEDED,
            images=images,
            enhanced_prompt=enhanced_prompt,
        )
