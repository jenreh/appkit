"""Tests for ImageGalleryState (appkit_imagecreator.state).

Uses the plain-stub pattern: a _StubImageGallery class that does NOT
inherit from rx.State, so __setattr__ / parent_state issues are avoided.
Raw functions are extracted via _unwrap (EventHandler.fn) and computed
vars via _CV dict entries (.fget).
"""

# ruff: noqa: SLF001, ARG002
from __future__ import annotations

from datetime import UTC, datetime
from datetime import date as date_type
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from appkit_imagecreator.backend.models import (
    GeneratedImageData,
    GeneratedImageModel,
    ImageGeneratorResponse,
    ImageResponseState,
)
from appkit_imagecreator.state import (
    COUNT_OPTIONS,
    MAX_SIZE_BYTES,
    QUALITY_OPTIONS,
    SIZE_OPTIONS,
    ImageGalleryState,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
_CV = ImageGalleryState.__dict__


def _unwrap(name: str):
    """Extract the raw function from an EventHandler descriptor."""
    descriptor = ImageGalleryState.__dict__[name]
    return descriptor.fn


def _make_image(
    image_id: int = 1,
    *,
    prompt: str = "test prompt",
    model: str = "dall-e-3",
    width: int = 1024,
    height: int = 1024,
    style: str | None = None,
    quality: str | None = None,
    config: dict[str, Any] | None = None,
    is_uploaded: bool = False,
    created_at: datetime | None = None,
) -> GeneratedImageModel:
    return GeneratedImageModel(
        id=image_id,
        user_id=1,
        prompt=prompt,
        model=model,
        content_type="image/png",
        width=width,
        height=height,
        style=style,
        quality=quality,
        config=config,
        is_uploaded=is_uploaded,
        created_at=created_at or datetime(2025, 1, 15, 12, 0, 0, tzinfo=UTC),
    )


# ---------------------------------------------------------------------------
# Stub
# ---------------------------------------------------------------------------
class _StubImageGallery:
    """Minimal stub mirroring ImageGalleryState vars.

    Private helpers are bound from the real class so that
    EventHandler-wrapped methods can call ``self._find_image(...)`` etc.
    """

    # Bind private helpers from ImageGalleryState
    _find_image = ImageGalleryState._find_image
    _find_history_image = ImageGalleryState._find_history_image
    _close_all_popups = ImageGalleryState._close_all_popups
    _is_image_selected = ImageGalleryState._is_image_selected
    _refresh_generators = ImageGalleryState._refresh_generators
    _auto_select_uploaded_images = ImageGalleryState._auto_select_uploaded_images
    _get_image_bytes = ImageGalleryState._get_image_bytes

    # staticmethod must stay static — use staticmethod() wrapper
    _format_date_label = staticmethod(ImageGalleryState._format_date_label)
    _validate_upload_file = staticmethod(ImageGalleryState._validate_upload_file)

    def __init__(self) -> None:
        self.images: list[GeneratedImageModel] = []
        self.history_images: list[GeneratedImageModel] = []
        self.loading_images = False
        self.is_uploading = False
        self.is_generating = False
        self._generation_cancelled = False
        self.prompt = ""
        self.generating_prompt = ""
        self.selected_style = ""
        self.style_popup_open = False
        self.styles_preset: dict[str, dict[str, str]] = {
            "Anime": {"prompt": "anime style", "path": "styles/anime.png"},
            "Realistic": {"prompt": "realistic photo", "path": "styles/realistic.png"},
        }
        self.config_popup_open = False
        self.selected_size = "Square (1024x1024)"
        self.selected_width = 1024
        self.selected_height = 1024
        self.selected_quality = "Auto"
        self.count_popup_open = False
        self.selected_count = 1
        self.enhance_prompt = True
        self.generator = ""
        self.generators: list[dict[str, str]] = []
        self.zoom_modal_open = False
        self.zoom_image: GeneratedImageModel | None = None
        self.current_zoomed_image_index: int = -1
        self.selected_images: list[GeneratedImageModel] = []
        self.history_drawer_open = False
        self.deleting_image_id = 0
        self._initialized = False
        self._current_user_id = 0

    # Background tasks use ``async with self``
    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    # Some methods call ``await self.get_state(UserSession)``
    async def get_state(self, _cls):
        return self._mock_user_session


# ===========================================================================
# Computed vars
# ===========================================================================
class TestComputedVars:
    def test_has_images_empty(self) -> None:
        s = _StubImageGallery()
        assert _CV["has_images"].fget(s) is False

    def test_has_images_with_data(self) -> None:
        s = _StubImageGallery()
        s.images = [_make_image()]
        assert _CV["has_images"].fget(s) is True

    def test_count_label(self) -> None:
        s = _StubImageGallery()
        s.selected_count = 3
        assert _CV["count_label"].fget(s) == "3x"

    def test_size_options_returns_presets(self) -> None:
        s = _StubImageGallery()
        result = _CV["size_options"].fget(s)
        assert result == SIZE_OPTIONS

    def test_quality_options_returns_presets(self) -> None:
        s = _StubImageGallery()
        result = _CV["quality_options"].fget(s)
        assert result == QUALITY_OPTIONS

    def test_count_options_returns_presets(self) -> None:
        s = _StubImageGallery()
        result = _CV["count_options"].fget(s)
        assert result == COUNT_OPTIONS

    def test_is_edit_mode_false(self) -> None:
        s = _StubImageGallery()
        assert _CV["is_edit_mode"].fget(s) is False

    def test_is_edit_mode_true(self) -> None:
        s = _StubImageGallery()
        s.selected_images = [_make_image()]
        assert _CV["is_edit_mode"].fget(s) is True

    def test_selected_images_count(self) -> None:
        s = _StubImageGallery()
        s.selected_images = [_make_image(1), _make_image(2)]
        assert _CV["selected_images_count"].fget(s) == 2

    def test_current_generator_label_empty(self) -> None:
        s = _StubImageGallery()
        assert _CV["current_generator_label"].fget(s) == ""

    def test_current_generator_label_match(self) -> None:
        s = _StubImageGallery()
        s.generator = "dall-e-3"
        s.generators = [{"id": "dall-e-3", "label": "DALL·E 3"}]
        assert _CV["current_generator_label"].fget(s) == "DALL·E 3"

    def test_current_generator_label_no_match(self) -> None:
        s = _StubImageGallery()
        s.generator = "unknown"
        s.generators = [{"id": "dall-e-3", "label": "DALL·E 3"}]
        assert _CV["current_generator_label"].fget(s) == ""

    def test_can_navigate_previous_false_at_start(self) -> None:
        s = _StubImageGallery()
        s.current_zoomed_image_index = 0
        assert _CV["can_navigate_previous"].fget(s) is False

    def test_can_navigate_previous_true(self) -> None:
        s = _StubImageGallery()
        s.images = [_make_image(1), _make_image(2)]
        s.current_zoomed_image_index = 1
        assert _CV["can_navigate_previous"].fget(s) is True

    def test_can_navigate_next_false_at_end(self) -> None:
        s = _StubImageGallery()
        s.images = [_make_image(1)]
        s.current_zoomed_image_index = 0
        assert _CV["can_navigate_next"].fget(s) is False

    def test_can_navigate_next_true(self) -> None:
        s = _StubImageGallery()
        s.images = [_make_image(1), _make_image(2)]
        s.current_zoomed_image_index = 0
        assert _CV["can_navigate_next"].fget(s) is True

    def test_selected_style_path_empty(self) -> None:
        s = _StubImageGallery()
        s.selected_style = ""
        assert _CV["selected_style_path"].fget(s) == ""

    def test_selected_style_path_relative(self) -> None:
        s = _StubImageGallery()
        s.selected_style = "Anime"
        result = _CV["selected_style_path"].fget(s)
        assert result == "/styles/anime.png"

    def test_selected_style_path_absolute(self) -> None:
        s = _StubImageGallery()
        s.styles_preset = {"abs": {"path": "/already/absolute.png", "prompt": ""}}
        s.selected_style = "abs"
        assert _CV["selected_style_path"].fget(s) == "/already/absolute.png"

    def test_selected_style_path_http(self) -> None:
        s = _StubImageGallery()
        s.styles_preset = {"web": {"path": "https://example.com/img.png", "prompt": ""}}
        s.selected_style = "web"
        assert _CV["selected_style_path"].fget(s) == "https://example.com/img.png"


# ===========================================================================
# Helper methods
# ===========================================================================
class TestHelpers:
    def test_find_image_found(self) -> None:
        s = _StubImageGallery()
        img = _make_image(42)
        s.images = [img]
        result = ImageGalleryState._find_image(s, 42)
        assert result is not None
        assert result.id == 42

    def test_find_image_not_found(self) -> None:
        s = _StubImageGallery()
        s.images = [_make_image(1)]
        assert ImageGalleryState._find_image(s, 999) is None

    def test_find_history_image_found(self) -> None:
        s = _StubImageGallery()
        img = _make_image(99)
        s.history_images = [img]
        result = ImageGalleryState._find_history_image(s, 99)
        assert result is not None
        assert result.id == 99

    def test_find_history_image_not_found(self) -> None:
        s = _StubImageGallery()
        s.history_images = []
        assert ImageGalleryState._find_history_image(s, 1) is None

    def test_close_all_popups(self) -> None:
        s = _StubImageGallery()
        s.style_popup_open = True
        s.config_popup_open = True
        s.count_popup_open = True
        ImageGalleryState._close_all_popups(s)
        assert not s.style_popup_open
        assert not s.config_popup_open
        assert not s.count_popup_open

    def test_is_image_selected_true(self) -> None:
        s = _StubImageGallery()
        s.selected_images = [_make_image(5)]
        assert ImageGalleryState._is_image_selected(s, 5) is True

    def test_is_image_selected_false(self) -> None:
        s = _StubImageGallery()
        s.selected_images = [_make_image(5)]
        assert ImageGalleryState._is_image_selected(s, 99) is False


# ===========================================================================
# Popup handlers (sync event handlers)
# ===========================================================================
class TestPopupHandlers:
    def test_toggle_style_popup_opens(self) -> None:
        s = _StubImageGallery()
        fn = _unwrap("toggle_style_popup")
        fn(s)
        assert s.style_popup_open is True

    def test_toggle_style_popup_closes(self) -> None:
        s = _StubImageGallery()
        s.style_popup_open = True
        fn = _unwrap("toggle_style_popup")
        fn(s)
        assert s.style_popup_open is False

    def test_toggle_style_popup_closes_others(self) -> None:
        s = _StubImageGallery()
        s.config_popup_open = True
        s.count_popup_open = True
        fn = _unwrap("toggle_style_popup")
        fn(s)
        assert s.style_popup_open is True
        assert s.config_popup_open is False
        assert s.count_popup_open is False

    def test_toggle_config_popup_opens(self) -> None:
        s = _StubImageGallery()
        fn = _unwrap("toggle_config_popup")
        fn(s)
        assert s.config_popup_open is True

    def test_toggle_config_popup_closes(self) -> None:
        s = _StubImageGallery()
        s.config_popup_open = True
        fn = _unwrap("toggle_config_popup")
        fn(s)
        assert s.config_popup_open is False

    def test_toggle_count_popup_opens(self) -> None:
        s = _StubImageGallery()
        fn = _unwrap("toggle_count_popup")
        fn(s)
        assert s.count_popup_open is True

    def test_set_selected_style_sets(self) -> None:
        s = _StubImageGallery()
        fn = _unwrap("set_selected_style")
        fn(s, "Anime")
        assert s.selected_style == "Anime"
        assert s.style_popup_open is False

    def test_set_selected_style_toggles_off(self) -> None:
        s = _StubImageGallery()
        s.selected_style = "Anime"
        fn = _unwrap("set_selected_style")
        fn(s, "Anime")
        assert s.selected_style == ""

    def test_set_selected_size(self) -> None:
        s = _StubImageGallery()
        fn = _unwrap("set_selected_size")
        fn(s, "Portrait (2:3)")
        assert s.selected_size == "Portrait (2:3)"
        assert s.selected_width == 1024
        assert s.selected_height == 1536

    def test_set_selected_size_no_match(self) -> None:
        s = _StubImageGallery()
        fn = _unwrap("set_selected_size")
        fn(s, "Unknown")
        assert s.selected_size == "Unknown"
        # Width/height unchanged
        assert s.selected_width == 1024
        assert s.selected_height == 1024

    def test_set_selected_quality(self) -> None:
        s = _StubImageGallery()
        fn = _unwrap("set_selected_quality")
        fn(s, "High")
        assert s.selected_quality == "High"

    def test_set_selected_count(self) -> None:
        s = _StubImageGallery()
        fn = _unwrap("set_selected_count")
        fn(s, [3])
        assert s.selected_count == 3

    def test_set_selected_count_empty(self) -> None:
        s = _StubImageGallery()
        fn = _unwrap("set_selected_count")
        fn(s, [])
        assert s.selected_count == 1


# ===========================================================================
# Generator & prompt handlers
# ===========================================================================
class TestGeneratorHandlers:
    def test_set_generator(self) -> None:
        s = _StubImageGallery()
        fn = _unwrap("set_generator")
        fn(s, "dall-e-3")
        assert s.generator == "dall-e-3"

    def test_set_enhance_prompt(self) -> None:
        s = _StubImageGallery()
        fn = _unwrap("set_enhance_prompt")
        fn(s, False)
        assert s.enhance_prompt is False

    def test_clear_prompt(self) -> None:
        s = _StubImageGallery()
        s.prompt = "something"
        s.selected_images = [_make_image()]
        fn = _unwrap("clear_prompt")
        fn(s)
        assert s.prompt == ""
        assert s.selected_images == []

    def test_set_prompt(self) -> None:
        s = _StubImageGallery()
        fn = _unwrap("set_prompt")
        fn(s, "a cat on the moon")
        assert s.prompt == "a cat on the moon"

    def test_cancel_generation(self) -> None:
        s = _StubImageGallery()
        s.is_generating = True
        s.generating_prompt = "generating..."
        fn = _unwrap("cancel_generation")
        fn(s)
        assert s._generation_cancelled is True
        assert s.is_generating is False
        assert s.generating_prompt == ""


# ===========================================================================
# Image action handlers (sync)
# ===========================================================================
class TestImageActions:
    def test_open_zoom_modal(self) -> None:
        s = _StubImageGallery()
        s.images = [_make_image(10), _make_image(20)]
        fn = _unwrap("open_zoom_modal")
        fn(s, 20)
        assert s.zoom_modal_open is True
        assert s.zoom_image is not None
        assert s.zoom_image.id == 20
        assert s.current_zoomed_image_index == 1

    def test_open_zoom_modal_tracks_first_image_index(self) -> None:
        s = _StubImageGallery()
        s.images = [_make_image(10), _make_image(20)]
        fn = _unwrap("open_zoom_modal")
        fn(s, 10)
        assert s.current_zoomed_image_index == 0

    def test_open_zoom_modal_not_found(self) -> None:
        s = _StubImageGallery()
        s.images = []
        fn = _unwrap("open_zoom_modal")
        fn(s, 999)
        assert s.zoom_modal_open is False
        assert s.zoom_image is None
        assert s.current_zoomed_image_index == -1

    def test_close_zoom_modal(self) -> None:
        s = _StubImageGallery()
        s.zoom_modal_open = True
        s.zoom_image = _make_image()
        s.current_zoomed_image_index = 2
        fn = _unwrap("close_zoom_modal")
        fn(s)
        assert s.zoom_modal_open is False
        assert s.zoom_image is None
        assert s.current_zoomed_image_index == -1

    def test_navigate_to_next_image(self) -> None:
        s = _StubImageGallery()
        s.images = [_make_image(1), _make_image(2), _make_image(3)]
        s.current_zoomed_image_index = 0
        s.zoom_image = s.images[0]
        fn = _unwrap("navigate_to_next_image")
        fn(s)
        assert s.current_zoomed_image_index == 1
        assert s.zoom_image is not None
        assert s.zoom_image.id == 2

    def test_navigate_to_next_image_at_end_is_noop(self) -> None:
        s = _StubImageGallery()
        s.images = [_make_image(1), _make_image(2)]
        s.current_zoomed_image_index = 1
        s.zoom_image = s.images[1]
        fn = _unwrap("navigate_to_next_image")
        fn(s)
        assert s.current_zoomed_image_index == 1
        assert s.zoom_image.id == 2

    def test_navigate_to_previous_image(self) -> None:
        s = _StubImageGallery()
        s.images = [_make_image(1), _make_image(2), _make_image(3)]
        s.current_zoomed_image_index = 2
        s.zoom_image = s.images[2]
        fn = _unwrap("navigate_to_previous_image")
        fn(s)
        assert s.current_zoomed_image_index == 1
        assert s.zoom_image is not None
        assert s.zoom_image.id == 2

    def test_navigate_to_previous_image_at_start_is_noop(self) -> None:
        s = _StubImageGallery()
        s.images = [_make_image(1), _make_image(2)]
        s.current_zoomed_image_index = 0
        s.zoom_image = s.images[0]
        fn = _unwrap("navigate_to_previous_image")
        fn(s)
        assert s.current_zoomed_image_index == 0
        assert s.zoom_image.id == 1

    def test_add_image_to_prompt(self) -> None:
        s = _StubImageGallery()
        img = _make_image(7)
        s.images = [img]
        fn = _unwrap("add_image_to_prompt")
        fn(s, 7)
        assert len(s.selected_images) == 1
        assert s.selected_images[0].id == 7

    def test_add_image_to_prompt_already_selected(self) -> None:
        s = _StubImageGallery()
        img = _make_image(7)
        s.images = [img]
        s.selected_images = [img]
        fn = _unwrap("add_image_to_prompt")
        fn(s, 7)
        assert len(s.selected_images) == 1  # no duplicate

    def test_add_image_to_prompt_not_found(self) -> None:
        s = _StubImageGallery()
        s.images = []
        fn = _unwrap("add_image_to_prompt")
        fn(s, 999)
        assert len(s.selected_images) == 0

    def test_remove_image_from_prompt(self) -> None:
        s = _StubImageGallery()
        s.selected_images = [_make_image(1), _make_image(2)]
        fn = _unwrap("remove_image_from_prompt")
        fn(s, 1)
        assert len(s.selected_images) == 1
        assert s.selected_images[0].id == 2

    def test_remove_image_from_view(self) -> None:
        s = _StubImageGallery()
        s.images = [_make_image(1), _make_image(2)]
        s.selected_images = [_make_image(1)]
        fn = _unwrap("remove_image_from_view")
        fn(s, 1)
        assert len(s.images) == 1
        assert s.images[0].id == 2
        assert len(s.selected_images) == 0

    def test_toggle_history(self) -> None:
        s = _StubImageGallery()
        fn = _unwrap("toggle_history")
        fn(s)
        assert s.history_drawer_open is True
        fn(s)
        assert s.history_drawer_open is False

    def test_close_history_drawer(self) -> None:
        s = _StubImageGallery()
        s.history_drawer_open = True
        fn = _unwrap("close_history_drawer")
        fn(s)
        assert s.history_drawer_open is False


# ===========================================================================
# copy_config_to_prompt
# ===========================================================================
class TestCopyConfigToPrompt:
    def test_copies_all_fields(self) -> None:
        s = _StubImageGallery()
        img = _make_image(
            1,
            prompt="sunset",
            model="dall-e-3",
            width=1536,
            height=1024,
            style="Anime",
            quality="High",
            config={"count": 2, "enhance_prompt": False},
        )
        s.images = [img]
        fn = _unwrap("copy_config_to_prompt")
        fn(s, 1)
        assert s.prompt == "sunset"
        assert s.selected_style == "Anime"
        assert s.selected_quality == "High"
        assert s.selected_width == 1536
        assert s.selected_height == 1024
        assert s.generator == "dall-e-3"
        assert s.selected_count == 2
        assert s.enhance_prompt is False

    def test_copies_default_quality(self) -> None:
        s = _StubImageGallery()
        img = _make_image(1, quality=None, style=None)
        s.images = [img]
        fn = _unwrap("copy_config_to_prompt")
        fn(s, 1)
        assert s.selected_quality == "Auto"
        assert s.selected_style == ""

    def test_not_found(self) -> None:
        s = _StubImageGallery()
        s.images = []
        fn = _unwrap("copy_config_to_prompt")
        fn(s, 999)
        # No change
        assert s.prompt == ""

    def test_size_label_match(self) -> None:
        s = _StubImageGallery()
        img = _make_image(1, width=1024, height=1536)
        s.images = [img]
        fn = _unwrap("copy_config_to_prompt")
        fn(s, 1)
        assert s.selected_size == "Portrait (2:3)"


# ===========================================================================
# add_history_image_to_grid
# ===========================================================================
class TestAddHistoryImageToGrid:
    def test_adds_from_history(self) -> None:
        s = _StubImageGallery()
        img = _make_image(5)
        s.history_images = [img]
        s.images = []
        fn = _unwrap("add_history_image_to_grid")
        fn(s, "5")
        assert len(s.images) == 1
        assert s.images[0].id == 5

    def test_already_in_grid(self) -> None:
        s = _StubImageGallery()
        img = _make_image(5)
        s.images = [img]
        s.history_images = [img]
        fn = _unwrap("add_history_image_to_grid")
        fn(s, "5")
        assert len(s.images) == 1  # no duplicate

    def test_not_in_history(self) -> None:
        s = _StubImageGallery()
        s.images = []
        s.history_images = []
        fn = _unwrap("add_history_image_to_grid")
        fn(s, "999")
        assert len(s.images) == 0


# ===========================================================================
# history_images_by_date computed var
# ===========================================================================
class TestHistoryImagesByDate:
    def test_empty(self) -> None:
        s = _StubImageGallery()
        result = _CV["history_images_by_date"].fget(s)
        assert result == []

    def test_grouped_by_date(self) -> None:
        s = _StubImageGallery()
        img1 = _make_image(1, created_at=datetime(2025, 1, 15, 10, 0, tzinfo=UTC))
        img2 = _make_image(2, created_at=datetime(2025, 1, 15, 14, 0, tzinfo=UTC))
        img3 = _make_image(3, created_at=datetime(2025, 1, 16, 9, 0, tzinfo=UTC))
        s.history_images = [img1, img2, img3]
        result = _CV["history_images_by_date"].fget(s)
        assert len(result) == 2
        # Sorted descending: Jan 16 first
        assert len(result[0][1]) == 1  # Jan 16
        assert len(result[1][1]) == 2  # Jan 15


# ===========================================================================
# _format_date_label
# ===========================================================================
class TestFormatDateLabel:
    def test_formats_date(self) -> None:
        result = ImageGalleryState._format_date_label(date_type(2025, 1, 15))
        # Exact format depends on locale, just ensure it's a non-empty string
        assert isinstance(result, str)
        assert len(result) > 0
        assert "2025" in result


# ===========================================================================
# _get_image_bytes (async)
# ===========================================================================
class TestGetImageBytes:
    @pytest.mark.asyncio
    async def test_returns_bytes_directly(self) -> None:
        s = _StubImageGallery()
        img_data = GeneratedImageData(image_bytes=b"hello", content_type="image/png")
        result = await ImageGalleryState._get_image_bytes(s, img_data)
        assert result == b"hello"

    @pytest.mark.asyncio
    async def test_returns_none_no_data(self) -> None:
        s = _StubImageGallery()
        img_data = GeneratedImageData()
        result = await ImageGalleryState._get_image_bytes(s, img_data)
        assert result is None

    @pytest.mark.asyncio
    @patch("appkit_imagecreator.state.httpx.AsyncClient")
    async def test_fetches_from_url(self, mock_client_cls) -> None:
        s = _StubImageGallery()
        mock_resp = MagicMock()
        mock_resp.content = b"fetched-bytes"
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        img_data = GeneratedImageData(
            external_url="https://example.com/img.png",
            content_type="image/png",
        )
        result = await ImageGalleryState._get_image_bytes(s, img_data)
        assert result == b"fetched-bytes"

    @pytest.mark.asyncio
    @patch("appkit_imagecreator.state.httpx.AsyncClient")
    async def test_fetch_url_error(self, mock_client_cls) -> None:
        s = _StubImageGallery()
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.HTTPError("fail"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        img_data = GeneratedImageData(
            external_url="https://example.com/bad.png",
        )
        result = await ImageGalleryState._get_image_bytes(s, img_data)
        assert result is None


# ===========================================================================
# _validate_upload_file (static)
# ===========================================================================
class TestValidateUploadFile:
    def test_valid_png(self) -> None:
        file = MagicMock()
        file.content_type = "image/png"
        file.size = 1024
        assert ImageGalleryState._validate_upload_file(file, ".png") is None

    def test_valid_by_extension(self) -> None:
        file = MagicMock()
        file.content_type = "application/octet-stream"
        file.size = 1024
        assert ImageGalleryState._validate_upload_file(file, ".jpg") is None

    def test_invalid_type(self) -> None:
        file = MagicMock()
        file.content_type = "text/plain"
        file.size = 1024
        result = ImageGalleryState._validate_upload_file(file, ".txt")
        assert result == "unsupported format"

    def test_too_large(self) -> None:
        file = MagicMock()
        file.content_type = "image/png"
        file.size = MAX_SIZE_BYTES + 1
        result = ImageGalleryState._validate_upload_file(file, ".png")
        assert "limit" in result


# ===========================================================================
# _auto_select_uploaded_images
# ===========================================================================
class TestAutoSelectUploadedImages:
    def test_selects_new_images(self) -> None:
        s = _StubImageGallery()
        img = _make_image(10)
        s.images = [img]
        s.selected_images = []
        ImageGalleryState._auto_select_uploaded_images(s, [10])
        assert len(s.selected_images) == 1
        assert s.selected_images[0].id == 10

    def test_skips_already_selected(self) -> None:
        s = _StubImageGallery()
        img = _make_image(10)
        s.images = [img]
        s.selected_images = [img]
        ImageGalleryState._auto_select_uploaded_images(s, [10])
        assert len(s.selected_images) == 1

    def test_skips_not_found(self) -> None:
        s = _StubImageGallery()
        s.images = []
        s.selected_images = []
        ImageGalleryState._auto_select_uploaded_images(s, [999])
        assert len(s.selected_images) == 0


# ===========================================================================
# _show_upload_results (static)
# ===========================================================================
class TestShowUploadResults:
    def test_success(self) -> None:
        results = ImageGalleryState._show_upload_results(2, [], False)
        assert len(results) == 1  # success toast

    def test_success_with_skipped(self) -> None:
        results = ImageGalleryState._show_upload_results(1, ["f.txt (bad)"], False)
        assert len(results) == 1  # warning toast

    def test_all_skipped(self) -> None:
        results = ImageGalleryState._show_upload_results(0, ["f.txt (bad)"], False)
        assert len(results) == 1  # error toast

    def test_exceeded_limit(self) -> None:
        results = ImageGalleryState._show_upload_results(3, [], True)
        assert len(results) == 2  # success + info

    def test_empty(self) -> None:
        results = ImageGalleryState._show_upload_results(0, [], False)
        assert len(results) == 0


# ===========================================================================
# _refresh_generators
# ===========================================================================
class TestRefreshGenerators:
    @patch("appkit_imagecreator.state.generator_registry")
    def test_filters_by_role(self, mock_reg) -> None:
        s = _StubImageGallery()
        mock_reg.list_generators.return_value = [
            {"id": "g1", "label": "Gen 1", "required_role": ""},
            {"id": "g2", "label": "Gen 2", "required_role": "admin"},
            {"id": "g3", "label": "Gen 3", "required_role": "user"},
        ]
        ImageGalleryState._refresh_generators(s, ["user"])
        assert len(s.generators) == 2
        ids = {g["id"] for g in s.generators}
        assert "g1" in ids
        assert "g3" in ids
        assert s.generator == "g1"  # first available

    @patch("appkit_imagecreator.state.generator_registry")
    def test_keeps_valid_selection(self, mock_reg) -> None:
        s = _StubImageGallery()
        s.generator = "g2"
        mock_reg.list_generators.return_value = [
            {"id": "g1", "label": "1", "required_role": ""},
            {"id": "g2", "label": "2", "required_role": ""},
        ]
        ImageGalleryState._refresh_generators(s, [])
        assert s.generator == "g2"

    @patch("appkit_imagecreator.state.generator_registry")
    def test_resets_invalid_selection(self, mock_reg) -> None:
        s = _StubImageGallery()
        s.generator = "gone"
        mock_reg.list_generators.return_value = [
            {"id": "g1", "label": "1", "required_role": ""},
        ]
        ImageGalleryState._refresh_generators(s, [])
        assert s.generator == "g1"

    @patch("appkit_imagecreator.state.generator_registry")
    def test_no_generators(self, mock_reg) -> None:
        s = _StubImageGallery()
        mock_reg.list_generators.return_value = []
        ImageGalleryState._refresh_generators(s, [])
        assert s.generators == []
        assert s.generator == ""


# ===========================================================================
# clear_grid_view (async event)
# ===========================================================================
class TestClearGridView:
    @pytest.mark.asyncio
    async def test_clears_images(self) -> None:
        s = _StubImageGallery()
        s.images = [_make_image(1)]
        s.zoom_modal_open = True
        s.zoom_image = _make_image(1)
        fn = _unwrap("clear_grid_view")
        await fn(s)
        assert s.images == []
        assert s.zoom_modal_open is False
        assert s.zoom_image is None


# ===========================================================================
# init_generators (async event)
# ===========================================================================
class TestInitGenerators:
    @pytest.mark.asyncio
    @patch("appkit_imagecreator.state.generator_registry")
    async def test_loads_generators(self, mock_reg) -> None:
        s = _StubImageGallery()
        mock_reg._loaded = False
        mock_reg.initialize = AsyncMock()
        mock_reg.list_generators.return_value = [
            {"id": "g1", "label": "Gen 1", "required_role": ""},
        ]

        mock_user = MagicMock()
        mock_user.user = MagicMock()
        mock_user.user.roles = ["admin"]
        s._mock_user_session = mock_user

        fn = _unwrap("init_generators")
        await fn(s)
        mock_reg.initialize.assert_awaited_once()
        assert len(s.generators) == 1

    @pytest.mark.asyncio
    @patch("appkit_imagecreator.state.generator_registry")
    async def test_skips_init_if_loaded(self, mock_reg) -> None:
        s = _StubImageGallery()
        mock_reg._loaded = True
        mock_reg.initialize = AsyncMock()
        mock_reg.list_generators.return_value = []

        mock_user = MagicMock()
        mock_user.user = None
        s._mock_user_session = mock_user

        fn = _unwrap("init_generators")
        await fn(s)
        mock_reg.initialize.assert_not_awaited()


# ===========================================================================
# generate_images (background task, async generator)
# ===========================================================================
class TestGenerateImages:
    @pytest.mark.asyncio
    @patch("appkit_imagecreator.state.get_asyncdb_session")
    @patch("appkit_imagecreator.state.image_repo")
    @patch("appkit_imagecreator.state.generator_registry")
    async def test_empty_prompt_yields_warning(
        self, mock_reg, mock_repo, mock_session
    ) -> None:
        s = _StubImageGallery()
        s.prompt = "   "
        fn = _unwrap("generate_images")
        [r async for r in fn(s)]
        # Should yield a toast warning, not generate
        assert s.is_generating is False

    @pytest.mark.asyncio
    @patch("appkit_imagecreator.state.get_asyncdb_session")
    @patch("appkit_imagecreator.state.image_repo")
    @patch("appkit_imagecreator.state.generator_registry")
    async def test_concurrent_generation_blocked(
        self, mock_reg, mock_repo, mock_session
    ) -> None:
        s = _StubImageGallery()
        s.prompt = "a cat"
        s.is_generating = True  # already generating
        fn = _unwrap("generate_images")
        [r async for r in fn(s)]
        # Should return early; no finally block reached
        assert s.is_generating is True  # unchanged — early return

    @pytest.mark.asyncio
    @patch("appkit_imagecreator.state.get_asyncdb_session")
    @patch("appkit_imagecreator.state.image_repo")
    @patch("appkit_imagecreator.state.generator_registry")
    async def test_no_user_yields_error(
        self, mock_reg, mock_repo, mock_session
    ) -> None:
        s = _StubImageGallery()
        s.prompt = "a cat"

        mock_user = MagicMock()
        mock_user.user = None
        s._mock_user_session = mock_user

        fn = _unwrap("generate_images")
        [r async for r in fn(s)]
        assert s.is_generating is False

    @pytest.mark.asyncio
    @patch("appkit_imagecreator.state.get_asyncdb_session")
    @patch("appkit_imagecreator.state.image_repo")
    @patch("appkit_imagecreator.state.generator_registry")
    async def test_successful_generation(
        self, mock_reg, mock_repo, mock_session
    ) -> None:
        s = _StubImageGallery()
        s.prompt = "a sunset"
        s.generator = "test-gen"
        s.selected_images = []

        mock_user = MagicMock()
        mock_user.user = MagicMock()
        mock_user.user.user_id = 42
        s._mock_user_session = mock_user

        # Mock generator
        mock_client = AsyncMock()
        mock_client.generate = AsyncMock(
            return_value=ImageGeneratorResponse(
                state=ImageResponseState.SUCCEEDED,
                generated_images=[
                    GeneratedImageData(
                        image_bytes=b"img-bytes",
                        content_type="image/png",
                    )
                ],
            )
        )
        mock_reg.get.return_value = mock_client

        # Mock DB session and repo
        mock_sess = AsyncMock()
        mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_sess)
        mock_session.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_saved = MagicMock()
        mock_saved.id = 100
        mock_saved.user_id = 42
        mock_saved.prompt = "a sunset"
        mock_saved.model = "test-gen"
        mock_saved.content_type = "image/png"
        mock_saved.width = 1024
        mock_saved.height = 1024
        mock_saved.style = None
        mock_saved.quality = None
        mock_saved.enhanced_prompt = None
        mock_saved.config = None
        mock_saved.is_uploaded = False
        mock_saved.is_deleted = False
        mock_saved.created_at = datetime(2025, 1, 15, tzinfo=UTC)
        mock_saved.image_data = b"img-bytes"
        mock_repo.create = AsyncMock(return_value=mock_saved)

        fn = _unwrap("generate_images")
        [r async for r in fn(s)]

        assert s.is_generating is False
        assert len(s.images) == 1
        assert s.images[0].id == 100
        mock_client.generate.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("appkit_imagecreator.state.get_asyncdb_session")
    @patch("appkit_imagecreator.state.image_repo")
    @patch("appkit_imagecreator.state.generator_registry")
    async def test_failed_response(self, mock_reg, mock_repo, mock_session) -> None:
        s = _StubImageGallery()
        s.prompt = "a cat"
        s.generator = "test-gen"

        mock_user = MagicMock()
        mock_user.user = MagicMock()
        mock_user.user.user_id = 1
        s._mock_user_session = mock_user

        mock_client = AsyncMock()
        mock_client.generate = AsyncMock(
            return_value=ImageGeneratorResponse(
                state=ImageResponseState.FAILED,
                error="API error",
            )
        )
        mock_reg.get.return_value = mock_client

        fn = _unwrap("generate_images")
        [r async for r in fn(s)]
        assert s.is_generating is False
        assert len(s.images) == 0

    @pytest.mark.asyncio
    @patch("appkit_imagecreator.state.get_asyncdb_session")
    @patch("appkit_imagecreator.state.image_repo")
    @patch("appkit_imagecreator.state.generator_registry")
    async def test_cancelled_before_api(
        self, mock_reg, mock_repo, mock_session
    ) -> None:
        s = _StubImageGallery()
        s.prompt = "a cat"
        s.generator = "test-gen"

        mock_user = MagicMock()
        mock_user.user = MagicMock()
        mock_user.user.user_id = 1
        s._mock_user_session = mock_user

        # Set cancellation flag in advance; will be checked after snapshot
        s._generation_cancelled = True

        fn = _unwrap("generate_images")
        [r async for r in fn(s)]
        assert s.is_generating is False


# ===========================================================================
# download_image (background task, async generator)
# ===========================================================================
class TestDownloadImage:
    @pytest.mark.asyncio
    @patch("appkit_imagecreator.state.get_asyncdb_session")
    @patch("appkit_imagecreator.state.image_repo")
    async def test_image_not_found(self, mock_repo, mock_session) -> None:
        s = _StubImageGallery()
        s.images = []  # no images
        fn = _unwrap("download_image")
        results = [r async for r in fn(s, 999)]
        # Should yield error toast
        assert len(results) >= 1

    @pytest.mark.asyncio
    @patch("appkit_imagecreator.state.get_asyncdb_session")
    @patch("appkit_imagecreator.state.image_repo")
    async def test_db_image_not_found(self, mock_repo, mock_session) -> None:
        s = _StubImageGallery()
        img = _make_image(10)
        s.images = [img]

        mock_sess = AsyncMock()
        mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_sess)
        mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_repo.find_by_id = AsyncMock(return_value=None)

        fn = _unwrap("download_image")
        results = [r async for r in fn(s, 10)]
        assert len(results) >= 1

    @pytest.mark.asyncio
    @patch("appkit_imagecreator.state.get_asyncdb_session")
    @patch("appkit_imagecreator.state.image_repo")
    async def test_successful_download(self, mock_repo, mock_session) -> None:
        s = _StubImageGallery()
        img = _make_image(10)
        s.images = [img]

        mock_db_image = MagicMock()
        mock_db_image.image_data = b"raw-image-data"

        mock_sess = AsyncMock()
        mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_sess)
        mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_repo.find_by_id = AsyncMock(return_value=mock_db_image)

        fn = _unwrap("download_image")
        results = [r async for r in fn(s, 10)]
        # Should yield rx.download
        assert len(results) >= 1


