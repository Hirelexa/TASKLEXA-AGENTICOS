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
os.environ.setdefault("NEO4J_URI", "bolt://127.0.0.1:17687")
os.environ.setdefault("NEO4J_USER", "neo4j")
os.environ.setdefault("NEO4J_PASSWORD", "tasklexa_dev_password")


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


async def _advance_to_running(client, mission_id: str) -> None:
    for target_status in ("PLANNING", "ASSEMBLING", "RUNNING"):
        resp = await client.post(f"/missions/{mission_id}/transitions", json={"status": target_status})
        assert resp.status_code == 200, resp.text


@unittest.skipUnless(_database_reachable(), "PostgreSQL is not reachable; run under docker compose to verify.")
@unittest.skipUnless(_httpx_available(), "httpx is not installed; install apps/api.")
class VerifierTests(unittest.TestCase):
    def _cleanup(self, mission_ids: list[str]) -> None:
        async def _run() -> None:
            from sqlalchemy import text
            from sqlalchemy.ext.asyncio import create_async_engine

            async_url = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
            engine = create_async_engine(async_url)
            async with engine.begin() as connection:
                await connection.execute(
                    text("ALTER TABLE execution_events DISABLE TRIGGER execution_events_immutable")
                )
                for mission_id in mission_ids:
                    await connection.execute(text("DELETE FROM missions WHERE id = :mid"), {"mid": mission_id})
                await connection.execute(
                    text("ALTER TABLE execution_events ENABLE TRIGGER execution_events_immutable")
                )
            await engine.dispose()

        asyncio.run(_run())

    def test_passing_verification_completes_the_mission(self) -> None:
        import httpx

        from tasklexa_api.main import app

        mission_ids: list[str] = []

        async def _run() -> None:
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                created = await client.post(
                    "/missions",
                    json={
                        "title": "Verifier passing test",
                        "objective": "Verify Phase 11 PASSED outcome completes the mission",
                        "created_by": "integration-test",
                    },
                )
                mission_id = created.json()["id"]
                mission_ids.append(mission_id)
                await _advance_to_running(client, mission_id)

                task = (
                    await client.post(
                        f"/missions/{mission_id}/tasks",
                        json={
                            "mission_id": mission_id,
                            "title": "The only task",
                            "required_capabilities": ["planning"],
                        },
                    )
                ).json()

                first_dispatch = await client.post(f"/missions/{mission_id}/orchestrator/dispatch")
                self.assertEqual(first_dispatch.json()["dispatched"][0]["status"], "DISPATCHED")
                complete = await client.post(
                    f"/missions/{mission_id}/tasks/{task['id']}/complete",
                    json={"actual_output": "done", "confidence": 0.95},
                )
                self.assertEqual(complete.status_code, 200, complete.text)
                second_dispatch = await client.post(f"/missions/{mission_id}/orchestrator/dispatch")
                self.assertEqual(second_dispatch.json()["mission_transitioned_to"], "VERIFYING")

                verify = await client.post(f"/missions/{mission_id}/verify")
                self.assertEqual(verify.status_code, 200, verify.text)
                report = verify.json()
                self.assertEqual(report["verification_status"], "PASSED")
                self.assertEqual(report["issues"], [])

                mission_after = (await client.get(f"/missions/{mission_id}")).json()
                self.assertEqual(mission_after["status"], "COMPLETED")

                reports = (await client.get(f"/missions/{mission_id}/verification-reports")).json()
                self.assertEqual(len(reports), 1)

                fetched_report = (
                    await client.get(f"/missions/{mission_id}/verification-reports/{report['id']}")
                ).json()
                self.assertEqual(fetched_report["id"], report["id"])

                cannot_verify_again_usefully = await client.post(f"/missions/{mission_id}/verify")
                self.assertEqual(cannot_verify_again_usefully.status_code, 200)
                mission_still = (await client.get(f"/missions/{mission_id}")).json()
                self.assertEqual(mission_still["status"], "COMPLETED")

                events = (await client.get(f"/missions/{mission_id}/events")).json()
                self.assertIn("VERIFICATION_STARTED", [e["event_type"] for e in events])

        asyncio.run(_run())
        self._cleanup(mission_ids)

    def test_failed_task_causes_failing_verification(self) -> None:
        import httpx

        from tasklexa_api.main import app

        mission_ids: list[str] = []

        async def _run() -> None:
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                created = await client.post(
                    "/missions",
                    json={
                        "title": "Verifier failing test",
                        "objective": "Verify Phase 11 FAILED outcome fails the mission",
                        "created_by": "integration-test",
                    },
                )
                mission_id = created.json()["id"]
                mission_ids.append(mission_id)
                await _advance_to_running(client, mission_id)

                task_a = (
                    await client.post(
                        f"/missions/{mission_id}/tasks",
                        json={
                            "mission_id": mission_id,
                            "title": "Will complete",
                            "required_capabilities": ["planning"],
                        },
                    )
                ).json()
                task_b = (
                    await client.post(
                        f"/missions/{mission_id}/tasks",
                        json={
                            "mission_id": mission_id,
                            "title": "Will fail",
                            "required_capabilities": ["verification"],
                        },
                    )
                ).json()

                first_dispatch = await client.post(f"/missions/{mission_id}/orchestrator/dispatch")
                self.assertEqual(len(first_dispatch.json()["dispatched"]), 2)
                complete_a = await client.post(
                    f"/missions/{mission_id}/tasks/{task_a['id']}/complete", json={"actual_output": "ok"}
                )
                self.assertEqual(complete_a.status_code, 200, complete_a.text)
                fail_b = await client.post(
                    f"/missions/{mission_id}/tasks/{task_b['id']}/fail", json={"reason": "could not complete"}
                )
                self.assertEqual(fail_b.status_code, 200, fail_b.text)

                dispatch = await client.post(f"/missions/{mission_id}/orchestrator/dispatch")
                self.assertEqual(dispatch.json()["mission_transitioned_to"], "VERIFYING")

                verify = await client.post(f"/missions/{mission_id}/verify")
                report = verify.json()
                self.assertEqual(report["verification_status"], "FAILED")
                self.assertTrue(any("failed" in issue.lower() for issue in report["issues"]))

                mission_after = (await client.get(f"/missions/{mission_id}")).json()
                self.assertEqual(mission_after["status"], "FAILED")

        asyncio.run(_run())
        self._cleanup(mission_ids)

    def test_success_criteria_without_evidence_yields_partial_and_no_transition(self) -> None:
        import httpx

        from tasklexa_api.main import app

        mission_ids: list[str] = []

        async def _run() -> None:
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                created = await client.post(
                    "/missions",
                    json={
                        "title": "Verifier partial test",
                        "objective": "Verify Phase 11 PARTIAL outcome leaves the mission in VERIFYING",
                        "created_by": "integration-test",
                        "success_criteria": ["must reduce churn by 10%"],
                    },
                )
                mission_id = created.json()["id"]
                mission_ids.append(mission_id)
                await _advance_to_running(client, mission_id)

                task = (
                    await client.post(
                        f"/missions/{mission_id}/tasks",
                        json={
                            "mission_id": mission_id,
                            "title": "Only task",
                            "required_capabilities": ["planning"],
                        },
                    )
                ).json()
                first_dispatch = await client.post(f"/missions/{mission_id}/orchestrator/dispatch")
                self.assertEqual(first_dispatch.json()["dispatched"][0]["status"], "DISPATCHED")
                complete = await client.post(f"/missions/{mission_id}/tasks/{task['id']}/complete", json={})
                self.assertEqual(complete.status_code, 200, complete.text)
                second_dispatch = await client.post(f"/missions/{mission_id}/orchestrator/dispatch")
                self.assertEqual(second_dispatch.json()["mission_transitioned_to"], "VERIFYING")

                verify = await client.post(f"/missions/{mission_id}/verify")
                report = verify.json()
                self.assertEqual(report["verification_status"], "PARTIAL")

                mission_after = (await client.get(f"/missions/{mission_id}")).json()
                self.assertEqual(mission_after["status"], "VERIFYING")

                verify_again = await client.post(f"/missions/{mission_id}/verify")
                self.assertEqual(verify_again.json()["verification_status"], "PARTIAL")

                reports = (await client.get(f"/missions/{mission_id}/verification-reports")).json()
                self.assertEqual(len(reports), 2)

        asyncio.run(_run())
        self._cleanup(mission_ids)


if __name__ == "__main__":
    unittest.main()
