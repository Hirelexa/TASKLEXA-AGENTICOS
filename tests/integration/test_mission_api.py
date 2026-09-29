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


def _httpx_available() -> bool:
    try:
        import httpx  # noqa: F401
    except ImportError:
        return False
    return True


@unittest.skipUnless(_database_reachable(), "PostgreSQL is not reachable; run under docker compose to verify.")
@unittest.skipUnless(_httpx_available(), "httpx is not installed; install apps/api.")
class MissionApiTests(unittest.TestCase):
    def test_mission_lifecycle_through_http(self) -> None:
        import httpx

        from tasklexa_api.main import app

        async def _run() -> None:
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                created = await client.post(
                    "/missions",
                    json={
                        "title": "API lifecycle test",
                        "objective": "Verify Phase 3 mission API and state machine",
                        "created_by": "integration-test",
                    },
                )
                self.assertEqual(created.status_code, 201, created.text)
                mission = created.json()
                mission_id = mission["id"]
                self.assertEqual(mission["status"], "DRAFT")

                fetched = await client.get(f"/missions/{mission_id}")
                self.assertEqual(fetched.status_code, 200)
                self.assertEqual(fetched.json()["id"], mission_id)

                listed = await client.get("/missions")
                self.assertEqual(listed.status_code, 200)
                self.assertIn(mission_id, [row["id"] for row in listed.json()])

                invalid = await client.post(f"/missions/{mission_id}/transitions", json={"status": "COMPLETED"})
                self.assertEqual(invalid.status_code, 409, invalid.text)

                to_planning = await client.post(
                    f"/missions/{mission_id}/transitions", json={"status": "PLANNING"}
                )
                self.assertEqual(to_planning.status_code, 200, to_planning.text)
                self.assertEqual(to_planning.json()["status"], "PLANNING")

                events = await client.get(f"/missions/{mission_id}/events")
                self.assertEqual(events.status_code, 200)
                event_types = [event["event_type"] for event in events.json()]
                self.assertIn("MISSION_CREATED", event_types)
                self.assertIn("MISSION_STATUS_CHANGED", event_types)

                missing = await client.get("/missions/00000000-0000-0000-0000-000000000000")
                self.assertEqual(missing.status_code, 404)

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


if __name__ == "__main__":
    unittest.main()
