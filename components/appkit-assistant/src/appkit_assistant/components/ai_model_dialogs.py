"""Dialog components for AI model management."""

import logging

import reflex as rx

import appkit_mantine as mn
from appkit_assistant.backend.database.models import AssistantAIModel
from appkit_assistant.state.ai_model_admin_state import AIModelAdminState
from appkit_ui.components.dialogs import delete_dialog
from appkit_ui.components.form_inputs import form_field

logger = logging.getLogger(__name__)

_MAX_TEMPERATURE: float = 2.0

# Known processor types offered in the dropdown
KNOWN_PROCESSOR_TYPES = [
    {"value": "openai", "label": "OpenAI"},
    {"value": "claude", "label": "Anthropic Claude"},
    {"value": "perplexity", "label": "Perplexity"},
    {"value": "gemini", "label": "Google Gemini"},
    {"value": "lorem_ipsum", "label": "Lorem Ipsum (Test)"},
]

# Suggested icons for convenience - still a free-text field
KNOWN_ICONS = [
    {"value": "openai", "label": "OpenAI"},
    {"value": "anthropic", "label": "Anthropic"},
    {"value": "perplexity", "label": "Perplexity"},
    {"value": "googlegemini", "label": "Google Gemini"},
    {"value": "codesandbox", "label": "Codesandbox (Standard)"},
]


# Processor → default icon mapping
PROCESSOR_DEFAULT_ICONS: dict[str, str] = {
    "openai": "openai",
    "claude": "anthropic",
    "perplexity": "perplexity",
    "gemini": "googlegemini",
    "lorem_ipsum": "codesandbox",
}


class AIModelValidationState(rx.State):
    """Validation state for add/edit AI model forms."""

    model_id: str = ""
    text: str = ""
    icon: str = ""
    model: str = ""
    processor_type: str = ""
    temperature: str = "0.05"
    stream: bool = False
    supports_tools: bool = False
    supports_attachments: bool = False
    supports_search: bool = False
    supports_skills: bool = False
    requires_role: str = ""
    # API credentials (stored encrypted; leave blank to use global config)
    api_key: str = ""
    base_url: str = ""
    on_azure: bool = False

    model_id_error: str = ""
    text_error: str = ""
    processor_type_error: str = ""
    temperature_error: str = ""

    @rx.event
    def initialize(self, record: AssistantAIModel | None = None) -> None:
        """Reset validation state for add or edit mode."""
        if record is None:
            self.model_id = ""
            self.text = ""
            self.icon = ""
            self.model = ""
            self.processor_type = ""
            self.temperature = "0.05"
            self.stream = False
            self.supports_tools = False
            self.supports_attachments = False
            self.supports_search = False
            self.supports_skills = False
            self.requires_role = ""
            self.api_key = ""
            self.base_url = ""
            self.on_azure = False
        else:
            self.model_id = record.model_id
            self.text = record.text
            self.icon = record.icon or ""
            self.model = record.model or ""
            self.processor_type = record.processor_type
            self.temperature = str(record.temperature)
            self.stream = record.stream
            self.supports_tools = record.supports_tools
            self.supports_attachments = record.supports_attachments
            self.supports_search = record.supports_search
            self.supports_skills = record.supports_skills
            self.requires_role = record.requires_role or ""
            self.api_key = record.api_key or ""
            self.base_url = record.base_url or ""
            self.on_azure = record.on_azure

        self.model_id_error = ""
        self.text_error = ""
        self.processor_type_error = ""
        self.temperature_error = ""

    # --- Field setters with inline validation ---

    def set_model_id(self, value: str) -> None:
        self.model_id = value
        self.validate_model_id()

    def set_text(self, value: str) -> None:
        self.text = value
        self.validate_text()

    def set_icon(self, value: str) -> None:
        self.icon = value

    def set_model(self, value: str) -> None:
        self.model = value

    def set_processor_type(self, value: str) -> None:
        self.processor_type = value
        # Auto-set icon when it is still empty or the codesandbox default
        if not self.icon or self.icon == "codesandbox":
            self.icon = PROCESSOR_DEFAULT_ICONS.get(value, "codesandbox")
        self.validate_processor_type()

    def set_temperature(self, value: str) -> None:
        self.temperature = value
        self.validate_temperature()

    def set_stream(self, value: bool) -> None:
        self.stream = value

    def set_supports_tools(self, value: bool) -> None:
        self.supports_tools = value

    def set_supports_attachments(self, value: bool) -> None:
        self.supports_attachments = value

    def set_supports_search(self, value: bool) -> None:
        self.supports_search = value

    def set_supports_skills(self, value: bool) -> None:
        self.supports_skills = value

    def set_requires_role(self, value: str) -> None:
        self.requires_role = value

    def set_api_key(self, value: str) -> None:
        self.api_key = value

    def set_base_url(self, value: str) -> None:
        self.base_url = value

    def set_on_azure(self, value: bool) -> None:
        self.on_azure = value

    # --- Validators ---

    @rx.event
    def validate_model_id(self) -> None:
        if not self.model_id or not self.model_id.strip():
            self.model_id_error = "Modell-ID ist ein Pflichtfeld."
        else:
            self.model_id_error = ""

    @rx.event
    def validate_text(self) -> None:
        if not self.text or not self.text.strip():
            self.text_error = "Anzeigename ist ein Pflichtfeld."
        else:
            self.text_error = ""

    @rx.event
    def validate_processor_type(self) -> None:
        if not self.processor_type or not self.processor_type.strip():
            self.processor_type_error = "Prozessortyp ist ein Pflichtfeld."
        else:
            self.processor_type_error = ""

    @rx.event
    def validate_temperature(self) -> None:
        try:
            val = float(self.temperature)
            if val < 0 or val > _MAX_TEMPERATURE:
                self.temperature_error = "Temperatur muss zwischen 0 und 2 liegen."
            else:
                self.temperature_error = ""
        except ValueError:
            self.temperature_error = "Temperatur muss eine Zahl sein."

    @rx.var
    def has_errors(self) -> bool:
        return bool(
            self.model_id_error
            or self.text_error
            or self.processor_type_error
            or self.temperature_error
        )


