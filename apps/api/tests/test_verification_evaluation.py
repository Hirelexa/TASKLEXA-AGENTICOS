import unittest
import uuid
from datetime import UTC, datetime

from tasklexa_api.domain.enums import TaskPriority, TaskStatus, VerificationStatus
from tasklexa_api.domain.verification import evaluate_verification
from tasklexa_api.schemas.mission import TaskRead


def _task(status: TaskStatus) -> TaskRead:
    return TaskRead(
        id=uuid.uuid4(),
        mission_id=uuid.uuid4(),
        title="task",
        description=None,
        status=status,
        priority=TaskPriority.MEDIUM,
        required_capabilities=None,
        dependencies=None,
        assigned_agent=None,
        tool_requirements=None,
        expected_output=None,
        actual_output=None,
        confidence=None,
        created_at=datetime.now(UTC),
        completed_at=None,
    )


class VerificationEvaluationTests(unittest.TestCase):
    def test_all_completed_tasks_no_criteria_no_evidence_passes(self) -> None:
        tasks = [_task(TaskStatus.COMPLETED), _task(TaskStatus.COMPLETED)]
        result = evaluate_verification(
            tasks=tasks,
            evidence_count=0,
            unresolved_conflict_count=0,
            pending_approval_count=0,
            decision_count=0,
            success_criteria=None,
        )
        self.assertEqual(result.verification_status, VerificationStatus.PASSED)
        self.assertEqual(result.issues, [])

    def test_unsettled_task_fails_verification(self) -> None:
        tasks = [_task(TaskStatus.COMPLETED), _task(TaskStatus.RUNNING)]
        result = evaluate_verification(
            tasks=tasks,
            evidence_count=0,
            unresolved_conflict_count=0,
            pending_approval_count=0,
            decision_count=0,
            success_criteria=None,
        )
        self.assertEqual(result.verification_status, VerificationStatus.FAILED)
        self.assertTrue(any("still in progress" in issue for issue in result.issues))

    def test_any_failed_task_fails_verification(self) -> None:
        tasks = [_task(TaskStatus.COMPLETED), _task(TaskStatus.FAILED)]
        result = evaluate_verification(
            tasks=tasks,
            evidence_count=5,
            unresolved_conflict_count=0,
            pending_approval_count=0,
            decision_count=0,
            success_criteria=None,
        )
        self.assertEqual(result.verification_status, VerificationStatus.FAILED)

    def test_unresolved_conflict_fails_verification(self) -> None:
        tasks = [_task(TaskStatus.COMPLETED)]
        result = evaluate_verification(
            tasks=tasks,
            evidence_count=0,
            unresolved_conflict_count=1,
            pending_approval_count=0,
            decision_count=0,
            success_criteria=None,
        )
        self.assertEqual(result.verification_status, VerificationStatus.FAILED)

    def test_pending_approval_fails_verification(self) -> None:
        tasks = [_task(TaskStatus.COMPLETED)]
        result = evaluate_verification(
            tasks=tasks,
            evidence_count=0,
            unresolved_conflict_count=0,
            pending_approval_count=1,
            decision_count=0,
            success_criteria=None,
        )
        self.assertEqual(result.verification_status, VerificationStatus.FAILED)

    def test_success_criteria_without_evidence_is_partial_not_passed(self) -> None:
        tasks = [_task(TaskStatus.COMPLETED)]
        result = evaluate_verification(
            tasks=tasks,
            evidence_count=0,
            unresolved_conflict_count=0,
            pending_approval_count=0,
            decision_count=0,
            success_criteria=["must reduce churn by 10%"],
        )
        self.assertEqual(result.verification_status, VerificationStatus.PARTIAL)
        self.assertTrue(any("no evidence" in issue for issue in result.issues))

    def test_success_criteria_with_evidence_passes(self) -> None:
        tasks = [_task(TaskStatus.COMPLETED)]
        result = evaluate_verification(
            tasks=tasks,
            evidence_count=3,
            unresolved_conflict_count=0,
            pending_approval_count=0,
            decision_count=0,
            success_criteria=["must reduce churn by 10%"],
        )
        self.assertEqual(result.verification_status, VerificationStatus.PASSED)

    def test_no_tasks_at_all_still_passes(self) -> None:
        result = evaluate_verification(
            tasks=[],
            evidence_count=0,
            unresolved_conflict_count=0,
            pending_approval_count=0,
            decision_count=0,
            success_criteria=None,
        )
        self.assertEqual(result.verification_status, VerificationStatus.PASSED)

    def test_confidence_is_lower_when_more_criteria_fail(self) -> None:
        clean = evaluate_verification(
            tasks=[_task(TaskStatus.COMPLETED)],
            evidence_count=0,
            unresolved_conflict_count=0,
            pending_approval_count=0,
            decision_count=0,
            success_criteria=None,
        )
        messy = evaluate_verification(
            tasks=[_task(TaskStatus.FAILED)],
            evidence_count=0,
            unresolved_conflict_count=1,
            pending_approval_count=1,
            decision_count=0,
            success_criteria=None,
        )
        self.assertGreater(clean.confidence, messy.confidence)

    def test_decisions_reviewed_criterion_only_appears_when_decisions_exist(self) -> None:
        without = evaluate_verification(
            tasks=[_task(TaskStatus.COMPLETED)],
            evidence_count=0,
            unresolved_conflict_count=0,
            pending_approval_count=0,
            decision_count=0,
            success_criteria=None,
        )
        with_decisions = evaluate_verification(
            tasks=[_task(TaskStatus.COMPLETED)],
            evidence_count=0,
            unresolved_conflict_count=0,
            pending_approval_count=0,
            decision_count=2,
            success_criteria=None,
        )
        without_names = {c["criterion"] for c in without.criteria_results}
        with_names = {c["criterion"] for c in with_decisions.criteria_results}
        self.assertNotIn("decisions_reviewed", without_names)
        self.assertIn("decisions_reviewed", with_names)


if __name__ == "__main__":
    unittest.main()
