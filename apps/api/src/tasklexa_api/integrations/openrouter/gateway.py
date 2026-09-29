from datetime import UTC, datetime

import httpx
from pydantic import BaseModel, ValidationError

from tasklexa_api.domain.errors import (
    ProviderCallFailedError,
    ProviderNotConfiguredError,
    StructuredOutputValidationError,
)
from tasklexa_api.schemas.health import IntegrationHealth
from tasklexa_api.integrations.openrouter.client import OpenRouterClient
from tasklexa_api.schemas.model_gateway import (
    CostEstimate,
    ModelCatalog,
    ModelInfo,
    ModelRequest,
    ModelResponse,
    ModelSelectionRequest,
    SelectedModel,
    StructuredModelRequest,
    TokenUsage,
    ValidatedModelResponse,
)

PROVIDER_NAME = "OpenRouter"


class ModelGateway:
    def __init__(self, api_key: str | None, client: OpenRouterClient | None = None) -> None:
        self._api_key = api_key
        self._client = client or OpenRouterClient(api_key=api_key)

    def _require_configured(self) -> None:
        if not self._api_key:
            raise ProviderNotConfiguredError(PROVIDER_NAME)

    async def health(self) -> IntegrationHealth:
        if not self._api_key:
            return IntegrationHealth(
                provider=PROVIDER_NAME,
                purpose="Model gateway",
                status="NOT_CONFIGURED",
                details="Credential is missing; no live provider calls will be attempted.",
            )

        try:
            response = await self._client.list_models()
        except httpx.HTTPError as exc:
            return IntegrationHealth(
                provider=PROVIDER_NAME,
                purpose="Model gateway",
                status="FAILED",
                details=f"Request to OpenRouter failed: {exc.__class__.__name__}",
            )

        if response.status_code == 200:
            return IntegrationHealth(
                provider=PROVIDER_NAME,
                purpose="Model gateway",
                status="LIVE",
                details="Authenticated call to GET /models succeeded.",
            )

        return IntegrationHealth(
            provider=PROVIDER_NAME,
            purpose="Model gateway",
            status="FAILED",
            details=f"GET /models returned HTTP {response.status_code}.",
        )

    async def list_models(self) -> ModelCatalog:
        self._require_configured()

        try:
            response = await self._client.list_models()
        except httpx.HTTPError as exc:
            raise ProviderCallFailedError(PROVIDER_NAME, exc.__class__.__name__) from exc

        if response.status_code != 200:
            raise ProviderCallFailedError(PROVIDER_NAME, f"GET /models returned HTTP {response.status_code}")

        body = response.json()
        models = [
            ModelInfo(
                id=entry["id"],
                name=entry.get("name"),
                context_length=entry.get("context_length"),
                pricing=entry.get("pricing"),
            )
            for entry in body.get("data", [])
        ]
        return ModelCatalog(models=models, fetched_at=datetime.now(UTC))

    def select_model(self, request: ModelSelectionRequest) -> SelectedModel:
        if not request.preferred_models:
            raise ValueError(
                "select_model requires at least one preferred model id; "
                "Phase 4 does not hard-code a default model (see docs/architecture.md open questions)."
            )

        return SelectedModel(
            model_id=request.preferred_models[0],
            fallback_models=request.preferred_models[1:],
            rationale="Selected the first entry of the caller-supplied preferred_models list.",
        )

    async def complete(self, request: ModelRequest) -> ModelResponse:
        self._require_configured()

        payload: dict = {
            "model": request.model,
            "messages": [message.model_dump() for message in request.messages],
        }
        if request.fallback_models:
            payload["models"] = [request.model, *request.fallback_models]
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens

        try:
            response = await self._client.chat_completions(payload)
        except httpx.HTTPError as exc:
            raise ProviderCallFailedError(PROVIDER_NAME, exc.__class__.__name__) from exc

        if response.status_code != 200:
            raise ProviderCallFailedError(
                PROVIDER_NAME, f"POST /chat/completions returned HTTP {response.status_code}: {response.text}"
            )

        return self._parse_completion(response.json())

    def _parse_completion(self, body: dict) -> ModelResponse:
        choice = body["choices"][0]
        usage_body = body.get("usage")
        usage = (
            TokenUsage(
                prompt_tokens=usage_body["prompt_tokens"],
                completion_tokens=usage_body["completion_tokens"],
                total_tokens=usage_body["total_tokens"],
            )
            if usage_body
            else None
        )
        return ModelResponse(
            model=body["model"],
            content=choice["message"]["content"],
            finish_reason=choice.get("finish_reason"),
            usage=usage,
        )

    async def complete_structured(
        self, request: StructuredModelRequest, schema: type[BaseModel]
    ) -> ValidatedModelResponse:
        self._require_configured()

        payload: dict = {
            "model": request.model,
            "messages": [message.model_dump() for message in request.messages],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": request.response_schema_name,
                    "strict": True,
                    "schema": schema.model_json_schema(),
                },
            },
        }
        if request.fallback_models:
            payload["models"] = [request.model, *request.fallback_models]

        try:
            response = await self._client.chat_completions(payload)
        except httpx.HTTPError as exc:
            raise ProviderCallFailedError(PROVIDER_NAME, exc.__class__.__name__) from exc

        if response.status_code != 200:
            raise ProviderCallFailedError(
                PROVIDER_NAME, f"POST /chat/completions returned HTTP {response.status_code}: {response.text}"
            )

        parsed = self._parse_completion(response.json())

        try:
            validated = schema.model_validate_json(parsed.content)
        except ValidationError as exc:
            raise StructuredOutputValidationError(request.response_schema_name, str(exc)) from exc

        return ValidatedModelResponse(model=parsed.model, data=validated.model_dump(mode="json"), usage=parsed.usage)

    def estimate_cost(self, usage: TokenUsage, model_id: str) -> CostEstimate:
        return CostEstimate(
            model=model_id,
            estimated_cost_usd=None,
            note=(
                "OpenRouter usage/cost metadata shape is not verified against a live response "
                "(see docs/architecture.md Phase 4 open questions); cost is not computed."
            ),
        )

    async def aclose(self) -> None:
        await self._client.aclose()
