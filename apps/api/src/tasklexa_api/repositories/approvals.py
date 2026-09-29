import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tasklexa_api.domain.enums import ApprovalStatus, ExecutionEventStatus, ExecutionEventType, MissionStatus
from tasklexa_api.domain.errors import ApprovalNotFoundError, InvalidApprovalTransitionError
from tasklexa_api.models.decision import Approval
from tasklexa_api.models.execution_event import ExecutionEvent
from tasklexa_api.repositories.missions import transition_mission


async def get_approval(session: AsyncSession, approval_id: uuid.UUID) -> Approval | None:
    return await session.get(Approval, approval_id)


async def list_approvals_for_mission(session: AsyncSession, mission_id: uuid.UUID) -> list[Approval]:
    result = await session.execute(select(Approval).where(Approval.mission_id == mission_id))
    return list(result.scalars().all())


async def _resolve_approval(
    session: AsyncSession,
    mission_id: uuid.UUID,
    approval_id: uuid.UUID,
    target_approval_status: ApprovalStatus,
    target_mission_status: MissionStatus,
    approved_by: str,
    comments: str | None,
) -> Approval:
    approval = await get_approval(session, approval_id)
    if approval is None or approval.mission_id != mission_id:
        raise ApprovalNotFoundError(approval_id)
    if approval.status != ApprovalStatus.PENDING:
        raise InvalidApprovalTransitionError(
            approval_id, f"cannot resolve an approval in status {approval.status.value}"
        )

    approval.status = target_approval_status
    approval.approved_by = approved_by
    approval.approved_at = datetime.now(UTC)
    approval.comments = comments

    event_type = (
        ExecutionEventType.APPROVAL_REJECTED
        if target_approval_status == ApprovalStatus.REJECTED
        else ExecutionEventType.APPROVAL_GRANTED
    )
    session.add(
        ExecutionEvent(
            mission_id=mission_id,
            correlation_id=uuid.uuid4(),
            event_type=event_type,
            status=ExecutionEventStatus.SUCCESS,
            payload={"approval_id": str(approval_id), "approval_status": target_approval_status.value},
        )
    )

    await transition_mission(session, mission_id, target_mission_status)
    await session.refresh(approval)
    return approval


async def approve_approval(
    session: AsyncSession, mission_id: uuid.UUID, approval_id: uuid.UUID, approved_by: str, comments: str | None
) -> Approval:
    return await _resolve_approval(
        session, mission_id, approval_id, ApprovalStatus.APPROVED, MissionStatus.RUNNING, approved_by, comments
    )


async def modify_approval(
    session: AsyncSession, mission_id: uuid.UUID, approval_id: uuid.UUID, approved_by: str, comments: str | None
) -> Approval:
    return await _resolve_approval(
        session, mission_id, approval_id, ApprovalStatus.MODIFIED, MissionStatus.RUNNING, approved_by, comments
    )


async def reject_approval(
    session: AsyncSession, mission_id: uuid.UUID, approval_id: uuid.UUID, approved_by: str, comments: str | None
) -> Approval:
    return await _resolve_approval(
        session, mission_id, approval_id, ApprovalStatus.REJECTED, MissionStatus.CANCELLED, approved_by, comments
    )
