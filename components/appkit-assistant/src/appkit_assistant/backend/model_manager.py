from __future__ import annotations

import logging
import threading
from typing import Self

from appkit_assistant.backend.processors.processor_base import ProcessorBase
from appkit_assistant.backend.schemas import AIModel

logger = logging.getLogger(__name__)


class ModelManager:
    """Singleton service manager for AI processing services."""

    _instance: ModelManager | None = None
    _lock = threading.Lock()
    _default_model_id = (
        None  # Default model ID will be set to the first registered model
    )

    def __new__(cls) -> Self:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(ModelManager, cls).__new__(cls)  # noqa UP008
        return cls._instance

    def __init__(self):
        """Initialize the service manager if not already initialized."""
        if not hasattr(self, "_initialized"):
            self._processors: dict[str, ProcessorBase] = {}
            self._models: dict[str, AIModel] = {}
            self._model_to_processor: dict[str, str] = {}
            self._initialized = True
            logger.debug("ModelManager initialized")

    def register_processor(self, processor_name: str, processor: ProcessorBase) -> None:
        """
        Register a processor with the service manager.

        Args:
            processor_name: Name of the processor.
            processor: Instance of a Processor.
        """
        self._processors[processor_name] = processor

        # Extract and register all models supported by this processor
        supported_models = processor.get_supported_models()
        for model_id, model in supported_models.items():
            self._models[model_id] = model
            self._model_to_processor[model_id] = processor_name

            # Set the first registered model as default if no default is set
            if self._default_model_id is None:
                self._default_model_id = model_id
                logger.debug("Set first model %s as default", model_id)

                # Set the first registered model as default if no default is set
                if self._default_model_id is None:
                    self._default_model_id = model_id
                    logger.debug("Set first model %s as default", model_id)

        logger.debug("Registered processor: %s", processor_name)

    def get_processor_for_model(self, model_id: str) -> ProcessorBase | None:
        """
        Get the processor that supports the specified model.

        Args:
            model_id: ID of the model.

        Returns:
            The processor that supports the model or None if no processor is found.
        """
        processor_name = self._model_to_processor.get(model_id)
        if processor_name:
            return self._processors.get(processor_name)
        return None

    def get_all_models(self) -> list[AIModel]:
        """
        Get all registered models.

        Returns:
            List of all models.
        """
        return sorted(
            self._models.values(),
            key=lambda model: (
                model.icon.lower() if model.icon else "",
                model.text.lower(),
            ),
        )

    def get_model(self, model_id: str) -> AIModel | None:
        """
        Get a model by its ID.

        Args:
            model_id: ID of the model.

        Returns:
            The model or None if not found.
        """
        return self._models.get(model_id)

    def get_default_model(self) -> str:
        """
        Get the default model ID.

        Returns:
            The default model ID as a string.
        """
        if self._default_model_id is None:
            if self._models:
                self._default_model_id = next(iter(self._models.keys()))
                logger.debug(
                    "Using first available model %s as default", self._default_model_id
                )
            else:
                logger.warning("No models registered, returning fallback model name")
                return "default"
        return self._default_model_id

    def set_default_model(self, model_id: str) -> None:
        """
        Set the default model ID.

        Args:
            model_id: ID of the model to set as default.
        """
        if model_id in self._models:
            self._default_model_id = model_id
            logger.debug("Default model set to: %s", model_id)
        else:
            logger.warning(
                "Attempted to set unregistered model %s as default. Ignoring.", model_id
            )

    def clear_all(self) -> None:
        """Clear all registered processors and models.

        Used by AIModelRegistry to fully reload from DB.
        """
        self._processors.clear()
        self._models.clear()
        self._model_to_processor.clear()
        self._default_model_id = None
        logger.debug("ModelManager cleared all processors and models")
