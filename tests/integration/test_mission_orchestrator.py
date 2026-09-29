import asyncio
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "api" / "src"))

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://tasklexa:tasklexa_dev_password@127.0.0.1:15432/tasklexa"
)
os.environ.setdefault("DATABASE_URL", DATABASE_URL)
os.environ.setdefault("REDIS_URL", "redis://127.0.0.1:16379/0")


def _database_reachable() -> bool:
    try:
        import asyncpg
    except ImportError:
        return False

    async def _probe() -> bool:
        url = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
        try:
            conn = await asyncio.wait_for(asyncpg.connect(url), timeout=2.0)
        except Exception:
            return False
        await conn.close()
        return True

    return asyncio.run(_probe())


def _redis_reachable() -> bool:
    try:
        import redis.asyncio as redis
    except ImportError:
        return False

    async def _probe() -> bool:
        client = redis.from_url(os.environ["REDIS_URL"])
        try:
            return bool(await asyncio.wait_for(client.ping(), timeout=2.0))
        except Exception:
            return False
        finally:
            await client.aclose()

    return asyncio.run(_probe())


def _httpx_available() -> bool:
    try:
        import httpx  # noqa: F401
    except ImportError:
        return False
    return True


@unittest.skipUnless(_database_reachable(), "PostgreSQL is not reachable; run under docker compose to verify.")
@unittest.skipUnless(_redis_reachable(), "Redis is not reachable; run under docker compose to verify.")
@unittest.skipUnless(_httpx_available(), "httpx is not installed; install apps/api.")
class MissionOrchestratorTests(unittest.TestCase):
    def test_full_dependency_graph_execution_with_failure_and_replan(self) -> None:
        import httpx

        from tasklexa_api.main import app

        async def _run() -> None:
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                created = await client.post(
                    "/missions",
                    json={
                        "title": "Orchestrator lifecycle test",
                        "objective": "Verify Phase 8 dependency graph execution, failure cascade, and replan",
                        "created_by": "integration-test",
                    },
                )
                self.assertEqual(created.status_code, 201, created.text)
                mission_id = created.json()["id"]

                for target_status in ("PLANNING", "ASSEMBLING", "RUNNING"):
                    resp = await client.post(
                        f"/missions/{mission_id}/transitions", json={"status": target_status}
                    )
                    self.assertEqual(resp.status_code, 200, resp.text)

                task_a = (
                    await client.post(
                        f"/missions/{mission_id}/tasks",
                        json={
                            "mission_id": mission_id,
                            "title": "Research the target",
                            "required_capabilities": ["research"],
                        },
                    )
                ).json()
                task_b = (
                    await client.post(
                        f"/missions/{mission_id}/tasks",
                        json={
                            "mission_id": mission_id,
                            "title": "Plan next steps",
                            "required_capabilities": ["planning"],
                            "dependencies": [task_a["id"]],
                        },
                    )
                ).json()
                task_c = (
                    await client.post(
                        f"/missions/{mission_id}/tasks",
                        json={
                            "mission_id": mission_id,
                            "title": "Do something nobody can do",
                            "required_capabilities": ["not_a_real_capability"],
                            "dependencies": [task_a["id"]],
                        },
                    )
                ).json()

                first_dispatch = (await client.post(f"/missions/{mission_id}/orchestrator/dispatch")).json()
                self.assertEqual(first_dispatch["readiness"]["ready_task_ids"], [task_a["id"]])
                self.assertEqual(
                    set(first_dispatch["readiness"]["blocked_task_ids"]), {task_b["id"], task_c["id"]}
                )
                self.assertEqual(len(first_dispatch["dispatched"]), 1)
                self.assertEqual(first_dispatch["dispatched"][0]["status"], "DISPATCHED")

                fetched_a = (await client.get(f"/missions/{mission_id}/tasks/{task_a['id']}")).json()
                self.assertEqual(fetched_a["status"], "ASSIGNED")
                self.assertIsNotNone(fetched_a["assigned_agent"])

                complete_a = await client.post(
                    f"/missions/{mission_id}/tasks/{task_a['id']}/complete",
                    json={"actual_output": "found the answer", "confidence": 0.9},
                )
                self.assertEqual(complete_a.status_code, 200, complete_a.text)
                self.assertEqual(complete_a.json()["status"], "COMPLETED")

                second_dispatch = (await client.post(f"/missions/{mission_id}/orchestrator/dispatch")).json()
                self.assertEqual(set(second_dispatch["readiness"]["ready_task_ids"]), {task_b["id"], task_c["id"]})
                results_by_task = {row["task_id"]: row for row in second_dispatch["dispatched"]}
                self.assertEqual(results_by_task[task_b["id"]]["status"], "DISPATCHED")
                self.assertEqual(results_by_task[task_c["id"]]["status"], "NO_AGENT_AVAILABLE")

                fail_c = await client.post(
                    f"/missions/{mission_id}/tasks/{task_c['id']}/fail",
                    json={"reason": "no agent covers this capability"},
                )
                self.assertEqual(fail_c.status_code, 200, fail_c.text)
                self.assertEqual(fail_c.json()["cascaded_failure_ids"], [])

                complete_b = await client.post(
                    f"/missions/{mission_id}/tasks/{task_b['id']}/complete",
                    json={"actual_output": "plan made", "confidence": 0.8},
                )
                self.assertEqual(complete_b.status_code, 200, complete_b.text)

                third_dispatch = (await client.post(f"/missions/{mission_id}/orchestrator/dispatch")).json()
                self.assertEqual(third_dispatch["readiness"]["ready_task_ids"], [])
                self.assertEqual(third_dispatch["mission_transitioned_to"], "VERIFYING")

                mission_after = (await client.get(f"/missions/{mission_id}")).json()
                self.assertEqual(mission_after["status"], "VERIFYING")

                replanned_c = await client.post(f"/missions/{mission_id}/tasks/{task_c['id']}/replan")
                self.assertEqual(replanned_c.status_code, 200, replanned_c.text)
                self.assertEqual(replanned_c.json()["status"], "PENDING")

                events = (await client.get(f"/missions/{mission_id}/events")).json()
                event_types = [event["event_type"] for event in events]
                for expected in (
                    "MISSION_CREATED",
                    "AGENT_SELECTED",
                    "AGENT_STARTED",
                    "TASK_COMPLETED",
                    "TASK_FAILED",
                    "TASK_REPLANNED",
                ):
                    self.assertIn(expected, event_types, f"missing {expected} in {event_types}")

                cannot_fail_completed = await client.post(
                    f"/missions/{mission_id}/tasks/{task_a['id']}/fail", json={"reason": "too late"}
                )
                self.assertEqual(cannot_fail_completed.status_code, 409)

            from sqlalchemy import text
            from sqlalchemy.ext.asyncio import create_async_engine

            async_url = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
            engine = create_async_engine(async_url)
            async with engine.begin() as connection:
                await connection.execute(
                    text("ALTER TABLE execution_events DISABLE TRIGGER execution_events_immutable")
                )
                await connection.execute(text("DELETE FROM missions WHERE id = :mid"), {"mid": mission_id})
                await connection.execute(
                    text("ALTER TABLE execution_events ENABLE TRIGGER execution_events_immutable")
                )
            await engine.dispose()

        asyncio.run(_run())

    def test_concurrent_dispatch_is_rejected_by_the_redis_lock(self) -> None:
        import httpx

        from tasklexa_api.integrations.redis.dependency import get_redis_client
        from tasklexa_api.integrations.redis.lock import RedisLock

        async def _run() -> None:
            client = get_redis_client()
            key = "mission-dispatch:concurrency-test"
            held_lock = RedisLock(client, key)
            self.assertTrue(await held_lock.acquire())
            try:
                contending_lock = RedisLock(client, key)
                self.assertFalse(await contending_lock.acquire())
            finally:
                await held_lock.release()

            released_ok = RedisLock(client, key)
            self.assertTrue(await released_ok.acquire())
            await released_ok.release()

        asyncio.run(_run())


if __name__ == "__main__":
    unittest.main()
