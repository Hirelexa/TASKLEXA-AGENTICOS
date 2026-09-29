from tasklexa_api.domain.enums import MissionStatus
from tasklexa_api.domain.errors import InvalidMissionTransitionError

# Mirrors docs/architecture.md's "Mission State Machine" mermaid diagram exactly
# (verbatim, not inferred - see ADR-021, which supersedes ADR-010's provisional map).
#
#   DRAFT --> PLANNING: start_mission
#   PLANNING --> ASSEMBLING: valid_plan_created
#   PLANNING --> FAILED: planning_invalid_after_retries
#   ASSEMBLING --> RUNNING: team_and_tools_resolved
#   ASSEMBLING --> FAILED: required_capability_unavailable
#   RUNNING --> WAITING_APPROVAL: approval_required
#   WAITING_APPROVAL --> RUNNING: approval_approved_or_modified
#   WAITING_APPROVAL --> CANCELLED: approval_rejected_terminal
#   RUNNING --> VERIFYING: tasks_complete
#   RUNNING --> FAILED: unrecoverable_failure
#   RUNNING --> PLANNING: bounded_replan_requested
#   VERIFYING --> COMPLETED: verification_passed
#   VERIFYING --> FAILED: verification_failed
MISSION_TRANSITIONS: dict[MissionStatus, frozenset[MissionStatus]] = {
    MissionStatus.DRAFT: frozenset({MissionStatus.PLANNING}),
    MissionStatus.PLANNING: frozenset({MissionStatus.ASSEMBLING, MissionStatus.FAILED}),
    MissionStatus.ASSEMBLING: frozenset({MissionStatus.RUNNING, MissionStatus.FAILED}),
    MissionStatus.RUNNING: frozenset(
        {
            MissionStatus.WAITING_APPROVAL,
            MissionStatus.VERIFYING,
            MissionStatus.FAILED,
            MissionStatus.PLANNING,
        }
    ),
    MissionStatus.WAITING_APPROVAL: frozenset({MissionStatus.RUNNING, MissionStatus.CANCELLED}),
    MissionStatus.VERIFYING: frozenset({MissionStatus.COMPLETED, MissionStatus.FAILED}),
    MissionStatus.COMPLETED: frozenset(),
    MissionStatus.FAILED: frozenset(),
    MissionStatus.CANCELLED: frozenset(),
}

TERMINAL_MISSION_STATUSES: frozenset[MissionStatus] = frozenset(
    {MissionStatus.COMPLETED, MissionStatus.FAILED, MissionStatus.CANCELLED}
)


def validate_transition(current: MissionStatus, target: MissionStatus) -> None:
    if target not in MISSION_TRANSITIONS[current]:
        raise InvalidMissionTransitionError(current, target)
