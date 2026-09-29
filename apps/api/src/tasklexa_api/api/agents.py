import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from tasklexa_api.db.session import get_session
from tasklexa_api.integrations.neo4j.dependency import get_graph_service
from tasklexa_api.repositories.agents import create_agent_definition, get_agent_definition, list_agent_definitions
from tasklexa_api.schemas.agent import AgentDefinitionCreate, AgentDefinitionRead
from tasklexa_api.schemas.graph import GraphAgentRef

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


@router.get("/by-capability/{capability}", response_model=list[GraphAgentRef])
async def find_agents_by_capability_endpoint(capability: str) -> list[GraphAgentRef]:
    """Query the Neo4j graph projection, not the PostgreSQL registry directly.

    An agent only appears here once it has been assigned to a task in some
    mission and that mission's graph has been projected (see
    POST /missions/{id}/graph/project) - this reflects the graph's current
    projected state, not the full live Agent Registry from GET /agents.
    """
    return await get_graph_service().find_agents_by_capability(capability)


@router.get("/{agent_id}", response_model=AgentDefinitionRead)
async def get_agent_definition_endpoint(
    agent_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> AgentDefinitionRead:
    agent = await get_agent_definition(session, agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail=f"AgentDefinition {agent_id} not found")
    return AgentDefinitionRead.model_validate(agent)
