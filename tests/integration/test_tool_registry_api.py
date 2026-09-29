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
os.environ.setdefault("NEO4J_URI", "bolt://127.0.0.1:17687")
os.environ.setdefault("NEO4J_USER", "neo4j")
os.environ.setdefault("NEO4J_PASSWORD", "tasklexa_dev_password")

SIMILARWEB_TOOL_ID = "e97908ea-63f3-5886-b190-79dc3bd2b0c6"


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
class ToolRegistryApiTests(unittest.TestCase):
    def test_seeded_similarweb_tool_is_listed_and_not_configured(self) -> None:
        import httpx

        from tasklexa_api.main import app

        async def _run() -> None:
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                listed = await client.get("/tools")
                self.assertEqual(listed.status_code, 200)
                by_name = {row["name"]: row for row in listed.json()}
                self.assertIn("similarweb", by_name)

                similarweb = by_name["similarweb"]
                self.assertEqual(similarweb["id"], SIMILARWEB_TOOL_ID)
                self.assertEqual(similarweb["status"], "NOT_CONFIGURED")
                self.assertEqual(
                    set(similarweb["capabilities"]),
                    {"digital_market_intelligence", "website_analysis", "competitive_intelligence"},
                )

                fetched = await client.get(f"/tools/{SIMILARWEB_TOOL_ID}")
                self.assertEqual(fetched.status_code, 200)
                self.assertEqual(fetched.json()["name"], "similarweb")

                missing = await client.get("/tools/00000000-0000-0000-0000-000000000000")
                self.assertEqual(missing.status_code, 404)

                health = await client.get("/health/integrations")
                self.assertEqual(health.status_code, 200)
                integrations_by_provider = {row["provider"]: row for row in health.json()["integrations"]}
                self.assertEqual(integrations_by_provider["Similarweb"]["status"], "NOT_CONFIGURED")

        asyncio.run(_run())


if __name__ == "__main__":
    unittest.main()
