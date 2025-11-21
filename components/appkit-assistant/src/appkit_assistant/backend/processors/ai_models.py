from typing import Final

from appkit_assistant.backend.models import AIModel

DEFAULT: Final = AIModel(
    id="default",
    text="Default (GPT 4.1 Mini)",
    icon="avvia_intelligence",
    model="default",
    stream=True,
)

GEMINI_2_5_FLASH: Final = AIModel(
    id="gemini-2-5-flash",
    text="Gemini 2.5 Flash",
    icon="googlegemini",
    model="gemini-2-5-flash",
)

LLAMA_3_2_VISION: Final = AIModel(
    id="llama32_vision_90b",
    text="Llama 3.2 Vision 90B (OnPrem)",
    icon="ollama",
    model="lllama32_vision_90b",
)

GPT_4o: Final = AIModel(
    id="gpt-4o",
    text="GPT 4o",
    icon="openai",
    model="gpt-4o",
    stream=True,
    supports_attachments=True,
    supports_tools=True,
)

GPT_4_1: Final = AIModel(
    id="gpt-4.1",
    text="GPT-4.1",
    icon="openai",
    model="gpt-4.1",
    stream=True,
    supports_attachments=True,
    supports_tools=True,
)

O3: Final = AIModel(
    id="o3",
    text="o3 Reasoning",
    icon="openai",
    model="o3",
    temperature=1,
    stream=True,
    supports_attachments=True,
    supports_tools=True,
)

O4_MINI: Final = AIModel(
    id="o4-mini",
    text="o4 Mini Reasoning",
    icon="openai",
    model="o4-mini",
    stream=True,
    supports_attachments=True,
    supports_tools=True,
    temperature=1,
)

GPT_5: Final = AIModel(
    id="gpt-5",
    text="GPT 5",
    icon="openai",
    model="gpt-5",
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

GPT_5_CHAT: Final = AIModel(
    id="gpt-5-chat",
    text="GPT 5 Chat",
    icon="openai",
    model="gpt-5-chat",
    stream=True,
    supports_attachments=True,
    supports_tools=False,
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

GPT_5_1_MINI: Final = AIModel(
    id="gpt-5.1-mini",
    text="GPT 5.1 Mini",
    icon="openai",
    model="gpt-5.1-mini",
    stream=True,
    supports_attachments=True,
    supports_tools=True,
    temperature=1,
)

GPT_5_NANO: Final = AIModel(
    id="gpt-5-nano",
    text="GPT 5 Nano",
    icon="openai",
    model="gpt-5-nano",
    stream=True,
    supports_attachments=True,
    supports_tools=True,
    temperature=1,
)
