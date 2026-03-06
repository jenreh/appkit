"""BPMN component configuration."""

from pydantic import Field

from appkit_commons.configuration.base import BaseConfig

VALID_DIAGRAM_TYPES = ("process", "collaboration", "choreography")


class BPMNConfig(BaseConfig):
    """Configuration for the BPMN MCP server.

    Attributes:
        storage_dir: Directory for saving diagram files.
        default_model: LLM model name for BPMN generation.
        max_file_size_mb: Maximum file size in megabytes.
        diagram_types: Allowed diagram type values.
    """

    storage_dir: str = "uploaded_files/bpmn"
    default_model: str = "gpt-5.3-codex"
    max_file_size_mb: int = 10
    diagram_types: list[str] = Field(default_factory=lambda: list(VALID_DIAGRAM_TYPES))
