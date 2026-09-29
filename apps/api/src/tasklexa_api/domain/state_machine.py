from tasklexa_api.domain.enums import MissionStatus
from tasklexa_api.domain.errors import InvalidMissionTransitionError

MISSION_TRANSITIONS: dict[MissionStatus, frozenset[MissionStatus]] = {
    MissionStatus.DRAFT: frozenset({MissionStatus.PLANNING, MissionStatus.CANCELLED}),
    MissionStatus.PLANNING: frozenset(
        {MissionStatus.ASSEMBLING, MissionStatus.FAILED, MissionStatus.CANCELLED}
    ),
    MissionStatus.ASSEMBLING: frozenset(
        {MissionStatus.RUNNING, MissionStatus.FAILED, MissionStatus.CANCELLED}
    ),
    MissionStatus.RUNNING: frozenset(
        {
            MissionStatus.WAITING_APPROVAL,
            MissionStatus.VERIFYING,
            MissionStatus.FAILED,
            MissionStatus.CANCELLED,
        }
    ),
    MissionStatus.WAITING_APPROVAL: frozenset(
        {MissionStatus.RUNNING, MissionStatus.FAILED, MissionStatus.CANCELLED}
    ),
    MissionStatus.VERIFYING: frozenset(
        {MissionStatus.COMPLETED, MissionStatus.FAILED, MissionStatus.CANCELLED}
    ),
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
