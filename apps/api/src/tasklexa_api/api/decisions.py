import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from tasklexa_api.db.session import get_session
from tasklexa_api.domain.errors import InvalidMissionTransitionError, MissionNotFoundError
from tasklexa_api.repositories.decisions import create_decision, get_decision, list_decisions_for_mission
from tasklexa_api.repositories.missions import get_mission
from tasklexa_api.schemas.decision import DecisionCreate, DecisionRead

router = APIRouter(prefix="/missions/{mission_id}/decisions", tags=["decisions"])


@router.post("", response_model=DecisionRead, status_code=201)
async def create_decision_endpoint(
    mission_id: uuid.UUID, payload: DecisionCreate, session: AsyncSession = Depends(get_session)
) -> DecisionRead:
    if payload.mission_id != mission_id:
        raise HTTPException(status_code=400, detail="payload mission_id must match the URL mission_id")
    try:
        decision = await create_decision(session, payload)
    except MissionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidMissionTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return DecisionRead.model_validate(decision)


@router.get("", response_model=list[DecisionRead])
async def list_decisions_endpoint(
    mission_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> list[DecisionRead]:
    mission = await get_mission(session, mission_id)
    if mission is None:
        raise HTTPException(status_code=404, detail=f"Mission {mission_id} not found")
    decisions = await list_decisions_for_mission(session, mission_id)
    return [DecisionRead.model_validate(decision) for decision in decisions]


@router.get("/{decision_id}", response_model=DecisionRead)
async def get_decision_endpoint(
    mission_id: uuid.UUID, decision_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> DecisionRead:
    decision = await get_decision(session, decision_id)
    if decision is None or decision.mission_id != mission_id:
        raise HTTPException(status_code=404, detail=f"Decision {decision_id} not found in mission {mission_id}")
    return DecisionRead.model_validate(decision)
