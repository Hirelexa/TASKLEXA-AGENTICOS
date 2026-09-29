import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from tasklexa_api.db.session import get_session
from tasklexa_api.domain.errors import (
    InvalidTaskTransitionError,
    LockAcquisitionError,
    MissionNotFoundError,
    TaskNotFoundError,
)
from tasklexa_api.repositories.missions import get_mission
from tasklexa_api.repositories.orchestrator import complete_task, fail_task, replan_task, run_dispatch_cycle
from tasklexa_api.repositories.tasks import create_task, get_task, list_tasks_for_mission
from tasklexa_api.schemas.mission import TaskCreate, TaskRead
from tasklexa_api.schemas.orchestrator import (
    CompleteTaskRequest,
    DispatchReport,
    FailTaskRequest,
    FailTaskResult,
)

router = APIRouter(prefix="/missions/{mission_id}/tasks", tags=["tasks"])


async def _require_mission(session: AsyncSession, mission_id: uuid.UUID) -> None:
    mission = await get_mission(session, mission_id)
    if mission is None:
        raise HTTPException(status_code=404, detail=f"Mission {mission_id} not found")


async def _require_task_in_mission(session: AsyncSession, mission_id: uuid.UUID, task_id: uuid.UUID):
    task = await get_task(session, task_id)
    if task is None or task.mission_id != mission_id:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found in mission {mission_id}")
    return task


@router.post("", response_model=TaskRead, status_code=201)
async def create_task_endpoint(
    mission_id: uuid.UUID, payload: TaskCreate, session: AsyncSession = Depends(get_session)
) -> TaskRead:
    await _require_mission(session, mission_id)
    if payload.mission_id != mission_id:
        raise HTTPException(status_code=400, detail="payload mission_id must match the URL mission_id")
    task = await create_task(session, payload)
    return TaskRead.model_validate(task)


@router.get("", response_model=list[TaskRead])
async def list_tasks_endpoint(
    mission_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> list[TaskRead]:
    await _require_mission(session, mission_id)
    tasks = await list_tasks_for_mission(session, mission_id)
    return [TaskRead.model_validate(task) for task in tasks]


@router.get("/{task_id}", response_model=TaskRead)
async def get_task_endpoint(
    mission_id: uuid.UUID, task_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> TaskRead:
    task = await _require_task_in_mission(session, mission_id, task_id)
    return TaskRead.model_validate(task)


@router.post("/{task_id}/complete", response_model=TaskRead)
async def complete_task_endpoint(
    mission_id: uuid.UUID,
    task_id: uuid.UUID,
    payload: CompleteTaskRequest,
    session: AsyncSession = Depends(get_session),
) -> TaskRead:
    await _require_task_in_mission(session, mission_id, task_id)
    try:
        task = await complete_task(session, task_id, payload.actual_output, payload.confidence)
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidTaskTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return TaskRead.model_validate(task)


@router.post("/{task_id}/fail", response_model=FailTaskResult)
async def fail_task_endpoint(
    mission_id: uuid.UUID,
    task_id: uuid.UUID,
    payload: FailTaskRequest,
    session: AsyncSession = Depends(get_session),
) -> FailTaskResult:
    await _require_task_in_mission(session, mission_id, task_id)
    try:
        return await fail_task(session, mission_id, task_id, payload.reason)
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidTaskTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/{task_id}/replan", response_model=TaskRead)
async def replan_task_endpoint(
    mission_id: uuid.UUID, task_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> TaskRead:
    await _require_task_in_mission(session, mission_id, task_id)
    try:
        task = await replan_task(session, mission_id, task_id)
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidTaskTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return TaskRead.model_validate(task)


orchestrator_router = APIRouter(prefix="/missions/{mission_id}/orchestrator", tags=["orchestrator"])


@orchestrator_router.post("/dispatch", response_model=DispatchReport)
async def dispatch_endpoint(
    mission_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> DispatchReport:
    try:
        return await run_dispatch_cycle(session, mission_id)
    except MissionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except LockAcquisitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
