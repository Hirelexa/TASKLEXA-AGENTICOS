import uuid
from datetime import datetime

from sqlalchemy import ARRAY, Boolean, DateTime, Enum, Float, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from tasklexa_api.db.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin
from tasklexa_api.domain.enums import ApprovalStatus, ConflictStatus, DecisionStatus, RiskLevel


class Decision(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "decisions"

    mission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("missions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    options: Mapped[list | None] = mapped_column(JSONB)
    recommendation: Mapped[str | None] = mapped_column(Text)
    evidence_ids: Mapped[list[uuid.UUID] | None] = mapped_column(ARRAY(UUID(as_uuid=True)))
    confidence: Mapped[float | None] = mapped_column(Float)
    risk_level: Mapped[RiskLevel] = mapped_column(
        Enum(RiskLevel, name="decision_risk_level"), nullable=False, default=RiskLevel.LOW
    )
    approval_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[DecisionStatus] = mapped_column(
        Enum(DecisionStatus, name="decision_status"), nullable=False, default=DecisionStatus.OPEN
    )


class Approval(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "approvals"

    mission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("missions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    decision_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("decisions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    requested_by: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    status: Mapped[ApprovalStatus] = mapped_column(
        Enum(ApprovalStatus, name="approval_status"), nullable=False, default=ApprovalStatus.PENDING
    )
    approved_by: Mapped[str | None] = mapped_column(Text)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    comments: Mapped[str | None] = mapped_column(Text)


class Conflict(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "conflicts"

    mission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("missions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    decision_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("decisions.id", ondelete="SET NULL"), index=True
    )
    detected_by: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    original_recommendations: Mapped[list | None] = mapped_column(JSONB)
    conflicting_evidence_ids: Mapped[list[uuid.UUID] | None] = mapped_column(ARRAY(UUID(as_uuid=True)))
    resolution: Mapped[str | None] = mapped_column(Text)
    status: Mapped[ConflictStatus] = mapped_column(
        Enum(ConflictStatus, name="conflict_status"), nullable=False, default=ConflictStatus.DETECTED
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
