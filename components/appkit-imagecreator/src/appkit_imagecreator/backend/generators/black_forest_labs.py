import asyncio
import logging

import httpx

from appkit_imagecreator.backend.models import (
    GenerationInput,
    ImageGenerator,
    ImageGeneratorResponse,
    ImageResponseState,
)

logger = logging.getLogger(__name__)


class BlackForestLabsImageGenerator(ImageGenerator):
    """Generator for the Together AI API (Flux Schnell model)."""

    def __init__(
        self,
        api_key: str,
        label: str = "Flux.1 Kontext [Pro]",
        id: str = "flux-kontext-pro",  # noqa: A002
        model: str = "flux-kontext-pro",
        backend_server: str | None = None,
    ) -> None:
        super().__init__(
            id=id,
            label=label,
            model=model,
            api_key=api_key,
            backend_server=backend_server,
        )

    async def _perform_generation(
        self, input_data: GenerationInput
    ) -> ImageGeneratorResponse:
        prompt = self._format_prompt(input_data.prompt, input_data.negative_prompt)

        api_url = f"https://api.bfl.ai/v1/{self.model}"
        headers = {
            "accept": "application/json",
            "x-key": self.api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "prompt": prompt,
            "aspect_ratio": self._aspect_ratio(input_data.width, input_data.height),
            "seed": input_data.seed,
            "prompt_upsampling": input_data.enhance_prompt,
            "safety_tolerance": 6,
        }

        error_msg = None
        image_url = None

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(api_url, headers=headers, json=payload)
                response.raise_for_status()  # Raise an exception for bad status codes
                request_data = response.json()

                polling_url = request_data.get("polling_url")
                polling_headers = {
                    "accept": "application/json",
                    "x-key": self.api_key,
                }

                while True:
                    await asyncio.sleep(1.5)  # Use asyncio.sleep for async context
                    poll_response = await client.get(
                        polling_url, headers=polling_headers
                    )
                    poll_response.raise_for_status()
                    result = poll_response.json()
                    status = result.get("status")

                    if status == "Ready":
                        image_url = result.get("result", {}).get("sample")
                        if not image_url:
                            error_msg = (
                                "Bild-URL wurde im 'Ready'-Status nicht gefunden."
                            )
                        break
                    if status not in ["Pending", "Processing", "Queued"]:
                        error_msg = f"Ein Fehler oder ein unerwarteter Status ist aufgetreten: {result}"  # noqa: E501
                        break
        except httpx.HTTPStatusError as e:
            error_msg = (
                f"HTTP-Fehler aufgetreten: {e.response.status_code} - {e.response.text}"
            )
            logger.error(error_msg)
        except httpx.RequestError as e:
            error_msg = f"Anfragefehler aufgetreten: {e!s}"
            logger.error(error_msg)
        except Exception as e:
            error_msg = f"Ein unerwarteter Fehler ist aufgetreten: {e!s}"
            logger.exception("Unerwarteter Fehler während der Bildgenerierung")

        if error_msg or not image_url:
            final_error_message = (
                error_msg or "Zu dem generierten Bild wurde keine URL erstellt."
            )
            logger.error(
                "Image generation failed: %s",
                final_error_message,
            )
            return ImageGeneratorResponse(
                state=ImageResponseState.FAILED,
                images=[],
                error=final_error_message,
                enhanced_prompt=prompt,  # BFL does enhancement server-side
            )

        return ImageGeneratorResponse(
            state=ImageResponseState.SUCCEEDED,
            images=[image_url],
            enhanced_prompt=prompt,  # BFL does enhancement server-side via prompt_upsampling
        )
