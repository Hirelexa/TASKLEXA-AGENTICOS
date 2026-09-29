import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from tasklexa_api.domain.capability_resolver import resolve_team
from tasklexa_api.domain.enums import (
    AgentExecutionStatus,
    ExecutionEventStatus,
    ExecutionEventType,
    MissionStatus,
    TaskStatus,
)
from tasklexa_api.domain.errors import (
    InvalidMissionTransitionError,
    InvalidTaskTransitionError,
    MissionNotFoundError,
    MissionPausedError,
    TaskNotFoundError,
)
from tasklexa_api.domain.orchestrator import compute_task_readiness
from tasklexa_api.integrations.redis.dependency import get_redis_client
from tasklexa_api.integrations.redis.lock import RedisLock
from tasklexa_api.models.agent import AgentExecution
from tasklexa_api.models.execution_event import ExecutionEvent
from tasklexa_api.models.mission import Mission, Task
from tasklexa_api.repositories.agent_executions import get_running_agent_execution_for_task
from tasklexa_api.repositories.agents import list_agent_definitions
from tasklexa_api.repositories.missions import get_mission, transition_mission
from tasklexa_api.repositories.tasks import get_task, list_tasks_for_mission
from tasklexa_api.repositories.tools import list_tool_definitions
from tasklexa_api.schemas.agent import AgentDefinitionRead
from tasklexa_api.schemas.mission import TaskRead
from tasklexa_api.schemas.orchestrator import DispatchReport, FailTaskResult, TaskDispatchResult
from tasklexa_api.schemas.tool import ToolDefinitionRead

_ALL_SETTLED_STATUSES = frozenset({TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED})


async def run_dispatch_cycle(session: AsyncSession, mission_id: uuid.UUID) -> DispatchReport:
    mission = await get_mission(session, mission_id)
    if mission is None:
        raise MissionNotFoundError(mission_id)
    if mission.status == MissionStatus.WAITING_APPROVAL:
        # docs/domain-model.md: "PENDING approvals pause mission execution for
        # the relevant action... No action gated by approval may execute
        # before approval or modification is recorded."
        raise MissionPausedError(mission_id)

    lock = RedisLock(get_redis_client(), f"mission-dispatch:{mission_id}")
    async with lock:
        return await _run_dispatch_cycle_locked(session, mission_id, mission)


async def _run_dispatch_cycle_locked(session: AsyncSession, mission_id: uuid.UUID, mission: Mission) -> DispatchReport:
    task_rows = await list_tasks_for_mission(session, mission_id)
    tasks_by_id = {task.id: task for task in task_rows}
    readiness = compute_task_readiness([TaskRead.model_validate(task) for task in task_rows])

    agent_rows = await list_agent_definitions(session, active_only=True)
    tool_rows = await list_tool_definitions(session, available_only=True)
    agents = [AgentDefinitionRead.model_validate(agent) for agent in agent_rows]
    tools = [ToolDefinitionRead.model_validate(tool) for tool in tool_rows]

    dispatched: list[TaskDispatchResult] = []
    now = datetime.now(UTC)

    for task_id in readiness.ready_task_ids:
        task = tasks_by_id[task_id]
        plan = resolve_team(mission_id, task.required_capabilities or [], agents, tools)

        if not plan.selected_agents:
            dispatched.append(
                TaskDispatchResult(
                    task_id=task_id,
                    status="NO_AGENT_AVAILABLE",
                    detail=f"unresolved capabilities: {plan.unresolved_capabilities}",
                )
            )
            continue

        agent_id = plan.selected_agents[0]
        task.status = TaskStatus.ASSIGNED
        task.assigned_agent = agent_id

        agent_execution = AgentExecution(
            mission_id=mission_id,
            agent_definition_id=agent_id,
            task_id=task_id,
            status=AgentExecutionStatus.RUNNING,
            started_at=now,
        )
        session.add(agent_execution)
        await session.flush()

        session.add(
            ExecutionEvent(
                mission_id=mission_id,
                task_id=task_id,
                agent_execution_id=agent_execution.id,
                correlation_id=uuid.uuid4(),
                event_type=ExecutionEventType.AGENT_SELECTED,
                status=ExecutionEventStatus.SUCCESS,
                payload={"agent_definition_id": str(agent_id)},
            )
        )
        session.add(
            ExecutionEvent(
                mission_id=mission_id,
                task_id=task_id,
                agent_execution_id=agent_execution.id,
                correlation_id=uuid.uuid4(),
                event_type=ExecutionEventType.AGENT_STARTED,
                status=ExecutionEventStatus.SUCCESS,
                payload={"agent_definition_id": str(agent_id)},
            )
        )
        dispatched.append(TaskDispatchResult(task_id=task_id, status="DISPATCHED", agent_id=agent_id))

    mission_transitioned_to = None
    all_settled = (
        bool(task_rows)
        and not readiness.ready_task_ids
        and not readiness.blocked_task_ids
        and not readiness.in_progress_task_ids
        and not readiness.cyclic_task_ids
        and all(task.status in _ALL_SETTLED_STATUSES for task in task_rows)
    )
    if all_settled and mission.status == MissionStatus.RUNNING:
        try:
            await transition_mission(session, mission_id, MissionStatus.VERIFYING)
            mission_transitioned_to = MissionStatus.VERIFYING
        except InvalidMissionTransitionError:
            pass

    await session.commit()
    return DispatchReport(
        mission_id=mission_id,
        readiness=readiness,
        dispatched=dispatched,
        mission_transitioned_to=mission_transitioned_to,
    )


