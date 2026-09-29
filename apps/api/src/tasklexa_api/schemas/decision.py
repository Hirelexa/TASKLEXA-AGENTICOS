import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from tasklexa_api.domain.enums import ApprovalStatus, ConflictStatus, DecisionStatus, RiskLevel


class DecisionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    mission_id: uuid.UUID
    title: str
    description: str | None
    options: list | None
    recommendation: str | None
    evidence_ids: list[uuid.UUID] | None
    confidence: float | None
    risk_level: RiskLevel
    approval_required: bool
    status: DecisionStatus


class ApprovalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    mission_id: uuid.UUID
    decision_id: uuid.UUID
    requested_by: str
    reason: str | None
    status: ApprovalStatus
    approved_by: str | None
    approved_at: datetime | None
    comments: str | None


class ConflictRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    mission_id: uuid.UUID
    decision_id: uuid.UUID | None
    detected_by: str
    summary: str
    original_recommendations: list | None
    conflicting_evidence_ids: list[uuid.UUID] | None
    resolution: str | None
    status: ConflictStatus
    created_at: datetime
    resolved_at: datetime | None
