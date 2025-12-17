import logging
from typing import Final

from appkit_commons.configuration.configuration import ReflexConfig
from appkit_commons.registry import service_registry
from appkit_imagecreator.backend.generators import (
    GoogleImageGenerator,
)
from appkit_imagecreator.backend.generators.openai import OpenAIImageGenerator
from appkit_imagecreator.backend.models import ImageGenerator
from appkit_imagecreator.configuration import ImageGeneratorConfig
from rxconfig import config

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

        if self.reflex_config.single_port:
            backend_server = f"{self.reflex_config.deploy_url}"
        else:
            backend_server = f"{self.reflex_config.deploy_url}:{config.backend_port}"

        self.register(
            OpenAIImageGenerator(
                api_key=self.config.openai_api_key.get_secret_value(),
                base_url=self.config.openai_base_url,
                backend_server=backend_server,
            )
        )
        self.register(
            OpenAIImageGenerator(
                api_key=self.config.openai_api_key.get_secret_value(),
                base_url=self.config.openai_base_url,
                backend_server=backend_server,
                model="FLUX-1.1-pro",
                label="Blackforest Labs FLUX 1.1-pro",
                id="FLUX-1.1-pro",
            )
        )
        self.register(
            GoogleImageGenerator(
                api_key=self.config.google_api_key.get_secret_value(),
                backend_server=backend_server,
            )
        )
        self.register(
            GoogleImageGenerator(
                api_key=self.config.google_api_key.get_secret_value(),
                backend_server=backend_server,
                model="imagen-3.0-generate-002",
                label="Google Imagen 3",
                id="imagen-3",
            )
        )

    def register(self, generator: ImageGenerator) -> None:
        """Register a new generator in the registry."""
        self._generators[generator.id] = generator

    def get(
        self,
        generator_id: str,
    ) -> ImageGenerator:
        """Get a generator by ID.

        If api_key or backend_server are provided, they will override the
        default values.
        """
        if generator_id not in self._generators:
            raise ValueError(f"Unknown generator ID: {generator_id}")

        return self._generators[generator_id]

    def list_generators(self) -> list[dict[str, str]]:
        """List all available generators with their IDs and labels."""
        return [{"id": gen.id, "label": gen.label} for gen in self._generators.values()]

    def get_generator_ids(self) -> list[str]:
        """Get the IDs of all registered generators."""
        return list(self._generators)

    def get_default_generator(self) -> ImageGenerator:
        """Get the default generator."""
        if not self._generators:
            raise ValueError("No generators registered.")

        return next(iter(self._generators.values()))


# Create a global instance of the registry
generator_registry: Final = ImageGeneratorRegistry()
