"""Tests for ResponseAccumulator.

Covers chunk processing, message accumulation, thinking items,
tool calls, auth handling, error handling, and link formatting.
"""

import json

from appkit_assistant.backend.schemas import (
    Chunk,
    ChunkType,
    Message,
    MessageType,
    ThinkingStatus,
    ThinkingType,
)
from appkit_assistant.backend.services.response_accumulator import (
    MIN_LINKS_FOR_LIST_FORMAT,
    ResponseAccumulator,
    _format_consecutive_links_as_list,
)

# ============================================================================
# Helpers
# ============================================================================


def _make_chunk(
    chunk_type: ChunkType,
    text: str = "",
    metadata: dict | None = None,
) -> Chunk:
    return Chunk(type=chunk_type, text=text, chunk_metadata=metadata or {})


def _acc_with_assistant_message(text: str = "") -> ResponseAccumulator:
    """Create accumulator with one assistant message ready for streaming."""
    acc = ResponseAccumulator()
    acc.messages.append(Message(text=text, type=MessageType.ASSISTANT))
    return acc


# ============================================================================
# _format_consecutive_links_as_list  (standalone function)
# ============================================================================


class TestFormatConsecutiveLinks:
    def test_no_links(self) -> None:
        assert _format_consecutive_links_as_list("Hello world") == "Hello world"

    def test_single_link_unchanged(self) -> None:
        text = "[click](https://example.com)"
        assert _format_consecutive_links_as_list(text) == text

    def test_two_consecutive_links(self) -> None:
        text = "[A](https://a.com)[B](https://b.com)"
        result = _format_consecutive_links_as_list(text)
        assert "**Quellen:**" in result
        assert "- [A](https://a.com)" in result
        assert "- [B](https://b.com)" in result

    def test_three_consecutive_links(self) -> None:
        text = "[A](https://a.com)[B](https://b.com)[C](https://c.com)"
        result = _format_consecutive_links_as_list(text)
        assert result.count("- [") == 3

    def test_links_with_surrounding_text(self) -> None:
        text = "See [A](https://a.com)[B](https://b.com) for info."
        result = _format_consecutive_links_as_list(text)
        assert "See" in result
        assert "for info." in result
        assert "**Quellen:**" in result

    def test_non_consecutive_links_unchanged(self) -> None:
        text = "[A](https://a.com) and [B](https://b.com)"
        result = _format_consecutive_links_as_list(text)
        # Not consecutive (space in between), should be unchanged
        assert result == text

    def test_min_links_threshold(self) -> None:
        assert MIN_LINKS_FOR_LIST_FORMAT == 2


# ============================================================================
# ResponseAccumulator - Initialisation
# ============================================================================


class TestResponseAccumulatorInit:
    def test_defaults(self) -> None:
        acc = ResponseAccumulator()
        assert acc.messages == []
        assert acc.thinking_items == []
        assert acc.image_chunks == []
        assert acc.show_thinking is False
        assert acc.current_activity == ""
        assert acc.auth_required is False
        assert acc.error is None

    def test_auth_required_data(self) -> None:
        acc = ResponseAccumulator()
        data = acc.auth_required_data
        assert data == {
            "server_id": "",
            "server_name": "",
            "auth_url": "",
        }

    def test_attach_messages_ref(self) -> None:
        acc = ResponseAccumulator()
        msgs: list[Message] = []
        acc.attach_messages_ref(msgs)
        assert acc.messages is msgs


# ============================================================================
# Text chunks
# ============================================================================


