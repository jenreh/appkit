"""BPMN component configuration."""

from typing import Literal

from pydantic import Field

from appkit_commons.configuration.base import BaseConfig

VALID_DIAGRAM_TYPES = ("process", "collaboration", "choreography")


class BPMNConfig(BaseConfig):
    """Configuration for the BPMN MCP server.

    Attributes:
        storage_dir: Directory for saving diagram files (filesystem / dual mode).
        storage_mode: Backend to use — ``filesystem``, ``database``, or ``both``.
        default_model: LLM model name for BPMN generation.
        max_file_size_mb: Maximum file size in megabytes.
        diagram_types: Allowed diagram type values.
        cleanup_days_threshold: Diagrams older than this many days are deleted.
    """

    storage_dir: str = "uploaded_files/bpmn"
    storage_mode: Literal["filesystem", "database", "both"] = "filesystem"
    default_model: str = "gpt-5.3-codex"
    max_file_size_mb: int = 10
    diagram_types: list[str] = Field(default_factory=lambda: list(VALID_DIAGRAM_TYPES))
    cleanup_days_threshold: int = 45
