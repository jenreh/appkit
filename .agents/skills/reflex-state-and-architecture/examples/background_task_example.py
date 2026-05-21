"""
Background Task + File Upload — canonical pattern.

Derived from: knai-hours HoursImportState.

Use this pattern when:
  - Processing takes more than ~1 second (Excel parsing, external API calls, etc.)
  - You want to stream progress updates to the UI without blocking it.
  - The operation involves file uploads.

Key Reflex rules for background tasks:
  - Decorate with @rx.event(background=True).
  - State mutations MUST happen inside `async with self:` blocks.
  - `yield` sends accumulated mutations to the frontend.
  - Never mutate self directly outside `async with self:` in a background handler.
"""

import logging
import pathlib
from collections.abc import AsyncGenerator
from datetime import UTC, datetime

import pandas as pd
import reflex as rx
from knai_myfeature.backend.models import ImportStatus, ImportSummary
from knai_myfeature.backend.repository import (
    ImportSummaryRepository,
    MyItemRepository,
)

import appkit_mantine as mn
from appkit_user.authentication.states import UserSession

logger = logging.getLogger(__name__)


class MyImportState(UserSession):
    """State for file upload and background processing."""

    # ── Upload progress ───────────────────────────────────────────────────────
    is_uploading: bool = False
    upload_progress: int = 0  # files completed so far
    upload_max: int = 0  # total files

    # ── Processing progress ───────────────────────────────────────────────────
    is_processing: bool = False
    process_progress: int = 0  # 0-100
    error_message: str = ""

    # ── Import results ────────────────────────────────────────────────────────
    import_stats: dict[str, int] = {
        "new_records": 0,
        "records_updated": 0,
        "duplicates_skipped": 0,
        "total_rows_processed": 0,
    }

    # ── Import history ────────────────────────────────────────────────────────
    recent_imports: list[ImportSummary] = []
    is_loading_history: bool = False

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    @rx.event
    async def on_load(self) -> AsyncGenerator:
        await self._reset_stats()
        async for _ in self.load_history():
            yield

    # ── File upload handler (regular async generator) ─────────────────────────
    # Not background=True here — we need to iterate over files sequentially
    # and kick off background processing for each.

    @rx.event
    async def handle_upload(self, files: list[rx.UploadFile]) -> AsyncGenerator:
        """Receive uploaded files and dispatch background processing."""
        user = await self.authenticated_user
        if not user or user.user_id == 0:
            yield rx.toast.error("Sie müssen angemeldet sein", position="top-right")
            return

        if not files:
            yield rx.toast.error("Keine Datei ausgewählt", position="top-right")
            return

        self.is_uploading = True
        self.upload_progress = 0
        self.upload_max = len(files)
        self.error_message = ""
        yield

        try:
            for i, file in enumerate(files):
                if not file.name.lower().endswith((".xlsx", ".xls")):
                    yield rx.toast.error(
                        f"Ungültiger Dateityp: {file.name}",
                        position="top-right",
                    )
                    continue

                # Persist file to disk so background task can access it
                file_content = await file.read()
                temp_path = rx.get_upload_dir() / f"import_{user.user_id}_{file.name}"
                with temp_path.open("wb") as f:
                    f.write(file_content)

                # Create a DB record to track this import
                import_record = await ImportSummaryRepository.create(
                    user_id=user.user_id,
                    filename=file.name,
                    import_date=datetime.now(UTC),
                    status=ImportStatus.PENDING,
                )

                # Hand off to background task
                yield MyImportState.process_file(
                    str(temp_path), import_record.id, user.user_id
                )

                self.upload_progress = i + 1
                yield

        except Exception as e:
            logger.error("Upload failed: %s", e)
            self.error_message = str(e)
            yield rx.toast.error(f"Upload fehlgeschlagen: {e}", position="top-right")
        finally:
            self.is_uploading = False

    # ── Background task — runs independently, streams progress ───────────────

    @rx.event(background=True)
    async def process_file(
        self, file_path: str, import_id: int, user_id: int
    ) -> AsyncGenerator:
        """
        Process a file in the background.

        IMPORTANT rules:
          - All state writes go inside `async with self:`.
          - After each `async with self:` block, yield to push updates.
          - Never yield inside `async with self:`.
        """
        async with self:
            self.is_processing = True
            self.process_progress = 10
        yield

        try:
            # ── Step 1: Read file (20%) ───────────────────────────────────────
            path = pathlib.Path(file_path)
            if not path.exists():  # noqa: ASYNC240
                raise FileNotFoundError(f"Temp file not found: {file_path}")

            raw_data = _read_file(path)  # pure function, no Reflex

            async with self:
                self.process_progress = 30
            yield

            # ── Step 2: Validate (50%) ────────────────────────────────────────
            validated = _validate(raw_data)  # raises on bad data

            async with self:
                self.process_progress = 50
            yield

            # ── Step 3: Persist to DB (80%) ───────────────────────────────────
            stats = await MyItemRepository.bulk_upsert(user_id, validated)

            async with self:
                self.process_progress = 80
                self.import_stats = {
                    "new_records": stats["new"],
                    "records_updated": stats["updated"],
                    "duplicates_skipped": stats["skipped"],
                    "total_rows_processed": len(validated),
                }
            yield

            # ── Step 4: Update import record (100%) ───────────────────────────
            await ImportSummaryRepository.mark_completed(
                import_id=import_id,
                **stats,
                total=len(validated),
            )

            async with self:
                self.process_progress = 100
                self.is_processing = False
            yield rx.toast.success(
                f"Import abgeschlossen: {stats['new']} neu, "
                f"{stats['skipped']} Duplikate",
                position="top-right",
            )

            # Refresh history list in the same background task
            async for _ in self.load_history():
                yield

        except Exception as e:
            logger.exception("Processing failed for import %d", import_id)
            await ImportSummaryRepository.mark_failed(import_id, str(e))

            async with self:
                self.is_processing = False
                self.error_message = str(e)
            yield rx.toast.error(
                f"Verarbeitung fehlgeschlagen: {e}", position="top-right"
            )

        finally:
            # Always clean up temp file
            pathlib.Path(file_path).unlink(missing_ok=True)  # noqa: ASYNC240

    # ── History ───────────────────────────────────────────────────────────────

    @rx.event
    async def load_history(self) -> AsyncGenerator:
        user = await self.authenticated_user
        if not user:
            return

        self.is_loading_history = True
        yield

        try:
            self.recent_imports = await ImportSummaryRepository.get_recent(
                user_id=user.user_id, limit=5
            )
        except Exception:
            logger.exception("Failed to load import history")
        finally:
            self.is_loading_history = False

    @rx.event
    async def clear_import_status(self) -> None:
        await self._reset_stats()

    # ── Private ───────────────────────────────────────────────────────────────

    async def _reset_stats(self) -> None:
        self.import_stats = {
            "new_records": 0,
            "records_updated": 0,
            "duplicates_skipped": 0,
            "total_rows_processed": 0,
        }
        self.error_message = ""
        self.process_progress = 0
        self.is_processing = False


