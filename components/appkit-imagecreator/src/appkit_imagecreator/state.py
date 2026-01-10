"""State management for the image gallery.

This module contains ImageGalleryState which manages:
- Image generation and storage
- Style/quality/count popup states
- Image grid display and zoom functionality
"""

from __future__ import annotations

import contextlib
import io
import locale
import logging
from collections import defaultdict
from collections.abc import AsyncGenerator
from datetime import date
from typing import Any

import httpx
import reflex as rx
from PIL import Image

from appkit_commons.database.session import get_asyncdb_session
from appkit_imagecreator.backend.generator_registry import generator_registry
from appkit_imagecreator.backend.models import (
    GeneratedImage,
    GeneratedImageData,
    GeneratedImageModel,
    GenerationInput,
    ImageGeneratorResponse,
    ImageResponseState,
)
from appkit_imagecreator.backend.repository import image_repo
from appkit_imagecreator.configuration import styles_preset
from appkit_user.authentication.states import UserSession

logger = logging.getLogger(__name__)

# Image size presets
SIZE_OPTIONS: list[dict[str, str | int]] = [
    {"label": "Square (1024x1024)", "width": 1024, "height": 1024},
    {"label": "Portrait (1024x1536)", "width": 1024, "height": 1536},
    {"label": "Landscape (1536x1024)", "width": 1536, "height": 1024},
]
QUALITY_OPTIONS: list[str] = ["Auto", "High", "Medium", "Low"]
COUNT_OPTIONS: list[int] = [1, 2, 3, 4]

# Upload constraints
MAX_REFERENCE_IMAGES = 8
MAX_FILES = 5
MAX_SIZE_MB = 20
MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024
ALLOWED_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})
ALLOWED_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".webp"})

# Content type mapping by extension
CONTENT_TYPE_MAP = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


