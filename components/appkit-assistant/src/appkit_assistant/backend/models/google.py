"""
Gemini model definitions for Google's GenAI API.
"""

from typing import Final

from appkit_assistant.backend.schemas import AIModel
from appkit_assistant.roles import (
    ASSISTANT_ADVANCED_MODELS_ROLE,
    ASSISTANT_BASIC_MODELS_ROLE,
)

GEMINI_3_PRO: Final = AIModel(
    id="gemini-3-pro-preview",
    text="Gemini 3 Pro",
    icon="googlegemini",
    model="gemini-3-pro-preview",
    stream=True,
    supports_attachments=False,
    supports_tools=True,
    keywords=["pro", "gemini"],
    requires_role=ASSISTANT_ADVANCED_MODELS_ROLE.name,
)

GEMINI_3_FLASH: Final = AIModel(
    id="gemini-3-flash-preview",
    text="Gemini 3 Flash",
    icon="googlegemini",
    model="gemini-3-flash-preview",
    stream=True,
    supports_attachments=False,
    supports_tools=True,
    keywords=["flash", "gemini"],
    requires_role=ASSISTANT_BASIC_MODELS_ROLE.name,
)
