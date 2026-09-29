import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from tasklexa_api.domain.capability_resolver import resolve_team
from tasklexa_api.domain.enums import ExecutionEventStatus, ExecutionEventType
from tasklexa_api.domain.errors import MissionNotFoundError
from tasklexa_api.models.execution_event import ExecutionEvent
from tasklexa_api.repositories.agents import list_agent_definitions
from tasklexa_api.repositories.missions import get_mission
from tasklexa_api.repositories.tools import list_tool_definitions
from tasklexa_api.schemas.agent import AgentDefinitionRead, AgentTeamPlan
from tasklexa_api.schemas.tool import ToolDefinitionRead


async def resolve_team_for_mission(
    session: AsyncSession, mission_id: uuid.UUID, required_capabilities: list[str]
) -> AgentTeamPlan:
    mission = await get_mission(session, mission_id)
    if mission is None:
        raise MissionNotFoundError(mission_id)

    agent_rows = await list_agent_definitions(session, active_only=True)
    tool_rows = await list_tool_definitions(session, available_only=True)

    plan = resolve_team(
        mission_id=mission_id,
        required_capabilities=required_capabilities,
        agents=[AgentDefinitionRead.model_validate(agent) for agent in agent_rows],
        tools=[ToolDefinitionRead.model_validate(tool) for tool in tool_rows],
    )

    for agent_id in plan.selected_agents:
        session.add(
            ExecutionEvent(
                mission_id=mission_id,
                correlation_id=uuid.uuid4(),
                event_type=ExecutionEventType.AGENT_SELECTED,
                status=ExecutionEventStatus.SUCCESS,
                payload={"agent_definition_id": str(agent_id)},
            )
        )
    if plan.selected_agents:
        await session.commit()

    return plan
