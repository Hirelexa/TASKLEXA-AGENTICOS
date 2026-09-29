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


class ProviderNotConfiguredError(Exception):
    def __init__(self, provider: str) -> None:
        self.provider = provider
        super().__init__(f"{provider} is not configured; no credential is present")


class ProviderCallFailedError(Exception):
    def __init__(self, provider: str, detail: str) -> None:
        self.provider = provider
        self.detail = detail
        super().__init__(f"{provider} call failed: {detail}")


class ProviderUnverifiedError(Exception):
    """A credential is present, but the integration's endpoint/schema is not confirmed.

    Distinct from ProviderNotConfiguredError (no credential at all) and
    ProviderCallFailedError (a real call was attempted and failed) - this
    means a live call is deliberately never attempted because there is
    nothing verified to call against yet.
    """

    def __init__(self, provider: str, detail: str) -> None:
        self.provider = provider
        self.detail = detail
        super().__init__(f"{provider} is UNVERIFIED: {detail}")


class StructuredOutputValidationError(Exception):
    def __init__(self, schema_name: str, detail: str) -> None:
        self.schema_name = schema_name
        self.detail = detail
        super().__init__(f"Structured output for schema '{schema_name}' failed validation: {detail}")


class TaskNotFoundError(Exception):
    def __init__(self, task_id: uuid.UUID) -> None:
        self.task_id = task_id
        super().__init__(f"Task {task_id} not found")


class InvalidTaskTransitionError(Exception):
    def __init__(self, task_id: uuid.UUID, detail: str) -> None:
        self.task_id = task_id
        self.detail = detail
        super().__init__(f"Task {task_id}: {detail}")


class LockAcquisitionError(Exception):
    def __init__(self, key: str) -> None:
        self.key = key
        super().__init__(f"Could not acquire lock '{key}'; another operation is already in progress")


class DecisionNotFoundError(Exception):
    def __init__(self, decision_id: uuid.UUID) -> None:
        self.decision_id = decision_id
        super().__init__(f"Decision {decision_id} not found")


class ApprovalNotFoundError(Exception):
    def __init__(self, approval_id: uuid.UUID) -> None:
        self.approval_id = approval_id
        super().__init__(f"Approval {approval_id} not found")


class InvalidApprovalTransitionError(Exception):
    def __init__(self, approval_id: uuid.UUID, detail: str) -> None:
        self.approval_id = approval_id
        self.detail = detail
        super().__init__(f"Approval {approval_id}: {detail}")


class MissionPausedError(Exception):
    """docs/domain-model.md: 'PENDING approvals pause mission execution for the
    relevant action... No action gated by approval may execute before approval
    or modification is recorded.'
    """

    def __init__(self, mission_id: uuid.UUID) -> None:
        self.mission_id = mission_id
        super().__init__(f"Mission {mission_id} is WAITING_APPROVAL; dispatch is paused until resolved")
