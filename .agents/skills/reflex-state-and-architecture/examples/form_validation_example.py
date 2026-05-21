"""
Form Validation — canonical pattern.

Derived from: alloq-team EmployeeValidationState.

Use this pattern when:
  - A modal or drawer contains an add/edit form.
  - Fields need per-field inline error display.
  - Some fields require async DB uniqueness checks (e.g. email).
  - The submit button must be disabled until the form is valid.

Key rules:
  - Use a DEDICATED rx.State subclass (not mixed into the main feature state).
  - Store all fields as str — inputs are always strings; parse/validate explicitly.
  - Per-field error is a str — empty string means no error.
  - Decorate validate_* methods with @rx.event so the UI can call them on on_blur.
  - Async DB uniqueness checks go in validate_<field>_unique — attach to on_blur,
    NOT on_change (avoids a DB hit on every keystroke).
  - form_version: int — increment in initialize() to force re-render of controlled
    inputs when resetting the form.
  - is_form_valid / is_form_invalid as @rx.var — use for enabling/disabling submit.
  - Call initialize() from the parent state's open_add_modal / open_edit_modal.
  - Call validate_all() before submit to surface all errors at once.
"""

import logging
from collections.abc import AsyncGenerator
from typing import Any

import reflex as rx
from alloq_commons.repositories.item_repository import item_repo
from alloq_feature.backend.entities import ItemEntity
from alloq_feature.models.item import Item

import appkit_mantine as mn
from appkit_commons.database.session import get_asyncdb_session

logger = logging.getLogger(__name__)


# ─── Validation state ─────────────────────────────────────────────────────────


class ItemValidationState(rx.State):
    """Isolated validation state for add/edit item forms."""

    form_version: int = 0  # increment on initialize() to force re-render

    # ── Fields ────────────────────────────────────────────────────────────────
    name: str = ""
    email: str = ""
    quantity: str = "1"

    # ── Errors (empty = no error) ─────────────────────────────────────────────
    name_error: str = ""
    email_error: str = ""
    quantity_error: str = ""

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    @rx.event
    def initialize(
        self,
        item: Item | None = None,
    ) -> None:
        """Reset or pre-fill the form. Call from parent state's open_*_modal."""
        if item is None:
            self.name = ""
            self.email = ""
            self.quantity = "1"
        else:
            self.name = item.name
            self.email = item.email or ""
            self.quantity = str(item.quantity)

        self.name_error = ""
        self.email_error = ""
        self.quantity_error = ""
        self.form_version += 1  # triggers re-render of controlled inputs

    # ── Setters — validate inline on every change ─────────────────────────────

    def set_name(self, value: str) -> None:
        self.name = value
        self.validate_name()

    def set_email(self, value: str) -> None:
        self.email = value
        self.validate_email()

    def set_quantity(self, value: str) -> None:
        self.quantity = value
        self.validate_quantity()

    # ── Validators — @rx.event so the UI can bind them to on_blur ─────────────

    @rx.event
    def validate_name(self) -> None:
        self.name_error = "Name darf nicht leer sein." if not self.name.strip() else ""

    @rx.event
    def validate_email(self) -> None:
        email = self.email.strip()
        if email and "@" not in email:
            self.email_error = "Bitte eine gültige E-Mail-Adresse eingeben."
        else:
            self.email_error = ""

    @rx.event
    async def validate_email_unique(self) -> None:
        """DB uniqueness check — attach to on_blur, NOT on_change."""
        email = self.email.strip()
        if not email or "@" not in email:
            return  # format check already done by validate_email

        # Get parent state to find the currently-edited item's ID (to exclude it)
        parent = await self.get_state(MyFeatureState)
        exclude_id = parent.selected_item.id if parent.selected_item else None

        async with get_asyncdb_session() as session:
            existing = await item_repo.find_by_email(
                session, email, exclude_id=exclude_id
            )
        self.email_error = "Diese E-Mail ist bereits vergeben." if existing else ""

    @rx.event
    def validate_quantity(self) -> None:
        try:
            val = int(self.quantity)
            self.quantity_error = "" if val >= 1 else "Muss mindestens 1 sein."
        except ValueError:
            self.quantity_error = "Muss eine ganze Zahl sein."

    @rx.event
    def validate_all(self) -> None:
        """Call before submit to surface all errors at once."""
        self.validate_name()
        self.validate_email()
        self.validate_quantity()

    # ── Computed vars — bind to submit button ─────────────────────────────────

    @rx.var
    def has_errors(self) -> bool:
        return bool(self.name_error or self.email_error or self.quantity_error)

    @rx.var
    def is_form_valid(self) -> bool:
        try:
            qty_valid = int(self.quantity) >= 1
        except ValueError:
            qty_valid = False
        return bool(self.name.strip() and qty_valid and not self.has_errors)

    @rx.var
    def is_form_invalid(self) -> bool:
        return not self.is_form_valid


