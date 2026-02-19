"""AI model registry: loads active models from DB and initialises ModelManager.

Each active DB model gets its own processor instance keyed by model_id.
All credentials (api_key, base_url, on_azure) come exclusively from the DB.
"""

import logging

from appkit_assistant.backend.database.models import AssistantAIModel
from appkit_assistant.backend.database.repositories import ai_model_repo
from appkit_assistant.backend.model_manager import ModelManager
from appkit_assistant.backend.processors import (
    ClaudeResponsesProcessor,
    GeminiResponsesProcessor,
    LoremIpsumProcessor,
    OpenAIResponsesProcessor,
    PerplexityProcessor,
)
from appkit_assistant.backend.processors.processor_base import ProcessorBase
from appkit_assistant.backend.services.openai_client_service import OpenAIClientService
from appkit_commons.database.session import get_asyncdb_session
from appkit_commons.registry import service_registry

logger = logging.getLogger(__name__)


def _create_processor(m: AssistantAIModel) -> ProcessorBase | None:
    """Build a single-model processor for the given DB record.

    Returns None when a required api_key is missing (except for lorem_ipsum).
    """
    if m.processor_type != "lorem_ipsum" and not m.api_key:
        logger.warning(
            "Model '%s' (type=%s) has no api_key - skipped",
            m.model_id,
            m.processor_type,
        )
        return None

    model_config = {m.model_id: m.to_ai_model()}
    processor: ProcessorBase | None = None

    match m.processor_type:
        case "lorem_ipsum":
            processor = LoremIpsumProcessor()
        case "openai":
            processor = OpenAIResponsesProcessor(
                api_key=m.api_key,
                base_url=m.base_url or None,
                models=model_config,
                on_azure=m.on_azure,
            )
        case "claude":
            processor = ClaudeResponsesProcessor(
                api_key=m.api_key,
                base_url=m.base_url or None,
                models=model_config,
                on_azure=m.on_azure,
            )
        case "perplexity":
            processor = PerplexityProcessor(
                api_key=m.api_key,
                models=model_config,
            )
        case "gemini":
            processor = GeminiResponsesProcessor(
                api_key=m.api_key,
                models=model_config,
            )
        case _:
            logger.warning(
                "Unknown processor type '%s' for model '%s'",
                m.processor_type,
                m.model_id,
            )
    return processor


def _register_openai_client_service(
    all_active: list[AssistantAIModel],
) -> None:
    """Register OpenAIClientService from the first openai model that has an api_key."""
    openai_model = next(
        (m for m in all_active if m.processor_type == "openai" and m.api_key), None
    )

    if not openai_model:
        logger.warning(
            "No openai DB model with api_key found; OpenAIClientService unavailable"
        )
        return

    service_registry().register_as(
        OpenAIClientService,
        OpenAIClientService(
            api_key=openai_model.api_key,
            base_url=openai_model.base_url or None,
            on_azure=openai_model.on_azure,
        ),
    )
    logger.debug(
        "OpenAIClientService registered from model '%s'", openai_model.model_id
    )


class AIModelRegistry:
    """Initialises ModelManager from database-backed AI model configuration.

    Similar to ``ImageGeneratorRegistry``: loads active models from the DB
    at startup, groups them by ``processor_type``, and registers the
    appropriate processor implementation with the ``ModelManager``.

    Call ``reload()`` after admin changes to apply updates at runtime.
    """

    _loaded: bool = False

    async def initialize(self) -> None:
        """Load models from DB once on startup (no-op if already loaded)."""
        if self._loaded:
            return
        await self.reload()
        self._loaded = True

    async def reload(self) -> None:
        """Re-load all active models from DB and re-register processors."""
        model_manager = ModelManager()
        model_manager.clear_all()

        try:
            async with get_asyncdb_session() as session:
                all_active = await ai_model_repo.find_all_active_ordered_by_text(
                    session
                )
                session.expunge_all()
        except Exception:
            logger.exception(
                "AIModelRegistry: failed to load models from DB; "
                "ModelManager will be empty"
            )
            return

        registered = 0
        for m in all_active:
            if processor := _create_processor(m):
                model_manager.register_processor(m.model_id, processor)
                registered += 1

        _register_openai_client_service(all_active)

        if default_model := next(
            (
                m
                for m in model_manager.get_all_models()
                if not isinstance(
                    model_manager.get_processor_for_model(m.id), LoremIpsumProcessor
                )
            ),
            None,
        ):
            model_manager.set_default_model(default_model.id)
        elif all_models := model_manager.get_all_models():
            # If no "real" model exists, but we have *some* model
            # (e.g. explicitly configured lorem_ipsum)
            # then use that as default instead of failing silently.
            model_manager.set_default_model(all_models[0].id)

        logger.info(
            "AIModelRegistry: registered %d/%d DB models",
            registered,
            len(all_active),
        )


# Singleton instance
ai_model_registry = AIModelRegistry()
