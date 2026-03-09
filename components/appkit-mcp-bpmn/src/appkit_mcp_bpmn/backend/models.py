"""SQLAlchemy model for persisted BPMN diagrams."""

from sqlalchemy import Boolean, DateTime, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from appkit_commons.database.entities import Base, Entity


class BpmnDiagram(Base, Entity):
    """Database model for a BPMN diagram saved by a user.

    Stores the raw XML blob, the original natural-language prompt, the
    diagram type, and soft-delete metadata so that the cleanup service
    can mark old records as deleted without destroying audit history.

    Inherits ``id``, ``created``, and ``updated`` from :class:`Entity`.
    """

    __tablename__ = "mcp_bpmn_diagrams"

    diagram_id: Mapped[str] = mapped_column(
        String(36), nullable=False, unique=True, index=True
    )
    user_id: Mapped[int] = mapped_column(nullable=False, index=True)
    xml_content: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    prompt: Mapped[str | None] = mapped_column(String(8000), nullable=True)
    diagram_type: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default="process"
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false", index=True
    )
    deleted_at: Mapped[None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
