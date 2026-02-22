"""Pytest fixtures for appkit-imagecreator tests."""

import base64
from datetime import UTC, datetime
from typing import Any

import pytest
import pytest_asyncio
from faker import Faker
from sqlalchemy.ext.asyncio import AsyncSession

from appkit_imagecreator.backend.generator_repository import (
    ImageGeneratorModelRepository,
)
from appkit_imagecreator.backend.models import (
    GeneratedImage,
    ImageGeneratorModel,
)
from appkit_imagecreator.backend.repository import GeneratedImageRepository


@pytest.fixture
def faker_instance() -> Faker:
    """Provide a Faker instance for generating realistic test data."""
    return Faker()


@pytest_asyncio.fixture
async def image_repo() -> GeneratedImageRepository:
    """Provide GeneratedImageRepository instance."""
    return GeneratedImageRepository()


@pytest_asyncio.fixture
async def generator_model_repo() -> ImageGeneratorModelRepository:
    """Provide ImageGeneratorModelRepository instance."""
    return ImageGeneratorModelRepository()


@pytest_asyncio.fixture
async def image_generator_model_factory(
    async_session: AsyncSession, faker_instance: Faker
):
    """Factory for creating test ImageGeneratorModel instances."""

    async def _create_model(**kwargs: Any) -> ImageGeneratorModel:
        defaults = {
            "model_id": f"test-model-{faker_instance.uuid4()}",
            "model": "dall-e-3",
            "label": f"Test Generator {faker_instance.word()}",
            "processor_type": "appkit_imagecreator.backend.generators.openai.OpenAIImageGenerator",
            "api_key": faker_instance.password(length=32),
            "base_url": None,
            "extra_config": {"output_format": "png", "quality": "standard"},
            "required_role": None,
            "active": True,
        }
        defaults.update(kwargs)
        model = ImageGeneratorModel(**defaults)
        async_session.add(model)
        await async_session.flush()
        await async_session.refresh(model)
        return model

    return _create_model


@pytest_asyncio.fixture
async def generated_image_factory(async_session: AsyncSession, faker_instance: Faker):
    """Factory for creating test GeneratedImage instances."""

    async def _create_image(**kwargs: Any) -> GeneratedImage:
        # Create a small test image (1x1 pixel PNG)
        test_image_bytes = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        )

        defaults = {
            "user_id": 1,
            "prompt": faker_instance.sentence(nb_words=8),
            "enhanced_prompt": faker_instance.sentence(nb_words=12),
            "style": faker_instance.random_element(
                ["realistic", "artistic", "minimalist", None]
            ),
            "model": "dall-e-3",
            "image_data": test_image_bytes,
            "content_type": "image/png",
            "width": 1024,
            "height": 1024,
            "quality": "standard",
            "config": {"output_format": "png"},
            "is_uploaded": False,
            "is_deleted": False,
        }
        defaults.update(kwargs)
        image = GeneratedImage(**defaults)
        async_session.add(image)
        await async_session.flush()
        await async_session.refresh(image)
        return image

    return _create_image


@pytest.fixture
def mock_openai_response_base64() -> dict[str, Any]:
    """Mock OpenAI API response with base64 encoded image."""
    # 1x1 pixel PNG
    test_image_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

    return {
        "created": int(datetime.now(UTC).timestamp()),
        "data": [{"b64_json": test_image_b64, "revised_prompt": "An enhanced prompt"}],
    }


@pytest.fixture
def mock_openai_response_url() -> dict[str, Any]:
    """Mock OpenAI API response with image URL."""
    return {
        "created": int(datetime.now(UTC).timestamp()),
        "data": [
            {
                "url": "https://example.com/image.png",
                "revised_prompt": "An enhanced prompt",
            }
        ],
    }


@pytest.fixture
def mock_google_response() -> dict[str, Any]:
    """Mock Google Imagen API response."""
    test_image_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

    return {
        "predictions": [
            {
                "bytesBase64Encoded": test_image_b64,
                "mimeType": "image/png",
            }
        ]
    }


@pytest.fixture
def sample_image_bytes() -> bytes:
    """Provide sample PNG image bytes for testing."""
    # 1x1 pixel PNG
    return base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    )
