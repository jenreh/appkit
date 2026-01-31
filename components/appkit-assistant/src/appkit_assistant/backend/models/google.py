"""
Gemini model definitions for Google's GenAI API.
"""

from typing import Final

from appkit_assistant.backend.schemas import AIModel

GEMINI_3_PRO: Final = AIModel(
    id="gemini-3-pro-preview",
    text="Gemini 3 Pro",
    icon="googlegemini",
    model="gemini-3-pro-preview",
    stream=True,
    supports_attachments=False,
    supports_tools=True,
)

GEMINI_3_FLASH: Final = AIModel(
    id="gemini-3-flash-preview",
    text="Gemini 3 Flash",
    icon="googlegemini",
    model="gemini-3-flash-preview",
    stream=True,
    supports_attachments=False,
    supports_tools=True,
)
