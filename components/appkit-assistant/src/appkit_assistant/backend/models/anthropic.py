"""
Claude model definitions for the Anthropic's Claude API.
"""

from typing import Final

from appkit_assistant.backend.schemas import (
    AIModel,
)
from appkit_assistant.roles import (
    ASSISTANT_ADVANCED_MODELS_ROLE,
    ASSISTANT_BASIC_MODELS_ROLE,
)

CLAUDE_HAIKU_4_5: Final = AIModel(
    id="claude-haiku-4.5",
    text="Claude 4.5 Haiku",
    icon="anthropic",
    model="claude-haiku-4-5",
    stream=True,
    supports_attachments=False,
    supports_tools=True,
    temperature=1.0,
    keywords=["haiku", "claude"],
    requires_role=ASSISTANT_BASIC_MODELS_ROLE.name,
)

CLAUDE_SONNET_4_5: Final = AIModel(
    id="claude-sonnet-4.5",
    text="Claude 4.5 Sonnet",
    icon="anthropic",
    model="claude-sonnet-4-5",
    stream=True,
    supports_attachments=False,
    supports_tools=True,
    temperature=1.0,
    keywords=["sonnet", "claude"],
    requires_role=ASSISTANT_ADVANCED_MODELS_ROLE.name,
)
