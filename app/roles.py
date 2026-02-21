from typing import Final

from appkit_assistant.roles import (
    ASSISTANT_ADMIN_ROLE,
    ASSISTANT_ADMIN_SKILL_ROLE,
    ASSISTANT_ADVANCED_MODELS_ROLE,
    ASSISTANT_BASIC_MODELS_ROLE,
    ASSISTANT_FILE_UPLOAD_ROLE,
    ASSISTANT_PERPLEXITY_MODEL_ROLE,
    ASSISTANT_USER_ROLE,
    ASSISTANT_WEB_SEARCH_ROLE,
)
from appkit_commons.roles import Role
from appkit_imagecreator.roles import (
    IMAGE_GEN_ADMIN_ROLE,
    IMAGE_GEN_AZURE_ROLE,
    IMAGE_GEN_GOOGLE_ROLE,
    IMAGE_GEN_USER_ROLE,
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
    ASSISTANT_ADMIN_SKILL_ROLE,
    MCP_BASIC_ROLE,
    MCP_ADVANCED_ROLE,
    IMAGE_GEN_USER_ROLE,
    IMAGE_GEN_ADMIN_ROLE,
    IMAGE_GEN_GOOGLE_ROLE,
    IMAGE_GEN_AZURE_ROLE,
]
