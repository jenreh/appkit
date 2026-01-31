from typing import Final

from appkit_assistant.backend.schemas import AIModel

O3: Final = AIModel(
    id="o3",
    text="o3 Reasoning",
    icon="openai",
    model="o3",
    temperature=1,
    stream=True,
    supports_attachments=False,
    supports_tools=True,
)

GPT_5_MINI: Final = AIModel(
    id="gpt-5-mini",
    text="GPT 5 Mini",
    icon="openai",
    model="gpt-5-mini",
    stream=True,
    supports_attachments=True,
    supports_tools=True,
    temperature=1,
)

GPT_5_1: Final = AIModel(
    id="gpt-5.1",
    text="GPT 5.1",
    icon="openai",
    model="gpt-5.1",
    stream=True,
    supports_attachments=True,
    supports_tools=True,
    temperature=1,
)

GPT_5_2: Final = AIModel(
    id="gpt-5.2",
    text="GPT 5.2",
    icon="openai",
    model="gpt-5.2",
    stream=True,
    supports_attachments=True,
    supports_tools=True,
    temperature=1,
)
