"""Fixtures for OpenAI image generator integration tests."""

import os

import pytest

from appkit_mcp_image.backend.generators.openai import OpenAIImageGenerator


@pytest.fixture
def openai_image_generator() -> OpenAIImageGenerator:
    """Provide a real OpenAI image generator for integration tests."""
    return OpenAIImageGenerator(
        api_key=os.environ.get("OPENAI_API_KEY", ""),
        base_url=os.environ.get("OPENAI_BASE_URL"),
        backend_server=os.environ.get("BACKEND_SERVER", "http://localhost:8000"),
    )
