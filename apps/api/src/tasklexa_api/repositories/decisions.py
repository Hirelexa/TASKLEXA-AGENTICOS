import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tasklexa_api.models.decision import Approval, Decision


async def list_decisions_for_mission(session: AsyncSession, mission_id: uuid.UUID) -> list[Decision]:
    result = await session.execute(select(Decision).where(Decision.mission_id == mission_id))
    return list(result.scalars().all())


async def list_approvals_for_decision(session: AsyncSession, decision_id: uuid.UUID) -> list[Approval]:
    result = await session.execute(select(Approval).where(Approval.decision_id == decision_id))
    return list(result.scalars().all())
