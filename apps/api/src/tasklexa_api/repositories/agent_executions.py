import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tasklexa_api.domain.enums import AgentExecutionStatus
from tasklexa_api.models.agent import AgentExecution


async def get_agent_execution(session: AsyncSession, agent_execution_id: uuid.UUID) -> AgentExecution | None:
    return await session.get(AgentExecution, agent_execution_id)


async def get_running_agent_execution_for_task(session: AsyncSession, task_id: uuid.UUID) -> AgentExecution | None:
    result = await session.execute(
        select(AgentExecution)
        .where(AgentExecution.task_id == task_id, AgentExecution.status == AgentExecutionStatus.RUNNING)
        .order_by(AgentExecution.started_at.desc())
        .limit(1)
    )
    return result.scalars().first()
