"""Citation Handler Protocol and implementations.

Provides a unified interface for extracting and yielding citations
from different AI API responses.
"""

import json
import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from typing import Any, Protocol

from appkit_assistant.backend.schemas import Chunk, ChunkType

logger = logging.getLogger(__name__)


@dataclass
class Citation:
    """Standardized citation data structure."""

    cited_text: str = ""
    document_title: str | None = None
    document_index: int = 0
    url: str | None = None
    # Location info (varies by type)
    start_char_index: int | None = None
    end_char_index: int | None = None
    start_page_number: int | None = None
    end_page_number: int | None = None
    start_block_index: int | None = None
    end_block_index: int | None = None
    # Raw data for passthrough
    raw_data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "cited_text": self.cited_text,
            "document_index": self.document_index,
        }
        if self.document_title:
            result["document_title"] = self.document_title
        if self.url:
            result["url"] = self.url
        if self.start_char_index is not None:
            result["start_char_index"] = self.start_char_index
            result["end_char_index"] = self.end_char_index
        if self.start_page_number is not None:
            result["start_page_number"] = self.start_page_number
            result["end_page_number"] = self.end_page_number
        if self.start_block_index is not None:
            result["start_block_index"] = self.start_block_index
            result["end_block_index"] = self.end_block_index
        return result


class CitationHandlerProtocol(Protocol):
    """Protocol for citation handlers."""

    def extract_citations(self, delta: Any) -> list[Citation]:
        """Extract citations from a response delta/chunk.

        Args:
            delta: The response delta object (vendor-specific)

        Returns:
            List of extracted Citation objects
        """
        ...

    async def yield_citation_chunks(
        self,
        citations: list[Citation] | list[str],
        processor_name: str,
    ) -> AsyncGenerator[Chunk, None]:
        """Yield citation chunks for display.

        Args:
            citations: List of Citation objects or URL strings
            processor_name: Name of the processor for metadata

        Yields:
            Chunk objects for citation display
        """
        ...


class BaseCitationHandler(ABC):
    """Base class for citation handlers."""

    @abstractmethod
    def extract_citations(self, delta: Any) -> list[Citation]:
        """Extract citations from a response delta."""

    async def yield_citation_chunks(
        self,
        citations: list[Citation] | list[str],
        processor_name: str,
    ) -> AsyncGenerator[Chunk, None]:
        """Default implementation yields ANNOTATION chunks."""
        if not citations:
            return

        logger.debug("Processing %d citations", len(citations))

        for citation in citations:
            if isinstance(citation, str):
                # URL string
                yield Chunk(
                    type=ChunkType.ANNOTATION,
                    text=citation,
                    chunk_metadata={
                        "url": citation,
                        "processor": processor_name,
                    },
                )
            else:
                # Citation object
                text = citation.url or citation.document_title or citation.cited_text
                yield Chunk(
                    type=ChunkType.ANNOTATION,
                    text=text or "",
                    chunk_metadata={
                        "citation": json.dumps(citation.to_dict()),
                        "processor": processor_name,
                    },
                )


class ClaudeCitationHandler(BaseCitationHandler):
    """Citation handler for Claude API responses.

    Claude provides citations in text delta's citations field with
    various location types (char, page, content_block).
    """

    def extract_citations(self, delta: Any) -> list[Citation]:
        """Extract citations from Claude text delta.

        Args:
            delta: Claude API text delta object

        Returns:
            List of Citation objects
        """
        citations = []

        text_block_citations = getattr(delta, "citations", None)
        if not text_block_citations:
            return citations

        for citation_obj in text_block_citations:
            citation = Citation(
                cited_text=getattr(citation_obj, "cited_text", ""),
                document_index=getattr(citation_obj, "document_index", 0),
                document_title=getattr(citation_obj, "document_title", None),
            )

            # Handle different citation location types
            citation_type = getattr(citation_obj, "type", None)
            if citation_type == "char_location":
                citation.start_char_index = getattr(citation_obj, "start_char_index", 0)
                citation.end_char_index = getattr(citation_obj, "end_char_index", 0)
            elif citation_type == "page_location":
                citation.start_page_number = getattr(
                    citation_obj, "start_page_number", 0
                )
                citation.end_page_number = getattr(citation_obj, "end_page_number", 0)
            elif citation_type == "content_block_location":
                citation.start_block_index = getattr(
                    citation_obj, "start_block_index", 0
                )
                citation.end_block_index = getattr(citation_obj, "end_block_index", 0)

            citations.append(citation)

        return citations


class PerplexityCitationHandler(BaseCitationHandler):
    """Citation handler for Perplexity API responses.

    Perplexity provides URL-based citations that should be displayed
    as annotation chunks after streaming completes.
    """

    def extract_citations(self, delta: Any) -> list[Citation]:
        """Extract citations from Perplexity response.

        Args:
            delta: Perplexity response with citations attribute

        Returns:
            List of Citation objects with URLs
        """
        citations = []

        raw_citations = getattr(delta, "citations", None)
        if not raw_citations:
            return citations

        citations.extend(
            Citation(url=url, document_title=url)
            for url in raw_citations
            if isinstance(url, str)
        )

        return citations

    async def yield_citation_chunks(
        self,
        citations: list[Citation] | list[str],
        processor_name: str,
    ) -> AsyncGenerator[Chunk, None]:
        """Yield citation chunks for Perplexity.

        Perplexity yields:
        1. A TEXT chunk with all citations in metadata (for accumulator)
        2. Individual ANNOTATION chunks for immediate display
        """
        if not citations:
            return

        logger.debug("Processing %d Perplexity citations", len(citations))

        # Convert to list of dicts for JSON
        citations_data = []
        for citation in citations:
            if isinstance(citation, str):
                citations_data.append({"url": citation, "document_title": citation})
            else:
                citations_data.append(
                    {
                        "url": citation.url,
                        "document_title": citation.document_title,
                    }
                )

        # Yield TEXT chunk with citations metadata for accumulator
        yield Chunk(
            type=ChunkType.TEXT,
            text="",  # Empty text, just carries citations metadata
            chunk_metadata={
                "citations": json.dumps(citations_data),
                "source": "perplexity",
                "processor": processor_name,
            },
        )

        # Yield individual ANNOTATION chunks for display
        for citation in citations:
            url = citation if isinstance(citation, str) else citation.url
            if url:
                yield Chunk(
                    type=ChunkType.ANNOTATION,
                    text=url,
                    chunk_metadata={
                        "url": url,
                        "source": "perplexity",
                        "processor": processor_name,
                    },
                )


class NullCitationHandler(BaseCitationHandler):
    """No-op citation handler for APIs without citation support.

    Use this for OpenAI and Gemini processors that don't have
    built-in citation extraction.
    """

    def extract_citations(self, delta: Any) -> list[Citation]:  # noqa: ARG002
        """Return empty list - no citation support.

        Args:
            delta: Ignored

        Returns:
            Empty list
        """
        return []

    async def yield_citation_chunks(
        self,
        citations: list[Citation] | list[str],  # noqa: ARG002
        processor_name: str,  # noqa: ARG002
    ) -> AsyncGenerator[Chunk, None]:
        """Yield nothing - no citation support."""
        return
        yield  # Make this a generator  # noqa: B901
