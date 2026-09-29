import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from tasklexa_api.domain.enums import ApprovalStatus, ConflictStatus, DecisionStatus, RiskLevel


class DecisionCreate(BaseModel):
    mission_id: uuid.UUID
    title: str
    description: str | None = None
    options: list = Field(default_factory=list)
    recommendation: str | None = None
    evidence_ids: list[uuid.UUID] = Field(default_factory=list)
    confidence: float | None = None
    risk_level: RiskLevel = RiskLevel.LOW
    approval_required: bool = False
    requested_by: str
    approval_reason: str | None = None


class ApprovalDecisionRequest(BaseModel):
    approved_by: str
    comments: str | None = None


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
