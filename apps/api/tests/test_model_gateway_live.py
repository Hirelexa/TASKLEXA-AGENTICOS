import asyncio
import os
import unittest

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")


@unittest.skipUnless(
    OPENROUTER_API_KEY,
    "OPENROUTER_API_KEY is not set; this environment has no live OpenRouter credential "
    "(see docs/integration-status.md - OpenRouter remains NOT_CONFIGURED). "
    "This mocked-vs-live separation is required by docs/architecture.md Phase 4 scope.",
)
class ModelGatewayLiveTests(unittest.TestCase):
    def test_health_is_live_with_real_credential(self) -> None:
        from tasklexa_api.integrations.openrouter.gateway import ModelGateway

        async def _run() -> None:
            gateway = ModelGateway(api_key=OPENROUTER_API_KEY)
            try:
                health = await gateway.health()
                self.assertEqual(health.status, "LIVE")
            finally:
                await gateway.aclose()

        asyncio.run(_run())

    def test_list_models_returns_a_non_empty_catalog(self) -> None:
        from tasklexa_api.integrations.openrouter.gateway import ModelGateway

        async def _run() -> None:
            gateway = ModelGateway(api_key=OPENROUTER_API_KEY)
            try:
                catalog = await gateway.list_models()
                self.assertGreater(len(catalog.models), 0)
            finally:
                await gateway.aclose()

        asyncio.run(_run())


if __name__ == "__main__":
    unittest.main()
