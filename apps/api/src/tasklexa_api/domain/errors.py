import uuid

from tasklexa_api.domain.enums import MissionStatus


class MissionNotFoundError(Exception):
    def __init__(self, mission_id: uuid.UUID) -> None:
        self.mission_id = mission_id
        super().__init__(f"Mission {mission_id} not found")


class InvalidMissionTransitionError(Exception):
    def __init__(self, current: MissionStatus, target: MissionStatus) -> None:
        self.current = current
        self.target = target
        super().__init__(f"Cannot transition mission from {current.value} to {target.value}")