_COMPLETABLE_STATUSES = frozenset({TaskStatus.ASSIGNED, TaskStatus.RUNNING, TaskStatus.WAITING_APPROVAL})


async def complete_task(
    session: AsyncSession, task_id: uuid.UUID, actual_output: str | None, confidence: float | None
) -> Task:
    task = await get_task(session, task_id)
    if task is None:
        raise TaskNotFoundError(task_id)
    if task.status not in _COMPLETABLE_STATUSES:
        raise InvalidTaskTransitionError(
            task_id, f"cannot complete a task in status {task.status.value}"
        )

    now = datetime.now(UTC)
    task.status = TaskStatus.COMPLETED
    task.actual_output = actual_output
    task.confidence = confidence
    task.completed_at = now

    agent_execution = await get_running_agent_execution_for_task(session, task_id)
    if agent_execution is not None:
        agent_execution.status = AgentExecutionStatus.COMPLETED
        agent_execution.completed_at = now
        agent_execution.output = actual_output
        agent_execution.confidence = confidence

    session.add(
        ExecutionEvent(
            mission_id=task.mission_id,
            task_id=task_id,
            agent_execution_id=agent_execution.id if agent_execution else None,
            correlation_id=uuid.uuid4(),
            event_type=ExecutionEventType.TASK_COMPLETED,
            status=ExecutionEventStatus.SUCCESS,
            payload={"confidence": confidence} if confidence is not None else None,
        )
    )
    await session.commit()
    await session.refresh(task)
    return task


_UNFAILABLE_STATUSES = frozenset({TaskStatus.COMPLETED, TaskStatus.CANCELLED})


async def fail_task(session: AsyncSession, mission_id: uuid.UUID, task_id: uuid.UUID, reason: str) -> FailTaskResult:
    task = await get_task(session, task_id)
    if task is None or task.mission_id != mission_id:
        raise TaskNotFoundError(task_id)
    if task.status in _UNFAILABLE_STATUSES:
        raise InvalidTaskTransitionError(task_id, f"cannot fail a task in status {task.status.value}")

    task.status = TaskStatus.FAILED
    session.add(
        ExecutionEvent(
            mission_id=mission_id,
            task_id=task_id,
            correlation_id=uuid.uuid4(),
            event_type=ExecutionEventType.TASK_FAILED,
            status=ExecutionEventStatus.FAILURE,
            error_category="task_failed",
            payload={"reason": reason},
        )
    )

    failed_ids = {task_id}
    cascaded: list[uuid.UUID] = []
    all_tasks = await list_tasks_for_mission(session, mission_id)
    changed = True
    while changed:
        changed = False
        for candidate in all_tasks:
            if candidate.id in failed_ids or candidate.status != TaskStatus.PENDING:
                continue
            deps = candidate.dependencies or []
            if any(dep_id in failed_ids for dep_id in deps):
                candidate.status = TaskStatus.FAILED
                failed_ids.add(candidate.id)
                cascaded.append(candidate.id)
                session.add(
                    ExecutionEvent(
                        mission_id=mission_id,
                        task_id=candidate.id,
                        correlation_id=uuid.uuid4(),
                        event_type=ExecutionEventType.TASK_FAILED,
                        status=ExecutionEventStatus.FAILURE,
                        error_category="cascaded_failure",
                        payload={"cascaded_from": str(task_id)},
                    )
                )
                changed = True

    await session.commit()
    return FailTaskResult(task_id=task_id, cascaded_failure_ids=cascaded)


async def replan_task(session: AsyncSession, mission_id: uuid.UUID, task_id: uuid.UUID) -> Task:
    task = await get_task(session, task_id)
    if task is None or task.mission_id != mission_id:
        raise TaskNotFoundError(task_id)
    if task.status != TaskStatus.FAILED:
        raise InvalidTaskTransitionError(task_id, f"cannot replan a task in status {task.status.value}")

    task.status = TaskStatus.PENDING
    task.assigned_agent = None
    task.actual_output = None
    task.completed_at = None

    session.add(
        ExecutionEvent(
            mission_id=mission_id,
            task_id=task_id,
            correlation_id=uuid.uuid4(),
            event_type=ExecutionEventType.TASK_REPLANNED,
            status=ExecutionEventStatus.SUCCESS,
        )
    )
    await session.commit()
    await session.refresh(task)
    return task
