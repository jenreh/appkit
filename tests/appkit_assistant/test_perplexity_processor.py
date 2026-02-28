# ruff: noqa: ARG002, SLF001, S105, S106
"""Tests for PerplexityProcessor.

Covers init, process validation, payload building, citation formatting,
streaming/non-streaming response handling, and citation annotation yielding.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from appkit_assistant.backend.models.perplexity import PerplexityAIModel
from appkit_assistant.backend.processors.perplexity_processor import (
    PerplexityProcessor,
)
from appkit_assistant.backend.schemas import ChunkType, Message, MessageType

_PATCH = "appkit_assistant.backend.processors.perplexity_processor"
_OAI_BASE_PATCH = "appkit_assistant.backend.processors.openai_base"


def _model(model_id: str = "sonar", stream: bool = True) -> PerplexityAIModel:
    return PerplexityAIModel(
        id=model_id,
        text=model_id,
        model=model_id,
        stream=stream,
        temperature=0.7,
    )


def _make_processor(
    api_key: str = "pplx-test",
    models: dict[str, PerplexityAIModel] | None = None,
) -> PerplexityProcessor:
    if models is None:
        models = {"sonar": _model(), "sonar-sync": _model("sonar-sync", stream=False)}
    with patch(f"{_OAI_BASE_PATCH}.AsyncOpenAI") as mock_cls:
        mock_cls.return_value = MagicMock()
        return PerplexityProcessor(api_key=api_key, models=models)


def _msgs() -> list[Message]:
    return [
        Message(type=MessageType.HUMAN, text="Hello"),
        Message(type=MessageType.ASSISTANT, text="Hi"),
        Message(type=MessageType.HUMAN, text="Search something"),
    ]


# ============================================================================
# Initialization
# ============================================================================


class TestInitialization:
    def test_basic_init(self) -> None:
        proc = _make_processor()
        assert proc.base_url == "https://api.perplexity.ai"
        assert proc.client is not None
        assert proc._chunk_factory is not None

    def test_no_api_key(self) -> None:
        with patch(f"{_OAI_BASE_PATCH}.AsyncOpenAI"):
            proc = PerplexityProcessor(api_key=None, models={"s": _model()})
        assert proc.client is None

    def test_get_supported_models(self) -> None:
        proc = _make_processor()
        assert "sonar" in proc.get_supported_models()


# ============================================================================
# process() validation
# ============================================================================


class TestProcessValidation:
    @pytest.mark.asyncio
    async def test_no_client_raises(self) -> None:
        with patch(f"{_OAI_BASE_PATCH}.AsyncOpenAI"):
            proc = PerplexityProcessor(api_key=None, models={"s": _model()})
        with pytest.raises(ValueError, match="not initialized"):
            async for _ in proc.process(_msgs(), "sonar"):
                pass

    @pytest.mark.asyncio
    async def test_unsupported_model_raises(self) -> None:
        proc = _make_processor()
        with pytest.raises(ValueError, match="not supported"):
            async for _ in proc.process(_msgs(), "nonexistent"):
                pass

    @pytest.mark.asyncio
    async def test_mcp_servers_logs_warning(self) -> None:
        proc = _make_processor()
        server = MagicMock()

        # Must look like AsyncStream for isinstance check
        mock_stream = AsyncMock()
        mock_stream.__aiter__ = MagicMock(return_value=iter([]))

        async def _fake_create(**_kwargs):
            return mock_stream

        with (
            patch.object(
                proc.client.chat.completions,
                "create",
                side_effect=_fake_create,
            ),
            patch(f"{_PATCH}.logger") as mock_logger,
        ):
            # Model "sonar" has stream=True but we return a non-AsyncStream
            # so it goes to non-streaming path. Just verify warning logged.
            try:
                async for _ in proc.process(_msgs(), "sonar", mcp_servers=[server]):
                    pass
            except Exception:  # noqa: BLE001, S110
                pass
            mock_logger.warning.assert_called()


# ============================================================================
# _build_perplexity_payload
# ============================================================================


class TestBuildPerplexityPayload:
    def test_default_payload(self) -> None:
        proc = _make_processor()
        model = _model()
        payload = proc._build_perplexity_payload(model, None)
        assert payload["return_images"] is True
        assert payload["return_related_questions"] is True
        assert "web_search_options" in payload
        assert payload["search_domain_filter"] == []

    def test_custom_search_domain(self) -> None:
        proc = _make_processor()
        model = _model()
        model.search_domain_filter = ["example.com"]
        payload = proc._build_perplexity_payload(model, None)
        assert payload["search_domain_filter"] == ["example.com"]

    def test_payload_merge(self) -> None:
        proc = _make_processor()
        model = _model()
        extra = {"custom_key": "value"}
        payload = proc._build_perplexity_payload(model, extra)
        assert payload["custom_key"] == "value"

    def test_payload_override(self) -> None:
        proc = _make_processor()
        model = _model()
        extra = {"return_images": False}
        payload = proc._build_perplexity_payload(model, extra)
        assert payload["return_images"] is False


# ============================================================================
# _format_citations
# ============================================================================


class TestFormatCitations:
    def test_replaces_citations(self) -> None:
        proc = _make_processor()
        text = "According to [1] and [2]."
        citations = ["https://a.com", "https://b.com"]
        result = proc._format_citations(text, citations)
        assert "[[1]](https://a.com)" in result
        assert "[[2]](https://b.com)" in result

    def test_out_of_range_citation(self) -> None:
        proc = _make_processor()
        text = "See [5]."
        citations = ["https://a.com"]
        result = proc._format_citations(text, citations)
        assert result == "See [5]."

    def test_no_citations(self) -> None:
        proc = _make_processor()
        text = "No citations here."
        result = proc._format_citations(text, [])
        assert result == "No citations here."

    def test_invalid_citation_zero(self) -> None:
        proc = _make_processor()
        text = "Check [0] reference."
        citations = ["https://a.com"]
        result = proc._format_citations(text, citations)
        assert result == "Check [0] reference."


# ============================================================================
# _process_streaming_response
# ============================================================================


class TestProcessStreamingResponse:
    @pytest.mark.asyncio
    async def test_basic_streaming(self) -> None:
        proc = _make_processor()
        proc._reset_statistics("sonar")

        events = [
            SimpleNamespace(
                choices=[SimpleNamespace(delta=SimpleNamespace(content="Hello "))],
                citations=None,
                usage=None,
                id="resp1",
            ),
            SimpleNamespace(
                choices=[SimpleNamespace(delta=SimpleNamespace(content="World"))],
                citations=["https://a.com"],
                usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5),
                id="resp1",
            ),
        ]

        async def mock_aiter():
            for e in events:
                yield e

        model = _model()
        chunks = [
            c async for c in proc._process_streaming_response(mock_aiter(), model, None)
        ]

        text_chunks = [c for c in chunks if c.type == ChunkType.TEXT]
        assert len(text_chunks) >= 2
        completions = [c for c in chunks if c.type == ChunkType.COMPLETION]
        assert len(completions) == 1
        assert completions[0].statistics is not None
        annotations = [c for c in chunks if c.type == ChunkType.ANNOTATION]
        assert len(annotations) == 1

    @pytest.mark.asyncio
    async def test_streaming_with_cancellation(self) -> None:
        proc = _make_processor()
        proc._reset_statistics("sonar")
        cancel = asyncio.Event()
        cancel.set()

        events = [
            SimpleNamespace(
                choices=[SimpleNamespace(delta=SimpleNamespace(content="Hi"))],
                citations=None,
                usage=None,
                id="r1",
            ),
        ]

        async def mock_aiter():
            for e in events:
                yield e

        model = _model()
        chunks = [
            c
            async for c in proc._process_streaming_response(mock_aiter(), model, cancel)
        ]
        completions = [c for c in chunks if c.type == ChunkType.COMPLETION]
        assert len(completions) == 1

    @pytest.mark.asyncio
    async def test_streaming_empty_content_skipped(self) -> None:
        proc = _make_processor()
        proc._reset_statistics("sonar")

        events = [
            SimpleNamespace(
                choices=[SimpleNamespace(delta=SimpleNamespace(content=None))],
                citations=None,
                usage=None,
                id="r1",
            ),
            SimpleNamespace(
                choices=[SimpleNamespace(delta=SimpleNamespace(content=""))],
                citations=None,
                usage=None,
                id="r1",
            ),
        ]

        async def mock_aiter():
            for e in events:
                yield e

        model = _model()
        chunks = [
            c async for c in proc._process_streaming_response(mock_aiter(), model, None)
        ]
        text_chunks = [c for c in chunks if c.type == ChunkType.TEXT]
        assert len(text_chunks) == 0

    @pytest.mark.asyncio
    async def test_streaming_no_choices(self) -> None:
        proc = _make_processor()
        proc._reset_statistics("sonar")

        async def mock_aiter():
            yield SimpleNamespace(choices=[], citations=None, usage=None, id="r1")

        model = _model()
        chunks = [
            c async for c in proc._process_streaming_response(mock_aiter(), model, None)
        ]
        text_chunks = [c for c in chunks if c.type == ChunkType.TEXT]
        assert len(text_chunks) == 0

    @pytest.mark.asyncio
    async def test_citation_formatting_in_stream(self) -> None:
        proc = _make_processor()
        proc._reset_statistics("sonar")

        async def mock_aiter():
            yield SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        delta=SimpleNamespace(content="See [1] for details")
                    )
                ],
                citations=["https://example.com"],
                usage=None,
                id="r1",
            )

        model = _model()
        chunks = [
            c async for c in proc._process_streaming_response(mock_aiter(), model, None)
        ]
        text_chunks = [c for c in chunks if c.type == ChunkType.TEXT]
        assert any("[[1]](https://example.com)" in c.text for c in text_chunks)


# ============================================================================
# _process_non_streaming_response
# ============================================================================


class TestProcessNonStreamingResponse:
    @pytest.mark.asyncio
    async def test_basic_non_streaming(self) -> None:
        proc = _make_processor()
        proc._reset_statistics("sonar")

        session = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="Result"))],
            citations=["https://cite.com"],
            usage=SimpleNamespace(prompt_tokens=15, completion_tokens=20),
            id="resp-1",
        )

        model = _model("sonar-sync", stream=False)
        chunks = [c async for c in proc._process_non_streaming_response(session, model)]

        text_chunks = [c for c in chunks if c.type == ChunkType.TEXT]
        assert len(text_chunks) == 1
        annotations = [c for c in chunks if c.type == ChunkType.ANNOTATION]
        assert len(annotations) == 1
        completions = [c for c in chunks if c.type == ChunkType.COMPLETION]
        assert len(completions) == 1

    @pytest.mark.asyncio
    async def test_no_citations(self) -> None:
        proc = _make_processor()
        proc._reset_statistics("sonar")

        session = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="plain"))],
            usage=SimpleNamespace(prompt_tokens=5, completion_tokens=10),
            id="resp-2",
        )

        model = _model("sonar-sync", stream=False)
        chunks = [c async for c in proc._process_non_streaming_response(session, model)]
        annotations = [c for c in chunks if c.type == ChunkType.ANNOTATION]
        assert len(annotations) == 0

    @pytest.mark.asyncio
    async def test_no_content(self) -> None:
        proc = _make_processor()
        proc._reset_statistics("sonar")

        session = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=None))],
            usage=SimpleNamespace(prompt_tokens=5, completion_tokens=0),
            id="resp-3",
        )

        model = _model("sonar-sync", stream=False)
        chunks = [c async for c in proc._process_non_streaming_response(session, model)]
        text_chunks = [c for c in chunks if c.type == ChunkType.TEXT]
        assert len(text_chunks) == 0

    @pytest.mark.asyncio
    async def test_citations_formatted_in_content(self) -> None:
        proc = _make_processor()
        proc._reset_statistics("sonar")

        session = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="Ref [1] here"))],
            citations=["https://ref.com"],
            usage=SimpleNamespace(prompt_tokens=5, completion_tokens=10),
            id="resp-4",
        )

        model = _model("sonar-sync", stream=False)
        chunks = [c async for c in proc._process_non_streaming_response(session, model)]
        text_chunks = [c for c in chunks if c.type == ChunkType.TEXT]
        assert any("[[1]](https://ref.com)" in c.text for c in text_chunks)


# ============================================================================
# _yield_citations
# ============================================================================


class TestYieldCitations:
    @pytest.mark.asyncio
    async def test_no_citations(self) -> None:
        proc = _make_processor()
        chunks = [c async for c in proc._yield_citations([])]
        assert len(chunks) == 0

    @pytest.mark.asyncio
    async def test_multiple_citations(self) -> None:
        proc = _make_processor()
        citations = ["https://a.com", "https://b.com", "https://c.com"]
        chunks = [c async for c in proc._yield_citations(citations)]
        assert len(chunks) == 3
        for i, c in enumerate(chunks):
            assert c.type == ChunkType.ANNOTATION
            assert c.chunk_metadata["url"] == citations[i]
            assert c.chunk_metadata["source"] == "perplexity"
            assert c.chunk_metadata["index"] == str(i + 1)


# ============================================================================
# Full process() flow (streaming)
# ============================================================================


class TestProcessFlowStreaming:
    @pytest.mark.asyncio
    async def test_streaming_flow(self) -> None:
        proc = _make_processor()

        events = [
            SimpleNamespace(
                choices=[SimpleNamespace(delta=SimpleNamespace(content="Answer"))],
                citations=["https://src.com"],
                usage=SimpleNamespace(prompt_tokens=10, completion_tokens=20),
                id="s1",
            ),
        ]

        async def mock_aiter():
            for e in events:
                yield e

        mock_stream = mock_aiter()

        # Patch AsyncStream so isinstance(mock_stream, AsyncStream) → True
        with patch(
            f"{_PATCH}.AsyncStream",
            new=type(mock_stream),
        ):
            proc.client.chat.completions.create = AsyncMock(return_value=mock_stream)
            chunks = [c async for c in proc.process(_msgs(), "sonar")]

        types_found = {c.type for c in chunks}
        assert ChunkType.TEXT in types_found
        assert ChunkType.COMPLETION in types_found
        assert ChunkType.ANNOTATION in types_found

    @pytest.mark.asyncio
    async def test_process_error_propagates(self) -> None:
        proc = _make_processor()
        proc.client.chat.completions.create = AsyncMock(
            side_effect=RuntimeError("API error")
        )
        with pytest.raises(RuntimeError, match="API error"):
            async for _ in proc.process(_msgs(), "sonar"):
                pass


# ============================================================================
# Full process() flow (non-streaming)
# ============================================================================


class TestProcessFlowNonStreaming:
    @pytest.mark.asyncio
    async def test_non_streaming_flow(self) -> None:
        proc = _make_processor()

        session = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="Result"))],
            citations=["https://ref.com"],
            usage=SimpleNamespace(prompt_tokens=5, completion_tokens=10),
            id="ns-1",
        )
        proc.client.chat.completions.create = AsyncMock(return_value=session)

        chunks = [c async for c in proc.process(_msgs(), "sonar-sync")]
        types_found = {c.type for c in chunks}
        assert ChunkType.TEXT in types_found
        assert ChunkType.COMPLETION in types_found