def _role_select() -> rx.Component:
    """Role selection dropdown for model access control."""
    return mn.select(
        label="Erforderliche Rolle",
        description=("Nur Benutzer mit dieser Rolle können dieses Modell verwenden."),
        data=AIModelAdminState.available_roles,
        value=AIModelValidationState.requires_role,
        on_change=AIModelValidationState.set_requires_role,
        placeholder="Keine Einschränkung",
        clearable=True,
        name="requires_role",
        width="100%",
    )


def _processor_type_field() -> rx.Component:
    """Processor type select."""
    return mn.select(
        label="Prozessortyp",
        description="Welcher Prozessor verarbeitet Anfragen für dieses Modell?",
        data=KNOWN_PROCESSOR_TYPES,
        value=AIModelValidationState.processor_type,
        on_change=AIModelValidationState.set_processor_type,
        error=AIModelValidationState.processor_type_error,
        placeholder="Prozessortyp auswählen",
        required=True,
        allow_deselect=False,
        name="processor_type",
        width="100%",
    )


def _capability_switches() -> rx.Component:
    """Capability toggle switches for the model."""
    return mn.simple_grid(
        mn.switch(
            label="Streaming",
            checked=AIModelValidationState.stream,
            on_change=AIModelValidationState.set_stream,
            name="stream",
        ),
        mn.switch(
            label="Tools",
            checked=AIModelValidationState.supports_tools,
            on_change=AIModelValidationState.set_supports_tools,
            name="supports_tools",
        ),
        mn.switch(
            label="Attachments",
            checked=AIModelValidationState.supports_attachments,
            on_change=AIModelValidationState.set_supports_attachments,
            name="supports_attachments",
        ),
        mn.switch(
            label="Web Search",
            checked=AIModelValidationState.supports_search,
            on_change=AIModelValidationState.set_supports_search,
            name="supports_search",
        ),
        mn.switch(
            label="Skills",
            checked=AIModelValidationState.supports_skills,
            on_change=AIModelValidationState.set_supports_skills,
            name="supports_skills",
        ),
        cols=2,
        spacing="sm",
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
            disabled=AIModelValidationState.has_errors,
            loading=AIModelAdminState.loading,
        ),
        direction="row",
        gap="9px",
        justify_content="end",
        padding="16px",
        border_top="1px solid var(--mantine-color-default-border)",
        background="var(--mantine-color-body)",
        width="100%",
    )


