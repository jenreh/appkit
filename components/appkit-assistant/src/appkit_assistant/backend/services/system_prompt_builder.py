"""System Prompt Builder service.

Provides unified system prompt construction with MCP tool injection
for all AI processors.
"""

import logging

from appkit_assistant.backend.system_prompt_cache import get_system_prompt

logger = logging.getLogger(__name__)


class SystemPromptBuilder:
    """Service for building system prompts with MCP tool injection."""

    # Header for MCP tool selection guidelines
    MCP_SECTION_HEADER = (
        "### Tool-Auswahlrichtlinien (Einbettung externer Beschreibungen)"
    )

    def _build_mcp_section(self, mcp_prompt: str) -> str:
        """Build the MCP tool selection section.

        Args:
            mcp_prompt: The MCP tool prompts from servers

        Returns:
            Formatted MCP section or empty string
        """
        if not mcp_prompt:
            return ""
        return f"{self.MCP_SECTION_HEADER}\n{mcp_prompt}"

    async def build(self, mcp_prompt: str = "") -> str:
        """Build the complete system prompt with MCP section.

        Retrieves the base system prompt from cache and injects
        the MCP tool prompts via the {mcp_prompts} placeholder.

        Args:
            mcp_prompt: Optional MCP tool prompts from servers

        Returns:
            Complete formatted system prompt
        """
        # Get base system prompt from cache
        system_prompt_template = await get_system_prompt()

        # Build MCP section
        mcp_section = self._build_mcp_section(mcp_prompt)

        # Format template with MCP prompts
        return system_prompt_template.format(mcp_prompts=mcp_section)

    async def build_with_prefix(
        self,
        mcp_prompt: str = "",
        prefix: str = "",
    ) -> str:
        """Build system prompt with optional prefix.

        Args:
            mcp_prompt: Optional MCP tool prompts
            prefix: Optional prefix to prepend (e.g., for Gemini's leading newlines)

        Returns:
            Complete formatted system prompt with prefix
        """
        prompt = await self.build(mcp_prompt)
        if prefix:
            return f"{prefix}{prompt}"
        return prompt


# Singleton instance
_system_prompt_builder: SystemPromptBuilder | None = None


def get_system_prompt_builder() -> SystemPromptBuilder:
    """Get or create the system prompt builder singleton.

    Returns:
        The SystemPromptBuilder instance
    """
    global _system_prompt_builder  # noqa: PLW0603
    if _system_prompt_builder is None:
        _system_prompt_builder = SystemPromptBuilder()
    return _system_prompt_builder
