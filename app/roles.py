from typing import Final

from appkit_assistant.roles import (
    ASSISTANT_ADMIN_ROLE,
    ASSISTANT_ADVANCED_MODELS_ROLE,
    ASSISTANT_BASIC_MODELS_ROLE,
    ASSISTANT_FILE_UPLOAD_ROLE,
    ASSISTANT_PERPLEXITY_MODEL_ROLE,
    ASSISTANT_USER_ROLE,
    ASSISTANT_WEB_SEARCH_ROLE,
    SKILL_ADMIN_ROLE,
)
from appkit_commons.roles import Role

IMAGE_GENERATOR_GROUP = "Bildgenerator"

IMAGE_GENERATOR_ROLE = Role(
    id=2,
    name="image_generator",
    label="Bildgenerator",
    description="Berechtigung für die Bildgenerierung",
    group=IMAGE_GENERATOR_GROUP,
)


MCP_GROUP: Final[str] = "MCP Servers"

MCP_BASIC_ROLE = Role(
    name="mcp_basic",
    label="MCP Basic",
    description="Zugriff auf MCP Server mit Basis-Modellen (z.B. GPT-3.5)",
    group=MCP_GROUP,
)

MCP_ADVANCED_ROLE = Role(
    name="mcp_advanced",
    label="MCP Advanced",
    description="Zugriff auf MCP Server mit erweiterten Modellen (z.B. GPT-4)",
    group=MCP_GROUP,
)


ALL_ROLES: list[Role] = [
    ASSISTANT_USER_ROLE,
    ASSISTANT_BASIC_MODELS_ROLE,
    ASSISTANT_ADVANCED_MODELS_ROLE,
    ASSISTANT_PERPLEXITY_MODEL_ROLE,
    ASSISTANT_FILE_UPLOAD_ROLE,
    ASSISTANT_WEB_SEARCH_ROLE,
    ASSISTANT_ADMIN_ROLE,
    MCP_BASIC_ROLE,
    MCP_ADVANCED_ROLE,
    IMAGE_GENERATOR_ROLE,
    SKILL_ADMIN_ROLE,
]
