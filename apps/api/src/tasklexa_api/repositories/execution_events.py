import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tasklexa_api.models.execution_event import ExecutionEvent
from tasklexa_api.schemas.execution_event import ExecutionEventCreate


async def record_event(session: AsyncSession, event: ExecutionEventCreate) -> ExecutionEvent:
    row = ExecutionEvent(**event.model_dump())
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def list_events_for_mission(
    session: AsyncSession, mission_id: uuid.UUID, limit: int = 200
) -> list[ExecutionEvent]:
    result = await session.execute(
        select(ExecutionEvent)
        .where(ExecutionEvent.mission_id == mission_id)
        .order_by(ExecutionEvent.created_at.asc())
        .limit(limit)
    )
    return list(result.scalars().all())
