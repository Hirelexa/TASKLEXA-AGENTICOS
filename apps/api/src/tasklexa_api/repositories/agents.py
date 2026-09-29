import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tasklexa_api.domain.enums import AgentDefinitionStatus
from tasklexa_api.models.agent import AgentDefinition
from tasklexa_api.schemas.agent import AgentDefinitionCreate


async def create_agent_definition(session: AsyncSession, data: AgentDefinitionCreate) -> AgentDefinition:
    agent = AgentDefinition(
        name=data.name,
        description=data.description,
        capabilities=data.capabilities,
        allowed_tools=data.allowed_tools,
        preferred_model_policy=data.preferred_model_policy,
        permissions=data.permissions,
        risk_level=data.risk_level,
        provider=data.provider,
        status=AgentDefinitionStatus.ACTIVE,
    )
    session.add(agent)
    await session.commit()
    await session.refresh(agent)
    return agent


async def get_agent_definition(session: AsyncSession, agent_id: uuid.UUID) -> AgentDefinition | None:
    return await session.get(AgentDefinition, agent_id)


async def list_agent_definitions(session: AsyncSession, active_only: bool = False) -> list[AgentDefinition]:
    query = select(AgentDefinition).order_by(AgentDefinition.name.asc())
    if active_only:
        query = query.where(AgentDefinition.status == AgentDefinitionStatus.ACTIVE)
    result = await session.execute(query)
    return list(result.scalars().all())
