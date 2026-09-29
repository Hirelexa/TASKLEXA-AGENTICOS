import httpx

# Verified from docs/architecture.md's Integration Contract: Band.
AGENT_API_BASE_URL = "https://app.band.ai/api/v1/agent"
WEBSOCKET_URL = "wss://app.band.ai/api/v1/socket/websocket"


class BandClient:
    """REST transport for the Band Agent API.

    Only AGENT_API_BASE_URL and the auth-header convention (Bearer, matching
    every other provider in this codebase) are verified against real docs.
    The specific path segments below (/contexts, /participants, /messages,
    /events) are an inferred REST convention, not confirmed against Band's
    actual route names - see docs/decisions.md ADR-017.
    """

    def __init__(self, api_key: str | None, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._api_key = api_key
        self._http = httpx.AsyncClient(base_url=AGENT_API_BASE_URL, timeout=15.0, transport=transport)

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._api_key}"}

    async def get(self, path: str, **params) -> httpx.Response:
        return await self._http.get(path, headers=self._headers(), params=params)

    async def post(self, path: str, json: dict) -> httpx.Response:
        return await self._http.post(path, headers=self._headers(), json=json)

    async def aclose(self) -> None:
        await self._http.aclose()
