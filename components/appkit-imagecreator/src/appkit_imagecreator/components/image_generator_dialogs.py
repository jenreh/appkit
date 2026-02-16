"""Dialog components for image generator model management."""

import json
import logging

import reflex as rx

import appkit_mantine as mn
from appkit_imagecreator.admin_state import ImageGeneratorAdminState
from appkit_imagecreator.backend.models import ImageGeneratorModel
from appkit_ui.components.dialogs import delete_dialog
from appkit_ui.components.form_inputs import form_field

logger = logging.getLogger(__name__)


class ImageGeneratorValidationState(rx.State):
    """Validation state for image generator add/edit forms."""

    model_id: str = ""
    model: str = ""
    label: str = ""
    processor_type: str = ""
    api_key: str = ""
    base_url: str = ""
    extra_config: str = ""
    required_role: str = ""
    is_edit: bool = False

    model_id_error: str = ""
    label_error: str = ""
    processor_type_error: str = ""
    api_key_error: str = ""
    extra_config_error: str = ""

    @rx.event
    def initialize(self, generator: ImageGeneratorModel | None = None) -> None:
        """Reset validation state for add or edit mode."""
        self.is_edit = generator is not None
        if generator is None:
            self.model_id = ""
            self.model = ""
            self.label = ""
            self.processor_type = ""
            self.api_key = ""
            self.base_url = ""
            self.extra_config = ""
            self.required_role = ""
        else:
            self.model_id = generator.model_id
            self.model = generator.model or ""
            self.label = generator.label
            self.processor_type = generator.processor_type
            self.api_key = generator.api_key or ""
            self.base_url = generator.base_url or ""
            self.extra_config = (
                json.dumps(generator.extra_config, indent=2)
                if generator.extra_config
                else ""
            )
            self.required_role = generator.required_role or ""

        self.model_id_error = ""
        self.label_error = ""
        self.processor_type_error = ""
        self.api_key_error = ""
        self.extra_config_error = ""

    # --- Field setters with inline validation ---

    def set_model_id(self, value: str) -> None:
        self.model_id = value
        self.validate_model_id()

    def set_model(self, value: str) -> None:
        self.model = value

    def set_label(self, value: str) -> None:
        self.label = value
        self.validate_label()

    def set_processor_type(self, value: str) -> None:
        self.processor_type = value
        self.validate_processor_type()

    def set_api_key(self, value: str) -> None:
        self.api_key = value

    def set_base_url(self, value: str) -> None:
        self.base_url = value

    def set_extra_config(self, value: str) -> None:
        self.extra_config = value

    def set_required_role(self, value: str) -> None:
        self.required_role = value

    # --- Validators ---

    @rx.event
    def validate_model_id(self) -> None:
        if not self.model_id or not self.model_id.strip():
            self.model_id_error = "Die Modell-ID darf nicht leer sein."
        else:
            self.model_id_error = ""

    @rx.event
    def validate_label(self) -> None:
        if not self.label or not self.label.strip():
            self.label_error = "Das Label darf nicht leer sein."
        else:
            self.label_error = ""

    @rx.event
    def validate_processor_type(self) -> None:
        if not self.processor_type or not self.processor_type.strip():
            self.processor_type_error = "Der Prozessortyp darf nicht leer sein."
        elif "." not in self.processor_type:
            self.processor_type_error = (
                "Vollqualifizierter Klassenname erforderlich (z.B. modul.Klasse)."
            )
        else:
            self.processor_type_error = ""

    @rx.event
    def validate_extra_config(self) -> None:
        if not self.extra_config or not self.extra_config.strip():
            self.extra_config_error = ""
            return
        try:
            parsed = json.loads(self.extra_config)
            if not isinstance(parsed, dict):
                self.extra_config_error = "Muss ein JSON-Objekt sein."
            else:
                self.extra_config_error = ""
        except json.JSONDecodeError:
            self.extra_config_error = "Ungültiges JSON-Format."

    @rx.var
    def has_errors(self) -> bool:
        return bool(
            self.model_id_error
            or self.label_error
            or self.processor_type_error
            or self.api_key_error
            or self.extra_config_error
        )


# --- Known processor types for convenience ---
KNOWN_PROCESSORS = [
    {
        "value": ("appkit_imagecreator.backend.generators.openai.OpenAIImageGenerator"),
        "label": "OpenAI Image Generator",
    },
    {
        "value": (
            "appkit_imagecreator.backend.generators"
            ".nano_banana.NanoBananaImageGenerator"
        ),
        "label": "Google Nano Banana",
    },
    {
        "value": (
            "appkit_imagecreator.backend.generators"
            ".black_forest_labs.BlackForestLabsImageGenerator"
        ),
        "label": "Black Forest Labs",
    },
]


def _role_select() -> rx.Component:
    """Role selection dropdown for generator access control."""
    return mn.select(
        label="Erforderliche Rolle",
        description=(
            "Nur Benutzer mit dieser Rolle können diesen Generator verwenden."
        ),
        data=ImageGeneratorAdminState.available_roles,
        value=ImageGeneratorValidationState.required_role,
        on_change=ImageGeneratorValidationState.set_required_role,
        placeholder="Rolle auswählen",
        clearable=True,
        name="required_role",
        width="100%",
    )


def _processor_type_field() -> rx.Component:
    """Processor type select with known generator types."""
    return mn.select(
        label="Prozessortyp",
        description="Generator-Implementierung auswählen",
        data=KNOWN_PROCESSORS,
        value=ImageGeneratorValidationState.processor_type,
        on_change=ImageGeneratorValidationState.set_processor_type,
        error=ImageGeneratorValidationState.processor_type_error,
        placeholder="Prozessortyp auswählen",
        required=True,
        allow_deselect=False,
        name="processor_type",
        width="100%",
    )


