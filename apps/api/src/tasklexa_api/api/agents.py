import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from tasklexa_api.db.session import get_session
from tasklexa_api.repositories.agents import create_agent_definition, get_agent_definition, list_agent_definitions
from tasklexa_api.schemas.agent import AgentDefinitionCreate, AgentDefinitionRead

router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("", response_model=AgentDefinitionRead, status_code=201)
async def create_agent_definition_endpoint(
    payload: AgentDefinitionCreate, session: AsyncSession = Depends(get_session)
) -> AgentDefinitionRead:
    agent = await create_agent_definition(session, payload)
    return AgentDefinitionRead.model_validate(agent)


@router.get("", response_model=list[AgentDefinitionRead])
async def list_agent_definitions_endpoint(
    session: AsyncSession = Depends(get_session),
) -> list[AgentDefinitionRead]:
    agents = await list_agent_definitions(session)
    return [AgentDefinitionRead.model_validate(agent) for agent in agents]


@router.get("/{agent_id}", response_model=AgentDefinitionRead)
async def get_agent_definition_endpoint(
    agent_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> AgentDefinitionRead:
    agent = await get_agent_definition(session, agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail=f"AgentDefinition {agent_id} not found")
    return AgentDefinitionRead.model_validate(agent)
