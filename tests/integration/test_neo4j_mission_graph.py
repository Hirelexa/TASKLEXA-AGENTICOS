import asyncio
import os
import sys
import uuid
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "api" / "src"))

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://tasklexa:tasklexa_dev_password@127.0.0.1:15432/tasklexa"
)
os.environ.setdefault("DATABASE_URL", DATABASE_URL)
os.environ.setdefault("NEO4J_URI", "bolt://127.0.0.1:17687")
os.environ.setdefault("NEO4J_USER", "neo4j")
os.environ.setdefault("NEO4J_PASSWORD", "tasklexa_dev_password")

RESEARCH_AGENT_ID = uuid.UUID("bc1c9110-c18e-5230-97e1-c3d5b2c17611")


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


def _neo4j_reachable() -> bool:
    try:
        from neo4j import AsyncGraphDatabase
    except ImportError:
        return False

    async def _probe() -> bool:
        driver = AsyncGraphDatabase.driver(
            os.environ["NEO4J_URI"], auth=(os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"])
        )
        try:
            await asyncio.wait_for(driver.verify_connectivity(), timeout=3.0)
        except Exception:
            return False
        finally:
            await driver.close()
        return True

    return asyncio.run(_probe())


def _httpx_available() -> bool:
    try:
        import httpx  # noqa: F401
    except ImportError:
        return False
    return True


@unittest.skipUnless(_database_reachable(), "PostgreSQL is not reachable; run under docker compose to verify.")
@unittest.skipUnless(_neo4j_reachable(), "Neo4j is not reachable; run under docker compose to verify.")
@unittest.skipUnless(_httpx_available(), "httpx is not installed; install apps/api.")
class Neo4jMissionGraphTests(unittest.TestCase):
    def test_projection_repair_and_capability_lookup(self) -> None:
        import httpx
        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import create_async_engine

        from tasklexa_api.main import app

        async def _run() -> None:
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                created = await client.post(
                    "/missions",
                    json={
                        "title": "Graph projection test",
                        "objective": "Verify Phase 6 Neo4j mission graph projection and repair",
                        "created_by": "integration-test",
                    },
                )
                self.assertEqual(created.status_code, 201, created.text)
                mission_id = created.json()["id"]

                async_url = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
                engine = create_async_engine(async_url)

                task_id = uuid.uuid4()
                evidence_id = uuid.uuid4()
                decision_id = uuid.uuid4()
                approval_id = uuid.uuid4()

                async with engine.begin() as connection:
                    await connection.execute(
                        text(
                            """
                            INSERT INTO tasks (id, mission_id, title, status, priority, required_capabilities, assigned_agent, created_at)
                            VALUES (:id, :mission_id, 'Research the target', 'PENDING', 'MEDIUM', ARRAY['research'], :agent_id, now())
                            """
                        ),
                        {"id": str(task_id), "mission_id": mission_id, "agent_id": str(RESEARCH_AGENT_ID)},
                    )
                    await connection.execute(
                        text(
                            """
                            INSERT INTO evidence (id, mission_id, task_id, source, source_type, content, confidence, demo, created_at)
                            VALUES (:id, :mission_id, :task_id, 'web search', 'external', 'some finding', 0.8, false, now())
                            """
                        ),
                        {"id": str(evidence_id), "mission_id": mission_id, "task_id": str(task_id)},
                    )
                    await connection.execute(
                        text(
                            """
                            INSERT INTO decisions (id, mission_id, title, options, evidence_ids, risk_level, approval_required, status)
                            VALUES (:id, :mission_id, 'Proceed with research findings', '[]', :evidence_ids, 'LOW', true, 'OPEN')
                            """
                        ),
                        {"id": str(decision_id), "mission_id": mission_id, "evidence_ids": [str(evidence_id)]},
                    )
                    await connection.execute(
                        text(
                            """
                            INSERT INTO approvals (id, mission_id, decision_id, requested_by, status)
                            VALUES (:id, :mission_id, :decision_id, 'integration-test', 'PENDING')
                            """
                        ),
                        {"id": str(approval_id), "mission_id": mission_id, "decision_id": str(decision_id)},
                    )

                first_report = await client.post(f"/missions/{mission_id}/graph/project")
                self.assertEqual(first_report.status_code, 200, first_report.text)
                first = first_report.json()
                self.assertEqual(first["failed"], 0)
                self.assertGreater(first["applied"], 0)

                graph_response = await client.get(f"/missions/{mission_id}/graph")
                self.assertEqual(graph_response.status_code, 200)
                graph = graph_response.json()
                labels_seen = {label for node in graph["nodes"] for label in node["labels"]}
                self.assertIn("Mission", labels_seen)
                self.assertIn("Task", labels_seen)
                self.assertIn("Agent", labels_seen)
                self.assertIn("Evidence", labels_seen)
                self.assertIn("Decision", labels_seen)
                self.assertIn("Approval", labels_seen)
                rel_types = {rel["type"] for rel in graph["relationships"]}
                self.assertIn("CONTAINS", rel_types)
                self.assertIn("ASSIGNED_TO", rel_types)
                self.assertIn("REQUIRES", rel_types)
                self.assertIn("SUPPORTS", rel_types)
                self.assertIn("REQUIRES_APPROVAL", rel_types)

                node_count_after_first = len(graph["nodes"])
                rel_count_after_first = len(graph["relationships"])

                second_report = await client.post(f"/missions/{mission_id}/graph/project")
                self.assertEqual(second_report.status_code, 200)
                self.assertEqual(second_report.json()["failed"], 0)

                graph_after_repair = (await client.get(f"/missions/{mission_id}/graph")).json()
                self.assertEqual(len(graph_after_repair["nodes"]), node_count_after_first)
                self.assertEqual(len(graph_after_repair["relationships"]), rel_count_after_first)

                capability_response = await client.get("/agents/by-capability/research")
                self.assertEqual(capability_response.status_code, 200)
                agent_ids = {row["id"] for row in capability_response.json()}
                self.assertIn(str(RESEARCH_AGENT_ID), agent_ids)

                missing_project = await client.post(
                    "/missions/00000000-0000-0000-0000-000000000000/graph/project"
                )
                self.assertEqual(missing_project.status_code, 404)

                async with engine.begin() as connection:
                    await connection.execute(
                        text("ALTER TABLE execution_events DISABLE TRIGGER execution_events_immutable")
                    )
                    await connection.execute(text("DELETE FROM missions WHERE id = :mid"), {"mid": mission_id})
                    await connection.execute(
                        text("ALTER TABLE execution_events ENABLE TRIGGER execution_events_immutable")
                    )
                await engine.dispose()

            from neo4j import AsyncGraphDatabase

            driver = AsyncGraphDatabase.driver(
                os.environ["NEO4J_URI"], auth=(os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"])
            )
            try:
                async with driver.session() as neo4j_session:
                    await neo4j_session.run(
                        "MATCH (m:Mission {id: $mission_id}) DETACH DELETE m", mission_id=mission_id
                    )
                    for node_id in (str(task_id), str(evidence_id), str(decision_id), str(approval_id)):
                        await neo4j_session.run("MATCH (n {id: $id}) DETACH DELETE n", id=node_id)
            finally:
                await driver.close()

        asyncio.run(_run())


if __name__ == "__main__":
    unittest.main()
