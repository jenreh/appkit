"""Tests for the PerplexityProcessor."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from openai import AsyncStream
from openai.types.chat import ChatCompletionChunk
from openai.types.chat.chat_completion_chunk import (
    Choice,
    ChoiceDelta,
)

from appkit_assistant.backend.processors.perplexity_processor import PerplexityProcessor
from appkit_assistant.backend.schemas import AIModel, ChunkType
from appkit_assistant.backend.services.chunk_factory import ChunkFactory

# ruff: noqa: SLF001


@pytest.fixture
def perplexity_processor() -> PerplexityProcessor:
    """Fixture for PerplexityProcessor with mocked client."""
    processor = PerplexityProcessor(api_key="test-key")
    processor.client = AsyncMock()
    # Mock chunk factory if needed, though default is likely fine
    processor._chunk_factory = ChunkFactory(processor_name="perplexity")
    return processor


@pytest.fixture
def mock_ai_model() -> AIModel:
    """Fixture for a basic AIModel config."""
    return AIModel(
        id="sonar-medium-online",
        text="Perplexity Sonar",
        model="sonar-medium-online",
        supports_search=True,
    )


class TestPerplexityProcessor:
    """Tests for PerplexityProcessor logic."""

    def test_format_citations_replaces_valid_citations(
        self, perplexity_processor: PerplexityProcessor
    ) -> None:
        """Test replacement of [N] with markdown links."""
        text = "This is a fact[1]. Another fact[2]."
        citations = ["https://example.com/1", "https://example.com/2"]

        result = perplexity_processor._format_citations(text, citations)

        assert result == (
            "This is a fact [[1]](https://example.com/1). "
            "Another fact [[2]](https://example.com/2)."
        )

    def test_format_citations_ignores_invalid_indices(
        self, perplexity_processor: PerplexityProcessor
    ) -> None:
        """Test ignoring citations that are out of bounds."""
        text = "This is a fact[1]. Another fact[99]."
        citations = ["https://example.com/1"]

        result = perplexity_processor._format_citations(text, citations)

        # [1] should be replaced, [99] should remain as is
        assert (
            result == "This is a fact [[1]](https://example.com/1). Another fact[99]."
        )

    def test_format_citations_handles_empty_citations(
        self, perplexity_processor: PerplexityProcessor
    ) -> None:
        """Test no replacement when citations list is empty."""
        text = "This is a fact [1]."
        citations: list[str] = []

        result = perplexity_processor._format_citations(text, citations)

        assert result == text

    def test_build_perplexity_payload_defaults(
        self, perplexity_processor: PerplexityProcessor, mock_ai_model: AIModel
    ) -> None:
        """Test payload construction with default model attributes."""
        # Ensure getattr defaults work if attributes are missing on the model object
        # The AIModel schema might not have specific Perplexity fields defined
        payload = perplexity_processor._build_perplexity_payload(mock_ai_model, {})

        assert payload["return_images"] is True
        assert payload["return_related_questions"] is True
        assert payload["search_domain_filter"] == []
        assert payload["web_search_options"]["search_context_size"] == "medium"

    @pytest.mark.asyncio
    async def test_process_streaming_response_citations(
        self, perplexity_processor: PerplexityProcessor, mock_ai_model: AIModel
    ) -> None:
        """Test citation replacement during streaming response."""
        # Setup mock stream
        mock_stream = AsyncMock(spec=AsyncStream)

        # Create a mock chunk with delta content
        chunk1 = MagicMock(spec=ChatCompletionChunk)
        chunk1.id = "msg-123"
        chunk1.choices = [
            Choice(
                delta=ChoiceDelta(content="Start of sentence[1]. "),
                index=0,
                logprobs=None,
                finish_reason=None,
            )
        ]
        # Attach citations to the chunk (Perplexity API does this)
        chunk1.citations = ["https://example.com/1"]

        # Create a second chunk
        chunk2 = MagicMock(spec=ChatCompletionChunk)
        chunk2.id = "msg-123"
        chunk2.choices = [
            Choice(
                delta=ChoiceDelta(content="End."),
                index=0,
                logprobs=None,
                finish_reason=None,
            )
        ]
        chunk2.citations = ["https://example.com/1"]  # Repeat citations

        # Mock async iteration
        mock_stream.__aiter__.return_value = [chunk1, chunk2]

        # Use the processor
        chunks = [
            chunk
            async for chunk in perplexity_processor._process_streaming_response(
                mock_stream, mock_ai_model, None
            )
        ]

        # Verify text chunks have formatted content
        text_chunks = [c for c in chunks if c.type == ChunkType.TEXT]
        assert len(text_chunks) == 2

        # First chunk should have citation replaced because citations were available
        assert text_chunks[0].text == "Start of sentence [[1]](https://example.com/1). "
        assert text_chunks[1].text == "End."

        # Verify annotation chunks yielded at the end
        annotation_chunks = [c for c in chunks if c.type == ChunkType.ANNOTATION]
        assert len(annotation_chunks) == 1
        assert annotation_chunks[0].chunk_metadata["url"] == "https://example.com/1"
        assert annotation_chunks[0].text == "https://example.com/1"
