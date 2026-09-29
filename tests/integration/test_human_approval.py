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


@unittest.skipUnless(_database_reachable(), "PostgreSQL is not reachable; run under docker compose to verify.")
@unittest.skipUnless(_httpx_available(), "httpx is not installed; install apps/api.")
class HumanApprovalTests(unittest.TestCase):
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

    def test_approval_blocks_dispatch_and_approve_resumes_it(self) -> None:
        import httpx

        from tasklexa_api.main import app

        mission_id_holder: list[str] = []

        async def _run() -> None:
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                created = await client.post(
                    "/missions",
                    json={
                        "title": "Approval blocking test",
                        "objective": "Verify Phase 10 approval blocking and resume",
                        "created_by": "integration-test",
                    },
                )
                mission_id = created.json()["id"]
                mission_id_holder.append(mission_id)

                for target_status in ("PLANNING", "ASSEMBLING", "RUNNING"):
                    resp = await client.post(
                        f"/missions/{mission_id}/transitions", json={"status": target_status}
                    )
                    self.assertEqual(resp.status_code, 200, resp.text)

                task = (
                    await client.post(
                        f"/missions/{mission_id}/tasks",
                        json={"mission_id": mission_id, "title": "A task that could dispatch"},
                    )
                ).json()

                before_dispatch = await client.post(f"/missions/{mission_id}/orchestrator/dispatch")
                self.assertEqual(before_dispatch.status_code, 200)
                self.assertEqual(before_dispatch.json()["readiness"]["ready_task_ids"], [task["id"]])

                decision = await client.post(
                    f"/missions/{mission_id}/decisions",
                    json={
                        "mission_id": mission_id,
                        "title": "Proceed with a risky action",
                        "approval_required": True,
                        "requested_by": "planning-agent",
                        "approval_reason": "high risk action needs a human sign-off",
                    },
                )
                self.assertEqual(decision.status_code, 201, decision.text)
                self.assertEqual(decision.json()["status"], "OPEN")

                mission_after_decision = (await client.get(f"/missions/{mission_id}")).json()
                self.assertEqual(mission_after_decision["status"], "WAITING_APPROVAL")

                approvals = (await client.get(f"/missions/{mission_id}/approvals")).json()
                self.assertEqual(len(approvals), 1)
                approval = approvals[0]
                self.assertEqual(approval["status"], "PENDING")
                self.assertEqual(approval["decision_id"], decision.json()["id"])

                blocked_dispatch = await client.post(f"/missions/{mission_id}/orchestrator/dispatch")
                self.assertEqual(blocked_dispatch.status_code, 409, blocked_dispatch.text)

                second_decision_while_paused = await client.post(
                    f"/missions/{mission_id}/decisions",
                    json={
                        "mission_id": mission_id,
                        "title": "Another decision while paused",
                        "approval_required": True,
                        "requested_by": "planning-agent",
                    },
                )
                self.assertEqual(second_decision_while_paused.status_code, 409)

                approve = await client.post(
                    f"/missions/{mission_id}/approvals/{approval['id']}/approve",
                    json={"approved_by": "human-operator", "comments": "looks fine"},
                )
                self.assertEqual(approve.status_code, 200, approve.text)
                self.assertEqual(approve.json()["status"], "APPROVED")

                mission_after_approval = (await client.get(f"/missions/{mission_id}")).json()
                self.assertEqual(mission_after_approval["status"], "RUNNING")

                resumed_dispatch = await client.post(f"/missions/{mission_id}/orchestrator/dispatch")
                self.assertEqual(resumed_dispatch.status_code, 200, resumed_dispatch.text)
                self.assertEqual(len(resumed_dispatch.json()["dispatched"]), 1)

                already_resolved = await client.post(
                    f"/missions/{mission_id}/approvals/{approval['id']}/approve",
                    json={"approved_by": "human-operator"},
                )
                self.assertEqual(already_resolved.status_code, 409)

                events = (await client.get(f"/missions/{mission_id}/events")).json()
                event_types = [event["event_type"] for event in events]
                for expected in ("DECISION_CREATED", "APPROVAL_REQUESTED", "APPROVAL_GRANTED"):
                    self.assertIn(expected, event_types)

        asyncio.run(_run())
        self._cleanup(mission_id_holder)

    def test_rejecting_an_approval_cancels_the_mission_terminally(self) -> None:
        import httpx

        from tasklexa_api.main import app

        mission_id_holder: list[str] = []

        async def _run() -> None:
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                created = await client.post(
                    "/missions",
                    json={
                        "title": "Approval rejection test",
                        "objective": "Verify Phase 10 rejection is terminal",
                        "created_by": "integration-test",
                    },
                )
                mission_id = created.json()["id"]
                mission_id_holder.append(mission_id)

                for target_status in ("PLANNING", "ASSEMBLING", "RUNNING"):
                    await client.post(f"/missions/{mission_id}/transitions", json={"status": target_status})

                decision = await client.post(
                    f"/missions/{mission_id}/decisions",
                    json={
                        "mission_id": mission_id,
                        "title": "Do the risky thing",
                        "approval_required": True,
                        "requested_by": "planning-agent",
                    },
                )
                approval_id = (await client.get(f"/missions/{mission_id}/approvals")).json()[0]["id"]

                reject = await client.post(
                    f"/missions/{mission_id}/approvals/{approval_id}/reject",
                    json={"approved_by": "human-operator", "comments": "too risky"},
                )
                self.assertEqual(reject.status_code, 200, reject.text)
                self.assertEqual(reject.json()["status"], "REJECTED")

                mission_after_reject = (await client.get(f"/missions/{mission_id}")).json()
                self.assertEqual(mission_after_reject["status"], "CANCELLED")

                # CANCELLED is terminal in the state machine (no outgoing edges - see
                # ADR-021), so there is no "resume" transition back to RUNNING or
                # WAITING_APPROVAL available at all, unlike the dispatch-time guard
                # that specifically blocks WAITING_APPROVAL. Dispatch itself doesn't
                # check mission status (a known Phase 8 limitation), so it still
                # succeeds here - there's just nothing to dispatch.
                dispatch_after_cancel = await client.post(f"/missions/{mission_id}/orchestrator/dispatch")
                self.assertEqual(dispatch_after_cancel.status_code, 200, dispatch_after_cancel.text)
                self.assertEqual(dispatch_after_cancel.json()["dispatched"], [])

                cannot_reapprove = await client.post(
                    f"/missions/{mission_id}/transitions", json={"status": "RUNNING"}
                )
                self.assertEqual(cannot_reapprove.status_code, 409)

        asyncio.run(_run())
        self._cleanup(mission_id_holder)


if __name__ == "__main__":
    unittest.main()
