import unittest

from tasklexa_api.domain.enums import MissionStatus
from tasklexa_api.domain.errors import InvalidMissionTransitionError
from tasklexa_api.domain.state_machine import (
    MISSION_TRANSITIONS,
    TERMINAL_MISSION_STATUSES,
    validate_transition,
)

# Every edge in docs/architecture.md's "Mission State Machine" mermaid diagram,
# transcribed verbatim (see ADR-021). This test exists specifically because an
# earlier hand-written version of MISSION_TRANSITIONS silently diverged from
# this diagram (extra CANCELLED edges that aren't drawn, a missing
# RUNNING -> PLANNING edge, a wrong WAITING_APPROVAL -> FAILED edge instead of
# -> CANCELLED) without anything catching it.
DOCUMENTED_EDGES = {
    (MissionStatus.DRAFT, MissionStatus.PLANNING),
    (MissionStatus.PLANNING, MissionStatus.ASSEMBLING),
    (MissionStatus.PLANNING, MissionStatus.FAILED),
    (MissionStatus.ASSEMBLING, MissionStatus.RUNNING),
    (MissionStatus.ASSEMBLING, MissionStatus.FAILED),
    (MissionStatus.RUNNING, MissionStatus.WAITING_APPROVAL),
    (MissionStatus.WAITING_APPROVAL, MissionStatus.RUNNING),
    (MissionStatus.WAITING_APPROVAL, MissionStatus.CANCELLED),
    (MissionStatus.RUNNING, MissionStatus.VERIFYING),
    (MissionStatus.RUNNING, MissionStatus.FAILED),
    (MissionStatus.RUNNING, MissionStatus.PLANNING),
    (MissionStatus.VERIFYING, MissionStatus.COMPLETED),
    (MissionStatus.VERIFYING, MissionStatus.FAILED),
}


class MissionStateMachineDocumentedEdgesTests(unittest.TestCase):
    def test_every_documented_edge_is_valid(self) -> None:
        for source, target in DOCUMENTED_EDGES:
            with self.subTest(source=source, target=target):
                validate_transition(source, target)  # must not raise

    def test_no_undocumented_edges_exist(self) -> None:
        actual_edges = {
            (source, target) for source, targets in MISSION_TRANSITIONS.items() for target in targets
        }
        self.assertEqual(actual_edges, DOCUMENTED_EDGES)

    def test_terminal_states_have_no_outgoing_edges(self) -> None:
        for status in (MissionStatus.COMPLETED, MissionStatus.FAILED, MissionStatus.CANCELLED):
            self.assertEqual(MISSION_TRANSITIONS[status], frozenset())

    def test_terminal_states_constant_matches_the_graph(self) -> None:
        graph_terminal = {status for status, targets in MISSION_TRANSITIONS.items() if not targets}
        self.assertEqual(graph_terminal, set(TERMINAL_MISSION_STATUSES))

    def test_every_mission_status_has_an_entry(self) -> None:
        self.assertEqual(set(MISSION_TRANSITIONS.keys()), set(MissionStatus))

    def test_rejecting_an_approval_is_terminal_not_a_return_to_running(self) -> None:
        # This is the specific bug that motivated writing this test file: an
        # earlier version allowed WAITING_APPROVAL -> FAILED, which isn't in
        # the diagram at all - rejection has exactly one destination.
        self.assertEqual(MISSION_TRANSITIONS[MissionStatus.WAITING_APPROVAL], frozenset({MissionStatus.RUNNING, MissionStatus.CANCELLED}))

    def test_bounded_replan_returns_running_to_planning(self) -> None:
        validate_transition(MissionStatus.RUNNING, MissionStatus.PLANNING)

    def test_invalid_transition_raises(self) -> None:
        with self.assertRaises(InvalidMissionTransitionError):
            validate_transition(MissionStatus.DRAFT, MissionStatus.COMPLETED)

    def test_draft_cannot_be_cancelled_directly(self) -> None:
        # Per the documented diagram, CANCELLED is reachable only via
        # WAITING_APPROVAL rejection - there is no direct DRAFT -> CANCELLED
        # edge, even though that might seem like a natural operation to allow.
        with self.assertRaises(InvalidMissionTransitionError):
            validate_transition(MissionStatus.DRAFT, MissionStatus.CANCELLED)


if __name__ == "__main__":
    unittest.main()
