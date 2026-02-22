"""Tests for ModelManager service."""

import asyncio
import logging
import threading
from collections.abc import AsyncGenerator

import pytest

from appkit_assistant.backend.database.models import MCPServer
from appkit_assistant.backend.model_manager import ModelManager
from appkit_assistant.backend.processors.processor_base import ProcessorBase
from appkit_assistant.backend.schemas import AIModel, Chunk, Message


class MockProcessor(ProcessorBase):
    """Mock processor for testing."""

    def __init__(self, models: dict[str, AIModel]) -> None:
        """Initialize with mock models."""
        super().__init__()
        self._models = models

    def get_supported_models(self) -> dict[str, AIModel]:
        """Return mock models."""
        return self._models

    async def process(
        self,
        _messages: list[Message],  # noqa: ARG002
        _model_id: str,  # noqa: ARG002
        _files: list[str] | None = None,  # noqa: ARG002
        _mcp_servers: list[MCPServer] | None = None,  # noqa: ARG002
        _cancellation_token: asyncio.Event | None = None,  # noqa: ARG002
    ) -> AsyncGenerator[Chunk, None]:
        """Mock process method."""
        yield Chunk(type="text", content="mocked_response")


@pytest.fixture
def reset_model_manager() -> None:
    """Reset ModelManager singleton for testing."""
    ModelManager._instance = None
    ModelManager._default_model_id = None
    yield
    ModelManager._instance = None
    ModelManager._default_model_id = None


@pytest.fixture
def sample_models() -> dict[str, AIModel]:
    """Create sample AI models for testing."""
    return {
        "gpt-4": AIModel(
            id="gpt-4",
            text="GPT-4",
            icon="openai",
            provider="openai",
            hidden=False,
            disabled=False,
        ),
        "gpt-3.5": AIModel(
            id="gpt-3.5",
            text="GPT-3.5",
            icon="openai",
            provider="openai",
            hidden=False,
            disabled=False,
        ),
    }


@pytest.fixture
def sample_models_alternative() -> dict[str, AIModel]:
    """Create alternative sample AI models for testing."""
    return {
        "claude-3": AIModel(
            id="claude-3",
            text="Claude 3",
            icon="anthropic",
            provider="anthropic",
            hidden=False,
            disabled=False,
        ),
    }