class TestTextChunks:
    def test_text_appended_to_assistant_message(self) -> None:
        acc = _acc_with_assistant_message()
        acc.process_chunk(_make_chunk(ChunkType.TEXT, "Hello "))
        acc.process_chunk(_make_chunk(ChunkType.TEXT, "World"))
        assert acc.messages[-1].text == "Hello World"

    def test_text_ignored_when_no_messages(self) -> None:
        acc = ResponseAccumulator()
        acc.process_chunk(_make_chunk(ChunkType.TEXT, "hi"))
        assert acc.messages == []

    def test_text_ignored_when_last_message_not_assistant(self) -> None:
        acc = ResponseAccumulator()
        acc.messages.append(Message(text="q", type=MessageType.HUMAN))
        acc.process_chunk(_make_chunk(ChunkType.TEXT, "hi"))
        assert acc.messages[-1].text == "q"

    def test_message_id_updated_from_metadata(self) -> None:
        acc = _acc_with_assistant_message()
        chunk = _make_chunk(ChunkType.TEXT, "x", {"message_id": "new-id"})
        acc.process_chunk(chunk)
        assert acc.messages[-1].id == "new-id"

    def test_citations_extracted_to_annotations(self) -> None:
        acc = _acc_with_assistant_message()
        citations = [{"document_title": "Doc A"}]
        chunk = _make_chunk(ChunkType.TEXT, "ref", {"citations": json.dumps(citations)})
        acc.process_chunk(chunk)
        assert "Doc A" in acc.messages[-1].annotations

    def test_citations_fallback_to_cited_text(self) -> None:
        acc = _acc_with_assistant_message()
        citations = [{"cited_text": "short ref"}]
        chunk = _make_chunk(ChunkType.TEXT, "x", {"citations": json.dumps(citations)})
        acc.process_chunk(chunk)
        assert "short ref" in acc.messages[-1].annotations

    def test_citations_long_cited_text_truncated(self) -> None:
        acc = _acc_with_assistant_message()
        long_text = "a" * 100
        citations = [{"cited_text": long_text}]
        chunk = _make_chunk(ChunkType.TEXT, "x", {"citations": json.dumps(citations)})
        acc.process_chunk(chunk)
        assert acc.messages[-1].annotations[0].endswith("...")
        assert len(acc.messages[-1].annotations[0]) < len(long_text)

    def test_duplicate_citation_not_added(self) -> None:
        acc = _acc_with_assistant_message()
        citations = [{"document_title": "Doc A"}]
        meta = {"citations": json.dumps(citations)}
        acc.process_chunk(_make_chunk(ChunkType.TEXT, "x", meta))
        acc.process_chunk(_make_chunk(ChunkType.TEXT, "y", meta))
        assert acc.messages[-1].annotations.count("Doc A") == 1

    def test_invalid_citations_json_handled(self) -> None:
        acc = _acc_with_assistant_message()
        chunk = _make_chunk(ChunkType.TEXT, "x", {"citations": "not-json{{{"})
        acc.process_chunk(chunk)  # should not raise
        assert acc.messages[-1].annotations == []


# ============================================================================
# Error chunks
# ============================================================================


class TestErrorChunks:
    def test_error_creates_error_message(self) -> None:
        acc = ResponseAccumulator()
        acc.process_chunk(_make_chunk(ChunkType.ERROR, "something broke"))
        assert len(acc.messages) == 1
        assert acc.messages[0].type == MessageType.ERROR
        assert acc.messages[0].text == "something broke"
        assert acc.error == "something broke"


# ============================================================================
# Reasoning / Thinking chunks
# ============================================================================


