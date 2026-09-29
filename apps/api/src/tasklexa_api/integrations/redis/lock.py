import uuid
from typing import Any, Protocol

from tasklexa_api.domain.errors import LockAcquisitionError

_RELEASE_IF_OWNER_SCRIPT = """
if redis.call("GET", KEYS[1]) == ARGV[1] then
    return redis.call("DEL", KEYS[1])
else
    return 0
end
"""


class RedisLockClient(Protocol):
    async def set(self, name: str, value: str, nx: bool = False, px: int | None = None) -> Any: ...

    async def eval(self, script: str, numkeys: int, *keys_and_args: str) -> Any: ...


class RedisLock:
    """A simple SET-NX-PX distributed lock with token-safe release.

    Matches docs/architecture.md's "Redis may hold ... execution locks" -
    used to prevent two concurrent dispatch cycles for the same mission
    from racing each other into a double assignment.
    """

    def __init__(self, client: RedisLockClient, key: str, ttl_ms: int = 30_000) -> None:
        self._client = client
        self._key = key
        self._ttl_ms = ttl_ms
        self._token = str(uuid.uuid4())

    async def acquire(self) -> bool:
        return bool(await self._client.set(self._key, self._token, nx=True, px=self._ttl_ms))

    async def release(self) -> None:
        await self._client.eval(_RELEASE_IF_OWNER_SCRIPT, 1, self._key, self._token)

    async def __aenter__(self) -> "RedisLock":
        if not await self.acquire():
            raise LockAcquisitionError(self._key)
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.release()
