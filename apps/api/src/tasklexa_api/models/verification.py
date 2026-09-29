import uuid

from sqlalchemy import Enum, Float, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from tasklexa_api.db.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin
from tasklexa_api.domain.enums import VerificationStatus


class VerificationReport(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "verification_reports"

    mission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("missions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    verification_status: Mapped[VerificationStatus] = mapped_column(
        Enum(VerificationStatus, name="verification_status"), nullable=False
    )
    criteria_results: Mapped[list | None] = mapped_column(JSONB)
    issues: Mapped[list | None] = mapped_column(JSONB)
    confidence: Mapped[float | None] = mapped_column(Float)
