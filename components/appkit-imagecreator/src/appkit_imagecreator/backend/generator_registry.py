import logging
from typing import Final

from appkit_commons.configuration.configuration import ReflexConfig
from appkit_commons.registry import service_registry
from appkit_imagecreator.backend.generators.black_forest_labs import (
    BlackForestLabsImageGenerator,
)
from appkit_imagecreator.backend.generators.nano_banana import (
    NanoBananaImageGenerator,
)
from appkit_imagecreator.backend.generators.openai import OpenAIImageGenerator
from appkit_imagecreator.backend.models import ImageGenerator
from appkit_imagecreator.configuration import ImageGeneratorConfig

logger = logging.getLogger(__name__)


class ImageGeneratorRegistry:
    """Registry of image generators.

    Maintains a collection of configured image generators that can be retrieved by ID.
    """

    def __init__(self):
        self.config = service_registry().get(ImageGeneratorConfig)
        self.reflex_config = service_registry().get(ReflexConfig)
        self._generators: dict[str, ImageGenerator] = {}
        self._initialize_default_generators()

        logger.debug("reflex config: %s", self.reflex_config)
        logger.debug("image generator config: %s", self.config)

    def _initialize_default_generators(self) -> None:
        """Initialize the registry with default generators."""
        self.register(
            OpenAIImageGenerator(
                api_key=self.config.openai_api_key.get_secret_value(),
                base_url=self.config.openai_base_url,
                model="gpt-image-1-mini",
                label="OpenAI GPT-Image-1 mini (Azure)",
                id="azure-gpt-image-1-mini",
            )
        )
        self.register(
            OpenAIImageGenerator(
                api_key=self.config.openai_api_key.get_secret_value(),
                base_url=self.config.openai_base_url,
                model="gpt-image-1.5",
                label="OpenAI GPT-Image-1.5 (Azure)",
                id="azure-gpt-image-1.5",
            )
        )
        self.register(
            NanoBananaImageGenerator(
                api_key=self.config.google_api_key.get_secret_value(),
                model="gemini-2.5-flash-image",
                label="Google Nano Banana",
                id="nano-banana",
            )
        )
        self.register(
            NanoBananaImageGenerator(
                api_key=self.config.google_api_key.get_secret_value(),
                model="gemini-3-pro-image-preview",
                label="Google Nano Banana Pro",
                id="nano-banana-pro",
            )
        )
        self.register(
            OpenAIImageGenerator(
                api_key=self.config.openai_api_key.get_secret_value(),
                base_url=self.config.openai_base_url,
                model="FLUX.1-Kontext-pro",
                label="Blackforest Labs FLUX.1-Kontext-pro (Azure)",
                id="FLUX.1-Kontext-pro",
            )
        )
        self.register(
            BlackForestLabsImageGenerator(
                api_key=self.config.blackforestlabs_api_key.get_secret_value(),
                base_url=self.config.blackforestlabs_base_url,
                model="flux-2-pro",
                label="Blackforest Labs FLUX.2-pro (Azure)",
                id="azure-flux-2-pro",
                supports_size=True,
            )
        )
        # self.register(
        #     BlackForestLabsImageGenerator(
        #         api_key=self.config.blackforestlabs_api_key.get_secret_value(),
        #         model="flux-2-pro",
        #         label="Blackforest Labs FLUX.2-pro (org)",
        #         id="bfl-flux-2-pro",
        #         supports_size=True,
        #     )
        # )

    def register(self, generator: ImageGenerator) -> None:
        """Register a new generator in the registry."""
        self._generators[generator.id] = generator

    def get(
        self,
        generator_id: str,
    ) -> ImageGenerator:
        """Get a generator by ID."""
        if generator_id not in self._generators:
            raise ValueError(f"Unknown generator ID: {generator_id}")

        return self._generators[generator_id]

    def list_generators(self) -> list[dict[str, str]]:
        """List all available generators with their IDs and labels."""
        return [{"id": gen.id, "label": gen.label} for gen in self._generators.values()]

    def get_generator_ids(self) -> list[str]:
        """Get the IDs of all registered generators."""
        return list(self._generators.keys())

    def get_default_generator(self) -> ImageGenerator:
        """Get the default generator."""
        if not self._generators:
            raise ValueError("No generators registered.")

        return next(iter(self._generators.values()))


# Create a global instance of the registry
generator_registry: Final = ImageGeneratorRegistry()
