import asyncio
import unittest

from tasklexa_api.domain.errors import ProviderNotConfiguredError, ProviderUnverifiedError
from tasklexa_api.domain.enums import ToolStatus
from tasklexa_api.integrations.similarweb.tool import SimilarwebTool
from tasklexa_api.schemas.similarweb import (
    AnalyzeWebsiteRequest,
    CompareCompetitorsRequest,
    SearchMarketSignalsRequest,
)


class SimilarwebHealthTests(unittest.TestCase):
    def test_health_is_not_configured_without_key_and_demo_off(self) -> None:
        tool = SimilarwebTool(api_key=None, demo_mode=False)
        health = asyncio.run(tool.health())
        self.assertEqual(health.status, "NOT_CONFIGURED")

    def test_health_is_unverified_with_key_present(self) -> None:
        tool = SimilarwebTool(api_key="some-key", demo_mode=False)
        health = asyncio.run(tool.health())
        self.assertEqual(health.status, "UNVERIFIED")

    def test_health_is_mock_when_demo_mode_enabled_regardless_of_key(self) -> None:
        tool_no_key = SimilarwebTool(api_key=None, demo_mode=True)
        tool_with_key = SimilarwebTool(api_key="some-key", demo_mode=True)
        self.assertEqual(asyncio.run(tool_no_key.health()).status, "MOCK")
        self.assertEqual(asyncio.run(tool_with_key.health()).status, "MOCK")


class SimilarwebMetadataTests(unittest.TestCase):
    def test_metadata_reports_not_configured_status_when_no_key_and_demo_off(self) -> None:
        tool = SimilarwebTool(api_key=None, demo_mode=False)
        metadata = tool.metadata()
        self.assertEqual(metadata.status, ToolStatus.NOT_CONFIGURED)
        self.assertEqual(metadata.name, "similarweb")
        self.assertIn("digital_market_intelligence", metadata.capabilities)

    def test_metadata_reports_available_status_in_demo_mode(self) -> None:
        tool = SimilarwebTool(api_key=None, demo_mode=True)
        self.assertEqual(tool.metadata().status, ToolStatus.AVAILABLE)

    def test_metadata_id_is_stable_across_instances(self) -> None:
        first = SimilarwebTool(api_key=None, demo_mode=False).metadata().id
        second = SimilarwebTool(api_key="key", demo_mode=True).metadata().id
        self.assertEqual(first, second)


class SimilarwebCanExecuteTests(unittest.TestCase):
    def test_unsupported_capability_is_never_available(self) -> None:
        tool = SimilarwebTool(api_key="key", demo_mode=True)
        result = tool.can_execute("unrelated_capability")
        self.assertFalse(result.available)

    def test_supported_capability_unavailable_without_key_and_demo_off(self) -> None:
        tool = SimilarwebTool(api_key=None, demo_mode=False)
        result = tool.can_execute("website_analysis")
        self.assertFalse(result.available)
        self.assertIn("NOT_CONFIGURED", result.reason)

    def test_supported_capability_unavailable_with_key_but_unverified(self) -> None:
        tool = SimilarwebTool(api_key="key", demo_mode=False)
        result = tool.can_execute("website_analysis")
        self.assertFalse(result.available)
        self.assertIn("unverified", result.reason.lower())

    def test_supported_capability_available_in_demo_mode(self) -> None:
        tool = SimilarwebTool(api_key=None, demo_mode=True)
        result = tool.can_execute("competitive_intelligence")
        self.assertTrue(result.available)


class SimilarwebCallTests(unittest.TestCase):
    def test_analyze_website_raises_not_configured_without_key(self) -> None:
        tool = SimilarwebTool(api_key=None, demo_mode=False)
        with self.assertRaises(ProviderNotConfiguredError):
            asyncio.run(tool.analyze_website(AnalyzeWebsiteRequest(domain="example.com")))

    def test_analyze_website_raises_unverified_with_key_present(self) -> None:
        tool = SimilarwebTool(api_key="key", demo_mode=False)
        with self.assertRaises(ProviderUnverifiedError):
            asyncio.run(tool.analyze_website(AnalyzeWebsiteRequest(domain="example.com")))

    def test_analyze_website_returns_labeled_demo_data(self) -> None:
        tool = SimilarwebTool(api_key=None, demo_mode=True)
        result = asyncio.run(tool.analyze_website(AnalyzeWebsiteRequest(domain="example.com")))
        self.assertTrue(result.demo)
        self.assertEqual(result.status, "MOCK")
        self.assertEqual(result.data["label"], "DEMO DATA")
        self.assertEqual(result.data["domain"], "example.com")

    def test_compare_competitors_returns_labeled_demo_data(self) -> None:
        tool = SimilarwebTool(api_key=None, demo_mode=True)
        result = asyncio.run(
            tool.compare_competitors(
                CompareCompetitorsRequest(domain="example.com", competitor_domains=["rival.com"])
            )
        )
        self.assertEqual(result.data["label"], "DEMO DATA")
        self.assertEqual(result.data["competitors"][0]["domain"], "rival.com")

    def test_search_market_signals_returns_labeled_demo_data(self) -> None:
        tool = SimilarwebTool(api_key=None, demo_mode=True)
        result = asyncio.run(tool.search_market_signals(SearchMarketSignalsRequest(query="ecommerce trends")))
        self.assertEqual(result.data["label"], "DEMO DATA")
        self.assertEqual(result.data["query"], "ecommerce trends")

    def test_demo_mode_takes_priority_even_with_a_key_present(self) -> None:
        tool = SimilarwebTool(api_key="some-key", demo_mode=True)
        result = asyncio.run(tool.analyze_website(AnalyzeWebsiteRequest(domain="example.com")))
        self.assertTrue(result.demo)


if __name__ == "__main__":
    unittest.main()
