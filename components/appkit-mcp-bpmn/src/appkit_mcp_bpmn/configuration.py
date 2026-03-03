"""BPMN component configuration."""

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

VALID_DIAGRAM_TYPES = ("process", "collaboration", "choreography")


@dataclass
class BPMNConfig:
    """Configuration for the BPMN MCP server.

    Attributes:
        storage_dir: Directory for saving diagram files.
        default_model: LLM model name for BPMN generation.
        max_file_size_mb: Maximum file size in megabytes.
        diagram_types: Allowed diagram type values.
    """

    storage_dir: str = "uploaded_files"
    default_model: str = "gpt-5-mini"
    max_file_size_mb: int = 10
    diagram_types: list[str] = field(default_factory=lambda: list(VALID_DIAGRAM_TYPES))
