import uuid

from sqlalchemy import Enum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from tasklexa_api.db.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin
from tasklexa_api.domain.enums import ExecutionEventStatus, ExecutionEventType


class ExecutionEvent(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "execution_events"

    mission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("missions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="SET NULL"), index=True
    )
    agent_execution_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_executions.id", ondelete="SET NULL"), index=True
    )
    correlation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    event_type: Mapped[ExecutionEventType] = mapped_column(
        Enum(ExecutionEventType, name="execution_event_type"), nullable=False, index=True
    )
    provider: Mapped[str | None] = mapped_column(Text)
    status: Mapped[ExecutionEventStatus] = mapped_column(
        Enum(ExecutionEventStatus, name="execution_event_status"), nullable=False
    )
    error_category: Mapped[str | None] = mapped_column(Text)
    payload: Mapped[dict | None] = mapped_column(JSONB)
