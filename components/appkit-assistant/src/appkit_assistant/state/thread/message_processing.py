"""Message processing mixin for ThreadState.

Core message submission, streaming, batching, and persistence pipeline.
"""

import asyncio
import logging
import re
import time
from collections.abc import AsyncGenerator
from typing import Any

import reflex as rx

from appkit_assistant.backend.database.models import (
    MCPServer,
    ThreadStatus,
)
from appkit_assistant.backend.database.repositories import (
    user_prompt_repo,
)
from appkit_assistant.backend.model_manager import ModelManager
from appkit_assistant.backend.schemas import (
    Chunk,
    ChunkType,
    Message,
    MessageType,
)
from appkit_assistant.backend.services import file_manager
from appkit_assistant.backend.services.response_accumulator import (
    ResponseAccumulator,
)
from appkit_assistant.backend.services.thread_service import ThreadService
from appkit_assistant.state.thread_list_state import ThreadListState
from appkit_commons.database.session import get_asyncdb_session
from appkit_user.authentication.states import UserSession

logger = logging.getLogger(__name__)

# Minimum interval between UI state flushes during streaming
_FLUSH_INTERVAL_S = 0.1  # 100 ms


class MessageProcessingMixin:
    """Mixin for message submission, streaming, and persistence.

    Expects state vars: ``processing``, ``cancellation_requested``,
    ``messages``, ``prompt``, ``thinking_items``, ``image_chunks``,
    ``show_thinking``, ``current_activity``, ``uploaded_files``,
    ``selected_mcp_servers``, ``selected_skills``, ``web_search_enabled``,
    ``with_thread_list``, ``_thread``, ``_skip_user_message``,
    ``_pending_file_cleanup``, ``_cancel_event``, ``_current_user_id``.
    """

    @rx.event(background=True)
    async def submit_message(self) -> AsyncGenerator[Any, Any]:
        """Submit a message and process the response."""
        yield rx.call_script("""
            const textarea = document.getElementById('composer-area');
            if (textarea) {
                textarea.value = '';
                textarea.style.height = 'auto';
                textarea.style.height = textarea.scrollHeight + 'px';
            }
        """)
        await self._process_message()

    @rx.event
    def request_cancellation(self) -> None:
        """Signal that the current processing should be cancelled."""
        self.cancellation_requested = True
        if self._cancel_event:
            self._cancel_event.set()
            logger.info("Cancellation requested by user")

    # ------------------------------------------------------------------
    # Core pipeline
    # ------------------------------------------------------------------

    async def _process_message(self) -> None:
        """Process the current message and stream the response.

        Uses time-based batching to reduce state lock contention:
        chunks are buffered and flushed to the UI periodically.
        """
        logger.debug("Processing message: %s", self.prompt)

        start = await self._begin_message_processing()
        if not start:
            return
        (
            current_prompt,
            selected_model,
            mcp_servers,
            file_paths,
            is_new_thread,
        ) = start

        processor = ModelManager().get_processor_for_model(selected_model)
        if not processor:
            await self._stop_processing_with_error(
                f"Keinen Adapter für das Modell gefunden: {selected_model}"
            )
            return

        async with self:
            user_session: UserSession = await self.get_state(UserSession)
            user_id = user_session.user.user_id if user_session.user else None

            logger.debug(
                "Pre-save check: is_new=%s, files=%d, user=%s",
                is_new_thread,
                len(file_paths) if file_paths else 0,
                user_id,
            )

            accumulator = ResponseAccumulator()
            accumulator.attach_messages_ref(self.messages)

            self.uploaded_files = []
            self._pending_file_cleanup = file_paths
            self._cancel_event = asyncio.Event()

        # Save thread to DB if new and has files
        if is_new_thread and file_paths and user_id:
            async with self:
                self._thread.state = ThreadStatus.ACTIVE
                self._thread.mcp_server_ids = [
                    s.id for s in self.selected_mcp_servers if s.id
                ]
                thread_copy = self._thread.model_copy()
            await ThreadService().save_thread(thread_copy, user_id)
            logger.debug(
                "Saved new thread %s to DB",
                thread_copy.thread_id,
            )

        first_response_received = False
        try:
            skill_ids = [s.openai_id for s in self.selected_skills]
            payload = {
                "thread_uuid": self._thread.thread_id,
                **({"web_search_enabled": True} if self.web_search_enabled else {}),
            }

            if skill_ids and self.selected_model_supports_skills:
                payload["skill_openai_ids"] = skill_ids

            chunk_buffer: list[Chunk] = []
            last_flush = time.monotonic()
            immediate_types = {
                ChunkType.COMPLETION,
                ChunkType.ERROR,
                ChunkType.AUTH_REQUIRED,
            }

            async for chunk in processor.process(
                self.messages,
                selected_model,
                files=file_paths or None,
                mcp_servers=mcp_servers,
                payload=payload,
                user_id=user_id,
                cancellation_token=self._cancel_event,
            ):
                chunk_buffer.append(chunk)

                now = time.monotonic()
                needs_flush = chunk.type in immediate_types or (
                    (now - last_flush) >= _FLUSH_INTERVAL_S
                )

                if needs_flush:
                    first_response_received = await self._flush_chunk_buffer(
                        chunks=chunk_buffer,
                        accumulator=accumulator,
                        current_prompt=current_prompt,
                        is_new_thread=is_new_thread,
                        first_response_received=(first_response_received),
                    )
                    chunk_buffer.clear()
                    last_flush = now

            # Flush remaining
            if chunk_buffer:
                first_response_received = await self._flush_chunk_buffer(
                    chunks=chunk_buffer,
                    accumulator=accumulator,
                    current_prompt=current_prompt,
                    is_new_thread=is_new_thread,
                    first_response_received=first_response_received,
                )

            await self._finalize_successful_response(accumulator)

        except Exception as ex:
            await self._handle_process_error(
                ex=ex,
                current_prompt=current_prompt,
                is_new_thread=is_new_thread,
                first_response_received=first_response_received,
            )

        finally:
            await self._finalize_processing()

    # ------------------------------------------------------------------
    # Prompt parsing
    # ------------------------------------------------------------------

    def _parse_prompt_segments(self, prompt: str) -> list[dict]:
        """Parse prompt into text and command segments.

        Identifies command patterns (/command_name) and splits text into
        segments of type ``"text"`` or ``"command"``.
        """
        segments: list[dict] = []
        pattern = r"(?:^|(?<=\s))/([a-zA-Z0-9-]+)"

        last_end = 0
        for match in re.finditer(pattern, prompt):
            text_before = prompt[last_end : match.start()].strip()
            if text_before:
                segments.append({"type": "text", "content": text_before})
            segments.append({"type": "command", "handle": match.group(1)})
            last_end = match.end()

        if last_end < len(prompt):
            text_after = prompt[last_end:].strip()
            if text_after:
                segments.append({"type": "text", "content": text_after})

        return segments

    async def _load_command_prompt_text(
        self, user_id: int, command_handle: str
    ) -> str | None:
        """Load the prompt text for a command from the database."""
        try:
            handle = command_handle.lstrip("/")
            async with get_asyncdb_session() as session:
                prompt = await user_prompt_repo.find_latest_accessible_by_handle(
                    session, user_id, handle
                )
                if prompt:
                    logger.debug(
                        "Loaded command prompt for handle '%s'",
                        handle,
                    )
                    return prompt.prompt_text

                logger.debug(
                    "Command prompt not found for handle '%s'",
                    handle,
                )
        except Exception as e:
            logger.error(
                "Error loading command prompt for %s: %s",
                command_handle,
                e,
            )
        return None

    async def _resolve_command_segments(
        self, segments: list[dict], user_id: int
    ) -> None:
        """Resolve command handles to text prompts from DB."""
        for segment in segments:
            if segment["type"] == "command":
                try:
                    text = await self._load_command_prompt_text(
                        user_id, segment["handle"]
                    )
                    segment["resolved_text"] = text
                    if text:
                        logger.debug(
                            "Resolved command %s to prompt text",
                            segment["handle"],
                        )
                    else:
                        logger.warning(
                            "Command %s not resolved for user %d",
                            segment["handle"],
                            user_id,
                        )
                except Exception as e:
                    logger.error(
                        "Error resolving command %s: %s",
                        segment["handle"],
                        e,
                    )

    def _create_user_messages(
        self,
        prompt: str,
        segments: list[dict],
        attachments: list[str],
    ) -> list[Message]:
        """Create message objects from parsed segments."""
        if not segments:
            return [
                Message(
                    text=prompt,
                    type=MessageType.HUMAN,
                    attachments=attachments,
                )
            ]

        messages: list[Message] = []
        for i, segment in enumerate(segments):
            if segment["type"] == "text":
                atts = attachments if i == 0 else []
                messages.append(
                    Message(
                        text=segment["content"],
                        type=MessageType.HUMAN,
                        attachments=atts,
                    )
                )
            elif segment["type"] == "command":
                valid_text = segment.get("resolved_text")
                if valid_text:
                    messages.append(Message(text=valid_text, type=MessageType.HUMAN))

        logger.debug(
            "Created %d messages from prompt segments",
            len(messages),
        )
        return messages

    # ------------------------------------------------------------------
    # Processing phases
    # ------------------------------------------------------------------

    async def _begin_message_processing(
        self,
    ) -> tuple[str, str, list[MCPServer], list[str], bool] | None:
        """Prepare state for sending a message. Returns None if no-op.

        Phases:
        1. Read state under lock (prompt, flags, files)
        2. Resolve /commands via DB outside the lock
        3. Re-acquire lock to set processing state and build messages
        """
        # Phase 1
        async with self:
            current_prompt = self.prompt.strip()
            if self.processing or not current_prompt:
                return None

            is_new_thread = self._thread.state == ThreadStatus.NEW
            file_paths = [f.file_path for f in self.uploaded_files]
            attachment_names = [f.filename for f in self.uploaded_files]
            skip_user_message = self._skip_user_message
            user_id = int(self.current_user_id or 0)

        # Phase 2
        segments: list[dict] = []
        if not skip_user_message:
            segments = self._parse_prompt_segments(current_prompt)
            await self._resolve_command_segments(segments, user_id)

        # Phase 3
        async with self:
            if self.processing:
                return None

            self.processing = True
            self.image_chunks = []
            self.thinking_items = []
            self.prompt = ""

            logger.debug(
                "Begin processing: is_new=%s, files=%d, file_paths=%s",
                is_new_thread,
                len(self.uploaded_files),
                file_paths,
            )

            if skip_user_message:
                self._skip_user_message = False
            else:
                new_messages = self._create_user_messages(
                    current_prompt, segments, attachment_names
                )
                self.messages.extend(new_messages)

            self.messages.append(Message(text="", type=MessageType.ASSISTANT))

            selected_model = self.get_selected_model
            if not selected_model:
                self._add_error_message("Kein Chat-Modell ausgewählt")
                self.processing = False
                return None

            return (
                current_prompt,
                selected_model,
                self.selected_mcp_servers,
                file_paths,
                is_new_thread,
            )

    async def _stop_processing_with_error(self, error_msg: str) -> None:
        """Stop processing and show an error message."""
        async with self:
            self._add_error_message(error_msg)
            self.processing = False

    async def _flush_chunk_buffer(
        self,
        *,
        chunks: list[Chunk],
        accumulator: ResponseAccumulator,
        current_prompt: str,
        is_new_thread: bool,
        first_response_received: bool,
    ) -> bool:
        """Process buffered chunks and sync UI state.

        Returns updated ``first_response_received``.
        """
        async with self:
            for chunk in chunks:
                accumulator.process_chunk(chunk)

            self.thinking_items = list(accumulator.thinking_items)
            self.current_activity = accumulator.current_activity
            if accumulator.show_thinking:
                self.show_thinking = True
            if accumulator.image_chunks:
                self.image_chunks = list(accumulator.image_chunks)

            if accumulator.auth_required:
                self._handle_auth_required_from_accumulator(accumulator)

            self.mcp_app_views = list(accumulator.mcp_app_views)

            if not first_response_received and is_new_thread:
                has_text = any(c.type == ChunkType.TEXT for c in chunks)
                if has_text:
                    first_response_received = True
                    self._thread.state = ThreadStatus.ACTIVE
                    if self._thread.title in {"", "Neuer Chat"}:
                        self._thread.title = current_prompt[:100]
                    if self.with_thread_list:
                        await self._notify_thread_created()

            return first_response_received

    async def _finalize_successful_response(
        self, accumulator: ResponseAccumulator
    ) -> None:
        """Finalize state after a successful full response.

        DB persistence happens outside the state lock.
        """
        async with self:
            self.show_thinking = False
            self.thinking_items = list(accumulator.thinking_items)
            self._thread.messages = list(self.messages)
            self._thread.ai_model = self.selected_model
            self._thread.mcp_server_ids = [
                s.id for s in self.selected_mcp_servers if s.id
            ]
            self._thread.skill_openai_ids = [s.openai_id for s in self.selected_skills]

            user_session: UserSession = await self.get_state(UserSession)
            user_id = user_session.user.user_id if user_session.user else None
            thread_copy = self._thread.model_copy()

        if user_id:
            await ThreadService().save_thread(thread_copy, user_id)

    async def _handle_process_error(
        self,
        *,
        ex: Exception,
        current_prompt: str,
        is_new_thread: bool,
        first_response_received: bool,
    ) -> None:
        """Handle failures during streaming and persist error state."""
        async with self:
            self._thread.state = ThreadStatus.ERROR

            if self.messages and self.messages[-1].type == MessageType.ASSISTANT:
                self.messages.pop()
            self.messages.append(Message(text=str(ex), type=MessageType.ERROR))

            if is_new_thread and not first_response_received:
                if self._thread.title in {"", "Neuer Chat"}:
                    self._thread.title = current_prompt[:100]
                if self.with_thread_list:
                    await self._notify_thread_created()

            self._thread.messages = list(self.messages)
            self._thread.mcp_server_ids = [
                s.id for s in self.selected_mcp_servers if s.id
            ]

            user_session: UserSession = await self.get_state(UserSession)
            user_id = user_session.user.user_id if user_session.user else None
            thread_copy = self._thread.model_copy()

        if user_id:
            await ThreadService().save_thread(thread_copy, user_id)

    async def _finalize_processing(self) -> None:
        """Mark processing done and close out the last message."""
        pending_files: list[str] = []
        async with self:
            if self.messages:
                self.messages[-1].done = True
            self.processing = False
            self.cancellation_requested = False
            self.current_activity = ""
            self._cancel_event = None

            if self._pending_file_cleanup:
                pending_files = list(self._pending_file_cleanup)
                self._pending_file_cleanup = []

        if pending_files:
            file_manager.cleanup_uploaded_files(pending_files)

    def _add_error_message(self, error_msg: str) -> None:
        """Add an error message to the conversation."""
        logger.error(error_msg)
        self.messages.append(Message(text=error_msg, type=MessageType.ERROR))

    async def _notify_thread_created(self) -> None:
        """Notify ThreadListState that a new thread was created.

        Called from within an ``async with self`` block.
        """
        threadlist_state: ThreadListState = await self.get_state(ThreadListState)
        await threadlist_state.add_thread(self._thread)
