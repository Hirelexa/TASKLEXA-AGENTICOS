import uuid
from datetime import datetime

from sqlalchemy import ARRAY, DateTime, Enum, Float, ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from tasklexa_api.db.base import Base, UUIDPrimaryKeyMixin
from tasklexa_api.domain.enums import AgentDefinitionStatus, AgentExecutionStatus, RiskLevel


class AgentDefinition(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "agent_definitions"

    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    capabilities: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    allowed_tools: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    preferred_model_policy: Mapped[dict | None] = mapped_column(JSONB)
    permissions: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    risk_level: Mapped[RiskLevel] = mapped_column(
        Enum(RiskLevel, name="agent_definition_risk_level"), nullable=False, default=RiskLevel.LOW
    )
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[AgentDefinitionStatus] = mapped_column(
        Enum(AgentDefinitionStatus, name="agent_definition_status"),
        nullable=False,
        default=AgentDefinitionStatus.ACTIVE,
    )


class AgentExecution(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "agent_executions"

    mission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("missions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    agent_definition_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_definitions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="SET NULL"), index=True
    )
    status: Mapped[AgentExecutionStatus] = mapped_column(
        Enum(AgentExecutionStatus, name="agent_execution_status"),
        nullable=False,
        default=AgentExecutionStatus.PENDING,
    )
    model_used: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    token_usage: Mapped[dict | None] = mapped_column(JSONB)
    estimated_cost: Mapped[float | None] = mapped_column(Numeric(12, 6))
    output: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[float | None] = mapped_column(Float)