class ImageGalleryState(rx.State):
    """State for the image gallery UI.

    Manages image generation, storage, and UI interactions including
    popup menus for style, size, quality, and count selection.
    """

    # Stored images (today's images for grid)
    images: list[GeneratedImageModel] = []
    # All images for history
    history_images: list[GeneratedImageModel] = []
    loading_images: bool = False

    # Upload state
    is_uploading: bool = False

    # Generation state
    is_generating: bool = False
    prompt: str = ""
    generating_prompt: str = ""  # The prompt being generated (for display)

    # Style selection
    selected_style: str = ""
    style_popup_open: bool = False
    styles_preset: dict[str, dict[str, str]] = styles_preset

    # Config popup state
    config_popup_open: bool = False
    selected_size: str = "Square (1024x1024)"
    selected_width: int = 1024
    selected_height: int = 1024
    selected_quality: str = "Auto"

    # Count popup state
    count_popup_open: bool = False
    selected_count: int = 1

    # Prompt enhancement
    enhance_prompt: bool = True

    # Model selection
    generator: str = generator_registry.get_default_generator().id
    generators: list[dict[str, str]] = generator_registry.list_generators()

    # Zoom modal state
    zoom_modal_open: bool = False
    zoom_image: GeneratedImageModel | None = None

    # Selected images for prompt (image-to-image)
    selected_images: list[GeneratedImageModel] = []

    # History drawer state
    history_drawer_open: bool = False
    deleting_image_id: int

    # Initialization
    _initialized: bool = False
    _current_user_id: int = 0

    # -------------------------------------------------------------------------
    # Computed properties
    # -------------------------------------------------------------------------

    @rx.var
    def has_images(self) -> bool:
        """Check if there are any images."""
        return len(self.images) > 0

    @rx.var
    def count_label(self) -> str:
        """Label for the count selector."""
        return f"{self.selected_count}x"

    @rx.var
    def size_options(self) -> list[dict[str, Any]]:
        """Get available size options."""
        return SIZE_OPTIONS

    @rx.var
    def quality_options(self) -> list[str]:
        """Get available quality options."""
        return QUALITY_OPTIONS

    @rx.var
    def count_options(self) -> list[int]:
        """Get available count options."""
        return COUNT_OPTIONS

    @rx.var
    def is_edit_mode(self) -> bool:
        """Check if we're in edit mode (reference images selected)."""
        return len(self.selected_images) > 0

    @rx.var
    def selected_images_count(self) -> int:
        """Number of selected reference images."""
        return len(self.selected_images)

    # -------------------------------------------------------------------------
    # Helper methods
    # -------------------------------------------------------------------------

    def _find_image(self, image_id: int) -> GeneratedImageModel | None:
        """Find an image by ID in the current images list."""
        return next((img for img in self.images if img.id == image_id), None)

    def _find_history_image(self, image_id: int) -> GeneratedImageModel | None:
        """Find an image by ID in the history images list."""
        return next((img for img in self.history_images if img.id == image_id), None)

    def _close_all_popups(self) -> None:
        """Close all popup menus."""
        self.style_popup_open = False
        self.config_popup_open = False
        self.count_popup_open = False

    def _is_image_selected(self, image_id: int) -> bool:
        """Check if an image is already in selected images."""
        return any(s.id == image_id for s in self.selected_images)

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    @rx.event(background=True)
    async def initialize(self) -> AsyncGenerator[Any, Any]:
        """Initialize the image gallery - load images from database."""
        async for _ in self._load_images():
            yield

    async def _load_images(self) -> AsyncGenerator[Any, Any]:
        """Load images from database (internal)."""
        async with self:
            user_session: UserSession = await self.get_state(UserSession)

            # Ensure we have the latest user state before determining ID
            is_authenticated = await user_session.is_authenticated
            current_user_id = user_session.user.user_id if user_session.user else 0

            # Handle user change
            if self._current_user_id != current_user_id:
                logger.debug(
                    "User changed from '%s' to '%s' - resetting state",
                    self._current_user_id or "(none)",
                    current_user_id or "(none)",
                )
                self._initialized = False
                self._current_user_id = current_user_id
                self.images = []
                self.history_images = []
                yield

            if self._initialized:
                self.loading_images = False
                yield
                return

            self.loading_images = True

            # Check authentication
            if not is_authenticated:
                self.images = []
                self.history_images = []
                self._current_user_id = 0
                self.loading_images = False
                yield
                return

            user_id = current_user_id

        if not user_id:
            async with self:
                self.loading_images = False
            yield
            return

        # Fetch images from database
        try:
            async with get_asyncdb_session() as session:
                # Load today's images for grid
                today_entities = await image_repo.find_today_by_user(session, user_id)
                today_images = [
                    GeneratedImageModel.model_validate(img) for img in today_entities
                ]

                # Load all images for history
                all_raw_entities = await image_repo.find_by_user(session, user_id)
                all_images = [
                    GeneratedImageModel.model_validate(img) for img in all_raw_entities
                ]

            async with self:
                self.images = today_images
                self.history_images = all_images
                self._initialized = True
                logger.debug(
                    "Loaded %d today's images, %d total for user %s",
                    len(today_images),
                    len(all_images),
                    user_id,
                )
            yield
        except Exception as e:
            logger.error("Error loading images: %s", e)
            async with self:
                self.images = []
                self.history_images = []
            yield
        finally:
            async with self:
                self.loading_images = False
            yield

    # -------------------------------------------------------------------------
    # Popup handlers
    # -------------------------------------------------------------------------

    @rx.event
    def toggle_style_popup(self) -> None:
        """Toggle the style selection popup."""
        was_open = self.style_popup_open
        self._close_all_popups()
        self.style_popup_open = not was_open

    @rx.event
    def toggle_config_popup(self) -> None:
        """Toggle the config popup."""
        was_open = self.config_popup_open
        self._close_all_popups()
        self.config_popup_open = not was_open

    @rx.event
    def toggle_count_popup(self) -> None:
        """Toggle the count selection popup."""
        was_open = self.count_popup_open
        self._close_all_popups()
        self.count_popup_open = not was_open

    @rx.event
    def set_selected_style(self, style: str) -> None:
        """Set the selected style (toggle if same style selected)."""
        self.selected_style = "" if style == self.selected_style else style
        self.style_popup_open = False

    @rx.var
    def selected_style_path(self) -> str:
        """Get the image path from the styles_preset dictionary."""
        style_data = self.styles_preset.get(self.selected_style, {})
        path = style_data.get("path", "")
        if path and not path.startswith(("http", "/")):
            return f"/{path}"
        return path

    @rx.event
    def set_selected_size(self, size_label: str) -> None:
        """Set the selected size from label."""
        self.selected_size = size_label
        for opt in SIZE_OPTIONS:
            if opt["label"] == size_label:
                self.selected_width = opt["width"]
                self.selected_height = opt["height"]
                break

    @rx.event
    def set_selected_quality(self, quality: str) -> None:
        """Set the selected quality."""
        self.selected_quality = quality

    @rx.event
    def set_selected_count(self, value: list[int | float]) -> None:
        """Set the number of images to generate."""
        self.selected_count = int(value[0]) if value else 1

    # -------------------------------------------------------------------------
    # Generator selection
    # -------------------------------------------------------------------------

    @rx.event
    def set_generator(self, generator_id: str) -> None:
        """Set the selected generator/model."""
        self.generator = generator_id

    @rx.event
    def set_enhance_prompt(self, value: bool) -> None:
        """Set the enhance_prompt flag."""
        self.enhance_prompt = value

    @rx.event
    def clear_prompt(self) -> None:
        """Clear all selected reference images."""
        self.selected_images = []
        self.prompt = ""

    # -------------------------------------------------------------------------
    # Prompt handlers
    # -------------------------------------------------------------------------

    @rx.event
    def set_prompt(self, prompt: str) -> None:
        """Set the prompt text."""
        self.prompt = prompt

    @rx.event
    def cancel_generation(self) -> None:
        """Cancel the current image generation."""
        self.is_generating = False
        self.generating_prompt = ""

    # -------------------------------------------------------------------------
    # Image generation
    # -------------------------------------------------------------------------

    async def _get_image_bytes(self, img_data: GeneratedImageData) -> bytes | None:
        """Extract bytes from GeneratedImageData, fetching from URL if needed.

        Args:
            img_data: Generated image data with either bytes or external URL

        Returns:
            Raw image bytes or None if extraction failed
        """
        if img_data.image_bytes:
            return img_data.image_bytes

        if img_data.external_url:
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(img_data.external_url, timeout=60.0)
                    resp.raise_for_status()
                    return resp.content
            except httpx.HTTPError as e:
                logger.error("Failed to fetch image from URL: %s", e)
                return None

        return None

    @rx.event(background=True)
    async def generate_images(  # noqa: PLR0912, PLR0915
        self,
    ) -> AsyncGenerator[Any, Any]:
        """Generate or edit images based on current settings.

        If selected_images is not empty, uses the edit API with those images
        as references. Otherwise, generates new images from scratch.
        """
        # Validation
        async with self:
            if not self.prompt.strip():
                yield rx.toast.warning("Bitte gib einen Prompt ein.", close_button=True)
                return

            self.is_generating = True
            self.generating_prompt = self.prompt
            self._close_all_popups()
        yield

        try:
            # Get user info
            async with self:
                user_session: UserSession = await self.get_state(UserSession)
                user_id = user_session.user.user_id if user_session.user else None

            if not user_id:
                yield rx.toast.error(
                    "Bitte melde dich an, um Bilder zu generieren.",
                    close_button=True,
                )
                return

            # Build generation input
            async with self:
                style_prompt = ""
                if self.selected_style and self.selected_style in self.styles_preset:
                    style_prompt = (
                        "\n" + self.styles_preset[self.selected_style]["prompt"]
                    )

                full_prompt = self.prompt + style_prompt

                # Check for reference images (image-to-image mode)
                has_references = len(self.selected_images) > 0
                reference_ids = [
                    img.id for img in self.selected_images[:MAX_REFERENCE_IMAGES]
                ]

                # Warn if more than max images selected
                if len(self.selected_images) > MAX_REFERENCE_IMAGES:
                    yield rx.toast.info(
                        f"Maximal {MAX_REFERENCE_IMAGES} Referenzbilder "
                        "werden verwendet.",
                        close_button=True,
                    )

                generation_input = GenerationInput(
                    prompt=full_prompt,
                    width=self.selected_width,
                    height=self.selected_height,
                    n=self.selected_count,
                    enhance_prompt=self.enhance_prompt,
                    reference_image_ids=reference_ids,
                )
                client = generator_registry.get(self.generator)

                # Capture state values for database save
                prompt = self.prompt
                style = self.selected_style
                model = self.generator
                width = self.selected_width
                height = self.selected_height
                quality = self.selected_quality
                should_enhance = self.enhance_prompt
                count = self.selected_count

            # Branch based on whether we have reference images
            if has_references:
                # Fetch reference image bytes from database
                reference_images: list[tuple[bytes, str]] = []
                async with get_asyncdb_session() as session:
                    for img_id in reference_ids:
                        result = await image_repo.find_by_id(session, img_id)
                        if result:
                            reference_images.append(
                                (result.image_data, result.content_type)
                            )
                        else:
                            logger.warning(
                                "Reference image %d not found in database", img_id
                            )

                if not reference_images:
                    async with self:
                        self.is_generating = False
                    yield rx.toast.error(
                        "Referenzbilder konnten nicht geladen werden.",
                        close_button=True,
                    )
                    return

                logger.debug(
                    "Editing with %d reference images",
                    len(reference_images),
                )

                # Call edit API
                response: ImageGeneratorResponse = await client.edit(
                    generation_input, reference_images
                )
            else:
                # Standard generation (no references)
                response = await client.generate(generation_input)

            if response.state != ImageResponseState.SUCCEEDED:
                async with self:
                    self.is_generating = False
                yield rx.toast.error(
                    f"Fehler beim Generieren: {response.error or 'Unbekannter Fehler'}",
                    close_button=True,
                )
                return

            if not response.generated_images:
                async with self:
                    self.is_generating = False
                yield rx.toast.error(
                    "Keine Bilder generiert.",
                    close_button=True,
                )
                return

            # Save each generated image to database
            enhanced_prompt = response.enhanced_prompt or full_prompt
            saved_count = 0

            for img_data in response.generated_images:
                image_bytes = await self._get_image_bytes(img_data)
                if not image_bytes:
                    logger.warning("Could not get bytes for generated image")
                    continue

                try:
                    # Build config dict with optional reference image info
                    config_dict: dict[str, Any] = {
                        "size": f"{width}x{height}",
                        "quality": quality,
                        "count": count,
                        "enhance_prompt": should_enhance,
                    }
                    if has_references:
                        config_dict["reference_image_ids"] = reference_ids

                    async with get_asyncdb_session() as session:
                        new_image = GeneratedImage(
                            user_id=user_id,
                            prompt=prompt,
                            model=model,
                            image_data=image_bytes,
                            content_type=img_data.content_type,
                            width=width,
                            height=height,
                            enhanced_prompt=enhanced_prompt,
                            style=style if style else None,
                            quality=quality if quality != "Auto" else None,
                            config=config_dict,
                        )
                        saved_entity = await image_repo.create(session, new_image)
                        saved_image = GeneratedImageModel.model_validate(saved_entity)
                    async with self:
                        self.images = [saved_image, *self.images]
                        self.history_images = [saved_image, *self.history_images]
                    saved_count += 1
                    yield
                except Exception as e:
                    logger.error("Error saving generated image: %s", e)

            if saved_count > 0:
                yield rx.toast.success(
                    f"{saved_count} Bild(er) erfolgreich generiert!",
                    close_button=True,
                )
            else:
                yield rx.toast.error(
                    "Keine Bilder konnten gespeichert werden.",
                    close_button=True,
                )

        except Exception as e:
            logger.exception("Error generating images")
            yield rx.toast.error(
                f"Fehler beim Generieren: {e!s}",
                close_button=True,
            )
        finally:
            async with self:
                self.is_generating = False
                self.generating_prompt = ""
            yield

    # -------------------------------------------------------------------------
    # Image management
    # -------------------------------------------------------------------------

    @rx.event()
    async def clear_grid_view(self) -> AsyncGenerator[Any, Any]:
        """Clear all images for the current user."""
        self.images = []
        self.zoom_modal_open = False
        self.zoom_image = None

    # -------------------------------------------------------------------------
    # Zoom modal handlers
    # -------------------------------------------------------------------------

    @rx.event
    def open_zoom_modal(self, image_id: int) -> None:
        """Open the zoom modal for a specific image."""
        if img := self._find_image(image_id):
            self.zoom_image = img
            self.zoom_modal_open = True

    @rx.event
    def close_zoom_modal(self) -> None:
        """Close the zoom modal."""
        self.zoom_modal_open = False
        self.zoom_image = None

    # -------------------------------------------------------------------------
    # Image action handlers (hover actions)
    # -------------------------------------------------------------------------

    @rx.event
    def add_image_to_prompt(self, image_id: int) -> None:
        """Add an image to the selected images for image-to-image generation."""
        if self._is_image_selected(image_id):
            return
        if img := self._find_image(image_id):
            self.selected_images = [*self.selected_images, img]

    @rx.event
    def remove_image_from_prompt(self, image_id: int) -> None:
        """Remove an image from the selected images."""
        self.selected_images = [s for s in self.selected_images if s.id != image_id]

    async def handle_upload(
        self, files: list[rx.UploadFile]
    ) -> AsyncGenerator[Any, Any]:
        """Handle uploaded reference images."""
        user_session: UserSession = await self.get_state(UserSession)
        user_id = user_session.user.user_id if user_session.user else 0

        if not user_id:
            yield rx.toast.error("Authentication required", close_button=True)
            return

        files_to_process = files[:MAX_FILES]
        exceeded_limit = len(files) > MAX_FILES

        self.is_uploading = True
        yield

        uploaded_ids, skipped = await self._process_upload_files(
            files_to_process, user_id
        )

        self._initialized = False
        async for _ in self._load_images():
            yield

        self._auto_select_uploaded_images(uploaded_ids)

        self.is_uploading = False
        yield

        for result in self._show_upload_results(
            len(uploaded_ids), skipped, exceeded_limit
        ):
            yield result

    async def _process_upload_files(
        self, files: list[rx.UploadFile], user_id: int
    ) -> tuple[list[int], list[str]]:
        """Process and save uploaded files. Returns (uploaded_ids, skipped_files)."""
        uploaded_ids: list[int] = []
        skipped: list[str] = []

        async with get_asyncdb_session() as session:
            for file in files:
                filename = file.filename or "unknown"
                ext_idx = filename.rfind(".")
                file_ext = filename[ext_idx:].lower() if ext_idx >= 0 else ""

                skip_reason = self._validate_upload_file(file, file_ext)
                if skip_reason:
                    skipped.append(f"{filename} ({skip_reason})")
                    logger.warning("Skipped %s: %s", filename, skip_reason)
                    continue

                try:
                    image_data = await file.read()
                    img = Image.open(io.BytesIO(image_data))
                    content_type = CONTENT_TYPE_MAP.get(
                        file_ext, file.content_type or "image/png"
                    )

                    image_entity = GeneratedImage(
                        user_id=user_id,
                        prompt="",
                        model="",
                        image_data=image_data,
                        content_type=content_type,
                        width=img.size[0],
                        height=img.size[1],
                        style=None,
                        enhanced_prompt=None,
                        quality=None,
                        config=None,
                        is_uploaded=True,
                    )
                    saved = await image_repo.create(session, image_entity)
                    uploaded_ids.append(saved.id)
                    logger.debug("Uploaded %s for user %d", filename, user_id)
                except Exception as e:
                    skipped.append(f"{filename} (error: {e!s})")
                    logger.exception("Failed to process %s", filename)

        return uploaded_ids, skipped

    @staticmethod
    def _validate_upload_file(file: rx.UploadFile, file_ext: str) -> str | None:
        """Validate file type and size. Returns error reason or None if valid."""
        is_valid_type = (
            file.content_type in ALLOWED_TYPES or file_ext in ALLOWED_EXTENSIONS
        )
        if not is_valid_type:
            return "unsupported format"
        if file.size and file.size > MAX_SIZE_BYTES:
            return f"exceeds {MAX_SIZE_MB}MB limit"
        return None

    def _auto_select_uploaded_images(self, uploaded_ids: list[int]) -> None:
        """Auto-select uploaded images."""
        for img_id in uploaded_ids:
            if self._is_image_selected(img_id):
                continue
            if img := self._find_image(img_id):
                self.selected_images = [*self.selected_images, img]

    @staticmethod
    def _show_upload_results(
        uploaded_count: int, skipped: list[str], exceeded_limit: bool
    ) -> list[rx.event.EventSpec]:
        """Generate toast notifications for upload results."""
        results = []
        if uploaded_count > 0:
            msg = f"Uploaded {uploaded_count} image(s)"
            if skipped:
                msg += f", skipped {len(skipped)}"
                results.append(rx.toast.warning(msg, close_button=True))
            else:
                results.append(rx.toast.success(msg, close_button=True))
        elif skipped:
            results.append(
                rx.toast.error(f"Failed: {', '.join(skipped[:3])}", close_button=True)
            )
        if exceeded_limit:
            results.append(
                rx.toast.info(
                    f"Only first {MAX_FILES} images uploaded", close_button=True
                )
            )
        return results

    @rx.event
    def copy_config_to_prompt(self, image_id: int) -> None:
        """Copy the prompt and configuration from an image to the input fields."""
        img = self._find_image(image_id)
        if not img:
            return

        self.prompt = img.prompt
        self.selected_style = img.style or ""
        self.selected_quality = img.quality or "Auto"
        self.selected_width = img.width
        self.selected_height = img.height
        self.generator = img.model

        # Find matching size label
        for opt in SIZE_OPTIONS:
            if opt["width"] == img.width and opt["height"] == img.height:
                self.selected_size = opt["label"]
                break

        # Restore count and enhance_prompt from config if available
        if img.config:
            self.selected_count = img.config.get("count", self.selected_count)
            self.enhance_prompt = img.config.get("enhance_prompt", self.enhance_prompt)

    @rx.event
    def remove_image_from_view(self, image_id: int) -> None:
        """Remove an image from the current view (doesn't delete from DB)."""
        self.images = [img for img in self.images if img.id != image_id]
        # Also remove from selected if present
        self.selected_images = [s for s in self.selected_images if s.id != image_id]

    @rx.event(background=True)
    async def download_image(self, image_id: int) -> AsyncGenerator[Any, Any]:
        """Download an image file."""
        async with self:
            image = self._find_image(image_id)

        if not image:
            yield rx.toast.error("Bild nicht gefunden", close_button=True)
            return

        try:
            # Fetch image data from repository
            async with get_asyncdb_session() as session:
                db_image = await image_repo.find_by_id(session, image_id)

            if db_image is None:
                yield rx.toast.error("Bilddaten nicht gefunden", close_button=True)
                return

            image_data = db_image.image_data
            filename = f"image_{image.id}.png"
            # Download raw binary data
            yield rx.download(data=image_data, filename=filename)
        except Exception as e:
            logger.error("Error downloading image: %s", e)
            yield rx.toast.error(f"Fehler beim Download: {e!s}", close_button=True)

    # -------------------------------------------------------------------------
    # History drawer handlers
    # -------------------------------------------------------------------------

    @rx.event
    def toggle_history(self) -> None:
        """Toggle the history drawer."""
        self.history_drawer_open = not self.history_drawer_open

    @rx.event
    def close_history_drawer(self) -> None:
        """Close the history drawer."""
        self.history_drawer_open = False

    @rx.event(background=True)
    async def delete_image_from_db(self, image_id: str) -> AsyncGenerator[Any, Any]:
        """Delete an image from the database and update both lists."""
        async with self:
            user_id = self._current_user_id
            if not user_id:
                logger.warning("Cannot delete image: user not authenticated")
                yield rx.toast.error("Nicht autorisiert.", close_button=True)
                return

            self.deleting_image_id = image_id
        yield

        try:
            logger.debug("Deleting image from database: %s", image_id)
            async with get_asyncdb_session() as session:
                await image_repo.delete_by_id_and_user(session, int(image_id), user_id)

            async with self:
                # Remove from both lists
                self.images = [img for img in self.images if img.id != int(image_id)]
                self.history_images = [
                    img for img in self.history_images if img.id != int(image_id)
                ]
                logger.debug("Image deleted successfully: %s", image_id)

            yield rx.toast.success("Bild gelöscht.", close_button=True)

        except Exception as e:
            logger.error("Error deleting image: %s", e)
            yield rx.toast.error(f"Fehler beim Löschen: {e!s}", close_button=True)
        finally:
            async with self:
                # Clear loading overlay
                self.deleting_image_id = ""
            yield

    @rx.event
    def add_history_image_to_grid(self, image_id: str) -> None:
        """Add an image from history to the main grid."""
        int_id = int(image_id)
        if self._find_image(int_id):
            return  # Already in grid
        if img := self._find_history_image(int_id):
            self.images = [img, *self.images]
            logger.debug("Added history image %s to grid", image_id)

    @rx.var
    def history_images_by_date(self) -> list[tuple[str, list[GeneratedImageModel]]]:
        """Group history images by date, sorted descending."""
        if not self.history_images:
            return []

        grouped: dict[date, list[GeneratedImageModel]] = defaultdict(list)
        for img in self.history_images:
            if img.created_at:
                grouped[img.created_at.date()].append(img)

        sorted_groups = sorted(grouped.items(), key=lambda x: x[0], reverse=True)

        return [
            (self._format_date_label(date_key), imgs)
            for date_key, imgs in sorted_groups
        ]

    @staticmethod
    def _format_date_label(d: date) -> str:
        """Format date as German label (e.g., '2. Jan. 2026')."""
        with contextlib.suppress(locale.Error):
            locale.setlocale(locale.LC_TIME, "de_DE.UTF-8")
        return d.strftime("%-d. %b %Y")