# ===========================================================================
# delete_image_from_db (background task, async generator)
# ===========================================================================
class TestDeleteImageFromDb:
    @pytest.mark.asyncio
    @patch("appkit_imagecreator.state.get_asyncdb_session")
    @patch("appkit_imagecreator.state.image_repo")
    async def test_not_authenticated(self, mock_repo, mock_session) -> None:
        s = _StubImageGallery()
        s._current_user_id = 0
        fn = _unwrap("delete_image_from_db")
        [r async for r in fn(s, "1")]
        assert s.deleting_image_id == 0

    @pytest.mark.asyncio
    @patch("appkit_imagecreator.state.get_asyncdb_session")
    @patch("appkit_imagecreator.state.image_repo")
    async def test_successful_delete(self, mock_repo, mock_session) -> None:
        s = _StubImageGallery()
        s._current_user_id = 42
        img = _make_image(5)
        s.images = [img]
        s.history_images = [img]

        mock_sess = AsyncMock()
        mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_sess)
        mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_repo.delete_by_id_and_user = AsyncMock()

        fn = _unwrap("delete_image_from_db")
        [r async for r in fn(s, "5")]
        assert len(s.images) == 0
        assert len(s.history_images) == 0
        assert s.deleting_image_id == 0
        mock_repo.delete_by_id_and_user.assert_awaited_once_with(mock_sess, 5, 42)

    @pytest.mark.asyncio
    @patch("appkit_imagecreator.state.get_asyncdb_session")
    @patch("appkit_imagecreator.state.image_repo")
    async def test_delete_error(self, mock_repo, mock_session) -> None:
        s = _StubImageGallery()
        s._current_user_id = 42

        mock_sess = AsyncMock()
        mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_sess)
        mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_repo.delete_by_id_and_user = AsyncMock(side_effect=RuntimeError("DB err"))

        fn = _unwrap("delete_image_from_db")
        [r async for r in fn(s, "1")]
        # Should yield error toast; deleting_image_id reset in finally
        assert s.deleting_image_id == 0


