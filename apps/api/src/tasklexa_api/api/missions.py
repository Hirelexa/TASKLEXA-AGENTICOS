import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from tasklexa_api.db.session import get_session
from tasklexa_api.domain.enums import MissionStatus
from tasklexa_api.domain.errors import InvalidMissionTransitionError, MissionNotFoundError
from tasklexa_api.integrations.neo4j.dependency import get_graph_service
from tasklexa_api.repositories.execution_events import list_events_for_mission
from tasklexa_api.repositories.graph_projection import project_mission
from tasklexa_api.repositories.missions import create_mission, get_mission, list_missions, transition_mission
from tasklexa_api.repositories.team_plans import resolve_team_for_mission
from tasklexa_api.repositories.verification import (
    get_verification_report,
    list_verification_reports_for_mission,
    run_verification,
)
from tasklexa_api.schemas.agent import AgentTeamPlan
from tasklexa_api.schemas.execution_event import ExecutionEventRead
from tasklexa_api.schemas.graph import MissionGraph, ProjectionReport
from tasklexa_api.schemas.mission import MissionCreate, MissionRead
from tasklexa_api.schemas.verification import VerificationReportRead

router = APIRouter(prefix="/missions", tags=["missions"])


class MissionTransitionRequest(BaseModel):
    status: MissionStatus


class TeamPlanRequest(BaseModel):
    required_capabilities: list[str] = Field(default_factory=list)


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


@router.post("/{mission_id}/team-plan", response_model=AgentTeamPlan)
async def resolve_team_plan_endpoint(
    mission_id: uuid.UUID,
    payload: TeamPlanRequest,
    session: AsyncSession = Depends(get_session),
) -> AgentTeamPlan:
    try:
        return await resolve_team_for_mission(session, mission_id, payload.required_capabilities)
    except MissionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{mission_id}/graph/project", response_model=ProjectionReport)
async def project_mission_graph_endpoint(
    mission_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> ProjectionReport:
    """Rebuild this mission's Neo4j projection from PostgreSQL.

    Every write is idempotent, so this is also the graph projection repair
    path: call it again after a failure and it converges to the current
    PostgreSQL state without duplicating anything.
    """
    try:
        return await project_mission(session, mission_id)
    except MissionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{mission_id}/graph", response_model=MissionGraph)
async def get_mission_graph_endpoint(
    mission_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> MissionGraph:
    mission = await get_mission(session, mission_id)
    if mission is None:
        raise HTTPException(status_code=404, detail=f"Mission {mission_id} not found")
    return await get_graph_service().get_mission_graph(mission_id)


@router.post("/{mission_id}/verify", response_model=VerificationReportRead)
async def verify_mission_endpoint(
    mission_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> VerificationReportRead:
    """Run an independent verification pass and, if it PASSED or FAILED while
    the mission is VERIFYING, apply the corresponding mission transition.

    Safe to call more than once - each call produces its own report; only a
    call made while the mission is actually VERIFYING can change mission
    status (see repositories.verification.run_verification).
    """
    try:
        report = await run_verification(session, mission_id)
    except MissionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return VerificationReportRead.model_validate(report)


@router.get("/{mission_id}/verification-reports", response_model=list[VerificationReportRead])
async def list_verification_reports_endpoint(
    mission_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> list[VerificationReportRead]:
    mission = await get_mission(session, mission_id)
    if mission is None:
        raise HTTPException(status_code=404, detail=f"Mission {mission_id} not found")
    reports = await list_verification_reports_for_mission(session, mission_id)
    return [VerificationReportRead.model_validate(report) for report in reports]


@router.get("/{mission_id}/verification-reports/{report_id}", response_model=VerificationReportRead)
async def get_verification_report_endpoint(
    mission_id: uuid.UUID, report_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> VerificationReportRead:
    report = await get_verification_report(session, report_id)
    if report is None or report.mission_id != mission_id:
        raise HTTPException(
            status_code=404, detail=f"VerificationReport {report_id} not found in mission {mission_id}"
        )
    return VerificationReportRead.model_validate(report)
