"""Tests for ImageGeneratorRegistry."""

from unittest.mock import AsyncMock, patch

import pytest

from appkit_imagecreator.backend.generator_registry import ImageGeneratorRegistry
from appkit_imagecreator.backend.models import (
    ImageGenerator,
    ImageModel,
)


class TestImageGeneratorRegistry:
    """Test suite for ImageGeneratorRegistry."""

    def test_initialization(self) -> None:
        """ImageGeneratorRegistry initializes with empty state."""
        # Act
        registry = ImageGeneratorRegistry()

        # Assert
        assert registry._generators == {}  # noqa: SLF001
        assert registry._loaded is False  # noqa: SLF001

    @pytest.mark.asyncio
    async def test_initialize_loads_generators(self) -> None:
        """initialize loads generators from database on first call."""
        # Arrange
        registry = ImageGeneratorRegistry()

        with patch.object(registry, "reload", new_callable=AsyncMock) as mock_reload:
            # Act
            await registry.initialize()

            # Assert
            mock_reload.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_skips_if_already_loaded(self) -> None:
        """initialize does not reload if already loaded."""
        # Arrange
        registry = ImageGeneratorRegistry()
        registry._loaded = True  # noqa: SLF001

        with patch.object(registry, "reload", new_callable=AsyncMock) as mock_reload:
            # Act
            await registry.initialize()

            # Assert
            mock_reload.assert_not_called()

    @pytest.mark.asyncio
    async def test_reload_queries_database(self, image_generator_model_factory) -> None:
        """reload queries database for active generators."""
        # Arrange
        registry = ImageGeneratorRegistry()

        # Create mock DB models
        mock_model = await image_generator_model_factory(
            model_id="test-model",
            label="Test Generator",
            processor_type="appkit_imagecreator.backend.generators.openai.OpenAIImageGenerator",
        )

        # Mock the database query
        with patch(
            "appkit_imagecreator.backend.generator_registry.get_asyncdb_session"
        ) as mock_get_session:
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = mock_session

            with patch(
                "appkit_imagecreator.backend.generator_registry.generator_model_repo.find_all_active"
            ) as mock_find:
                mock_find.return_value = [mock_model]

                # Act
                await registry.reload()

                # Assert
                mock_find.assert_called_once_with(mock_session)
                assert registry._loaded is True  # noqa: SLF001

    @pytest.mark.asyncio
    async def test_reload_instantiates_generators(
        self, image_generator_model_factory
    ) -> None:
        """reload instantiates generator classes from DB models."""
        # Arrange
        registry = ImageGeneratorRegistry()

        mock_model = await image_generator_model_factory(
            model_id="test-openai",
            processor_type="appkit_imagecreator.backend.generators.openai.OpenAIImageGenerator",
        )

        with patch(
            "appkit_imagecreator.backend.generator_registry.get_asyncdb_session"
        ) as mock_get_session:
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = mock_session

            with patch(
                "appkit_imagecreator.backend.generator_registry.generator_model_repo.find_all_active"
            ) as mock_find:
                mock_find.return_value = [mock_model]

                # Act
                await registry.reload()

                # Assert
                assert "test-openai" in registry._generators  # noqa: SLF001
                assert isinstance(registry._generators["test-openai"], ImageGenerator)  # noqa: SLF001

    @pytest.mark.asyncio
    async def test_reload_handles_instantiation_errors(
        self, image_generator_model_factory
    ) -> None:
        """reload logs and skips generators that fail to instantiate."""
        # Arrange
        registry = ImageGeneratorRegistry()

        # Model with invalid processor_type
        bad_model = await image_generator_model_factory(
            model_id="bad-model",
            processor_type="nonexistent.module.BadClass",
        )

        good_model = await image_generator_model_factory(
            model_id="good-model",
            processor_type="appkit_imagecreator.backend.generators.openai.OpenAIImageGenerator",
        )

        with patch(
            "appkit_imagecreator.backend.generator_registry.get_asyncdb_session"
        ) as mock_get_session:
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = mock_session

            with patch(
                "appkit_imagecreator.backend.generator_registry.generator_model_repo.find_all_active"
            ) as mock_find:
                mock_find.return_value = [bad_model, good_model]

                # Act
                await registry.reload()

                # Assert - good model loaded, bad model skipped
                assert "good-model" in registry._generators  # noqa: SLF001
                assert "bad-model" not in registry._generators  # noqa: SLF001

    def test_resolve_processor_class_valid(self) -> None:
        """_resolve_processor_class imports and returns correct class."""
        # Act
        cls = ImageGeneratorRegistry._resolve_processor_class(  # noqa: SLF001
            "appkit_imagecreator.backend.generators.openai.OpenAIImageGenerator"
        )

        # Assert
        assert cls.__name__ == "OpenAIImageGenerator"
        assert issubclass(cls, ImageGenerator)

    def test_resolve_processor_class_invalid_path_raises(self) -> None:
        """_resolve_processor_class raises for invalid module path."""
        # Act & Assert
        with pytest.raises(ModuleNotFoundError):
            ImageGeneratorRegistry._resolve_processor_class(  # noqa: SLF001
                "nonexistent.module.ClassName"
            )

    def test_resolve_processor_class_not_subclass_raises(self) -> None:
        """_resolve_processor_class raises TypeError if not ImageGenerator."""
        # Act & Assert
        with pytest.raises(TypeError, match="not an ImageGenerator subclass"):
            ImageGeneratorRegistry._resolve_processor_class(  # noqa: SLF001
                "appkit_imagecreator.backend.models.ImageModel"
            )

    @pytest.mark.asyncio
    async def test_instantiate_generator(self, image_generator_model_factory) -> None:
        """_instantiate_generator creates generator from DB model."""
        # Arrange
        db_model = await image_generator_model_factory(
            model_id="test-gen",
            model="dall-e-3",
            label="Test Generator",
            processor_type="appkit_imagecreator.backend.generators.openai.OpenAIImageGenerator",
            api_key="test-key-123",
            base_url="https://api.example.com",
            extra_config={"on_azure": True, "quality": "hd"},
        )

        # Act
        generator = ImageGeneratorRegistry._instantiate_generator(db_model)  # noqa: SLF001

        # Assert
        assert isinstance(generator, ImageGenerator)
        assert generator.model.id == "test-gen"
        assert generator.api_key == "test-key-123"
        assert hasattr(generator, "base_url")

    def test_register_adds_to_cache(self) -> None:
        """register adds generator to in-memory cache."""
        # Arrange
        registry = ImageGeneratorRegistry()
        model = ImageModel(id="test", model="dall-e-3", label="Test")
        generator = ImageGenerator(model=model, api_key="key")

        # Act
        registry.register(generator)

        # Assert
        assert "test" in registry._generators  # noqa: SLF001
        assert registry._generators["test"] == generator  # noqa: SLF001

    def test_get_returns_registered_generator(self) -> None:
        """get returns generator by ID."""
        # Arrange
        registry = ImageGeneratorRegistry()
        model = ImageModel(id="test-id", model="dall-e-3", label="Test")
        generator = ImageGenerator(model=model, api_key="key")
        registry.register(generator)

        # Act
        result = registry.get("test-id")

        # Assert
        assert result == generator

    def test_get_raises_for_unknown_id(self) -> None:
        """get raises ValueError for unknown generator ID."""
        # Arrange
        registry = ImageGeneratorRegistry()

        # Act & Assert
        with pytest.raises(ValueError, match="Unknown generator ID"):
            registry.get("nonexistent")

    def test_list_generators(self) -> None:
        """list_generators returns generator metadata."""
        # Arrange
        registry = ImageGeneratorRegistry()
        model1 = ImageModel(
            id="gen1", model="dall-e-3", label="Generator 1", required_role="admin"
        )
        model2 = ImageModel(
            id="gen2", model="flux", label="Generator 2", required_role=None
        )
        registry.register(ImageGenerator(model=model1, api_key="key1"))
        registry.register(ImageGenerator(model=model2, api_key="key2"))

        # Act
        result = registry.list_generators()

        # Assert
        assert len(result) == 2
        gen1_dict = next(g for g in result if g["id"] == "gen1")
        assert gen1_dict["label"] == "Generator 1"
        assert gen1_dict["required_role"] == "admin"

    def test_get_generator_ids(self) -> None:
        """get_generator_ids returns list of registered IDs."""
        # Arrange
        registry = ImageGeneratorRegistry()
        model1 = ImageModel(id="id1", model="dall-e-3", label="Gen 1")
        model2 = ImageModel(id="id2", model="flux", label="Gen 2")
        registry.register(ImageGenerator(model=model1, api_key="key"))
        registry.register(ImageGenerator(model=model2, api_key="key"))

        # Act
        result = registry.get_generator_ids()

        # Assert
        assert "id1" in result
        assert "id2" in result
        assert len(result) == 2

    def test_get_default_generator(self) -> None:
        """get_default_generator returns first registered generator."""
        # Arrange
        registry = ImageGeneratorRegistry()
        model = ImageModel(id="first", model="dall-e-3", label="First")
        generator = ImageGenerator(model=model, api_key="key")
        registry.register(generator)

        # Act
        result = registry.get_default_generator()

        # Assert
        assert result == generator

    def test_get_default_generator_raises_when_empty(self) -> None:
        """get_default_generator raises ValueError when no generators."""
        # Arrange
        registry = ImageGeneratorRegistry()

        # Act & Assert
        with pytest.raises(ValueError, match="No generators registered"):
            registry.get_default_generator()
