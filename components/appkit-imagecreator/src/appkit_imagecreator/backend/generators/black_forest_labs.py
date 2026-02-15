import asyncio
import base64
import logging

import httpx

from appkit_imagecreator.backend.models import (
    GeneratedImageData,
    GenerationInput,
    ImageGenerator,
    ImageGeneratorResponse,
    ImageModel,
    ImageResponseState,
)

logger = logging.getLogger(__name__)

FLUX1_KONTEXT_PRO = ImageModel(
    id="azure-flux1-kontext-pro",
    model="FLUX.1-Kontext-pro",
    label="Blackforest Labs FLUX.1-Kontext-pro (Azure)",
    config={
        "moderation": "low",
        "output_compression": 95,
        "output_format": "jpeg",
        "quality": "hd",
        "background": "auto",
    },
)

FLUX2_PRO = ImageModel(
    id="azure-flux-2-pro",
    model="flux-2-pro",
    label="Blackforest Labs FLUX.2-pro (Azure)",
    config={
        "safety_tolerance": 6,
        "output_format": "jpeg",
    },
)


class BlackForestLabsImageGenerator(ImageGenerator):
    """Generator for the Black Forest Labs API (Flux models).

    Supports both native BFL API and Azure AI endpoints:
    - Native BFL: Returns external URLs, requires polling
    - Azure: Returns base64 images directly, no polling needed
    """

    _base_url: str

    def __init__(
        self,
        model: ImageModel,
        api_key: str,
        base_url: str = "https://api.bfl.ai/v1/",
        supports_edit: bool = True,
        on_azure: bool = False,
    ) -> None:
        super().__init__(
            model=model,
            api_key=api_key,
            supports_edit=supports_edit,
        )
        self._base_url = base_url
        self._on_azure = on_azure

    def _get_api_params(self) -> tuple[str, dict[str, str]]:
        """Get API URL and headers based on provider (Azure vs Native)."""
        if self._on_azure:
            url = f"{self._base_url}/providers/blackforestlabs/v1/{self.model.model}?api-version=preview"  # noqa: E501
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            }
        else:
            url = f"{self._base_url}{self.model.model}"
            headers = {
                "accept": "application/json",
                "x-key": self.api_key,
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
        return url, headers

    def _build_payload(self, input_data: GenerationInput, prompt: str) -> dict:
        """Build the request payload."""
        payload = self.model.config.copy() if self.model.config else {}

        payload.update(
            {
                "prompt": prompt,
                "seed": input_data.seed,
            }
        )

        payload["width"] = input_data.width
        payload["height"] = input_data.height

        if self._on_azure:
            # Azure specific model name adjustment: "flux-2-pro" -> "flux.2-pro"
            payload["model"] = self.model.model.replace("-", ".", 1)

        return payload

    async def _poll_result(self, client: httpx.AsyncClient, polling_url: str) -> dict:
        """Poll BFL native API for result."""
        headers = {
            "accept": "application/json",
            "x-key": self.api_key,
            "Authorization": f"Bearer {self.api_key}",
        }

        while True:
            await asyncio.sleep(1.5)
            response = await client.get(polling_url, headers=headers)
            response.raise_for_status()
            data = response.json()

            status = data.get("status")
            if status == "Ready":
                return data
            if status not in {"Pending", "Processing", "Queued"}:
                raise ValueError(f"Unexpected status: {status}")

    async def _make_request(self, payload: dict) -> dict:
        """Execute the initial API request and poll if necessary."""
        url, headers = self._get_api_params()

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

            if self._on_azure:
                return data

            # Native BFL requires polling
            polling_url = data.get("polling_url")
            if not polling_url:
                raise ValueError("No polling URL in response")
            return await self._poll_result(client, polling_url)

    def _parse_response(self, data: dict, prompt: str) -> ImageGeneratorResponse:
        """Extract image data from response dictionary."""
        generated_images = []

        if self._on_azure:
            items = data.get("data", [])
            b64_json = items[0].get("b64_json") if items else None
            if not b64_json:
                raise ValueError("No image data in Azure response")
            image_bytes = base64.b64decode(b64_json)
            generated_images.append(GeneratedImageData(image_bytes=image_bytes))
        else:
            image_url = data.get("result", {}).get("sample")
            if not image_url:
                raise ValueError("No image URL in result")
            generated_images.append(GeneratedImageData(external_url=image_url))

        return ImageGeneratorResponse(
            state=ImageResponseState.SUCCEEDED,
            generated_images=generated_images,
            enhanced_prompt=prompt,
        )

    async def _perform_generation(
        self, input_data: GenerationInput
    ) -> ImageGeneratorResponse:
        """Generate image."""
        prompt = self._format_prompt(input_data.prompt, input_data.negative_prompt)
        payload = self._build_payload(input_data, prompt)
        return await self._execute(payload, prompt)

    async def _perform_edit(
        self,
        input_data: GenerationInput,
        reference_images: list[tuple[bytes, str]],
    ) -> ImageGeneratorResponse:
        """Edit image."""
        prompt = self._format_prompt(input_data.prompt, input_data.negative_prompt)
        payload = self._build_payload(input_data, prompt)

        # BFL supports max 8 images
        for idx, (img_bytes, _) in enumerate(reference_images[:8]):
            # Base64 encode and add as input_image, input_image_2, etc.
            key = "input_image" if idx == 0 else f"input_image_{idx + 1}"
            payload[key] = base64.b64encode(img_bytes).decode("utf-8")

        return await self._execute(payload, prompt)

    async def _execute(self, payload: dict, prompt: str) -> ImageGeneratorResponse:
        """Execute request and handle errors centrally."""
        try:
            data = await self._make_request(payload)
            return self._parse_response(data, prompt)
        except Exception as e:
            logger.error("Blackforest generation failed: %s", e)
            return ImageGeneratorResponse(
                state=ImageResponseState.FAILED,
                generated_images=[],
                error=str(e),
                enhanced_prompt=prompt,
            )
