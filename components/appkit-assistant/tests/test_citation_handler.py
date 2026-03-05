"""Tests for CitationHandler implementations.

Covers Citation model, BaseCitationHandler, ClaudeCitationHandler,
PerplexityCitationHandler, and NullCitationHandler.
"""

import json
from types import SimpleNamespace

import pytest

from appkit_assistant.backend.schemas import ChunkType
from appkit_assistant.backend.services.citation_handler import (
    Citation,
    ClaudeCitationHandler,
    NullCitationHandler,
    PerplexityCitationHandler,
)

# ============================================================================
# Citation dataclass
# ============================================================================


class TestCitation:
    def test_defaults(self) -> None:
        c = Citation()
        assert c.cited_text == ""
        assert c.document_title is None
        assert c.document_index == 0
        assert c.url is None
        assert c.raw_data == {}

    def test_to_dict_minimal(self) -> None:
        c = Citation(cited_text="ref")
        d = c.to_dict()
        assert d == {"cited_text": "ref", "document_index": 0}

    def test_to_dict_with_title_and_url(self) -> None:
        c = Citation(
            cited_text="text",
            document_title="Doc",
            url="https://example.com",
        )
        d = c.to_dict()
        assert d["document_title"] == "Doc"
        assert d["url"] == "https://example.com"

    def test_to_dict_with_char_location(self) -> None:
        c = Citation(start_char_index=10, end_char_index=20)
        d = c.to_dict()
        assert d["start_char_index"] == 10
        assert d["end_char_index"] == 20

    def test_to_dict_with_page_location(self) -> None:
        c = Citation(start_page_number=1, end_page_number=3)
        d = c.to_dict()
        assert d["start_page_number"] == 1
        assert d["end_page_number"] == 3

    def test_to_dict_with_block_location(self) -> None:
        c = Citation(start_block_index=0, end_block_index=5)
        d = c.to_dict()
        assert d["start_block_index"] == 0
        assert d["end_block_index"] == 5


# ============================================================================
# BaseCitationHandler.yield_citation_chunks (default impl)
# ============================================================================


class TestBaseCitationHandlerYield:
    @pytest.mark.asyncio
    async def test_empty_citations(self) -> None:
        handler = ClaudeCitationHandler()  # Concrete subclass
        chunks = [c async for c in handler.yield_citation_chunks([], "test")]
        assert chunks == []

    @pytest.mark.asyncio
    async def test_url_string_citations(self) -> None:
        handler = ClaudeCitationHandler()
        urls = ["https://a.com", "https://b.com"]
        chunks = [c async for c in handler.yield_citation_chunks(urls, "test")]
        assert len(chunks) == 2
        assert chunks[0].type == ChunkType.ANNOTATION
        assert chunks[0].text == "https://a.com"
        assert chunks[0].chunk_metadata["url"] == "https://a.com"

    @pytest.mark.asyncio
    async def test_citation_object_with_url(self) -> None:
        handler = ClaudeCitationHandler()
        citations = [Citation(url="https://doc.com", document_title="Doc")]
        chunks = [c async for c in handler.yield_citation_chunks(citations, "proc")]
        assert len(chunks) == 1
        assert chunks[0].text == "https://doc.com"
        meta = chunks[0].chunk_metadata
        assert meta["processor"] == "proc"
        parsed = json.loads(meta["citation"])
        assert parsed["document_title"] is not None

    @pytest.mark.asyncio
    async def test_citation_object_fallback_to_title(self) -> None:
        handler = ClaudeCitationHandler()
        citations = [Citation(document_title="My Doc")]
        chunks = [c async for c in handler.yield_citation_chunks(citations, "test")]
        assert chunks[0].text == "My Doc"

    @pytest.mark.asyncio
    async def test_citation_object_fallback_to_cited_text(self) -> None:
        handler = ClaudeCitationHandler()
        citations = [Citation(cited_text="some reference")]
        chunks = [c async for c in handler.yield_citation_chunks(citations, "test")]
        assert chunks[0].text == "some reference"


# ============================================================================
# ClaudeCitationHandler
# ============================================================================


