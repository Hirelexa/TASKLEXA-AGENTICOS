import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from tasklexa_api.domain.errors import MissionNotFoundError
from tasklexa_api.integrations.neo4j.dependency import get_graph_service
from tasklexa_api.repositories.agent_executions import get_agent_execution
from tasklexa_api.repositories.agents import get_agent_definition
from tasklexa_api.repositories.decisions import list_approvals_for_decision, list_decisions_for_mission
from tasklexa_api.repositories.evidence import list_evidence_for_mission
from tasklexa_api.repositories.missions import get_mission
from tasklexa_api.repositories.tasks import list_tasks_for_mission
from tasklexa_api.schemas.graph import ProjectionReport


async def project_mission(session: AsyncSession, mission_id: uuid.UUID) -> ProjectionReport:
    """Rebuild the Neo4j projection for a mission from PostgreSQL.

    Every write is a Cypher MERGE, so calling this repeatedly for the same
    mission is safe and is also how a failed/partial projection gets repaired
    (docs/architecture.md Phase 6: "Add graph projection repair path").
    """
    mission = await get_mission(session, mission_id)
    if mission is None:
        raise MissionNotFoundError(mission_id)

    graph_service = get_graph_service()
    results = []

    results.append(await graph_service.create_mission_graph(mission.id, mission.title, mission.status))

    tasks = await list_tasks_for_mission(session, mission_id)
    for task in tasks:
        results.append(
            await graph_service.add_task(
                mission_id=mission_id,
                task_id=task.id,
                title=task.title,
                status=task.status,
                priority=task.priority,
                required_capabilities=task.required_capabilities or [],
                dependencies=task.dependencies or [],
            )
        )
        if task.assigned_agent is not None:
            agent = await get_agent_definition(session, task.assigned_agent)
            if agent is not None:
                results.append(
                    await graph_service.add_agent_assignment(
                        task_id=task.id,
                        agent_id=agent.id,
                        agent_name=agent.name,
                        capabilities=agent.capabilities or [],
                        allowed_tools=agent.allowed_tools or [],
                    )
                )

    evidence_rows = await list_evidence_for_mission(session, mission_id)
    for evidence in evidence_rows:
        produced_by_agent_id = None
        if evidence.agent_execution_id is not None:
            agent_execution = await get_agent_execution(session, evidence.agent_execution_id)
            if agent_execution is not None:
                produced_by_agent_id = agent_execution.agent_definition_id

        results.append(
            await graph_service.add_evidence(
                mission_id=mission_id,
                evidence_id=evidence.id,
                source=evidence.source,
                source_type=evidence.source_type,
                confidence=evidence.confidence,
                task_id=evidence.task_id,
                produced_by_agent_id=produced_by_agent_id,
            )
        )

    decisions = await list_decisions_for_mission(session, mission_id)
    for decision in decisions:
        results.append(
            await graph_service.add_decision(
                mission_id=mission_id,
                decision_id=decision.id,
                title=decision.title,
                status=decision.status.value,
                evidence_ids=decision.evidence_ids or [],
            )
        )
        approvals = await list_approvals_for_decision(session, decision.id)
        for approval in approvals:
            results.append(
                await graph_service.add_approval(
                    decision_id=decision.id, approval_id=approval.id, status=approval.status.value
                )
            )

    applied = sum(1 for r in results if r.status == "APPLIED")
    failed = sum(1 for r in results if r.status == "FAILED")
    return ProjectionReport(mission_id=mission_id, applied=applied, failed=failed, results=results)
