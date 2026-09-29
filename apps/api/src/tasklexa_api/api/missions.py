import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from tasklexa_api.db.session import get_session
from tasklexa_api.domain.enums import MissionStatus
from tasklexa_api.domain.errors import InvalidMissionTransitionError, MissionNotFoundError
from tasklexa_api.repositories.execution_events import list_events_for_mission
from tasklexa_api.repositories.missions import create_mission, get_mission, list_missions, transition_mission
from tasklexa_api.schemas.execution_event import ExecutionEventRead
from tasklexa_api.schemas.mission import MissionCreate, MissionRead

router = APIRouter(prefix="/missions", tags=["missions"])


class MissionTransitionRequest(BaseModel):
    status: MissionStatus


@router.post("", response_model=MissionRead, status_code=201)
async def create_mission_endpoint(
    payload: MissionCreate, session: AsyncSession = Depends(get_session)
) -> MissionRead:
    mission = await create_mission(session, payload)
    return MissionRead.model_validate(mission)


@router.get("", response_model=list[MissionRead])
async def list_missions_endpoint(session: AsyncSession = Depends(get_session)) -> list[MissionRead]:
    missions = await list_missions(session)
    return [MissionRead.model_validate(mission) for mission in missions]


@router.get("/{mission_id}", response_model=MissionRead)
async def get_mission_endpoint(
    mission_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> MissionRead:
    mission = await get_mission(session, mission_id)
    if mission is None:
        raise HTTPException(status_code=404, detail=f"Mission {mission_id} not found")
    return MissionRead.model_validate(mission)


@router.post("/{mission_id}/transitions", response_model=MissionRead)
async def transition_mission_endpoint(
    mission_id: uuid.UUID,
    payload: MissionTransitionRequest,
    session: AsyncSession = Depends(get_session),
) -> MissionRead:
    try:
        mission = await transition_mission(session, mission_id, payload.status)
    except MissionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidMissionTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return MissionRead.model_validate(mission)


@router.get("/{mission_id}/events", response_model=list[ExecutionEventRead])
async def list_mission_events_endpoint(
    mission_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> list[ExecutionEventRead]:
    mission = await get_mission(session, mission_id)
    if mission is None:
        raise HTTPException(status_code=404, detail=f"Mission {mission_id} not found")
    events = await list_events_for_mission(session, mission_id)
    return [ExecutionEventRead.model_validate(event) for event in events]