def _modal_footer(
    submit_label: str,
    on_cancel: rx.EventHandler,
) -> rx.Component:
    """Footer buttons for add/edit modals."""
    return rx.flex(
        mn.button(
            "Abbrechen",
            variant="subtle",
            on_click=on_cancel,
        ),
        mn.button(
            submit_label,
            type="submit",
            disabled=ImageGeneratorValidationState.has_errors,
        ),
        direction="row",
        gap="9px",
        justify_content="end",
        margin_top="12px",
    )


def image_generator_form_fields() -> rx.Component:
    """Reusable form fields for add/edit modals."""
    return rx.flex(
        form_field(
            name="label",
            icon="tag",
            label="Label",
            hint="Anzeige-Label in der UI",
            type="text",
            placeholder="OpenAI GPT-Image-1.5",
            value=ImageGeneratorValidationState.label,
            required=True,
            max_length=100,
            on_change=ImageGeneratorValidationState.set_label,
            on_blur=ImageGeneratorValidationState.validate_label,
            validation_error=ImageGeneratorValidationState.label_error,
        ),
        form_field(
            name="model_id",
            icon="hash",
            label="Modell-ID",
            hint="Technische ID des Modells (z.B. gpt-image-1.5)",
            type="text",
            placeholder="gpt-image-1.5",
            value=ImageGeneratorValidationState.model_id,
            required=True,
            max_length=100,
            on_change=ImageGeneratorValidationState.set_model_id,
            on_blur=ImageGeneratorValidationState.validate_model_id,
            validation_error=ImageGeneratorValidationState.model_id_error,
        ),
        form_field(
            name="model",
            icon="box",
            label="Modell",
            hint="API-Modellname (z.B. FLUX.1-Kontext-pro)",
            type="text",
            placeholder="gpt-image-1.5",
            value=ImageGeneratorValidationState.model,
            max_length=100,
            on_change=ImageGeneratorValidationState.set_model,
        ),
        _processor_type_field(),
        form_field(
            name="api_key",
            icon="key",
            label="API-Schlüssel",
            hint="Wird verschlüsselt gespeichert",
            type="password",
            placeholder="sk-...",
            value=ImageGeneratorValidationState.api_key,
            on_change=ImageGeneratorValidationState.set_api_key,
            autocomplete="new-password",
        ),
        form_field(
            name="base_url",
            icon="link",
            label="Base-URL",
            hint=("Optionale Basis-URL für den API-Endpunkt (z.B. Azure-Endpoint)"),
            type="text",
            placeholder="https://api.openai.com/v1",
            value=ImageGeneratorValidationState.base_url,
            on_change=ImageGeneratorValidationState.set_base_url,
        ),
        mn.json_input(
            name="extra_config",
            label="Extra-Konfiguration (JSON)",
            description=(
                "Zusätzliche Konfiguration als JSON-Objekt"
                ' (z.B. {"on_azure": true, '
                '"output_format": "jpeg"})'
            ),
            placeholder="{}",
            value=ImageGeneratorValidationState.extra_config,
            on_change=ImageGeneratorValidationState.set_extra_config,
            on_blur=ImageGeneratorValidationState.validate_extra_config,
            error=ImageGeneratorValidationState.extra_config_error,
            format_on_blur=True,
            autosize=True,
            min_rows=3,
            max_rows=8,
            width="100%",
        ),
        _role_select(),
        direction="column",
        spacing="1",
    )


def add_image_generator_button() -> rx.Component:
    """Button that opens the add generator modal."""
    return mn.button(
        "Neuen Bildgenerator anlegen",
        left_section=rx.icon("plus", size=16),
        size="sm",
        on_click=[
            ImageGeneratorValidationState.initialize(generator=None),
            ImageGeneratorAdminState.open_add_modal,
        ],
    )


def add_image_generator_modal() -> rx.Component:
    """Modal for adding a new image generator."""
    return mn.modal(
        rx.form.root(
            mn.scroll_area(
                image_generator_form_fields(),
                h="60vh",
                w="100%",
            ),
            _modal_footer(
                "Bildgenerator anlegen",
                ImageGeneratorAdminState.close_add_modal,
            ),
            on_submit=ImageGeneratorAdminState.add_generator,
            reset_on_submit=False,
        ),
        title="Neuen Bildgenerator anlegen",
        opened=ImageGeneratorAdminState.add_modal_open,
        on_close=ImageGeneratorAdminState.close_add_modal,
        size="lg",
        centered=True,
        overlay_props={"backgroundOpacity": 0.5, "blur": 4},
    )


def edit_image_generator_modal() -> rx.Component:
    """Modal for editing an existing image generator."""
    return mn.modal(
        rx.form.root(
            mn.scroll_area(
                image_generator_form_fields(),
                h="60vh",
                w="100%",
            ),
            _modal_footer(
                "Bildgenerator aktualisieren",
                ImageGeneratorAdminState.close_edit_modal,
            ),
            on_submit=ImageGeneratorAdminState.modify_generator,
            reset_on_submit=False,
        ),
        title="Bildgenerator aktualisieren",
        opened=ImageGeneratorAdminState.edit_modal_open,
        on_close=ImageGeneratorAdminState.close_edit_modal,
        size="lg",
        centered=True,
        overlay_props={"backgroundOpacity": 0.5, "blur": 4},
    )


def delete_image_generator_dialog(
    generator: ImageGeneratorModel,
) -> rx.Component:
    """Confirmation dialog for deleting an image generator."""
    return delete_dialog(
        title="Bildgenerator löschen",
        content=generator.label,
        on_click=lambda: ImageGeneratorAdminState.delete_generator(generator.id),
        icon_button=True,
        variant="ghost",
        color_scheme="red",
    )