def ai_model_form_fields() -> rx.Component:
    """Reusable form fields for add/edit modals."""
    return mn.flex(
        form_field(
            name="text",
            icon="tag",
            label="Anzeigename",
            hint="Anzeige-Label in der Modellauswahl",
            type="text",
            placeholder="GPT 5 Mini",
            default_value=AIModelValidationState.text,
            required=True,
            max_length=100,
            on_blur=AIModelValidationState.set_text,
            validation_error=AIModelValidationState.text_error,
        ),
        form_field(
            name="model_id",
            icon="hash",
            label="Modell-ID",
            hint="Eindeutige interne ID (z.B. gpt-5-mini)",
            type="text",
            placeholder="gpt-5-mini",
            default_value=AIModelValidationState.model_id,
            required=True,
            max_length=100,
            on_blur=AIModelValidationState.set_model_id,
            validation_error=AIModelValidationState.model_id_error,
        ),
        form_field(
            name="model",
            icon="box",
            label="API-Modellname",
            hint="Name des Modells in der API (z.B. gpt-5-mini)",
            type="text",
            placeholder="gpt-5-mini",
            default_value=AIModelValidationState.model,
            max_length=100,
            on_blur=AIModelValidationState.set_model,
        ),
        mn.select(
            label="Icon",
            description="Symbol für die Modellauswahl",
            data=KNOWN_ICONS,
            value=AIModelValidationState.icon,
            on_change=AIModelValidationState.set_icon,
            placeholder="Icon auswählen",
            searchable=True,
            clearable=True,
            name="icon",
            width="100%",
        ),
        _processor_type_field(),
        form_field(
            name="temperature",
            icon="thermometer",
            label="Temperatur",
            hint="Sampling-Temperatur (0.0 - 2.0)",
            type="number",
            placeholder="0.05",
            default_value=AIModelValidationState.temperature,
            on_blur=AIModelValidationState.set_temperature,
            validation_error=AIModelValidationState.temperature_error,
        ),
        mn.divider(label="Fähigkeiten", my="4px"),
        _capability_switches(),
        mn.divider(label="API-Zugangsdaten", my="4px"),
        mn.switch(
            label="Azure-Endpunkt",
            checked=AIModelValidationState.on_azure,
            on_change=AIModelValidationState.set_on_azure,
            name="on_azure",
        ),
        form_field(
            name="base_url",
            icon="link",
            label="Base URL",
            hint="Optionaler API-Endpunkt (leer = Standard)",
            type="text",
            placeholder="https://api.openai.com/v1",
            default_value=AIModelValidationState.base_url,
            max_length=500,
            on_blur=AIModelValidationState.set_base_url,
        ),
        mn.password_input(
            name="api_key",
            label="API-Schlüssel",
            description="Schlüssel für dieses Modell",
            placeholder="sk-...",
            default_value=AIModelValidationState.api_key,
            on_blur=AIModelValidationState.set_api_key,
            required=True,
            w="100%",
        ),
        mn.divider(label="Zugriffssteuerung", my="4px"),
        _role_select(),
        direction="column",
        gap="9px",
        padding="12px",
    )


def add_ai_model_button() -> rx.Component:
    """Button that opens the add AI model modal."""
    return mn.button(
        "Neues KI-Modell anlegen",
        left_section=rx.icon("plus", size=16),
        size="sm",
        on_click=[
            AIModelValidationState.initialize(record=None),
            AIModelAdminState.open_add_modal,
        ],
    )


def _ai_model_modal(
    title: str,
    opened: bool | rx.Var,
    on_close: rx.EventHandler,
    on_submit: rx.EventHandler,
    submit_label: str,
) -> rx.Component:
    """Shared modal structure for add/edit AI model."""
    return mn.modal(
        rx.form.root(
            rx.flex(
                mn.scroll_area.autosize(
                    ai_model_form_fields(),
                    max_height="60vh",
                    width="100%",
                    type="always",
                    offset_scrollbars=True,
                ),
                _modal_footer(submit_label, on_close),
                direction="column",
            ),
            on_submit=on_submit,
            reset_on_submit=False,
            height="100%",
        ),
        title=title,
        opened=opened,
        on_close=on_close,
        size="lg",
        centered=True,
        overlay_props={"backgroundOpacity": 0.5, "blur": 4},
    )


def add_ai_model_modal() -> rx.Component:
    """Modal for adding a new AI model."""
    return _ai_model_modal(
        title="Neues KI-Modell anlegen",
        opened=AIModelAdminState.add_modal_open,
        on_close=AIModelAdminState.close_add_modal,
        on_submit=AIModelAdminState.add_model,
        submit_label="KI-Modell anlegen",
    )


def edit_ai_model_modal() -> rx.Component:
    """Modal for editing an existing AI model."""
    return _ai_model_modal(
        title="KI-Modell aktualisieren",
        opened=AIModelAdminState.edit_modal_open,
        on_close=AIModelAdminState.close_edit_modal,
        on_submit=AIModelAdminState.modify_model,
        submit_label="KI-Modell aktualisieren",
    )


def delete_ai_model_dialog(record: AssistantAIModel) -> rx.Component:
    """Confirmation dialog for deleting an AI model."""
    return delete_dialog(
        title="KI-Modell löschen",
        content=record.text,
        on_click=lambda: AIModelAdminState.delete_model(record.id),
        icon_button=True,
        variant="subtle",
        color="red",
    )