# ===========================================================================
# _process_upload_files (async)
# ===========================================================================
class TestProcessUploadFiles:
    @pytest.mark.asyncio
    @patch("appkit_imagecreator.state.get_asyncdb_session")
    @patch("appkit_imagecreator.state.image_repo")
    @patch("appkit_imagecreator.state.Image")
    async def test_successful_upload(
        self, mock_pil_image, mock_repo, mock_session
    ) -> None:
        s = _StubImageGallery()

        mock_file = AsyncMock()
        mock_file.filename = "test.png"
        mock_file.content_type = "image/png"
        mock_file.size = 1024
        mock_file.read = AsyncMock(return_value=b"png-data")

        mock_img = MagicMock()
        mock_img.size = (800, 600)
        mock_pil_image.open.return_value = mock_img

        mock_sess = AsyncMock()
        mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_sess)
        mock_session.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_saved = MagicMock()
        mock_saved.id = 55
        mock_repo.create = AsyncMock(return_value=mock_saved)

        uploaded_ids, skipped = await ImageGalleryState._process_upload_files(
            s, [mock_file], user_id=1
        )
        assert uploaded_ids == [55]
        assert skipped == []

    @pytest.mark.asyncio
    @patch("appkit_imagecreator.state.get_asyncdb_session")
    @patch("appkit_imagecreator.state.image_repo")
    async def test_skips_invalid_type(self, mock_repo, mock_session) -> None:
        s = _StubImageGallery()

        mock_file = AsyncMock()
        mock_file.filename = "doc.pdf"
        mock_file.content_type = "application/pdf"
        mock_file.size = 1024

        mock_sess = AsyncMock()
        mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_sess)
        mock_session.return_value.__aexit__ = AsyncMock(return_value=False)

        uploaded_ids, skipped = await ImageGalleryState._process_upload_files(
            s, [mock_file], user_id=1
        )
        assert uploaded_ids == []
        assert len(skipped) == 1
        assert "unsupported" in skipped[0]

    @pytest.mark.asyncio
    @patch("appkit_imagecreator.state.get_asyncdb_session")
    @patch("appkit_imagecreator.state.image_repo")
    @patch("appkit_imagecreator.state.Image")
    async def test_handles_processing_error(
        self, mock_pil_image, mock_repo, mock_session
    ) -> None:
        s = _StubImageGallery()

        mock_file = AsyncMock()
        mock_file.filename = "broken.png"
        mock_file.content_type = "image/png"
        mock_file.size = 1024
        mock_file.read = AsyncMock(side_effect=RuntimeError("read fail"))

        mock_sess = AsyncMock()
        mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_sess)
        mock_session.return_value.__aexit__ = AsyncMock(return_value=False)

        uploaded_ids, skipped = await ImageGalleryState._process_upload_files(
            s, [mock_file], user_id=1
        )
        assert uploaded_ids == []
        assert len(skipped) == 1
        assert "error" in skipped[0]
