import logging
from typing import Final

from appkit_commons.configuration.configuration import ReflexConfig
from appkit_commons.registry import service_registry
from appkit_imagecreator.backend.generators.black_forest_labs import (
    FLUX1_KONTEXT_PRO,
    FLUX2_PRO,
    BlackForestLabsImageGenerator,
)
from appkit_imagecreator.backend.generators.nano_banana import (
    NANO_BANANA,
    NANO_BANANA_PRO,
    NanoBananaImageGenerator,
)
from appkit_imagecreator.backend.generators.openai import (
    GPT_IMAGE_1_5,
    GPT_IMAGE_1_MINI,
    OpenAIImageGenerator,
)
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
                model=GPT_IMAGE_1_MINI,
                api_key=self.config.openai_api_key.get_secret_value(),
                base_url=self.config.openai_base_url,
                on_azure=self.config.uses_azure,
            )
        )
        self.register(
            OpenAIImageGenerator(
                model=GPT_IMAGE_1_5,
                api_key=self.config.openai_api_key.get_secret_value(),
                base_url=self.config.openai_base_url,
                on_azure=self.config.uses_azure,
            )
        )
        self.register(
            NanoBananaImageGenerator(
                api_key=self.config.google_api_key.get_secret_value(),
                model=NANO_BANANA,
            )
        )
        self.register(
            NanoBananaImageGenerator(
                api_key=self.config.google_api_key.get_secret_value(),
                model=NANO_BANANA_PRO,
            )
        )
        self.register(
            OpenAIImageGenerator(
                model=FLUX1_KONTEXT_PRO,
                api_key=self.config.openai_api_key.get_secret_value(),
                base_url=self.config.openai_base_url,
                on_azure=self.config.uses_azure,
            )
        )
        self.register(
            BlackForestLabsImageGenerator(
                api_key=self.config.blackforestlabs_api_key.get_secret_value(),
                base_url=f"{self.config.blackforestlabs_base_url}",
                model=FLUX2_PRO,
                on_azure=self.config.uses_azure,
            )
        )

    def register(self, generator: ImageGenerator) -> None:
        """Register a new generator in the registry."""
        self._generators[generator.model.id] = generator

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
        return [
            {"id": gen.model.id, "label": gen.model.label}
            for gen in self._generators.values()
        ]

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
