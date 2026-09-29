from sqlalchemy.ext.asyncio import AsyncSession

from tasklexa_api.models.execution_event import ExecutionEvent
from tasklexa_api.schemas.execution_event import ExecutionEventCreate


async def record_event(session: AsyncSession, event: ExecutionEventCreate) -> ExecutionEvent:
    row = ExecutionEvent(**event.model_dump())
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row
