import uuid

from tasklexa_api.domain.enums import RiskLevel, ToolStatus
from tasklexa_api.domain.errors import ProviderNotConfiguredError, ProviderUnverifiedError
from tasklexa_api.schemas.health import IntegrationHealth
from tasklexa_api.schemas.similarweb import (
    AnalyzeWebsiteRequest,
    CompareCompetitorsRequest,
    SearchMarketSignalsRequest,
    ToolAvailability,
    ToolResult,
)
from tasklexa_api.schemas.tool import ToolDefinitionRead

PROVIDER_NAME = "Similarweb"

# Deterministic id, matching the ToolDefinition row seeded by
# apps/api/migrations/versions/<seed similarweb tool>.py - see docs/decisions.md ADR-020.
TOOL_ID = uuid.UUID("e97908ea-63f3-5886-b190-79dc3bd2b0c6")
CAPABILITIES = ["digital_market_intelligence", "website_analysis", "competitive_intelligence"]


class SimilarwebTool:
    """Discoverable digital intelligence tool.

    docs/architecture.md's Similarweb integration contract lists both the MCP
    endpoint/transport/schemas and the direct REST endpoint schemas as
    unverified open questions, and its own Rules section says: "If MCP cannot
    be verified, keep a provider adapter marked UNVERIFIED or implement direct
    REST only after endpoint schemas are confirmed." Neither is confirmed, so
    this class deliberately never makes a live network call - see ADR-020.
    Only the DEMO_MODE path returns real ToolResult data, always labeled.
    """

    def __init__(self, api_key: str | None, demo_mode: bool) -> None:
        self._api_key = api_key
        self._demo_mode = demo_mode

    async def health(self) -> IntegrationHealth:
        if self._demo_mode:
            return IntegrationHealth(
                provider=PROVIDER_NAME,
                purpose="Discoverable digital intelligence tool",
                status="MOCK",
                details="DEMO_MODE is enabled; any Similarweb response is labeled DEMO DATA.",
            )
        if not self._api_key:
            return IntegrationHealth(
                provider=PROVIDER_NAME,
                purpose="Discoverable digital intelligence tool",
                status="NOT_CONFIGURED",
                details="Credential is missing; Similarweb remains unavailable.",
            )
        return IntegrationHealth(
            provider=PROVIDER_NAME,
            purpose="Discoverable digital intelligence tool",
            status="UNVERIFIED",
            details=(
                "Credential is present, but MCP and REST endpoint schemas are not confirmed "
                "(see docs/architecture.md open questions and ADR-020); no live call is attempted."
            ),
        )

    def metadata(self) -> ToolDefinitionRead:
        status = ToolStatus.NOT_CONFIGURED
        if self._demo_mode:
            status = ToolStatus.AVAILABLE
        return ToolDefinitionRead(
            id=TOOL_ID,
            name="similarweb",
            description=(
                "External digital market intelligence tool: website analysis, competitor "
                "comparison, and market signal search."
            ),
            provider="similarweb",
            capabilities=CAPABILITIES,
            authentication_type="api_key",
            risk_level=RiskLevel.LOW,
            requires_approval=False,
            status=status,
        )

    def can_execute(self, capability: str, policy_context: dict | None = None) -> ToolAvailability:
        if capability not in CAPABILITIES:
            return ToolAvailability(
                available=False,
                reason=f"'{capability}' is not among this tool's capabilities: {CAPABILITIES}",
            )
        if self._demo_mode:
            return ToolAvailability(
                available=True, reason="DEMO_MODE is enabled; calls return labeled demo data."
            )
        if not self._api_key:
            return ToolAvailability(available=False, reason="Credential is missing (NOT_CONFIGURED).")
        return ToolAvailability(
            available=False,
            reason="Credential is present but MCP/REST schemas are unverified (ADR-020); live calls are not implemented.",
        )

    def _require_callable(self) -> None:
        if self._demo_mode:
            return
        if not self._api_key:
            raise ProviderNotConfiguredError(PROVIDER_NAME)
        raise ProviderUnverifiedError(
            PROVIDER_NAME, "MCP and REST endpoint schemas are not confirmed; no live call is implemented"
        )

    async def analyze_website(self, request: AnalyzeWebsiteRequest) -> ToolResult:
        self._require_callable()
        return ToolResult(
            tool="similarweb.analyze_website",
            status="MOCK",
            demo=True,
            data={
                "label": "DEMO DATA",
                "domain": request.domain,
                "monthly_visits": 1_000_000,
                "engagement_rate": 0.42,
                "top_traffic_source": "search",
            },
        )

    async def compare_competitors(self, request: CompareCompetitorsRequest) -> ToolResult:
        self._require_callable()
        return ToolResult(
            tool="similarweb.compare_competitors",
            status="MOCK",
            demo=True,
            data={
                "label": "DEMO DATA",
                "domain": request.domain,
                "competitors": [
                    {"domain": competitor, "relative_traffic_share": 0.1}
                    for competitor in request.competitor_domains
                ],
            },
        )

    async def search_market_signals(self, request: SearchMarketSignalsRequest) -> ToolResult:
        self._require_callable()
        return ToolResult(
            tool="similarweb.search_market_signals",
            status="MOCK",
            demo=True,
            data={"label": "DEMO DATA", "query": request.query, "signals": []},
        )