# ─── Pure helper functions (no Reflex, easily testable) ──────────────────────


def _read_file(path: pathlib.Path) -> list[dict]:
    """Read and parse the uploaded file. Raise on unreadable input."""
    df = pd.read_excel(path)
    return df.to_dict("records")


def _validate(records: list[dict]) -> list[dict]:
    """Validate records. Raise ValueError on schema mismatch."""
    required = {"name", "date", "value"}
    for i, row in enumerate(records):
        missing = required - row.keys()
        if missing:
            raise ValueError(f"Row {i}: missing columns {missing}")
    return [r for r in records if r.get("value") is not None]


# ─── Matching UI component ────────────────────────────────────────────────────


def upload_section() -> rx.Component:
    """
    Drop-zone + upload button + progress bar + results grid.
    Mirrors the knai-hours import_section.py pattern.
    """
    return mn.stack(
        # Drop zone
        rx.upload(
            mn.stack(
                rx.icon("upload", size=24, color="gray"),
                mn.text("Dateien hierher ziehen oder klicken", size="2", ta="center"),
                mn.text("Unterstützte Formate: .xlsx, .xls", size="1", c="dimmed"),
                gap="sm",
                align="center",
                p="lg",
            ),
            id="my-upload",
            border="2px dashed #e2e8f0",
            border_radius="8px",
            multiple=True,
            accept={
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [
                    ".xlsx"
                ],
                "application/vnd.ms-excel": [".xls"],
            },
            max_files=5,
        ),
        # Controls
        mn.group(
            mn.button(
                "Hochladen",
                on_click=MyImportState.handle_upload(rx.upload_files("my-upload")),
                disabled=~rx.selected_files("my-upload").length(),
                loading=MyImportState.is_uploading,
                size="2",
            ),
            mn.button(
                "Zurücksetzen",
                on_click=rx.clear_selected_files("my-upload"),
                variant="outline",
                size="2",
            ),
            gap="sm",
        ),
        # Progress bar (only visible while processing)
        rx.cond(
            MyImportState.is_uploading | MyImportState.is_processing,
            mn.stack(
                mn.text("Verarbeitung läuft...", size="2", fw="medium"),
                mn.progress(
                    value=rx.cond(
                        MyImportState.is_processing,
                        MyImportState.process_progress,
                        (MyImportState.upload_progress / MyImportState.upload_max)
                        * 100,
                    ),
                    size="sm",
                    w="100%",
                ),
                gap="xs",
                w="100%",
            ),
        ),
        # Import results (only visible after a completed import)
        rx.cond(
            MyImportState.import_stats["total_rows_processed"] > 0,
            _import_results_grid(),
        ),
        gap="md",
        w="100%",
    )


def _import_results_grid() -> rx.Component:
    def result_card(value: rx.Var, label: str, color: str) -> rx.Component:
        return mn.stack(
            mn.text(value, size="5", fw="bold", c=color),
            mn.text(label, size="2", c="dimmed"),
            align="center",
            gap="2",
        )

    return mn.card(
        mn.stack(
            mn.heading("Import-Ergebnisse", size="3"),
            mn.simple_grid(
                result_card(MyImportState.import_stats["new_records"], "Neu", "green"),
                result_card(
                    MyImportState.import_stats["records_updated"],
                    "Aktualisiert",
                    "blue",
                ),
                result_card(
                    MyImportState.import_stats["duplicates_skipped"],
                    "Duplikate",
                    "orange",
                ),
                result_card(
                    MyImportState.import_stats["total_rows_processed"], "Gesamt", "gray"
                ),
                cols=4,
                spacing="md",
            ),
            mn.button(
                "Neuen Import starten",
                on_click=MyImportState.clear_import_status,
                variant="outline",
                size="2",
            ),
            gap="md",
        ),
        shadow="sm",
        padding="lg",
        radius="md",
        with_border=True,
    )
