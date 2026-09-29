import asyncio
import os
import unittest
import uuid

BAND_API_KEY = os.environ.get("BAND_AGENT_KEY") or os.environ.get("BAND_API_KEY")


@unittest.skipUnless(
    BAND_API_KEY,
    "BAND_AGENT_KEY/BAND_API_KEY are not set; this environment has no live Band credential "
    "(see docs/integration-status.md - Band remains NOT_CONFIGURED). "
    "This mocked-vs-live separation is required by docs/architecture.md Phase 7 scope. "
    "Note: the exact REST path names this adapter calls are an inferred convention, not "
    "confirmed against Band's real API (see ADR-017) - the first real credential this "
    "project gets should run this gate before the adapter is trusted for anything real.",
)
class BandAdapterLiveTests(unittest.TestCase):
    def test_health_is_live_with_real_credential(self) -> None:
        from tasklexa_api.integrations.band.adapter import BandAdapter

        async def _run() -> None:
            adapter = BandAdapter(api_key=BAND_API_KEY)
            try:
                health = await adapter.health()
                self.assertEqual(health.status, "LIVE")
            finally:
                await adapter.aclose()

        asyncio.run(_run())

    def test_create_and_teardown_a_mission_context(self) -> None:
        from tasklexa_api.integrations.band.adapter import BandAdapter

        async def _run() -> None:
            adapter = BandAdapter(api_key=BAND_API_KEY)
            try:
                context = await adapter.create_mission_context(uuid.uuid4(), "Live test context")
                self.assertTrue(context.context_id)
            finally:
                await adapter.aclose()

        asyncio.run(_run())


if __name__ == "__main__":
    unittest.main()