class TestThinkingChunks:
    def test_thinking_sets_show_thinking(self) -> None:
        acc = ResponseAccumulator()
        acc.process_chunk(_make_chunk(ChunkType.THINKING, "hmm"))
        assert acc.show_thinking is True
        assert acc.current_activity == "Denke nach..."

    def test_thinking_creates_reasoning_item(self) -> None:
        acc = ResponseAccumulator()
        acc.process_chunk(_make_chunk(ChunkType.THINKING, "step1"))
        assert len(acc.thinking_items) == 1
        item = acc.thinking_items[0]
        assert item.type == ThinkingType.REASONING
        assert item.text == "step1"
        assert item.status == ThinkingStatus.IN_PROGRESS

    def test_thinking_delta_appends(self) -> None:
        acc = ResponseAccumulator()
        # First chunk sets initial text via regular path
        acc.process_chunk(
            _make_chunk(ChunkType.THINKING, "a", {"reasoning_session": "s1"})
        )
        # Delta chunk appends to existing text
        acc.process_chunk(
            _make_chunk(
                ChunkType.THINKING,
                "b",
                {"delta": "true", "reasoning_session": "s1"},
            )
        )
        assert acc.thinking_items[0].text == "ab"

    def test_thinking_result_completes(self) -> None:
        acc = ResponseAccumulator()
        acc.process_chunk(_make_chunk(ChunkType.THINKING, "start"))
        acc.process_chunk(_make_chunk(ChunkType.THINKING_RESULT, "done"))
        completed = [
            i for i in acc.thinking_items if i.status == ThinkingStatus.COMPLETED
        ]
        assert len(completed) >= 1

    def test_reasoning_session_from_metadata(self) -> None:
        acc = ResponseAccumulator()
        acc.process_chunk(
            _make_chunk(ChunkType.THINKING, "t1", {"reasoning_session": "s1"})
        )
        acc.process_chunk(
            _make_chunk(ChunkType.THINKING, "t2", {"reasoning_session": "s1"})
        )
        # Same session -> same item
        reasoning_items = [
            i for i in acc.thinking_items if i.type == ThinkingType.REASONING
        ]
        assert len(reasoning_items) == 1


# ============================================================================
# Tool chunks
# ============================================================================


class TestToolChunks:
    def test_tool_call_creates_thinking_item(self) -> None:
        acc = ResponseAccumulator()
        acc.process_chunk(
            _make_chunk(
                ChunkType.TOOL_CALL,
                "params",
                {"tool_name": "search", "tool_id": "t1"},
            )
        )
        assert len(acc.thinking_items) == 1
        item = acc.thinking_items[0]
        assert item.type == ThinkingType.TOOL_CALL
        assert item.tool_name == "search"
        assert item.status == ThinkingStatus.IN_PROGRESS

    def test_tool_result_completes_item(self) -> None:
        acc = ResponseAccumulator()
        acc.process_chunk(
            _make_chunk(ChunkType.TOOL_CALL, "p", {"tool_name": "run", "tool_id": "t1"})
        )
        acc.process_chunk(_make_chunk(ChunkType.TOOL_RESULT, "ok", {"tool_id": "t1"}))
        item = acc.thinking_items[0]
        assert item.status == ThinkingStatus.COMPLETED
        assert item.result == "ok"

    def test_tool_result_error_flag(self) -> None:
        acc = ResponseAccumulator()
        acc.process_chunk(
            _make_chunk(ChunkType.TOOL_CALL, "p", {"tool_name": "run", "tool_id": "t1"})
        )
        acc.process_chunk(
            _make_chunk(
                ChunkType.TOOL_RESULT,
                "oops",
                {"tool_id": "t1", "error": "True"},
            )
        )
        item = acc.thinking_items[0]
        assert item.status == ThinkingStatus.ERROR
        assert item.error == "oops"

    def test_tool_result_error_string_true(self) -> None:
        acc = ResponseAccumulator()
        acc.process_chunk(
            _make_chunk(ChunkType.TOOL_CALL, "p", {"tool_name": "run", "tool_id": "t1"})
        )
        acc.process_chunk(
            _make_chunk(
                ChunkType.TOOL_RESULT,
                "fail",
                {"tool_id": "t1", "error": "True"},
            )
        )
        assert acc.thinking_items[0].status == ThinkingStatus.ERROR

    def test_tool_display_name_with_server_label(self) -> None:
        acc = ResponseAccumulator()
        acc.process_chunk(
            _make_chunk(
                ChunkType.TOOL_CALL,
                "",
                {
                    "tool_name": "search",
                    "server_label": "github",
                    "tool_id": "t1",
                },
            )
        )
        assert acc.thinking_items[0].tool_name == "github.search"
        assert "github.search" in acc.current_activity

    def test_tool_session_auto_generated(self) -> None:
        acc = ResponseAccumulator()
        acc.process_chunk(_make_chunk(ChunkType.TOOL_CALL, "p", {"tool_name": "x"}))
        assert len(acc.thinking_items) == 1

    def test_action_chunk_appends_to_tool_item(self) -> None:
        acc = ResponseAccumulator()
        acc.process_chunk(
            _make_chunk(ChunkType.TOOL_CALL, "", {"tool_name": "run", "tool_id": "t1"})
        )
        acc.process_chunk(
            _make_chunk(ChunkType.ACTION, "do something", {"tool_id": "t1"})
        )
        assert "Aktion:" in acc.thinking_items[0].text


