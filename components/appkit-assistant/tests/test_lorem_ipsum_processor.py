# ruff: noqa: ARG002, SLF001, S105, S106
"""Tests for LoremIpsumProcessor.

Covers init, process validation, text generation, cancellation,
paragraph separators, statistics, and model support.
"""

from __future__ import annotations

import asyncio

import pytest

from appkit_assistant.backend.processors.lorem_ipsum_processor import (
    LOREM_MODELS,
    LoremIpsumProcessor,
)
from appkit_assistant.backend.schemas import AIModel, ChunkType


def _model(model_id: str = "lorem-short") -> AIModel:
    return AIModel(id=model_id, text=model_id, model=model_id, stream=True)


# ============================================================================
# Initialization
# ============================================================================


class TestInitialization:
    def test_basic_init(self) -> None:
        proc = LoremIpsumProcessor()
        assert proc._processor_name == "lorem_ipsum"
        assert proc.models == LOREM_MODELS

    def test_custom_models(self) -> None:
        custom = {"test": _model("test")}
        proc = LoremIpsumProcessor(models=custom)
        assert proc.models == custom

    def test_get_supported_models(self) -> None:
        proc = LoremIpsumProcessor()
        models = proc.get_supported_models()
        assert "lorem-short" in models


# ============================================================================
# process() validation
# ============================================================================


class TestProcessValidation:
    @pytest.mark.asyncio
    async def test_unsupported_model_raises(self) -> None:
        proc = LoremIpsumProcessor()
        with pytest.raises(ValueError, match="not supported"):
            async for _ in proc.process([], "nonexistent"):
                pass


# ============================================================================
# process() output
# ============================================================================


class TestProcessOutput:
    @pytest.mark.asyncio
    async def test_yields_thinking_text_completion(self) -> None:
        proc = LoremIpsumProcessor()
        chunks = [c async for c in proc.process([], "lorem-short")]

        types_found = [c.type for c in chunks]

        # First chunk should be THINKING
        assert types_found[0] == ChunkType.THINKING
        # Last chunk should be COMPLETION
        assert types_found[-1] == ChunkType.COMPLETION
        # Should have TEXT chunks in between
        assert ChunkType.TEXT in types_found
        # Should have a second THINKING chunk near the end
        thinking_chunks = [c for c in chunks if c.type == ChunkType.THINKING]
        assert len(thinking_chunks) == 2

    @pytest.mark.asyncio
    async def test_text_chunks_have_metadata(self) -> None:
        proc = LoremIpsumProcessor()
        chunks = [c async for c in proc.process([], "lorem-short")]
        text_chunks = [c for c in chunks if c.type == ChunkType.TEXT]

        # Filter out paragraph separators
        word_chunks = [
            c
            for c in text_chunks
            if c.chunk_metadata.get("type") != "paragraph_separator"
        ]
        assert len(word_chunks) > 0
        for c in word_chunks:
            assert c.chunk_metadata["source"] == "lorem_ipsum"
            assert "paragraph" in c.chunk_metadata
            assert "total_paragraphs" in c.chunk_metadata

    @pytest.mark.asyncio
    async def test_paragraph_separators(self) -> None:
        proc = LoremIpsumProcessor()
        chunks = [c async for c in proc.process([], "lorem-short")]
        separators = [
            c
            for c in chunks
            if c.type == ChunkType.TEXT
            and c.chunk_metadata.get("type") == "paragraph_separator"
        ]
        # Should have at least 3 separators (4-8 paragraphs, so 3-7 separators)
        assert len(separators) >= 3

    @pytest.mark.asyncio
    async def test_completion_has_statistics(self) -> None:
        proc = LoremIpsumProcessor()
        chunks = [c async for c in proc.process([], "lorem-short")]
        completion = [c for c in chunks if c.type == ChunkType.COMPLETION]
        assert len(completion) == 1
        stats = completion[0].statistics
        assert stats is not None
        assert stats.input_tokens == 10
        assert stats.output_tokens > 0


# ============================================================================
# Cancellation
# ============================================================================


class TestCancellation:
    @pytest.mark.asyncio
    async def test_cancellation_stops_generation(self) -> None:
        proc = LoremIpsumProcessor()
        cancel = asyncio.Event()

        chunks = []
        count = 0
        async for c in proc.process([], "lorem-short", cancellation_token=cancel):
            chunks.append(c)
            count += 1
            if count == 3:
                cancel.set()

        # Should still get completion chunk but fewer text chunks
        types_found = {c.type for c in chunks}
        assert ChunkType.THINKING in types_found
        assert ChunkType.COMPLETION in types_found
