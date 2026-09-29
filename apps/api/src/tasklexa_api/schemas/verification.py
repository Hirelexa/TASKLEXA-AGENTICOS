import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from tasklexa_api.domain.enums import VerificationStatus


class VerificationReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    mission_id: uuid.UUID
    verification_status: VerificationStatus
    criteria_results: list | None
    issues: list | None
    confidence: float | None
    created_at: datetime
