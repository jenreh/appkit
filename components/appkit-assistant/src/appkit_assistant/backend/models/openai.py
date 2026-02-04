from typing import Final

from appkit_assistant.backend.schemas import AIModel
from appkit_assistant.roles import (
    ASSISTANT_ADVANCED_MODELS_ROLE,
    ASSISTANT_BASIC_MODELS_ROLE,
)

O3: Final = AIModel(
    id="o3",
    text="o3 Reasoning",
    icon="openai",
    model="o3",
    temperature=1,
    stream=True,
    supports_attachments=False,
    supports_tools=True,
    keywords=["reasoning", "o3"],
    requires_role=ASSISTANT_ADVANCED_MODELS_ROLE.name,
)

GPT_5_MINI: Final = AIModel(
    id="gpt-5-mini",
    text="GPT 5 Mini",
    icon="openai",
    model="gpt-5-mini",
    stream=True,
    supports_attachments=True,
    supports_tools=True,
    supports_search=True,
    temperature=1,
    keywords=["gpt-5", "mini"],
    requires_role=ASSISTANT_BASIC_MODELS_ROLE.name,
)

GPT_5_1: Final = AIModel(
    id="gpt-5.1",
    text="GPT 5.1",
    icon="openai",
    model="gpt-5.1",
    stream=True,
    supports_attachments=True,
    supports_tools=True,
    supports_search=True,
    temperature=1,
    keywords=["gpt-5", "5.1"],
    requires_role=ASSISTANT_ADVANCED_MODELS_ROLE.name,
)

GPT_5_2: Final = AIModel(
    id="gpt-5.2",
    text="GPT 5.2",
    icon="openai",
    model="gpt-5.2",
    stream=True,
    supports_attachments=True,
    supports_tools=True,
    supports_search=True,
    temperature=1,
    keywords=["gpt-5", "5.2"],
    requires_role=ASSISTANT_ADVANCED_MODELS_ROLE.name,
)