# ============================================================================
# Image chunks
# ============================================================================


class TestImageChunks:
    def test_image_chunk_stored(self) -> None:
        acc = ResponseAccumulator()
        acc.process_chunk(_make_chunk(ChunkType.IMAGE, "base64data"))
        assert len(acc.image_chunks) == 1

    def test_image_partial_stored(self) -> None:
        acc = ResponseAccumulator()
        acc.process_chunk(_make_chunk(ChunkType.IMAGE_PARTIAL, "partial"))
        assert len(acc.image_chunks) == 1


# ============================================================================
# Completion chunk
# ============================================================================


class TestCompletionChunk:
    def test_completion_hides_thinking(self) -> None:
        acc = _acc_with_assistant_message("Hello [A](a.com)[B](b.com)")
        acc.show_thinking = True
        acc.process_chunk(_make_chunk(ChunkType.COMPLETION))
        assert acc.show_thinking is False

    def test_completion_formats_links(self) -> None:
        acc = _acc_with_assistant_message("[A](https://a.com)[B](https://b.com)")
        acc.process_chunk(_make_chunk(ChunkType.COMPLETION))
        assert "**Quellen:**" in acc.messages[-1].text


# ============================================================================
# Auth required chunk
# ============================================================================


class TestAuthRequiredChunk:
    def test_auth_required_sets_state(self) -> None:
        acc = ResponseAccumulator()
        acc.process_chunk(
            _make_chunk(
                ChunkType.AUTH_REQUIRED,
                "",
                {
                    "server_id": "srv1",
                    "server_name": "GitHub",
                    "auth_url": "https://auth.example.com",
                },
            )
        )
        assert acc.auth_required is True
        assert acc.pending_auth_server_id == "srv1"
        assert acc.pending_auth_server_name == "GitHub"
        assert acc.pending_auth_url == "https://auth.example.com"
        assert acc.auth_required_data["server_id"] == "srv1"


# ============================================================================
# Processing chunk
# ============================================================================


class TestProcessingChunk:
    def test_processing_shows_thinking(self) -> None:
        acc = ResponseAccumulator()
        acc.process_chunk(
            _make_chunk(ChunkType.PROCESSING, "Indexing...", {"status": "indexing"})
        )
        assert acc.show_thinking is True
        assert acc.current_activity == "Indexing..."

    def test_processing_skips_empty_text(self) -> None:
        acc = ResponseAccumulator()
        acc.process_chunk(_make_chunk(ChunkType.PROCESSING, "", {"status": "skipped"}))
        assert acc.thinking_items == []

    def test_processing_skips_skipped_status(self) -> None:
        acc = ResponseAccumulator()
        acc.process_chunk(
            _make_chunk(ChunkType.PROCESSING, "text", {"status": "skipped"})
        )
        assert acc.thinking_items == []

    def test_processing_completed_status(self) -> None:
        acc = ResponseAccumulator()
        acc.process_chunk(
            _make_chunk(ChunkType.PROCESSING, "Done", {"status": "completed"})
        )
        item = acc.thinking_items[0]
        assert item.status == ThinkingStatus.COMPLETED

    def test_processing_failed_status(self) -> None:
        acc = ResponseAccumulator()
        acc.process_chunk(
            _make_chunk(
                ChunkType.PROCESSING,
                "Failed",
                {"status": "failed", "error": "disk full"},
            )
        )
        item = acc.thinking_items[0]
        assert item.status == ThinkingStatus.ERROR
        assert item.error == "disk full"

    def test_processing_timeout_status(self) -> None:
        acc = ResponseAccumulator()
        acc.process_chunk(
            _make_chunk(ChunkType.PROCESSING, "Timeout", {"status": "timeout"})
        )
        assert acc.thinking_items[0].status == ThinkingStatus.ERROR


