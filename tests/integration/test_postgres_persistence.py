import asyncio
import os
import sys
import unittest
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "api" / "src"))

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://tasklexa:tasklexa_dev_password@127.0.0.1:15432/tasklexa"
)


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


@unittest.skipUnless(_database_reachable(), "PostgreSQL is not reachable; run under docker compose to verify.")
class PostgresPersistenceTests(unittest.TestCase):
    def test_mission_and_execution_event_roundtrip(self) -> None:
        from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

        from tasklexa_api.models.execution_event import ExecutionEvent
        from tasklexa_api.models.mission import Mission
        from tasklexa_api.repositories.execution_events import record_event
        from tasklexa_api.schemas.execution_event import ExecutionEventCreate
        from tasklexa_api.domain.enums import ExecutionEventStatus, ExecutionEventType, MissionStatus

        async def _run() -> None:
            async_url = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
            engine = create_async_engine(async_url)
            sessionmaker = async_sessionmaker(bind=engine, expire_on_commit=False)

            mission_id = uuid.uuid4()

            async with sessionmaker() as session:
                mission = Mission(
                    id=mission_id,
                    title="Persistence roundtrip test",
                    objective="Verify Phase 2 persistence layer",
                    status=MissionStatus.DRAFT,
                    created_by="integration-test",
                )
                session.add(mission)
                await session.commit()

            try:
                async with sessionmaker() as session:
                    event = await record_event(
                        session,
                        ExecutionEventCreate(
                            mission_id=mission_id,
                            correlation_id=uuid.uuid4(),
                            event_type=ExecutionEventType.MISSION_CREATED,
                            status=ExecutionEventStatus.SUCCESS,
                        ),
                    )
                    self.assertIsNotNone(event.id)
                    self.assertEqual(event.event_type, ExecutionEventType.MISSION_CREATED)

                async with sessionmaker() as session:
                    from sqlalchemy import text

                    with self.assertRaises(Exception):
                        await session.execute(
                            text("UPDATE execution_events SET status = 'FAILURE' WHERE mission_id = :mid"),
                            {"mid": str(mission_id)},
                        )
                        await session.commit()
            finally:
                async with sessionmaker() as session:
                    from sqlalchemy import text

                    await session.execute(text("ALTER TABLE execution_events DISABLE TRIGGER execution_events_immutable"))
                    await session.execute(
                        text("DELETE FROM missions WHERE id = :mid"), {"mid": str(mission_id)}
                    )
                    await session.execute(text("ALTER TABLE execution_events ENABLE TRIGGER execution_events_immutable"))
                    await session.commit()

            await engine.dispose()

        asyncio.run(_run())


if __name__ == "__main__":
    unittest.main()
