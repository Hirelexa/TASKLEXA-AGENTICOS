import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from tasklexa_api.domain.enums import VerificationStatus


class VerificationEvaluation(BaseModel):
    verification_status: VerificationStatus
    criteria_results: list[dict] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)
    confidence: float


class VerificationReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    mission_id: uuid.UUID
    verification_status: VerificationStatus
    criteria_results: list | None
    issues: list | None
    confidence: float | None
    created_at: datetime
