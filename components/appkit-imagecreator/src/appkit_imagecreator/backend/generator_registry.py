import importlib
import logging
from typing import Final

from appkit_commons.database.session import get_asyncdb_session
from appkit_imagecreator.backend.generator_repository import (
    generator_model_repo,
)
from appkit_imagecreator.backend.models import (
    ImageGenerator,
    ImageGeneratorModel,
)

logger = logging.getLogger(__name__)


class ImageGeneratorRegistry:
    """Registry of image generators backed by database configuration.

    Loads active generators from the database, instantiates them
    via a plugin pattern using the stored processor_type class path,
    and caches them in memory. Call reload() to refresh after changes.
    """

    def __init__(self) -> None:
        self._generators: dict[str, ImageGenerator] = {}
        self._loaded = False

    async def initialize(self) -> None:
        """Load active generators from the database."""
        if self._loaded:
            return
        await self.reload()

    async def reload(self) -> None:
        """Re-query DB and re-instantiate all active generators."""
        new_generators: dict[str, ImageGenerator] = {}
        try:
            async with get_asyncdb_session() as session:
                models = await generator_model_repo.find_all_active(session)

                for db_model in models:
                    try:
                        generator = self._instantiate_generator(db_model)
                        new_generators[generator.model.id] = generator
                        logger.debug(
                            "Loaded generator: %s (%s)",
                            db_model.label,
                            db_model.processor_type,
                        )
                    except Exception:
                        logger.exception(
                            "Failed to instantiate generator %s",
                            db_model.label,
                        )

            self._generators = new_generators
            self._loaded = True
            logger.info(
                "Loaded %d active generators from database",
                len(self._generators),
            )
        except Exception:
            logger.exception("Failed to load generators from database")

    @staticmethod
    def _resolve_processor_class(
        processor_type: str,
    ) -> type[ImageGenerator]:
        """Dynamically import and return the generator class."""
        module_path, class_name = processor_type.rsplit(".", 1)
        module = importlib.import_module(module_path)
        cls = getattr(module, class_name)
        if not (isinstance(cls, type) and issubclass(cls, ImageGenerator)):
            msg = f"Processor {processor_type} is not an ImageGenerator subclass"
            raise TypeError(msg)
        return cls

    @staticmethod
    def _instantiate_generator(
        db_model: ImageGeneratorModel,
    ) -> ImageGenerator:
        """Create a generator instance from a DB model."""
        cls = ImageGeneratorRegistry._resolve_processor_class(db_model.processor_type)
        image_model = db_model.to_image_model()

        # Build constructor kwargs from DB fields
        kwargs: dict = {
            "model": image_model,
            "api_key": db_model.api_key,
        }
        if db_model.base_url:
            kwargs["base_url"] = db_model.base_url

        # Pass extra_config values as kwargs if the class accepts them
        extra = db_model.extra_config or {}
        for key in ("on_azure",):
            if key in extra:
                kwargs[key] = extra[key]

        return cls(**kwargs)

    def register(self, generator: ImageGenerator) -> None:
        """Register a generator in the in-memory cache."""
        self._generators[generator.model.id] = generator

    def get(self, generator_id: str) -> ImageGenerator:
        """Get a generator by ID."""
        if generator_id not in self._generators:
            msg = f"Unknown generator ID: {generator_id}"
            raise ValueError(msg)
        return self._generators[generator_id]

    def list_generators(self) -> list[dict[str, str | None]]:
        """List all available generators with their IDs and labels."""
        return [
            {
                "id": gen.model.id,
                "label": gen.model.label,
                "required_role": gen.model.required_role,
            }
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


# Global singleton — call await generator_registry.initialize()
# at app startup to load generators from the database.
generator_registry: Final = ImageGeneratorRegistry()
