import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tasklexa_api.domain.enums import (
    ApprovalStatus,
    ConflictStatus,
    ExecutionEventStatus,
    ExecutionEventType,
    MissionStatus,
    VerificationStatus,
)
from tasklexa_api.domain.errors import InvalidMissionTransitionError, MissionNotFoundError
from tasklexa_api.domain.verification import evaluate_verification
from tasklexa_api.models.execution_event import ExecutionEvent
from tasklexa_api.models.verification import VerificationReport
from tasklexa_api.repositories.approvals import list_approvals_for_mission
from tasklexa_api.repositories.decisions import list_conflicts_for_mission, list_decisions_for_mission
from tasklexa_api.repositories.evidence import list_evidence_for_mission
from tasklexa_api.repositories.missions import get_mission, transition_mission
from tasklexa_api.repositories.tasks import list_tasks_for_mission
from tasklexa_api.schemas.mission import TaskRead


async def get_verification_report(session: AsyncSession, report_id: uuid.UUID) -> VerificationReport | None:
    return await session.get(VerificationReport, report_id)


async def list_verification_reports_for_mission(
    session: AsyncSession, mission_id: uuid.UUID
) -> list[VerificationReport]:
    result = await session.execute(
        select(VerificationReport)
        .where(VerificationReport.mission_id == mission_id)
        .order_by(VerificationReport.created_at.asc())
    )
    return list(result.scalars().all())


async def run_verification(session: AsyncSession, mission_id: uuid.UUID) -> VerificationReport:
    """Independent final check before mission completion.

    Fetches everything docs/domain-model.md's Verification rules require
    inspecting, then delegates the actual pass/fail logic to the pure
    domain.verification.evaluate_verification() - this function's own job is
    just gathering data and applying the result (persisting the report,
    emitting the event, and attempting the mission transition it earns).
    """
    mission = await get_mission(session, mission_id)
    if mission is None:
        raise MissionNotFoundError(mission_id)

    tasks = await list_tasks_for_mission(session, mission_id)
    evidence = await list_evidence_for_mission(session, mission_id)
    decisions = await list_decisions_for_mission(session, mission_id)
    conflicts = await list_conflicts_for_mission(session, mission_id)
    approvals = await list_approvals_for_mission(session, mission_id)

    evaluation = evaluate_verification(
        tasks=[TaskRead.model_validate(task) for task in tasks],
        evidence_count=len(evidence),
        unresolved_conflict_count=sum(1 for c in conflicts if c.status != ConflictStatus.RESOLVED),
        pending_approval_count=sum(1 for a in approvals if a.status == ApprovalStatus.PENDING),
        decision_count=len(decisions),
        success_criteria=mission.success_criteria,
    )

    report = VerificationReport(
        mission_id=mission_id,
        verification_status=evaluation.verification_status,
        criteria_results=evaluation.criteria_results,
        issues=evaluation.issues,
        confidence=evaluation.confidence,
    )
    session.add(report)
    await session.flush()

    event_status = (
        ExecutionEventStatus.FAILURE
        if evaluation.verification_status == VerificationStatus.FAILED
        else ExecutionEventStatus.SUCCESS
    )
    session.add(
        ExecutionEvent(
            mission_id=mission_id,
            correlation_id=uuid.uuid4(),
            event_type=ExecutionEventType.VERIFICATION_STARTED,
            status=event_status,
            payload={"report_id": str(report.id), "verification_status": evaluation.verification_status.value},
        )
    )

    # Only actually completes/fails the mission when it's legitimately in
    # VERIFYING (the only state the diagram allows either edge from). Running
    # verification at any other time still produces a real report - it just
    # has no mission-level side effect, the same way project_mission() works
    # regardless of mission status.
    target_mission_status = {
        VerificationStatus.PASSED: MissionStatus.COMPLETED,
        VerificationStatus.FAILED: MissionStatus.FAILED,
    }.get(evaluation.verification_status)

    if target_mission_status is not None:
        try:
            await transition_mission(session, mission_id, target_mission_status)
        except InvalidMissionTransitionError:
            await session.commit()
    else:
        await session.commit()

    await session.refresh(report)
    return report
