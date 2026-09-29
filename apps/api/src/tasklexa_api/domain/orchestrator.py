import uuid

from tasklexa_api.domain.enums import TaskStatus
from tasklexa_api.schemas.mission import TaskRead
from tasklexa_api.schemas.orchestrator import TaskReadinessReport

_IN_PROGRESS_STATUSES = frozenset(
    {TaskStatus.READY, TaskStatus.ASSIGNED, TaskStatus.RUNNING, TaskStatus.WAITING_APPROVAL}
)


def _find_cycle_members(pending_ids: set[uuid.UUID], dependencies: dict[uuid.UUID, list[uuid.UUID]]) -> set[uuid.UUID]:
    """Three-color DFS over the pending-task subgraph (edges: task -> dependency).

    Only dependency edges pointing at another pending task matter here - an
    edge to an already-done/failed/in-progress task can never be part of a
    deadlock, since that task's fate is already decided or in flight.
    """
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[uuid.UUID, int] = {task_id: WHITE for task_id in pending_ids}
    cyclic: set[uuid.UUID] = set()

    def visit(task_id: uuid.UUID, stack: list[uuid.UUID]) -> None:
        color[task_id] = GRAY
        stack.append(task_id)
        for dep_id in dependencies.get(task_id, []):
            if dep_id not in pending_ids:
                continue
            if color[dep_id] == WHITE:
                visit(dep_id, stack)
            elif color[dep_id] == GRAY:
                cycle_start = stack.index(dep_id)
                cyclic.update(stack[cycle_start:])
        stack.pop()
        color[task_id] = BLACK

    for task_id in pending_ids:
        if color[task_id] == WHITE:
            visit(task_id, [])

    return cyclic


def compute_task_readiness(tasks: list[TaskRead]) -> TaskReadinessReport:
    done_ids = {t.id for t in tasks if t.status == TaskStatus.COMPLETED}
    failed_ids = {t.id for t in tasks if t.status == TaskStatus.FAILED}
    in_progress_ids = [t.id for t in tasks if t.status in _IN_PROGRESS_STATUSES]

    pending = [t for t in tasks if t.status == TaskStatus.PENDING]
    pending_ids = {t.id for t in pending}
    dependencies = {t.id: (t.dependencies or []) for t in pending}

    cyclic_ids = _find_cycle_members(pending_ids, dependencies)

    ready: list[uuid.UUID] = []
    blocked: list[uuid.UUID] = []

    for task in pending:
        if task.id in cyclic_ids:
            continue
        deps = task.dependencies or []
        if all(d in done_ids for d in deps):
            ready.append(task.id)
        else:
            blocked.append(task.id)

    return TaskReadinessReport(
        ready_task_ids=ready,
        blocked_task_ids=blocked,
        in_progress_task_ids=in_progress_ids,
        done_task_ids=list(done_ids),
        failed_task_ids=list(failed_ids),
        cyclic_task_ids=list(cyclic_ids),
    )