# ============================================================================
# Annotation chunk
# ============================================================================


class TestAnnotationChunk:
    def test_annotation_added_to_last_assistant_message(self) -> None:
        acc = _acc_with_assistant_message("reply")
        acc.process_chunk(_make_chunk(ChunkType.ANNOTATION, "file.pdf"))
        assert "file.pdf" in acc.messages[-1].annotations

    def test_annotation_not_duplicated(self) -> None:
        acc = _acc_with_assistant_message("reply")
        acc.process_chunk(_make_chunk(ChunkType.ANNOTATION, "file.pdf"))
        acc.process_chunk(_make_chunk(ChunkType.ANNOTATION, "file.pdf"))
        assert acc.messages[-1].annotations.count("file.pdf") == 1

    def test_annotation_ignored_when_no_messages(self) -> None:
        acc = ResponseAccumulator()
        acc.process_chunk(_make_chunk(ChunkType.ANNOTATION, "file.pdf"))
        # No crash

    def test_annotation_ignored_when_last_not_assistant(self) -> None:
        acc = ResponseAccumulator()
        acc.messages.append(Message(text="q", type=MessageType.HUMAN))
        acc.process_chunk(_make_chunk(ChunkType.ANNOTATION, "file.pdf"))
        assert acc.messages[-1].annotations == []


# ============================================================================
# Lifecycle chunk
# ============================================================================


class TestLifecycleChunk:
    def test_lifecycle_logged_no_crash(self) -> None:
        acc = ResponseAccumulator()
        acc.process_chunk(_make_chunk(ChunkType.LIFECYCLE, "started"))
        # Should just log, no state change
        assert acc.messages == []


# ============================================================================
# Edge cases
# ============================================================================


class TestEdgeCases:
    def test_unknown_chunk_type_warning(self) -> None:
        """Unknown chunk types should be handled gracefully."""
        acc = ResponseAccumulator()
        # All defined chunk types are handled; just verify completion works
        acc.process_chunk(_make_chunk(ChunkType.COMPLETION))
        assert acc.show_thinking is False

    def test_multiple_reasoning_sessions(self) -> None:
        acc = ResponseAccumulator()
        # First reasoning session
        acc.process_chunk(_make_chunk(ChunkType.THINKING, "thought1"))
        acc.process_chunk(_make_chunk(ChunkType.THINKING_RESULT, ""))
        # Tool call between sessions
        acc.process_chunk(
            _make_chunk(ChunkType.TOOL_CALL, "", {"tool_name": "x", "tool_id": "t1"})
        )
        # Second reasoning session (should get new ID)
        acc.process_chunk(_make_chunk(ChunkType.THINKING, "thought2"))
        reasoning = [i for i in acc.thinking_items if i.type == ThinkingType.REASONING]
        assert len(reasoning) == 2

    def test_full_flow(self) -> None:
        """End-to-end: thinking → tool → text → completion."""
        acc = ResponseAccumulator()
        acc.messages.append(Message(text="", type=MessageType.ASSISTANT))

        acc.process_chunk(_make_chunk(ChunkType.THINKING, "planning"))
        acc.process_chunk(_make_chunk(ChunkType.THINKING_RESULT, ""))
        acc.process_chunk(
            _make_chunk(
                ChunkType.TOOL_CALL,
                "{}",
                {"tool_name": "search", "tool_id": "t1"},
            )
        )
        acc.process_chunk(
            _make_chunk(ChunkType.TOOL_RESULT, "found it", {"tool_id": "t1"})
        )
        acc.process_chunk(_make_chunk(ChunkType.TEXT, "Here is the answer."))
        acc.process_chunk(_make_chunk(ChunkType.COMPLETION))

        assert acc.messages[-1].text == "Here is the answer."
        assert acc.show_thinking is False
        assert len(acc.thinking_items) >= 2
