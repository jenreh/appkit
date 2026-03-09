"""Abstract storage interface for BPMN diagrams."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class DiagramInfo:
    """Metadata returned after saving a BPMN diagram."""

    id: str
    download_url: str
    view_url: str


class StorageBackend(ABC):
    """Abstract base class for BPMN diagram storage."""

    @abstractmethod
    async def save(
        self,
        xml: str,
        prompt: str,
        user_id: int,
        diagram_id: str,
        diagram_type: str = "process",
    ) -> DiagramInfo:
        """Persist a BPMN diagram and return location metadata."""
        ...

    @abstractmethod
    async def load(self, diagram_id: str, user_id: int) -> str | None:
        """Load XML for a diagram.  Returns None if not found."""
        ...

    @abstractmethod
    async def delete_older_than_days(self, days: int) -> int:
        """Remove/soft-delete diagrams older than *days*.  Returns count."""
        ...
