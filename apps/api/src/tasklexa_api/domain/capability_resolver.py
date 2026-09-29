import uuid

from tasklexa_api.domain.enums import RiskLevel
from tasklexa_api.schemas.agent import AgentDefinitionRead, AgentTeamPlan
from tasklexa_api.schemas.tool import ToolDefinitionRead


def resolve_team(
    mission_id: uuid.UUID,
    required_capabilities: list[str],
    agents: list[AgentDefinitionRead],
    tools: list[ToolDefinitionRead],
) -> AgentTeamPlan:
    selected_agent_ids: list[uuid.UUID] = []
    selected_tool_ids: list[uuid.UUID] = []
    unresolved_capabilities: list[str] = []
    risk_notes: list[str] = []
    seen_agent_ids: set[uuid.UUID] = set()
    seen_tool_ids: set[uuid.UUID] = set()

    for capability in required_capabilities:
        agent_match = next((agent for agent in agents if capability in (agent.capabilities or [])), None)
        tool_match = next((tool for tool in tools if capability in (tool.capabilities or [])), None)

        if agent_match is None and tool_match is None:
            unresolved_capabilities.append(capability)
            continue

        if agent_match is not None and agent_match.id not in seen_agent_ids:
            selected_agent_ids.append(agent_match.id)
            seen_agent_ids.add(agent_match.id)
            if agent_match.risk_level == RiskLevel.HIGH:
                risk_notes.append(
                    f"Agent '{agent_match.name}' selected for capability '{capability}' is HIGH risk."
                )

        if tool_match is not None and tool_match.id not in seen_tool_ids:
            selected_tool_ids.append(tool_match.id)
            seen_tool_ids.add(tool_match.id)
            if tool_match.requires_approval:
                risk_notes.append(
                    f"Tool '{tool_match.name}' selected for capability '{capability}' requires approval."
                )

    return AgentTeamPlan(
        mission_id=mission_id,
        required_capabilities=required_capabilities,
        selected_agents=selected_agent_ids,
        selected_tools=selected_tool_ids,
        unresolved_capabilities=unresolved_capabilities,
        risk_notes=risk_notes,
    )
