from appkit_commons.configuration.base import BaseConfig


class McpUserConfig(BaseConfig):
    """Configuration for AppKit MCP User Server."""

    openai_model: str = "gpt-5-mini"
