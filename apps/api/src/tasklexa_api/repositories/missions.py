import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tasklexa_api.domain.enums import ExecutionEventStatus, ExecutionEventType, MissionStatus
from tasklexa_api.domain.errors import MissionNotFoundError
from tasklexa_api.domain.state_machine import TERMINAL_MISSION_STATUSES, validate_transition
from tasklexa_api.models.execution_event import ExecutionEvent
from tasklexa_api.models.mission import Mission
from tasklexa_api.schemas.mission import MissionCreate


async def create_mission(session: AsyncSession, data: MissionCreate) -> Mission:
    mission = Mission(
        title=data.title,
        objective=data.objective,
        description=data.description,
        status=MissionStatus.DRAFT,
        constraints=data.constraints,
        success_criteria=data.success_criteria,
        created_by=data.created_by,
    )
    session.add(mission)
    await session.flush()

    session.add(
        ExecutionEvent(
            mission_id=mission.id,
            correlation_id=uuid.uuid4(),
            event_type=ExecutionEventType.MISSION_CREATED,
            status=ExecutionEventStatus.SUCCESS,
            payload={"status": mission.status.value},
        )
    )
    await session.commit()
    await session.refresh(mission)
    return mission


async def get_mission(session: AsyncSession, mission_id: uuid.UUID) -> Mission | None:
    return await session.get(Mission, mission_id)


async def list_missions(session: AsyncSession, limit: int = 50) -> list[Mission]:
    result = await session.execute(select(Mission).order_by(Mission.created_at.desc()).limit(limit))
    return list(result.scalars().all())


async def transition_mission(
    session: AsyncSession, mission_id: uuid.UUID, target_status: MissionStatus
) -> Mission:
    mission = await session.get(Mission, mission_id)
    if mission is None:
        raise MissionNotFoundError(mission_id)

    validate_transition(mission.status, target_status)

    previous_status = mission.status
    now = datetime.now(UTC)

    mission.status = target_status
    if target_status == MissionStatus.RUNNING and mission.started_at is None:
        mission.started_at = now
    if target_status in TERMINAL_MISSION_STATUSES:
        mission.completed_at = now

    session.add(
        ExecutionEvent(
            mission_id=mission.id,
            correlation_id=uuid.uuid4(),
            event_type=ExecutionEventType.MISSION_STATUS_CHANGED,
            status=ExecutionEventStatus.SUCCESS,
            payload={"from": previous_status.value, "to": target_status.value},
        )
    )
    await session.commit()
    await session.refresh(mission)
    return mission
