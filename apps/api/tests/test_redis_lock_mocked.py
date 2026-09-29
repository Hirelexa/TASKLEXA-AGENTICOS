import asyncio
import unittest

from tasklexa_api.domain.errors import LockAcquisitionError
from tasklexa_api.integrations.redis.lock import RedisLock


class FakeRedisClient:
    """Minimal in-memory double for the two Redis operations RedisLock uses."""

    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    async def set(self, name: str, value: str, nx: bool = False, px: int | None = None):
        if nx and name in self._store:
            return None
        self._store[name] = value
        return True

    async def eval(self, script: str, numkeys: int, *keys_and_args: str):
        key, token = keys_and_args
        if self._store.get(key) == token:
            del self._store[key]
            return 1
        return 0


class RedisLockTests(unittest.TestCase):
    def test_acquire_succeeds_when_key_is_free(self) -> None:
        client = FakeRedisClient()
        lock = RedisLock(client, "mission-dispatch:abc")
        self.assertTrue(asyncio.run(lock.acquire()))

    def test_acquire_fails_when_already_held(self) -> None:
        client = FakeRedisClient()
        lock_one = RedisLock(client, "mission-dispatch:abc")
        lock_two = RedisLock(client, "mission-dispatch:abc")

        async def _run() -> tuple[bool, bool]:
            first = await lock_one.acquire()
            second = await lock_two.acquire()
            return first, second

        first, second = asyncio.run(_run())
        self.assertTrue(first)
        self.assertFalse(second)

    def test_release_only_removes_key_if_still_owner(self) -> None:
        client = FakeRedisClient()
        lock_one = RedisLock(client, "mission-dispatch:abc")
        lock_two = RedisLock(client, "mission-dispatch:abc")

        async def _run() -> bool:
            await lock_one.acquire()
            await lock_two.release()
            return await lock_two.acquire()

        can_acquire_after_wrong_release = asyncio.run(_run())
        self.assertFalse(can_acquire_after_wrong_release)

    def test_context_manager_raises_when_lock_unavailable(self) -> None:
        client = FakeRedisClient()

        async def _run() -> None:
            async with RedisLock(client, "mission-dispatch:abc"):
                with self.assertRaises(LockAcquisitionError):
                    async with RedisLock(client, "mission-dispatch:abc"):
                        pass

        asyncio.run(_run())

    def test_context_manager_releases_lock_on_exit(self) -> None:
        client = FakeRedisClient()

        async def _run() -> bool:
            async with RedisLock(client, "mission-dispatch:abc"):
                pass
            return await RedisLock(client, "mission-dispatch:abc").acquire()

        self.assertTrue(asyncio.run(_run()))

    def test_context_manager_releases_lock_even_on_exception(self) -> None:
        client = FakeRedisClient()

        async def _run() -> bool:
            try:
                async with RedisLock(client, "mission-dispatch:abc"):
                    raise RuntimeError("boom")
            except RuntimeError:
                pass
            return await RedisLock(client, "mission-dispatch:abc").acquire()

        self.assertTrue(asyncio.run(_run()))


if __name__ == "__main__":
    unittest.main()