class TestModelManager:
    """Test suite for ModelManager singleton service."""

    def test_singleton_creation(self, reset_model_manager: None) -> None:
        """ModelManager is a singleton."""
        # Act
        manager1 = ModelManager()
        manager2 = ModelManager()

        # Assert
        assert manager1 is manager2

    def test_initialization_only_once(self, reset_model_manager: None) -> None:
        """ModelManager initializes only once despite multiple instantiations."""
        # Act
        manager1 = ModelManager()
        processors_id_1 = id(manager1._processors)

        manager2 = ModelManager()
        processors_id_2 = id(manager2._processors)

        # Assert
        assert processors_id_1 == processors_id_2

    def test_register_processor_adds_models(
        self, reset_model_manager: None, sample_models: dict[str, AIModel]
    ) -> None:
        """Registering processor adds its models to the manager."""
        # Arrange
        manager = ModelManager()
        processor = MockProcessor(sample_models)

        # Act
        manager.register_processor("openai", processor)

        # Assert
        assert manager.get_model("gpt-4") is not None
        assert manager.get_model("gpt-3.5") is not None
        assert len(manager.get_all_models()) == 2

    def test_first_registered_model_becomes_default(
        self, reset_model_manager: None, sample_models: dict[str, AIModel]
    ) -> None:
        """First registered model is automatically set as default."""
        # Arrange
        manager = ModelManager()
        processor = MockProcessor(sample_models)

        # Act
        manager.register_processor("openai", processor)
        default = manager.get_default_model()

        # Assert
        assert default in sample_models

    def test_get_processor_for_model(
        self, reset_model_manager: None, sample_models: dict[str, AIModel]
    ) -> None:
        """get_processor_for_model returns correct processor."""
        # Arrange
        manager = ModelManager()
        processor = MockProcessor(sample_models)
        manager.register_processor("openai", processor)

        # Act
        retrieved = manager.get_processor_for_model("gpt-4")

        # Assert
        assert retrieved is processor

    def test_get_processor_for_unregistered_model(
        self, reset_model_manager: None
    ) -> None:
        """get_processor_for_model returns None for unregistered model."""
        # Arrange
        manager = ModelManager()

        # Act
        result = manager.get_processor_for_model("unknown-model")

        # Assert
        assert result is None

    def test_get_all_models_sorted(
        self, reset_model_manager: None, sample_models: dict[str, AIModel]
    ) -> None:
        """get_all_models returns sorted models."""
        # Arrange
        manager = ModelManager()
        processor = MockProcessor(sample_models)
        manager.register_processor("openai", processor)

        # Act
        models = manager.get_all_models()

        # Assert
        assert len(models) == 2
        # Check they're sorted by icon then text
        assert models[0].icon <= models[1].icon or (
            models[0].icon == models[1].icon
            and models[0].text.lower() <= models[1].text.lower()
        )

    def test_get_model_by_id(
        self, reset_model_manager: None, sample_models: dict[str, AIModel]
    ) -> None:
        """get_model retrieves correct model by ID."""
        # Arrange
        manager = ModelManager()
        processor = MockProcessor(sample_models)
        manager.register_processor("openai", processor)

        # Act
        model = manager.get_model("gpt-4")

        # Assert
        assert model is not None
        assert model.id == "gpt-4"
        assert model.text == "GPT-4"

    def test_get_nonexistent_model(self, reset_model_manager: None) -> None:
        """get_model returns None for nonexistent model."""
        # Arrange
        manager = ModelManager()

        # Act
        result = manager.get_model("nonexistent")

        # Assert
        assert result is None

    def test_get_default_model_with_no_models(
        self, reset_model_manager: None, caplog: pytest.LogCaptureFixture
    ) -> None:
        """get_default_model returns fallback when no models registered."""
        # Arrange
        manager = ModelManager()

        # Act
        with caplog.at_level(logging.WARNING):
            default = manager.get_default_model()

        # Assert
        assert default == "default"
        assert "No models registered" in caplog.text

    def test_get_default_model_uses_first_available(
        self, reset_model_manager: None, sample_models: dict[str, AIModel]
    ) -> None:
        """get_default_model uses first available when default unset."""
        # Arrange
        manager = ModelManager()
        manager._default_model_id = None  # Force unset
        processor = MockProcessor(sample_models)
        manager.register_processor("openai", processor)

        # Act
        default = manager.get_default_model()

        # Assert
        assert default in sample_models

    def test_set_default_model(
        self, reset_model_manager: None, sample_models: dict[str, AIModel]
    ) -> None:
        """set_default_model changes default model."""
        # Arrange
        manager = ModelManager()
        processor = MockProcessor(sample_models)
        manager.register_processor("openai", processor)

        # Act
        manager.set_default_model("gpt-3.5")

        # Assert
        assert manager.get_default_model() == "gpt-3.5"

    def test_set_default_model_unregistered_logs_warning(
        self, reset_model_manager: None, caplog: pytest.LogCaptureFixture
    ) -> None:
        """set_default_model logs warning for unregistered model."""
        # Arrange
        manager = ModelManager()

        # Act
        with caplog.at_level(logging.WARNING):
            manager.set_default_model("unknown-model")

        # Assert
        assert "Attempted to set unregistered model" in caplog.text
        assert manager.get_default_model() == "default"

    def test_unregister_single_processor(
        self, reset_model_manager: None, sample_models: dict[str, AIModel]
    ) -> None:
        """unregister_processors removes processor and its models."""
        # Arrange
        manager = ModelManager()
        processor = MockProcessor(sample_models)
        manager.register_processor("openai", processor)
        assert len(manager.get_all_models()) == 2

        # Act
        manager.unregister_processors({"openai"})

        # Assert
        assert len(manager.get_all_models()) == 0
        assert manager.get_model("gpt-4") is None

    def test_unregister_resets_default_if_removed(
        self,
        reset_model_manager: None,
        sample_models: dict[str, AIModel],
        sample_models_alternative: dict[str, AIModel],
    ) -> None:
        """unregister_processors resets default if it's removed."""
        # Arrange
        manager = ModelManager()
        processor1 = MockProcessor(sample_models)
        manager.register_processor("openai", processor1)
        original_default = manager.get_default_model()

        # Act
        manager.unregister_processors({"openai"})

        # Assert
        assert manager._default_model_id is None

    def test_unregister_nonexistent_processor(self, reset_model_manager: None) -> None:
        """unregister_processors handles nonexistent processor gracefully."""
        # Arrange
        manager = ModelManager()

        # Act - should not raise
        manager.unregister_processors({"nonexistent"})

        # Assert
        assert len(manager.get_all_models()) == 0

    def test_multiple_processors_registration(
        self,
        reset_model_manager: None,
        sample_models: dict[str, AIModel],
        sample_models_alternative: dict[str, AIModel],
    ) -> None:
        """Multiple processors can be registered with different models."""
        # Arrange
        manager = ModelManager()
        processor1 = MockProcessor(sample_models)
        processor2 = MockProcessor(sample_models_alternative)

        # Act
        manager.register_processor("openai", processor1)
        manager.register_processor("anthropic", processor2)

        # Assert
        assert len(manager.get_all_models()) == 3
        assert manager.get_processor_for_model("gpt-4") is processor1
        assert manager.get_processor_for_model("claude-3") is processor2

    def test_clear_all(
        self, reset_model_manager: None, sample_models: dict[str, AIModel]
    ) -> None:
        """clear_all removes all processors and models."""
        # Arrange
        manager = ModelManager()
        processor = MockProcessor(sample_models)
        manager.register_processor("openai", processor)
        assert len(manager.get_all_models()) == 2

        # Act
        manager.clear_all()

        # Assert
        assert len(manager.get_all_models()) == 0
        assert len(manager._processors) == 0
        assert manager._default_model_id is None

    def test_singleton_thread_safety(self, reset_model_manager: None) -> None:
        """ModelManager singleton is thread-safe."""
        # Arrange
        instances = []

        def create_instance() -> None:
            instances.append(ModelManager())

        # Act
        threads = [threading.Thread(target=create_instance) for _ in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # Assert
        assert len(instances) == 5
        assert all(inst is instances[0] for inst in instances)

    def test_empty_models_returns_empty_list(self, reset_model_manager: None) -> None:
        """get_all_models returns empty list when no models."""
        # Arrange
        manager = ModelManager()

        # Act
        models = manager.get_all_models()

        # Assert
        assert models == []

    def test_processor_with_empty_models(self, reset_model_manager: None) -> None:
        """Registering processor with no models works."""
        # Arrange
        manager = ModelManager()
        processor = MockProcessor({})

        # Act
        manager.register_processor("empty", processor)

        # Assert
        assert len(manager.get_all_models()) == 0

    def test_register_overwrite_processor(
        self,
        reset_model_manager: None,
        sample_models: dict[str, AIModel],
        sample_models_alternative: dict[str, AIModel],
    ) -> None:
        """Registering processor with same name overwrites previous."""
        # Arrange
        manager = ModelManager()
        processor1 = MockProcessor(sample_models)
        processor2 = MockProcessor(sample_models_alternative)

        # Act
        manager.register_processor("ai_processor", processor1)
        assert len(manager.get_all_models()) == 2
        manager.register_processor("ai_processor", processor2)

        # Assert
        assert len(manager.get_all_models()) == 3  # Old models still there
        assert manager.get_processor_for_model("claude-3") is processor2
