import uuid
from datetime import datetime

from sqlalchemy import ARRAY, DateTime, Enum, Float, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from tasklexa_api.db.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin
from tasklexa_api.domain.enums import MissionStatus, TaskPriority, TaskStatus


class Mission(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "missions"

    title: Mapped[str] = mapped_column(Text, nullable=False)
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[MissionStatus] = mapped_column(
        Enum(MissionStatus, name="mission_status"), nullable=False, default=MissionStatus.DRAFT
    )
    constraints: Mapped[list | None] = mapped_column(JSONB)
    success_criteria: Mapped[list | None] = mapped_column(JSONB)
    created_by: Mapped[str] = mapped_column(Text, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Task(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "tasks"

    mission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("missions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, name="task_status"), nullable=False, default=TaskStatus.PENDING
    )
    priority: Mapped[TaskPriority] = mapped_column(
        Enum(TaskPriority, name="task_priority"), nullable=False, default=TaskPriority.MEDIUM
    )
    required_capabilities: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    dependencies: Mapped[list[uuid.UUID] | None] = mapped_column(ARRAY(UUID(as_uuid=True)))
    assigned_agent: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_definitions.id", ondelete="SET NULL")
    )
    tool_requirements: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    expected_output: Mapped[str | None] = mapped_column(Text)
    actual_output: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[float | None] = mapped_column(Float)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
