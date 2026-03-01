"""Configuration for MCP App server."""

from appkit_commons.configuration.base import BaseConfig


class McpAppConfig(BaseConfig):
    """Configuration for the MCP App analytics server."""

    openai_model: str = "gpt-4o-mini"
    """OpenAI model for prompt enhancement and query generation"""
