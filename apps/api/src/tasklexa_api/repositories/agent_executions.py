import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from tasklexa_api.models.agent import AgentExecution


async def get_agent_execution(session: AsyncSession, agent_execution_id: uuid.UUID) -> AgentExecution | None:
    return await session.get(AgentExecution, agent_execution_id)
