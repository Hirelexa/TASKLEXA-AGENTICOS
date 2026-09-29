import uuid

from neo4j.exceptions import Neo4jError, ServiceUnavailable

from tasklexa_api.domain.enums import MissionStatus, TaskPriority, TaskStatus
from tasklexa_api.integrations.neo4j.client import Neo4jClient
from tasklexa_api.schemas.graph import (
    GraphAgentRef,
    GraphEvidenceRef,
    GraphMutationResult,
    GraphNode,
    GraphRelationship,
    MissionGraph,
    OutcomeInput,
    ToolUsageInput,
)
from tasklexa_api.schemas.health import IntegrationHealth

PROVIDER_NAME = "Neo4j"
_NEO4J_ERRORS = (Neo4jError, ServiceUnavailable, OSError)


class GraphService:
    def __init__(self, uri: str, user: str, password: str, client: Neo4jClient | None = None) -> None:
        self._client = client or Neo4jClient(uri=uri, user=user, password=password)

    async def health(self) -> IntegrationHealth:
        try:
            rows = await self._client.run("RETURN 1 AS ok")
        except _NEO4J_ERRORS as exc:
            return IntegrationHealth(
                provider=PROVIDER_NAME,
                purpose="Mission relationship graph",
                status="FAILED",
                details=f"Connectivity check failed: {exc.__class__.__name__}",
            )

        if rows and rows[0].get("ok") == 1:
            return IntegrationHealth(
                provider=PROVIDER_NAME,
                purpose="Mission relationship graph",
                status="LIVE",
                details="Authenticated Cypher query (RETURN 1) succeeded.",
            )

        return IntegrationHealth(
            provider=PROVIDER_NAME,
            purpose="Mission relationship graph",
            status="FAILED",
            details="RETURN 1 query returned an unexpected result.",
        )

    async def _mutate(self, mutation_summary: str, query: str, **params) -> GraphMutationResult:
        try:
            await self._client.run(query, **params)
        except _NEO4J_ERRORS as exc:
            return GraphMutationResult(
                status="FAILED", summary=mutation_summary, error=f"{exc.__class__.__name__}: {exc}"
            )
        return GraphMutationResult(status="APPLIED", summary=mutation_summary)

    async def create_mission_graph(
        self, mission_id: uuid.UUID, title: str, status: MissionStatus
    ) -> GraphMutationResult:
        return await self._mutate(
            f"MERGE Mission({mission_id})",
            """
            MERGE (m:Mission {id: $mission_id})
            SET m.title = $title, m.status = $status
            """,
            mission_id=str(mission_id),
            title=title,
            status=status.value,
        )

    async def add_task(
        self,
        mission_id: uuid.UUID,
        task_id: uuid.UUID,
        title: str,
        status: TaskStatus,
        priority: TaskPriority,
        required_capabilities: list[str],
        dependencies: list[uuid.UUID],
    ) -> GraphMutationResult:
        return await self._mutate(
            f"MERGE Task({task_id}) under Mission({mission_id})",
            """
            MERGE (m:Mission {id: $mission_id})
            MERGE (t:Task {id: $task_id})
            SET t.title = $title, t.status = $status, t.priority = $priority
            MERGE (m)-[:CONTAINS]->(t)
            WITH m, t
            UNWIND (CASE WHEN size($capabilities) = 0 THEN [null] ELSE $capabilities END) AS capability
            FOREACH (_ IN CASE WHEN capability IS NULL THEN [] ELSE [1] END |
                MERGE (c:Capability {name: capability})
                SET c.id = capability
                MERGE (m)-[:REQUIRES]->(c)
            )
            WITH t
            UNWIND (CASE WHEN size($dependencies) = 0 THEN [null] ELSE $dependencies END) AS dep_id
            FOREACH (_ IN CASE WHEN dep_id IS NULL THEN [] ELSE [1] END |
                MERGE (dep:Task {id: dep_id})
                MERGE (t)-[:DEPENDS_ON]->(dep)
            )
            """,
            mission_id=str(mission_id),
            task_id=str(task_id),
            title=title,
            status=status.value,
            priority=priority.value,
            capabilities=required_capabilities or [],
            dependencies=[str(d) for d in (dependencies or [])],
        )

    async def add_agent_assignment(
        self,
        task_id: uuid.UUID,
        agent_id: uuid.UUID,
        agent_name: str,
        capabilities: list[str],
        allowed_tools: list[str],
    ) -> GraphMutationResult:
        return await self._mutate(
            f"MERGE Agent({agent_id}) ASSIGNED_TO Task({task_id})",
            """
            MERGE (t:Task {id: $task_id})
            MERGE (a:Agent {id: $agent_id})
            SET a.name = $agent_name
            MERGE (t)-[:ASSIGNED_TO]->(a)
            WITH a
            UNWIND (CASE WHEN size($capabilities) = 0 THEN [null] ELSE $capabilities END) AS capability
            FOREACH (_ IN CASE WHEN capability IS NULL THEN [] ELSE [1] END |
                MERGE (c:Capability {name: capability})
                SET c.id = capability
                MERGE (a)-[:HAS_CAPABILITY]->(c)
            )
            WITH a
            UNWIND (CASE WHEN size($tools) = 0 THEN [null] ELSE $tools END) AS tool_name
            FOREACH (_ IN CASE WHEN tool_name IS NULL THEN [] ELSE [1] END |
                MERGE (tool:Tool {name: tool_name})
                SET tool.id = tool_name
                MERGE (a)-[:CAN_USE]->(tool)
            )
            """,
            task_id=str(task_id),
            agent_id=str(agent_id),
            agent_name=agent_name,
            capabilities=capabilities or [],
            tools=allowed_tools or [],
        )

    async def add_evidence(
        self,
        mission_id: uuid.UUID,
        evidence_id: uuid.UUID,
        source: str,
        source_type: str,
        confidence: float | None,
        task_id: uuid.UUID | None = None,
        produced_by_agent_id: uuid.UUID | None = None,
    ) -> GraphMutationResult:
        return await self._mutate(
            f"MERGE Evidence({evidence_id}) for Mission({mission_id})",
            """
            MERGE (m:Mission {id: $mission_id})
            MERGE (e:Evidence {id: $evidence_id})
            SET e.source = $source, e.source_type = $source_type, e.confidence = $confidence
            MERGE (m)-[:HAS_EVIDENCE]->(e)
            WITH e
            FOREACH (_ IN CASE WHEN $task_id IS NULL THEN [] ELSE [1] END |
                MERGE (t:Task {id: $task_id})
                MERGE (t)-[:HAS_EVIDENCE]->(e)
            )
            WITH e
            FOREACH (_ IN CASE WHEN $agent_id IS NULL THEN [] ELSE [1] END |
                MERGE (a:Agent {id: $agent_id})
                MERGE (a)-[:PRODUCED]->(e)
            )
            """,
            mission_id=str(mission_id),
            evidence_id=str(evidence_id),
            source=source,
            source_type=source_type,
            confidence=confidence,
            task_id=str(task_id) if task_id else None,
            agent_id=str(produced_by_agent_id) if produced_by_agent_id else None,
        )

    async def add_decision(
        self,
        mission_id: uuid.UUID,
        decision_id: uuid.UUID,
        title: str,
        status: str,
        evidence_ids: list[uuid.UUID],
    ) -> GraphMutationResult:
        return await self._mutate(
            f"MERGE Decision({decision_id}) for Mission({mission_id})",
            """
            MERGE (m:Mission {id: $mission_id})
            MERGE (d:Decision {id: $decision_id})
            SET d.title = $title, d.status = $status
            MERGE (m)-[:HAS_DECISION]->(d)
            WITH d
            UNWIND (CASE WHEN size($evidence_ids) = 0 THEN [null] ELSE $evidence_ids END) AS ev_id
            FOREACH (_ IN CASE WHEN ev_id IS NULL THEN [] ELSE [1] END |
                MERGE (e:Evidence {id: ev_id})
                MERGE (e)-[:SUPPORTS]->(d)
            )
            """,
            mission_id=str(mission_id),
            decision_id=str(decision_id),
            title=title,
            status=status,
            evidence_ids=[str(e) for e in (evidence_ids or [])],
        )

    async def add_approval(
        self, decision_id: uuid.UUID, approval_id: uuid.UUID, status: str
    ) -> GraphMutationResult:
        return await self._mutate(
            f"MERGE Approval({approval_id}) REQUIRES_APPROVAL from Decision({decision_id})",
            """
            MERGE (d:Decision {id: $decision_id})
            MERGE (ap:Approval {id: $approval_id})
            SET ap.status = $status
            MERGE (d)-[:REQUIRES_APPROVAL]->(ap)
            """,
            decision_id=str(decision_id),
            approval_id=str(approval_id),
            status=status,
        )

    async def add_tool_usage(
        self, mission_id: uuid.UUID, task_id: uuid.UUID, tool_usage: ToolUsageInput
    ) -> GraphMutationResult:
        return await self._mutate(
            f"MERGE Tool({tool_usage.tool_id}) USED_IN Task({task_id})",
            """
            MERGE (t:Task {id: $task_id})
            MERGE (tool:Tool {id: $tool_id})
            SET tool.name = $tool_name
            MERGE (t)-[:USED_TOOL {action: $action}]->(tool)
            """,
            task_id=str(task_id),
            tool_id=str(tool_usage.tool_id),
            tool_name=tool_usage.tool_name,
            action=tool_usage.action,
        )

    async def add_outcome(self, mission_id: uuid.UUID, outcome: OutcomeInput) -> GraphMutationResult:
        query = """
        MERGE (m:Mission {id: $mission_id})
        MERGE (o:Outcome {id: $outcome_id})
        SET o.summary = $summary, o.status = $status
        MERGE (m)-[:HAS_OUTCOME]->(o)
        """
        if outcome.decision_id:
            query += """
            WITH o
            MERGE (d:Decision {id: $decision_id})
            MERGE (d)-[:PRODUCES]->(o)
            """
        return await self._mutate(
            f"MERGE Outcome({outcome.id}) for Mission({mission_id})",
            query,
            mission_id=str(mission_id),
            outcome_id=str(outcome.id),
            summary=outcome.summary,
            status=outcome.status,
            decision_id=str(outcome.decision_id) if outcome.decision_id else None,
        )

    async def get_mission_graph(self, mission_id: uuid.UUID) -> MissionGraph:
        node_rows = await self._client.run(
            """
            MATCH p = (m:Mission {id: $mission_id})-[*0..8]-(x)
            UNWIND nodes(p) AS n
            RETURN DISTINCT n.id AS id, labels(n) AS labels, properties(n) AS properties
            """,
            mission_id=str(mission_id),
        )
        rel_rows = await self._client.run(
            """
            MATCH p = (m:Mission {id: $mission_id})-[*0..8]-(x)
            UNWIND relationships(p) AS rel
            RETURN DISTINCT type(rel) AS type, startNode(rel).id AS start_id, endNode(rel).id AS end_id
            """,
            mission_id=str(mission_id),
        )

        nodes = [
            GraphNode(id=row["id"], labels=row["labels"], properties=row["properties"])
            for row in node_rows
            if row["id"] is not None
        ]
        relationships = [
            GraphRelationship(type=row["type"], start_id=row["start_id"], end_id=row["end_id"])
            for row in rel_rows
            if row["start_id"] is not None and row["end_id"] is not None
        ]

        return MissionGraph(mission_id=mission_id, nodes=nodes, relationships=relationships)

    async def find_agents_by_capability(self, capability: str) -> list[GraphAgentRef]:
        rows = await self._client.run(
            """
            MATCH (a:Agent)-[:HAS_CAPABILITY]->(c:Capability {name: $capability})
            OPTIONAL MATCH (a)-[:HAS_CAPABILITY]->(other:Capability)
            RETURN a.id AS id, a.name AS name, collect(DISTINCT other.name) AS capabilities
            """,
            capability=capability,
        )
        return [
            GraphAgentRef(id=uuid.UUID(row["id"]), name=row["name"], capabilities=row["capabilities"])
            for row in rows
        ]

    async def find_related_evidence(self, decision_id: uuid.UUID) -> list[GraphEvidenceRef]:
        rows = await self._client.run(
            """
            MATCH (e:Evidence)-[:SUPPORTS]->(d:Decision {id: $decision_id})
            RETURN e.id AS id, e.source AS source, e.source_type AS source_type, e.confidence AS confidence
            """,
            decision_id=str(decision_id),
        )
        return [
            GraphEvidenceRef(
                id=uuid.UUID(row["id"]),
                source=row["source"],
                source_type=row["source_type"],
                confidence=row["confidence"],
            )
            for row in rows
        ]

    async def close(self) -> None:
        await self._client.close()
