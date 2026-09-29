import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tasklexa_api.models.evidence import Evidence


async def list_evidence_for_mission(session: AsyncSession, mission_id: uuid.UUID) -> list[Evidence]:
    result = await session.execute(
        select(Evidence).where(Evidence.mission_id == mission_id).order_by(Evidence.created_at.asc())
    )
    return list(result.scalars().all())
