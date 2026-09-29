import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tasklexa_api.domain.enums import ApprovalStatus, ExecutionEventStatus, ExecutionEventType, MissionStatus
from tasklexa_api.domain.errors import MissionNotFoundError
from tasklexa_api.models.decision import Approval, Decision
from tasklexa_api.models.execution_event import ExecutionEvent
from tasklexa_api.repositories.missions import get_mission, transition_mission
from tasklexa_api.schemas.decision import DecisionCreate


async def create_decision(session: AsyncSession, data: DecisionCreate) -> Decision:
    mission = await get_mission(session, data.mission_id)
    if mission is None:
        raise MissionNotFoundError(data.mission_id)

    decision = Decision(
        mission_id=data.mission_id,
        title=data.title,
        description=data.description,
        options=data.options,
        recommendation=data.recommendation,
        evidence_ids=data.evidence_ids,
        confidence=data.confidence,
        risk_level=data.risk_level,
        approval_required=data.approval_required,
    )
    session.add(decision)
    await session.flush()

    session.add(
        ExecutionEvent(
            mission_id=data.mission_id,
            correlation_id=uuid.uuid4(),
            event_type=ExecutionEventType.DECISION_CREATED,
            status=ExecutionEventStatus.SUCCESS,
            payload={"decision_id": str(decision.id), "approval_required": data.approval_required},
        )
    )

    if data.approval_required:
        approval = Approval(
            mission_id=data.mission_id,
            decision_id=decision.id,
            requested_by=data.requested_by,
            reason=data.approval_reason,
            status=ApprovalStatus.PENDING,
        )
        session.add(approval)
        await session.flush()

        session.add(
            ExecutionEvent(
                mission_id=data.mission_id,
                correlation_id=uuid.uuid4(),
                event_type=ExecutionEventType.APPROVAL_REQUESTED,
                status=ExecutionEventStatus.SUCCESS,
                payload={"decision_id": str(decision.id), "approval_id": str(approval.id)},
            )
        )
        await transition_mission(session, data.mission_id, MissionStatus.WAITING_APPROVAL)
    else:
        await session.commit()

    await session.refresh(decision)
    return decision


async def get_decision(session: AsyncSession, decision_id: uuid.UUID) -> Decision | None:
    return await session.get(Decision, decision_id)


async def list_decisions_for_mission(session: AsyncSession, mission_id: uuid.UUID) -> list[Decision]:
    result = await session.execute(select(Decision).where(Decision.mission_id == mission_id))
    return list(result.scalars().all())


async def list_approvals_for_decision(session: AsyncSession, decision_id: uuid.UUID) -> list[Approval]:
    result = await session.execute(select(Approval).where(Approval.decision_id == decision_id))
    return list(result.scalars().all())
