import asyncio
import unittest
import uuid
from collections import deque

from tasklexa_api.domain.enums import MissionStatus, TaskPriority, TaskStatus
from tasklexa_api.integrations.neo4j.graph_service import GraphService
from tasklexa_api.schemas.graph import OutcomeInput, ToolUsageInput


class FakeNeo4jClient:
    def __init__(self, responses: list[list[dict]] | None = None, error: Exception | None = None) -> None:
        self.calls: list[tuple[str, dict]] = []
        self._responses = deque(responses or [])
        self._error = error

    async def run(self, query: str, **params) -> list[dict]:
        self.calls.append((query, params))
        if self._error is not None:
            raise self._error
        if self._responses:
            return self._responses.popleft()
        return []

    async def close(self) -> None:
        pass


def _service(responses=None, error=None) -> tuple[GraphService, FakeNeo4jClient]:
    client = FakeNeo4jClient(responses=responses, error=error)
    service = GraphService(uri="bolt://unused:7687", user="unused", password="unused", client=client)
    return service, client


class GraphServiceHealthTests(unittest.TestCase):
    def test_health_reports_live_on_successful_query(self) -> None:
        service, _ = _service(responses=[[{"ok": 1}]])
        health = asyncio.run(service.health())
        self.assertEqual(health.status, "LIVE")

    def test_health_reports_failed_on_driver_error(self) -> None:
        from neo4j.exceptions import ServiceUnavailable

        service, _ = _service(error=ServiceUnavailable("no route to host"))
        health = asyncio.run(service.health())
        self.assertEqual(health.status, "FAILED")


class GraphServiceMutationTests(unittest.TestCase):
    def test_create_mission_graph_sends_expected_params(self) -> None:
        service, client = _service(responses=[[]])
        mission_id = uuid.uuid4()
        result = asyncio.run(service.create_mission_graph(mission_id, "Test Mission", MissionStatus.DRAFT))
        self.assertEqual(result.status, "APPLIED")
        _, params = client.calls[0]
        self.assertEqual(params["mission_id"], str(mission_id))
        self.assertEqual(params["status"], "DRAFT")

    def test_mutation_reports_failed_on_driver_error(self) -> None:
        from neo4j.exceptions import Neo4jError

        service, _ = _service(error=Neo4jError("boom"))
        result = asyncio.run(
            service.create_mission_graph(uuid.uuid4(), "Test Mission", MissionStatus.DRAFT)
        )
        self.assertEqual(result.status, "FAILED")
        self.assertIsNotNone(result.error)

    def test_add_task_passes_empty_lists_not_none(self) -> None:
        service, client = _service(responses=[[]])
        task_id = uuid.uuid4()
        mission_id = uuid.uuid4()
        result = asyncio.run(
            service.add_task(
                mission_id, task_id, "Do the thing", TaskStatus.PENDING, TaskPriority.MEDIUM, [], []
            )
        )
        self.assertEqual(result.status, "APPLIED")
        _, params = client.calls[0]
        self.assertEqual(params["capabilities"], [])
        self.assertEqual(params["dependencies"], [])

    def test_add_agent_assignment_stringifies_ids(self) -> None:
        service, client = _service(responses=[[]])
        task_id = uuid.uuid4()
        agent_id = uuid.uuid4()
        asyncio.run(
            service.add_agent_assignment(task_id, agent_id, "research-agent", ["research"], ["similarweb"])
        )
        _, params = client.calls[0]
        self.assertEqual(params["task_id"], str(task_id))
        self.assertEqual(params["agent_id"], str(agent_id))

    def test_add_evidence_without_task_or_agent_still_applies(self) -> None:
        service, client = _service(responses=[[]])
        result = asyncio.run(
            service.add_evidence(uuid.uuid4(), uuid.uuid4(), "web search", "external", 0.8)
        )
        self.assertEqual(result.status, "APPLIED")
        _, params = client.calls[0]
        self.assertIsNone(params["task_id"])
        self.assertIsNone(params["agent_id"])

    def test_add_outcome_without_decision_omits_decision_merge(self) -> None:
        service, client = _service(responses=[[]])
        outcome = OutcomeInput(id=uuid.uuid4(), summary="Mission succeeded", status="SUCCESS")
        result = asyncio.run(service.add_outcome(uuid.uuid4(), outcome))
        self.assertEqual(result.status, "APPLIED")
        query, _ = client.calls[0]
        self.assertNotIn("PRODUCES", query)

    def test_add_outcome_with_decision_includes_decision_merge(self) -> None:
        service, client = _service(responses=[[]])
        outcome = OutcomeInput(id=uuid.uuid4(), decision_id=uuid.uuid4(), summary="ok", status="SUCCESS")
        asyncio.run(service.add_outcome(uuid.uuid4(), outcome))
        query, _ = client.calls[0]
        self.assertIn("PRODUCES", query)

    def test_add_tool_usage_applies(self) -> None:
        service, client = _service(responses=[[]])
        usage = ToolUsageInput(tool_id=uuid.uuid4(), tool_name="similarweb", action="website_analysis")
        result = asyncio.run(service.add_tool_usage(uuid.uuid4(), uuid.uuid4(), usage))
        self.assertEqual(result.status, "APPLIED")
        self.assertEqual(client.calls[0][1]["tool_name"], "similarweb")


class GraphServiceQueryTests(unittest.TestCase):
    def test_get_mission_graph_parses_nodes_and_relationships(self) -> None:
        mission_id = uuid.uuid4()
        task_id = str(uuid.uuid4())
        node_rows = [
            {"id": str(mission_id), "labels": ["Mission"], "properties": {"title": "Test"}},
            {"id": task_id, "labels": ["Task"], "properties": {"title": "Step 1"}},
        ]
        rel_rows = [{"type": "CONTAINS", "start_id": str(mission_id), "end_id": task_id}]
        service, _ = _service(responses=[node_rows, rel_rows])

        graph = asyncio.run(service.get_mission_graph(mission_id))

        self.assertEqual(len(graph.nodes), 2)
        self.assertEqual(len(graph.relationships), 1)
        self.assertEqual(graph.relationships[0].type, "CONTAINS")

    def test_find_agents_by_capability_parses_rows(self) -> None:
        agent_id = uuid.uuid4()
        rows = [{"id": str(agent_id), "name": "research-agent", "capabilities": ["research", "summarization"]}]
        service, _ = _service(responses=[rows])

        agents = asyncio.run(service.find_agents_by_capability("research"))

        self.assertEqual(len(agents), 1)
        self.assertEqual(agents[0].id, agent_id)
        self.assertEqual(agents[0].name, "research-agent")

    def test_find_related_evidence_parses_rows(self) -> None:
        evidence_id = uuid.uuid4()
        rows = [{"id": str(evidence_id), "source": "web", "source_type": "external", "confidence": 0.7}]
        service, _ = _service(responses=[rows])

        evidence = asyncio.run(service.find_related_evidence(uuid.uuid4()))

        self.assertEqual(len(evidence), 1)
        self.assertEqual(evidence[0].id, evidence_id)
        self.assertEqual(evidence[0].confidence, 0.7)


if __name__ == "__main__":
    unittest.main()
