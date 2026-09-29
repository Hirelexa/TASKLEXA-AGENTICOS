# Phase 4 Report

Status: complete. `ModelGateway` adapter implemented against the interface specified in `docs/architecture.md`'s OpenRouter integration contract, reporting `NOT_CONFIGURED` with zero network calls when no credential is present, mocked unit tests covering every method, and a separate live test gate that skips cleanly without a real `OPENROUTER_API_KEY`.

## Deliverables

- `tasklexa_api.integrations.openrouter.client.OpenRouterClient`: thin async wrapper over `httpx.AsyncClient` for `GET /models` and `POST /chat/completions` against `https://openrouter.ai/api/v1`, with Bearer auth. Accepts an injectable `httpx.AsyncBaseTransport`, which is how the mocked tests avoid any real network access.
- `tasklexa_api.integrations.openrouter.gateway.ModelGateway`: implements every method from the documented Gateway interface — `health()`, `list_models()`, `select_model()`, `complete()`, `complete_structured()`, `estimate_cost()`.
- `tasklexa_api.schemas.model_gateway`: `ModelInfo`, `ModelCatalog`, `ModelSelectionRequest`, `SelectedModel`, `ChatMessage`, `ModelRequest`, `TokenUsage`, `ModelResponse`, `StructuredModelRequest`, `ValidatedModelResponse`, `CostEstimate`.
- `tasklexa_api.domain.errors`: `ProviderNotConfiguredError`, `ProviderCallFailedError`, `StructuredOutputValidationError` — gateway-layer exceptions, not tied to HTTP status codes (no route consumes the gateway directly yet; that's for the Mission Compiler in a later phase).
- `tasklexa_api.schemas.health`: `IntegrationHealth`, `HealthResponse`, `IntegrationsHealthResponse` moved out of `health.py` into the `schemas` package (consistent with every other domain schema) so `gateway.py` and `health.py` can both depend on it without a circular import.
- `GET /health/integrations` now calls the real `ModelGateway.health()` for the OpenRouter row instead of the Phase 1 placeholder. Verified live in the running container: still `NOT_CONFIGURED` (correct — no credential), but now via the actual adapter code path with the documented "no live provider calls without a credential" rule enforced in code, not just in the response text.
- `apps/api/tests/test_model_gateway_mocked.py`: 16 tests, all offline (`httpx.MockTransport`) — `NOT_CONFIGURED` short-circuit (asserts zero HTTP calls), `LIVE`/`FAILED` health mapping, model catalog parsing, chat completion parsing, structured-output validation success and failure, `select_model` behavior, and `estimate_cost`'s deliberate non-computation.
- `apps/api/tests/test_model_gateway_live.py`: 2 tests, gated on `OPENROUTER_API_KEY` being a real environment variable. Both skip in this environment with an explicit reason pointing at `docs/integration-status.md`.

## Design Notes

**No hard-coded default model.** `docs/architecture.md`'s open questions state "Exact model policy defaults require a live model catalog and account limits" — this repo has neither yet. `select_model()` therefore requires the caller to supply `preferred_models` and raises `ValueError` if the list is empty, rather than falling back to some invented model ID. Whatever component calls this next (the Mission Compiler / Capability Resolver in Phase 5) is responsible for sourcing that list from `AgentDefinition.preferred_model_policy`.

**`estimate_cost()` never fabricates a number.** The same open-questions section says "Usage/cost metadata shape must be verified against a live response before declaring cost tracking verified." Rather than guess at OpenRouter's pricing JSON shape and compute a plausible-looking dollar figure, `estimate_cost()` always returns `estimated_cost_usd: None` with a note explaining why. See ADR-012 — this is a "don't confuse demo/best-guess with real integration" call, same spirit as ADR-004.

**Structured outputs use OpenAI-compatible `response_format`.** `docs/architecture.md` confirms OpenRouter is OpenAI SDK-compatible and supports "JSON-schema response format" for structured outputs, but does not give the exact request shape. `complete_structured()` sends `response_format: {type: "json_schema", json_schema: {name, strict, schema}}` — the standard OpenAI-compatible shape — using the Pydantic model's own `model_json_schema()`. This has not been verified against a live OpenRouter response (see Known Limitations).

## Verification Status

- Mocked unit tests: 16/16 passing, zero network access (verified by asserting the mock transport's call count in the `NOT_CONFIGURED` cases).
- Live test gate: both tests present and correctly skip with a clear, non-misleading reason — this environment has no `OPENROUTER_API_KEY`.
- `GET /health/integrations` in the actual running container (rebuilt image, not just the local venv): OpenRouter reports `NOT_CONFIGURED` via the real `ModelGateway.health()` call path.
- Full existing regression (Phase 2 persistence test, Phase 3 Mission API test, health contract tests): all still passing against the rebuilt image.
- `python -m compileall` across all new/changed modules: passed.

## Known Limitations

- **Nothing here has been exercised against the real OpenRouter API.** Request/response parsing (`_parse_completion`, the `response_format` shape, the `/models` catalog shape) is built strictly from the documentation bullets in `docs/architecture.md`, not from a live call. The first real credential this project gets should run the live test gate before this adapter is trusted for anything user-facing.
- No caller uses `ModelGateway` yet — no route, no Mission Compiler. Phase 4 scope per `docs/architecture.md` was the adapter itself ("Implement adapter with NOT_CONFIGURED status. Add mocked unit tests and separate live test gate"), not wiring it into the orchestration flow. That's Phase 5+.
- `estimate_cost()` is intentionally a stub (see Design Notes) until pricing metadata shape is verified live.
