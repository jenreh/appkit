import asyncio
import base64
import logging

import httpx

from appkit_imagecreator.backend.models import (
    GeneratedImageData,
    GenerationInput,
    ImageGenerator,
    ImageGeneratorResponse,
    ImageResponseState,
)

logger = logging.getLogger(__name__)


class BlackForestLabsImageGenerator(ImageGenerator):
    """Generator for the Black Forest Labs API (Flux models).

    Supports both native BFL API and Azure AI endpoints:
    - Native BFL: Returns external URLs, requires polling
    - Azure: Returns base64 images directly, no polling needed
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.bfl.ai/v1/",
        label: str = "Flux.1 Kontext [Pro]",
        id: str = "flux-kontext-pro",  # noqa: A002
        model: str = "flux-kontext-pro",
        supports_size: bool = False,
        supports_edit: bool = True,
    ) -> None:
        super().__init__(
            id=id,
            label=label,
            model=model,
            api_key=api_key,
            supports_edit=supports_edit,
        )
        self.supports_size = supports_size
        self.base_url = base_url
        self.is_azure = "azure.com" in base_url.lower()

    def _build_payload(self, input_data: GenerationInput, prompt: str) -> dict:
        """Build the base payload for BFL API requests.

        Args:
            input_data: Generation parameters
            prompt: Formatted prompt

        Returns:
            API payload dict
        """
        # Native BFL API format
        payload = {
            "prompt": prompt,
            "seed": input_data.seed,
            "prompt_upsampling": input_data.enhance_prompt,
            "safety_tolerance": 5,
        }

        if self.is_azure:
            payload["model"] = self.model.replace("-", ".", 1)

        if self.supports_size:
            payload["width"] = input_data.width
            payload["height"] = input_data.height
        else:
            payload["aspect_ratio"] = self._aspect_ratio(
                input_data.width, input_data.height
            )

        return payload

    def _build_response(
        self,
        image_url: str | None,
        image_b64: str | None,
        error_msg: str | None,
        prompt: str,
    ) -> ImageGeneratorResponse:
        """Build ImageGeneratorResponse from API result.

        Args:
            image_url: URL of generated/edited image or None (BFL native)
            image_b64: Base64 encoded image data or None (Azure)
            error_msg: Error message or None
            prompt: Enhanced prompt used for generation

        Returns:
            ImageGeneratorResponse with appropriate state
        """
        if error_msg or (not image_url and not image_b64):
            final_error = (
                error_msg or "Zu dem generierten Bild wurde keine URL erstellt."
            )
            logger.error("Image operation failed: %s", final_error)
            return ImageGeneratorResponse(
                state=ImageResponseState.FAILED,
                generated_images=[],
                error=final_error,
                enhanced_prompt=prompt,
            )

        # Azure returns base64 data directly
        if image_b64:
            try:
                image_bytes = base64.b64decode(image_b64)
                return ImageGeneratorResponse(
                    state=ImageResponseState.SUCCEEDED,
                    generated_images=[GeneratedImageData(image_bytes=image_bytes)],
                    enhanced_prompt=prompt,
                )
            except Exception as e:
                error_msg = f"Fehler beim Dekodieren des Base64-Bildes: {e!s}"
                logger.exception("Base64 decode failed")
                return ImageGeneratorResponse(
                    state=ImageResponseState.FAILED,
                    generated_images=[],
                    error=error_msg,
                    enhanced_prompt=prompt,
                )

        # BFL native returns external URL
        return ImageGeneratorResponse(
            state=ImageResponseState.SUCCEEDED,
            generated_images=[GeneratedImageData(external_url=image_url)],
            enhanced_prompt=prompt,
        )

    async def _call_bfl_api(
        self,
        payload: dict,
    ) -> tuple[str | None, str | None, str | None]:
        """Call BFL API and poll for result (or get direct response for Azure).

        Returns:
            Tuple of (image_url, image_b64, error_message)
        """
        if self.is_azure:
            # Azure endpoint with query parameter
            api_url = f"{self.base_url}{self.model}?api-version=preview"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            }
        else:
            # Native BFL endpoint
            api_url = f"{self.base_url}{self.model}"
            headers = {
                "accept": "application/json",
                "x-key": self.api_key,
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(api_url, headers=headers, json=payload)
                response.raise_for_status()
                result_data = response.json()

                # Azure returns image directly in response
                if self.is_azure:
                    return self._handle_azure_response(result_data)

                # Native BFL requires polling
                return await self._handle_bfl_polling(client, result_data)

        except httpx.HTTPStatusError as e:
            error_msg = (
                f"HTTP-Fehler aufgetreten: {e.response.status_code} - {e.response.text}"
            )
            logger.error(error_msg)
            return None, None, error_msg
        except httpx.RequestError as e:
            error_msg = f"Anfragefehler aufgetreten: {e!s}"
            logger.error(error_msg)
            return None, None, error_msg
        except Exception as e:
            error_msg = f"Ein unerwarteter Fehler ist aufgetreten: {e!s}"
            logger.exception("Unerwarteter Fehler während der API-Anfrage")
            return None, None, error_msg

    def _handle_azure_response(
        self, result_data: dict
    ) -> tuple[str | None, str | None, str | None]:
        """Handle Azure API response.

        Args:
            result_data: JSON response from Azure API

        Returns:
            Tuple of (image_url, image_b64, error_message)
        """
        data_list = result_data.get("data", [])
        if not data_list:
            logger.error("Azure response missing 'data' field: %s", result_data)
            return None, None, "Azure-API gab kein 'data'-Feld zurück."

        image_b64 = data_list[0].get("b64_json")
        if not image_b64:
            logger.error("Azure response missing 'b64_json': %s", data_list[0])
            return None, None, "Azure-API gab kein Base64-Bild zurück."

        return None, image_b64, None

    async def _handle_bfl_polling(
        self, client: httpx.AsyncClient, result_data: dict
    ) -> tuple[str | None, str | None, str | None]:
        """Handle BFL native API polling.

        Args:
            client: HTTP client for polling
            result_data: Initial response with polling URL

        Returns:
            Tuple of (image_url, image_b64, error_message)
        """
        polling_url = result_data.get("polling_url")
        if not polling_url:
            return None, None, "Keine Polling-URL in der Antwort gefunden."

        polling_headers = {
            "accept": "application/json",
            "x-key": self.api_key,
            "Authorization": f"Bearer {self.api_key}",
        }

        while True:
            await asyncio.sleep(1.5)
            poll_response = await client.get(polling_url, headers=polling_headers)
            poll_response.raise_for_status()
            result = poll_response.json()
            status = result.get("status")

            if status == "Ready":
                image_url = result.get("result", {}).get("sample")
                if not image_url:
                    return (
                        None,
                        None,
                        "Bild-URL wurde im 'Ready'-Status nicht gefunden.",
                    )
                return image_url, None, None

            if status not in ["Pending", "Processing", "Queued"]:
                error_status = (
                    f"Ein Fehler oder ein unerwarteter Status ist aufgetreten: {result}"
                )
                return None, None, error_status

    async def _perform_generation(
        self, input_data: GenerationInput
    ) -> ImageGeneratorResponse:
        prompt = self._format_prompt(input_data.prompt, input_data.negative_prompt)
        payload = self._build_payload(input_data, prompt)
        image_url, image_b64, error_msg = await self._call_bfl_api(payload)
        return self._build_response(image_url, image_b64, error_msg, prompt)

    async def _perform_edit(
        self,
        input_data: GenerationInput,
        reference_images: list[tuple[bytes, str]],
    ) -> ImageGeneratorResponse:
        """Edit images using Black Forest Labs FLUX API with reference images.

        Args:
            input_data: Generation parameters including prompt
            reference_images: List of (image_bytes, content_type) tuples (max 8)

        Returns:
            ImageGeneratorResponse with edited images
        """
        prompt = self._format_prompt(input_data.prompt, input_data.negative_prompt)

        logger.info(
            "Editing with %d reference image(s) using %s",
            len(reference_images),
            self.model,
        )

        # BFL API supports up to 8 reference images
        max_images = 8
        if len(reference_images) > max_images:
            logger.warning(
                "BFL supports max %d images, using first %d",
                max_images,
                max_images,
            )
            reference_images = reference_images[:max_images]

        # Build base payload and add reference images
        payload = self._build_payload(input_data, prompt)

        logger.info(
            "Editing with reference images - size: %dx%d, model: %s",
            input_data.width,
            input_data.height,
            self.model,
        )

        # Add reference images as input_image, input_image_2, etc.
        for idx, (img_bytes, _) in enumerate(reference_images):
            img_b64 = base64.b64encode(img_bytes).decode("utf-8")
            key = "input_image" if idx == 0 else f"input_image_{idx + 1}"
            payload[key] = img_b64
            logger.debug("Added %s (%d bytes)", key, len(img_bytes))

        # Log non-image payload parameters
        payload_info = {
            k: v for k, v in payload.items() if not k.startswith("input_image")
        }
        logger.info("Edit payload parameters: %s", payload_info)

        image_url, image_b64, error_msg = await self._call_bfl_api(payload)
        return self._build_response(image_url, image_b64, error_msg, prompt)