# ─── Parent state — shows how to open/close and submit ────────────────────────


class MyFeatureState(rx.State):
    is_add_modal_open: bool = False
    is_edit_modal_open: bool = False
    selected_item: Item | None = None

    def open_add_modal(self) -> list[rx.event.EventSpec]:
        """Open add modal and reset form."""
        self.is_add_modal_open = True
        return [ItemValidationState.initialize()]  # no item → blank form

    def close_add_modal(self) -> None:
        self.is_add_modal_open = False

    def open_edit_modal(self, item: Item) -> list[rx.event.EventSpec]:
        """Open edit modal and pre-fill form with existing data."""
        self.selected_item = item
        self.is_edit_modal_open = True
        return [ItemValidationState.initialize(item)]  # item → pre-filled form

    def close_edit_modal(self) -> None:
        self.is_edit_modal_open = False
        self.selected_item = None

    @rx.event
    async def submit_item(self) -> AsyncGenerator[Any, None]:
        """Submit handler — guards with validate_all before proceeding."""
        form_state = await self.get_state(ItemValidationState)

        if form_state.is_form_invalid:
            # Surface all errors before bailing out
            yield ItemValidationState.validate_all()
            return

        # Proceed using validated values from form_state
        try:
            async with get_asyncdb_session() as session:
                if self.selected_item:
                    # Update existing
                    entity = await item_repo.find_by_id(session, self.selected_item.id)
                    entity.name = form_state.name
                    entity.email = form_state.email or None
                    entity.quantity = int(form_state.quantity)
                    await item_repo.update(session, entity)
                else:
                    # Create new
                    entity = ItemEntity(
                        name=form_state.name,
                        email=form_state.email or None,
                        quantity=int(form_state.quantity),
                    )
                    await item_repo.create(session, entity)

            self.close_add_modal()
            self.close_edit_modal()
            yield rx.toast.success("Gespeichert", position="top-right")
        except Exception as e:
            logger.error("Failed to save item: %s", e)
            yield rx.toast.error(f"Fehler: {e}", position="top-right")


# ─── UI — form component ──────────────────────────────────────────────────────


def item_form() -> rx.Component:
    """
    Form component for add/edit item modal.

    - Binds each input to the corresponding field in ItemValidationState.
    - Passes the error var directly to the `error` prop for inline display.
    - validate_email_unique is attached to on_blur (not on_change).
    - Submit button is disabled when is_form_invalid is True.
    """
    return mn.stack(
        mn.text_input(
            label="Name *",
            value=ItemValidationState.name,
            on_change=ItemValidationState.set_name,
            error=ItemValidationState.name_error,
        ),
        mn.text_input(
            label="E-Mail",
            value=ItemValidationState.email,
            on_change=ItemValidationState.set_email,
            on_blur=ItemValidationState.validate_email_unique,  # DB check on blur
            error=ItemValidationState.email_error,
        ),
        mn.number_input(
            label="Menge *",
            value=ItemValidationState.quantity,
            on_change=ItemValidationState.set_quantity,
            error=ItemValidationState.quantity_error,
            min=1,
        ),
        mn.group(
            mn.button(
                "Speichern",
                on_click=MyFeatureState.submit_item,
                disabled=ItemValidationState.is_form_invalid,
                variant="filled",
                size="2",
            ),
            mn.button(
                "Abbrechen",
                on_click=MyFeatureState.close_add_modal,
                variant="subtle",
                size="2",
            ),
            gap="sm",
        ),
        gap="sm",
    )


def add_item_modal() -> rx.Component:
    """Modal wrapper around the form — opened via MyFeatureState.open_add_modal."""
    return mn.modal(
        mn.modal.overlay(),
        mn.modal.content(
            mn.modal.header("Neues Element"),
            mn.modal.body(item_form()),
        ),
        opened=MyFeatureState.is_add_modal_open,
        on_close=MyFeatureState.close_add_modal,
    )
