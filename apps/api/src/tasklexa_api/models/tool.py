from sqlalchemy import ARRAY, Boolean, Enum, Text
from sqlalchemy.orm import Mapped, mapped_column

from tasklexa_api.db.base import Base, UUIDPrimaryKeyMixin
from tasklexa_api.domain.enums import RiskLevel, ToolStatus


class ToolDefinition(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "tool_definitions"

    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    capabilities: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    authentication_type: Mapped[str | None] = mapped_column(Text)
    risk_level: Mapped[RiskLevel] = mapped_column(
        Enum(RiskLevel, name="tool_definition_risk_level"), nullable=False, default=RiskLevel.LOW
    )
    requires_approval: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[ToolStatus] = mapped_column(
        Enum(ToolStatus, name="tool_status"), nullable=False, default=ToolStatus.NOT_CONFIGURED
    )
