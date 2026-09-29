import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from tasklexa_api.db.session import get_session
from tasklexa_api.domain.errors import ApprovalNotFoundError, InvalidApprovalTransitionError
from tasklexa_api.repositories.approvals import (
    approve_approval,
    get_approval,
    list_approvals_for_mission,
    modify_approval,
    reject_approval,
)
from tasklexa_api.repositories.missions import get_mission
from tasklexa_api.schemas.decision import ApprovalDecisionRequest, ApprovalRead

router = APIRouter(prefix="/missions/{mission_id}/approvals", tags=["approvals"])


async def _require_mission(session: AsyncSession, mission_id: uuid.UUID) -> None:
    mission = await get_mission(session, mission_id)
    if mission is None:
        raise HTTPException(status_code=404, detail=f"Mission {mission_id} not found")


@router.get("", response_model=list[ApprovalRead])
async def list_approvals_endpoint(
    mission_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> list[ApprovalRead]:
    await _require_mission(session, mission_id)
    approvals = await list_approvals_for_mission(session, mission_id)
    return [ApprovalRead.model_validate(approval) for approval in approvals]


@router.get("/{approval_id}", response_model=ApprovalRead)
async def get_approval_endpoint(
    mission_id: uuid.UUID, approval_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> ApprovalRead:
    approval = await get_approval(session, approval_id)
    if approval is None or approval.mission_id != mission_id:
        raise HTTPException(status_code=404, detail=f"Approval {approval_id} not found in mission {mission_id}")
    return ApprovalRead.model_validate(approval)


@router.post("/{approval_id}/approve", response_model=ApprovalRead)
async def approve_approval_endpoint(
    mission_id: uuid.UUID,
    approval_id: uuid.UUID,
    payload: ApprovalDecisionRequest,
    session: AsyncSession = Depends(get_session),
) -> ApprovalRead:
    try:
        approval = await approve_approval(session, mission_id, approval_id, payload.approved_by, payload.comments)
    except ApprovalNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidApprovalTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return ApprovalRead.model_validate(approval)


@router.post("/{approval_id}/modify", response_model=ApprovalRead)
async def modify_approval_endpoint(
    mission_id: uuid.UUID,
    approval_id: uuid.UUID,
    payload: ApprovalDecisionRequest,
    session: AsyncSession = Depends(get_session),
) -> ApprovalRead:
    try:
        approval = await modify_approval(session, mission_id, approval_id, payload.approved_by, payload.comments)
    except ApprovalNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidApprovalTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return ApprovalRead.model_validate(approval)


@router.post("/{approval_id}/reject", response_model=ApprovalRead)
async def reject_approval_endpoint(
    mission_id: uuid.UUID,
    approval_id: uuid.UUID,
    payload: ApprovalDecisionRequest,
    session: AsyncSession = Depends(get_session),
) -> ApprovalRead:
    try:
        approval = await reject_approval(session, mission_id, approval_id, payload.approved_by, payload.comments)
    except ApprovalNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidApprovalTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return ApprovalRead.model_validate(approval)
