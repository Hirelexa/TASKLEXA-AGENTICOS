import unittest
import uuid

from tasklexa_api.domain.capability_resolver import resolve_team
from tasklexa_api.domain.enums import AgentDefinitionStatus, RiskLevel, ToolStatus
from tasklexa_api.schemas.agent import AgentDefinitionRead
from tasklexa_api.schemas.tool import ToolDefinitionRead


def _agent(name: str, capabilities: list[str], risk_level: RiskLevel = RiskLevel.LOW) -> AgentDefinitionRead:
    return AgentDefinitionRead(
        id=uuid.uuid4(),
        name=name,
        description=f"{name} description",
        capabilities=capabilities,
        allowed_tools=[],
        preferred_model_policy=None,
        permissions=[],
        risk_level=risk_level,
        provider="tasklexa-internal",
        status=AgentDefinitionStatus.ACTIVE,
    )


def _tool(name: str, capabilities: list[str], requires_approval: bool = False) -> ToolDefinitionRead:
    return ToolDefinitionRead(
        id=uuid.uuid4(),
        name=name,
        description=f"{name} description",
        provider="tasklexa-internal",
        capabilities=capabilities,
        authentication_type=None,
        risk_level=RiskLevel.LOW,
        requires_approval=requires_approval,
        status=ToolStatus.AVAILABLE,
    )


class CapabilityResolverTests(unittest.TestCase):
    def test_matches_agent_for_each_required_capability(self) -> None:
        mission_id = uuid.uuid4()
        research = _agent("research-agent", ["research", "summarization"])
        analysis = _agent("analysis-agent", ["analysis"])

        plan = resolve_team(mission_id, ["research", "analysis"], [research, analysis], [])

        self.assertEqual(set(plan.selected_agents), {research.id, analysis.id})
        self.assertEqual(plan.unresolved_capabilities, [])

    def test_reports_unresolved_capability_when_nothing_matches(self) -> None:
        mission_id = uuid.uuid4()
        research = _agent("research-agent", ["research"])

        plan = resolve_team(mission_id, ["research", "quantum_computing"], [research], [])

        self.assertEqual(plan.selected_agents, [research.id])
        self.assertEqual(plan.unresolved_capabilities, ["quantum_computing"])

    def test_does_not_select_the_same_agent_twice(self) -> None:
        mission_id = uuid.uuid4()
        multi = _agent("multi-agent", ["research", "summarization"])

        plan = resolve_team(mission_id, ["research", "summarization"], [multi], [])

        self.assertEqual(plan.selected_agents, [multi.id])

    def test_empty_required_capabilities_yields_empty_plan(self) -> None:
        mission_id = uuid.uuid4()
        plan = resolve_team(mission_id, [], [_agent("a", ["x"])], [])

        self.assertEqual(plan.selected_agents, [])
        self.assertEqual(plan.selected_tools, [])
        self.assertEqual(plan.unresolved_capabilities, [])

    def test_high_risk_agent_produces_a_risk_note(self) -> None:
        mission_id = uuid.uuid4()
        risky = _agent("risky-agent", ["research"], risk_level=RiskLevel.HIGH)

        plan = resolve_team(mission_id, ["research"], [risky], [])

        self.assertEqual(len(plan.risk_notes), 1)
        self.assertIn("risky-agent", plan.risk_notes[0])
        self.assertIn("HIGH", plan.risk_notes[0])

    def test_tool_can_satisfy_a_capability_alongside_an_agent(self) -> None:
        mission_id = uuid.uuid4()
        research = _agent("research-agent", ["research"])
        web_tool = _tool("similarweb", ["digital_market_intelligence"], requires_approval=True)

        plan = resolve_team(
            mission_id, ["research", "digital_market_intelligence"], [research], [web_tool]
        )

        self.assertEqual(plan.selected_agents, [research.id])
        self.assertEqual(plan.selected_tools, [web_tool.id])
        self.assertEqual(plan.unresolved_capabilities, [])
        self.assertTrue(any("similarweb" in note for note in plan.risk_notes))

    def test_required_capabilities_are_echoed_back_verbatim(self) -> None:
        mission_id = uuid.uuid4()
        plan = resolve_team(mission_id, ["research", "planning"], [], [])
        self.assertEqual(plan.required_capabilities, ["research", "planning"])
        self.assertEqual(plan.mission_id, mission_id)


if __name__ == "__main__":
    unittest.main()
