import httpx

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


class OpenRouterClient:
    def __init__(self, api_key: str | None, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._api_key = api_key
        self._http = httpx.AsyncClient(base_url=OPENROUTER_BASE_URL, timeout=15.0, transport=transport)

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._api_key}"}

    async def list_models(self) -> httpx.Response:
        return await self._http.get("/models", headers=self._headers())

    async def chat_completions(self, payload: dict) -> httpx.Response:
        return await self._http.post("/chat/completions", headers=self._headers(), json=payload)

    async def aclose(self) -> None:
        await self._http.aclose()
