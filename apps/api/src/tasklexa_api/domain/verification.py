from tasklexa_api.domain.enums import TaskStatus, VerificationStatus
from tasklexa_api.schemas.mission import TaskRead
from tasklexa_api.schemas.verification import VerificationEvaluation

_UNSETTLED_TASK_STATUSES = frozenset(
    {TaskStatus.PENDING, TaskStatus.READY, TaskStatus.ASSIGNED, TaskStatus.RUNNING, TaskStatus.WAITING_APPROVAL}
)


def evaluate_verification(
    tasks: list[TaskRead],
    evidence_count: int,
    unresolved_conflict_count: int,
    pending_approval_count: int,
    decision_count: int,
    success_criteria: list[str] | None,
) -> VerificationEvaluation:
    """Pure, deterministic verification logic - no DB, no I/O.

    docs/domain-model.md: "Verification must inspect objective, success
    criteria, task outputs, evidence, decisions, actions, failures,
    contradictions, and constraints." "Actions" has no persisted entity
    anywhere in this codebase (ADR-015); "contradictions" maps to Conflict,
    inspected here via unresolved_conflict_count even though nothing creates
    a Conflict row yet (docs/phase-10.md's Known Limitations) - so this
    check honestly always passes today, not because it's skipped.
    """
    criteria_results: list[dict] = []
    issues: list[str] = []

    unsettled_tasks = [t for t in tasks if t.status in _UNSETTLED_TASK_STATUSES]
    all_tasks_settled = len(unsettled_tasks) == 0
    criteria_results.append(
        {
            "criterion": "all_tasks_settled",
            "passed": all_tasks_settled,
            "detail": f"{len(unsettled_tasks)} of {len(tasks)} task(s) not yet COMPLETED/FAILED/CANCELLED",
        }
    )
    if not all_tasks_settled:
        issues.append(f"{len(unsettled_tasks)} task(s) are still in progress")

    failed_tasks = [t for t in tasks if t.status == TaskStatus.FAILED]
    no_failed_tasks = len(failed_tasks) == 0
    criteria_results.append(
        {"criterion": "no_failed_tasks", "passed": no_failed_tasks, "detail": f"{len(failed_tasks)} task(s) FAILED"}
    )
    if not no_failed_tasks:
        issues.append(f"{len(failed_tasks)} task(s) failed: {[str(t.id) for t in failed_tasks]}")

    no_unresolved_conflicts = unresolved_conflict_count == 0
    criteria_results.append(
        {
            "criterion": "no_unresolved_conflicts",
            "passed": no_unresolved_conflicts,
            "detail": f"{unresolved_conflict_count} unresolved conflict(s)",
        }
    )
    if not no_unresolved_conflicts:
        issues.append(f"{unresolved_conflict_count} unresolved conflict(s) among agents")

    no_pending_approvals = pending_approval_count == 0
    criteria_results.append(
        {
            "criterion": "no_pending_approvals",
            "passed": no_pending_approvals,
            "detail": f"{pending_approval_count} pending approval(s)",
        }
    )
    if not no_pending_approvals:
        issues.append(f"{pending_approval_count} approval(s) still PENDING")

    has_evidence = evidence_count > 0
    criteria_results.append(
        {
            "criterion": "has_evidence",
            "passed": has_evidence,
            "detail": f"{evidence_count} evidence record(s)",
            "informational": True,
        }
    )

    success_criteria_defined = bool(success_criteria)
    criteria_results.append(
        {
            "criterion": "success_criteria_defined",
            "passed": success_criteria_defined,
            "detail": f"{len(success_criteria or [])} success criterion/criteria defined on the mission",
            "informational": True,
        }
    )

    if decision_count:
        criteria_results.append(
            {
                "criterion": "decisions_reviewed",
                "passed": True,
                "detail": f"{decision_count} decision(s) reviewed",
                "informational": True,
            }
        )

    hard_criteria_passed = all_tasks_settled and no_failed_tasks and no_unresolved_conflicts and no_pending_approvals

    if not hard_criteria_passed:
        verification_status = VerificationStatus.FAILED
    elif success_criteria_defined and not has_evidence:
        verification_status = VerificationStatus.PARTIAL
        issues.append("mission defines success_criteria but no evidence was recorded to substantiate it")
    else:
        verification_status = VerificationStatus.PASSED

    passed_count = sum(1 for c in criteria_results if c["passed"])
    confidence = passed_count / len(criteria_results)

    return VerificationEvaluation(
        verification_status=verification_status,
        criteria_results=criteria_results,
        issues=issues,
        confidence=confidence,
    )
