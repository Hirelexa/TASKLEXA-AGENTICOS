import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tasklexa_api.models.mission import Task


async def list_tasks_for_mission(session: AsyncSession, mission_id: uuid.UUID) -> list[Task]:
    result = await session.execute(
        select(Task).where(Task.mission_id == mission_id).order_by(Task.created_at.asc())
    )
    return list(result.scalars().all())