class TestClaudeCitationHandler:
    def test_extract_no_citations(self) -> None:
        handler = ClaudeCitationHandler()
        delta = SimpleNamespace()  # No citations attr
        assert handler.extract_citations(delta) == []

    def test_extract_empty_citations(self) -> None:
        handler = ClaudeCitationHandler()
        delta = SimpleNamespace(citations=[])
        assert handler.extract_citations(delta) == []

    def test_extract_char_location(self) -> None:
        handler = ClaudeCitationHandler()
        citation_obj = SimpleNamespace(
            cited_text="hello",
            document_index=1,
            document_title="Doc A",
            type="char_location",
            start_char_index=10,
            end_char_index=20,
        )
        delta = SimpleNamespace(citations=[citation_obj])
        result = handler.extract_citations(delta)
        assert len(result) == 1
        assert result[0].cited_text == "hello"
        assert result[0].start_char_index == 10
        assert result[0].end_char_index == 20

    def test_extract_page_location(self) -> None:
        handler = ClaudeCitationHandler()
        citation_obj = SimpleNamespace(
            cited_text="ref",
            document_index=0,
            document_title=None,
            type="page_location",
            start_page_number=1,
            end_page_number=3,
        )
        delta = SimpleNamespace(citations=[citation_obj])
        result = handler.extract_citations(delta)
        assert result[0].start_page_number == 1
        assert result[0].end_page_number == 3

    def test_extract_content_block_location(self) -> None:
        handler = ClaudeCitationHandler()
        citation_obj = SimpleNamespace(
            cited_text="block",
            document_index=0,
            document_title=None,
            type="content_block_location",
            start_block_index=0,
            end_block_index=2,
        )
        delta = SimpleNamespace(citations=[citation_obj])
        result = handler.extract_citations(delta)
        assert result[0].start_block_index == 0
        assert result[0].end_block_index == 2

    def test_extract_multiple_citations(self) -> None:
        handler = ClaudeCitationHandler()
        c1 = SimpleNamespace(
            cited_text="a",
            document_index=0,
            document_title=None,
            type="char_location",
            start_char_index=0,
            end_char_index=1,
        )
        c2 = SimpleNamespace(
            cited_text="b",
            document_index=1,
            document_title="Doc B",
            type="page_location",
            start_page_number=5,
            end_page_number=5,
        )
        delta = SimpleNamespace(citations=[c1, c2])
        result = handler.extract_citations(delta)
        assert len(result) == 2


# ============================================================================
# PerplexityCitationHandler
# ============================================================================


class TestPerplexityCitationHandler:
    def test_extract_no_citations(self) -> None:
        handler = PerplexityCitationHandler()
        delta = SimpleNamespace()
        assert handler.extract_citations(delta) == []

    def test_extract_url_citations(self) -> None:
        handler = PerplexityCitationHandler()
        delta = SimpleNamespace(citations=["https://a.com", "https://b.com"])
        result = handler.extract_citations(delta)
        assert len(result) == 2
        assert result[0].url == "https://a.com"
        assert result[0].document_title == "https://a.com"

    def test_extract_ignores_non_string(self) -> None:
        handler = PerplexityCitationHandler()
        delta = SimpleNamespace(citations=["https://a.com", 42, None])
        result = handler.extract_citations(delta)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_yield_citation_chunks_empty(self) -> None:
        handler = PerplexityCitationHandler()
        chunks = [c async for c in handler.yield_citation_chunks([], "perplexity")]
        assert chunks == []

    @pytest.mark.asyncio
    async def test_yield_citation_chunks_with_urls(self) -> None:
        handler = PerplexityCitationHandler()
        citations = [
            Citation(url="https://a.com", document_title="A"),
            Citation(url="https://b.com", document_title="B"),
        ]
        chunks = [
            c async for c in handler.yield_citation_chunks(citations, "perplexity")
        ]
        # Should yield TEXT chunk with metadata + ANNOTATION chunks
        text_chunks = [c for c in chunks if c.type == ChunkType.TEXT]
        annotation_chunks = [c for c in chunks if c.type == ChunkType.ANNOTATION]
        assert len(text_chunks) == 1
        assert len(annotation_chunks) == 2
        # TEXT chunk carries citations in metadata
        meta = text_chunks[0].chunk_metadata
        assert "citations" in meta
        citations_data = json.loads(meta["citations"])
        assert len(citations_data) == 2

    @pytest.mark.asyncio
    async def test_yield_citation_chunks_with_strings(self) -> None:
        handler = PerplexityCitationHandler()
        chunks = [
            c
            async for c in handler.yield_citation_chunks(
                ["https://a.com"], "perplexity"
            )
        ]
        assert len(chunks) == 2  # TEXT + ANNOTATION

    @pytest.mark.asyncio
    async def test_yield_skips_citation_without_url(self) -> None:
        handler = PerplexityCitationHandler()
        citations = [Citation(url=None, document_title="no-url")]
        chunks = [
            c async for c in handler.yield_citation_chunks(citations, "perplexity")
        ]
        # TEXT chunk is always yielded, but ANNOTATION should be skipped
        annotation_chunks = [c for c in chunks if c.type == ChunkType.ANNOTATION]
        assert len(annotation_chunks) == 0


# ============================================================================
# NullCitationHandler
# ============================================================================


class TestNullCitationHandler:
    def test_extract_returns_empty(self) -> None:
        handler = NullCitationHandler()
        assert handler.extract_citations(None) == []
        assert handler.extract_citations("anything") == []

    @pytest.mark.asyncio
    async def test_yield_returns_nothing(self) -> None:
        handler = NullCitationHandler()
        chunks = [c async for c in handler.yield_citation_chunks([], "test")]
        assert chunks == []

    @pytest.mark.asyncio
    async def test_yield_with_citations_still_empty(self) -> None:
        handler = NullCitationHandler()
        chunks = [
            c async for c in handler.yield_citation_chunks([Citation(url="x")], "test")
        ]
        assert chunks == []
