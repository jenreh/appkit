"""
Feature State — canonical pattern.

Derived from: knai-hours CapacityReportState + knai-team TeamRecommendationState.
Copy, rename, and strip the parts you don't need.
"""

import logging
from collections.abc import AsyncGenerator
from datetime import UTC, datetime

import reflex as rx
from knai_myfeature.backend.models import MyItem, MyItemDisplay
from knai_myfeature.backend.repository import MyItemRepository
from sqlmodel import select

from appkit_user.authentication.states import UserSession

logger = logging.getLogger(__name__)


class MyFeatureState(UserSession):
    """
    Manages UI state for My Feature.

    Inherits UserSession to get access to `self.authenticated_user`.
    Use rx.State directly if authentication is not required.
    """

    # ── Data ─────────────────────────────────────────────────────────────────
    items: list[MyItemDisplay] = []
    selected_item: MyItemDisplay | None = None

    # ── Loading flags ─────────────────────────────────────────────────────────
    is_loading: bool = False
    is_saving: bool = False

    # ── Filters ───────────────────────────────────────────────────────────────
    search_query: str = ""
    selected_year: int = datetime.now(UTC).year
    selected_month: int = datetime.now(UTC).month

    # ── Tree / expand state ───────────────────────────────────────────────────
    expanded_rows: dict[str, bool] = {}
    detail_cache: dict[str, list[MyItemDisplay]] = {}

    # ── Browser-persisted tab selection ───────────────────────────────────────
    selected_tab: str = rx.LocalStorage("overview", name="my-feature-tab", sync=True)

    # ── Private (not sent to frontend) ────────────────────────────────────────
    _initialized: bool = False

    # ── Computed vars ─────────────────────────────────────────────────────────

    @rx.var
    def filtered_items(self) -> list[MyItemDisplay]:
        """Client-side filter — runs on every state change."""
        q = self.search_query.lower()
        if not q:
            return self.items
        return [i for i in self.items if q in i.name.lower()]

    @rx.var
    def total_count(self) -> int:
        return len(self.items)

    @rx.var
    def selected_year_str(self) -> str:
        """Bridge int → str for mn.select components."""
        return str(self.selected_year)

    @rx.var
    def selected_month_str(self) -> str:
        return str(self.selected_month)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    @rx.event
    async def on_load(self) -> AsyncGenerator:
        """Called via on_load=[MyFeatureState.on_load] in the page factory."""
        async for _ in self.load_items():
            yield

    # ── Data loading ──────────────────────────────────────────────────────────

    @rx.event
    async def load_items(self) -> AsyncGenerator:
        """Load items for the authenticated user."""
        user = await self.authenticated_user
        if not user or user.user_id == 0:
            yield rx.toast.error("Sie müssen angemeldet sein", position="top-right")
            return

        self.is_loading = True
        yield  # push is_loading=True to frontend immediately

        try:
            rows = await MyItemRepository.get_all(user.user_id)
            self.items = [MyItemDisplay.from_model(r) for r in rows]
        except Exception:
            logger.exception("Failed to load items")
            yield rx.toast.error("Laden fehlgeschlagen", position="top-right")
        finally:
            self.is_loading = False  # always clears, even on error

    # ── Filter / navigation events ────────────────────────────────────────────

    @rx.event
    def set_search_query(self, value: str) -> None:
        self.search_query = value

    @rx.event
    async def set_year(self, year: str) -> AsyncGenerator:
        try:
            self.selected_year = int(year)
            self._clear_caches()
            async for _ in self.load_items():
                yield
        except ValueError:
            yield rx.toast.error("Ungültiges Jahr", position="top-right")

    @rx.event
    async def set_month(self, month: str) -> AsyncGenerator:
        try:
            self.selected_month = int(month)
            self._clear_caches()
            async for _ in self.load_items():
                yield
        except ValueError:
            yield rx.toast.error("Ungültiger Monat", position="top-right")

    @rx.event
    def set_selected_tab(self, value: str | list[str]) -> None:
        if isinstance(value, list):
            self.selected_tab = value[0] if value else "overview"
        else:
            self.selected_tab = value

    # ── Row expand / detail lazy loading ─────────────────────────────────────

    @rx.event
    async def toggle_row(self, key: str) -> AsyncGenerator:
        """Toggle expansion and lazy-load details on first open."""
        is_open = self.expanded_rows.get(key, False)
        self.expanded_rows[key] = not is_open

        if not is_open and key not in self.detail_cache:
            async for _ in self._load_detail(key):
                yield
        else:
            yield

    @rx.event
    async def _load_detail(self, key: str) -> AsyncGenerator:
        user = await self.authenticated_user
        if not user:
            return

        yield  # let toggle render first

        try:
            details = await MyItemRepository.get_details(user.user_id, key)
            self.detail_cache[key] = [MyItemDisplay.from_model(d) for d in details]
        except Exception:
            logger.exception("Failed to load detail for %s", key)

    # ── CRUD ──────────────────────────────────────────────────────────────────

    @rx.event
    async def save_item(self, form_data: dict) -> AsyncGenerator:
        user = await self.authenticated_user
        if not user:
            return

        self.is_saving = True
        yield

        try:
            await MyItemRepository.upsert(user.user_id, form_data)
            yield rx.toast.success("Gespeichert", position="top-right")
            async for _ in self.load_items():
                yield
        except Exception:
            logger.exception("Save failed")
            yield rx.toast.error("Speichern fehlgeschlagen", position="top-right")
        finally:
            self.is_saving = False

    @rx.event
    async def delete_item(self, item_id: int) -> AsyncGenerator:
        user = await self.authenticated_user
        if not user:
            return

        try:
            await MyItemRepository.delete(user.user_id, item_id)
            yield rx.toast.success("Gelöscht", position="top-right")
            async for _ in self.load_items():
                yield
        except Exception:
            logger.exception("Delete failed")
            yield rx.toast.error("Löschen fehlgeschlagen", position="top-right")

    # ── Inline DB query via rx.asession (for simple one-off queries) ──────────

    @rx.event
    async def load_options(self) -> None:
        """Use rx.asession() for lightweight inline queries."""
        async with rx.asession() as session:
            result = await session.exec(
                select(MyItem.name).distinct().order_by(MyItem.name)
            )
            self._options = list(result.all())

    # ── Private helpers ───────────────────────────────────────────────────────

    def _clear_caches(self) -> None:
        """Call before any filter change that invalidates cached detail data."""
        self.detail_cache.clear()
        self.expanded_rows.clear()

    # ── Background tasks for async I/O ─────────────────────────────────────────

    """Use `@rx.background` for any network calls, DB queries, or long computations.
    Always acquire state with `async with self:` before mutating."""

    @rx.background
    async def fetch_data(self):
        async with self:
            self.is_loading = True
        result = await some_long_running_api_call()
        async with self:
            self.data = result
            self.is_loading = False
