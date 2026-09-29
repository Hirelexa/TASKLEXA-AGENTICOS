import unittest
import uuid

from tasklexa_api.domain.enums import TaskPriority, TaskStatus
from tasklexa_api.domain.orchestrator import compute_task_readiness
from tasklexa_api.schemas.mission import TaskRead


def _task(
    task_id: uuid.UUID,
    mission_id: uuid.UUID,
    status: TaskStatus = TaskStatus.PENDING,
    dependencies: list[uuid.UUID] | None = None,
) -> TaskRead:
    from datetime import UTC, datetime

    return TaskRead(
        id=task_id,
        mission_id=mission_id,
        title=f"task {task_id}",
        description=None,
        status=status,
        priority=TaskPriority.MEDIUM,
        required_capabilities=None,
        dependencies=dependencies,
        assigned_agent=None,
        tool_requirements=None,
        expected_output=None,
        actual_output=None,
        confidence=None,
        created_at=datetime.now(UTC),
        completed_at=None,
    )


class TaskReadinessTests(unittest.TestCase):
    def test_task_with_no_dependencies_is_ready(self) -> None:
        mission_id = uuid.uuid4()
        a = uuid.uuid4()
        report = compute_task_readiness([_task(a, mission_id)])
        self.assertEqual(report.ready_task_ids, [a])

    def test_task_waiting_on_incomplete_dependency_is_blocked(self) -> None:
        mission_id = uuid.uuid4()
        a, b = uuid.uuid4(), uuid.uuid4()
        report = compute_task_readiness(
            [_task(a, mission_id), _task(b, mission_id, dependencies=[a])]
        )
        self.assertEqual(report.ready_task_ids, [a])
        self.assertEqual(report.blocked_task_ids, [b])

    def test_task_becomes_ready_once_dependency_completes(self) -> None:
        mission_id = uuid.uuid4()
        a, b = uuid.uuid4(), uuid.uuid4()
        report = compute_task_readiness(
            [_task(a, mission_id, status=TaskStatus.COMPLETED), _task(b, mission_id, dependencies=[a])]
        )
        self.assertEqual(report.ready_task_ids, [b])
        self.assertEqual(report.done_task_ids, [a])

    def test_task_depending_on_failed_task_stays_blocked_not_ready(self) -> None:
        mission_id = uuid.uuid4()
        a, b = uuid.uuid4(), uuid.uuid4()
        report = compute_task_readiness(
            [_task(a, mission_id, status=TaskStatus.FAILED), _task(b, mission_id, dependencies=[a])]
        )
        self.assertEqual(report.ready_task_ids, [])
        self.assertEqual(report.blocked_task_ids, [b])
        self.assertEqual(report.failed_task_ids, [a])

    def test_in_progress_task_is_reported_separately(self) -> None:
        mission_id = uuid.uuid4()
        a = uuid.uuid4()
        report = compute_task_readiness([_task(a, mission_id, status=TaskStatus.RUNNING)])
        self.assertEqual(report.in_progress_task_ids, [a])
        self.assertEqual(report.ready_task_ids, [])

    def test_direct_two_task_cycle_is_detected(self) -> None:
        mission_id = uuid.uuid4()
        a, b = uuid.uuid4(), uuid.uuid4()
        report = compute_task_readiness(
            [_task(a, mission_id, dependencies=[b]), _task(b, mission_id, dependencies=[a])]
        )
        self.assertEqual(set(report.cyclic_task_ids), {a, b})
        self.assertEqual(report.ready_task_ids, [])
        self.assertEqual(report.blocked_task_ids, [])

    def test_self_dependency_is_a_cycle(self) -> None:
        mission_id = uuid.uuid4()
        a = uuid.uuid4()
        report = compute_task_readiness([_task(a, mission_id, dependencies=[a])])
        self.assertEqual(report.cyclic_task_ids, [a])

    def test_three_task_cycle_is_detected(self) -> None:
        mission_id = uuid.uuid4()
        a, b, c = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        report = compute_task_readiness(
            [
                _task(a, mission_id, dependencies=[b]),
                _task(b, mission_id, dependencies=[c]),
                _task(c, mission_id, dependencies=[a]),
            ]
        )
        self.assertEqual(set(report.cyclic_task_ids), {a, b, c})

    def test_cycle_does_not_falsely_block_unrelated_tasks(self) -> None:
        mission_id = uuid.uuid4()
        a, b, unrelated = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        report = compute_task_readiness(
            [
                _task(a, mission_id, dependencies=[b]),
                _task(b, mission_id, dependencies=[a]),
                _task(unrelated, mission_id),
            ]
        )
        self.assertEqual(set(report.cyclic_task_ids), {a, b})
        self.assertEqual(report.ready_task_ids, [unrelated])

    def test_dependency_on_task_outside_the_given_set_never_resolves(self) -> None:
        mission_id = uuid.uuid4()
        a = uuid.uuid4()
        phantom_dependency = uuid.uuid4()
        report = compute_task_readiness([_task(a, mission_id, dependencies=[phantom_dependency])])
        self.assertEqual(report.ready_task_ids, [])
        self.assertEqual(report.blocked_task_ids, [a])
        self.assertEqual(report.cyclic_task_ids, [])

    def test_empty_task_list_yields_empty_report(self) -> None:
        report = compute_task_readiness([])
        self.assertEqual(report.ready_task_ids, [])
        self.assertEqual(report.blocked_task_ids, [])
        self.assertEqual(report.cyclic_task_ids, [])


if __name__ == "__main__":
    unittest.main()
