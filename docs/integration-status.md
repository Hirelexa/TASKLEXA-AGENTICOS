# Integration Status

Status: Phase 4 complete. Local infrastructure (PostgreSQL, Redis, Neo4j) verified `LIVE` under Docker Compose. PostgreSQL holds the full migrated domain model with immutable execution events, a Mission create/read API with a deterministic state machine is live, and the OpenRouter `ModelGateway` adapter is implemented with full mocked coverage. No live external provider integration tests have been run — every external provider remains `NOT_CONFIGURED` in this environment.

| Provider | Purpose | Documentation | Authentication | Implementation Status | Test Status | Last Verification | Known Limitations |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Band | Agent collaboration rooms, participants, messages, events, real-time agent communication | https://docs.band.ai/api/agent-api, https://docs.band.ai/integrations/sdks/overview, https://docs.band.ai/integrations/mcp/reference | Agent and/or user keys; exact account setup not verified | `NOT_CONFIGURED` | Not tested | 2026-09-29 docs review | Needs credentials and SDK inspection. MCP is useful for commands but not sufficient for unsolicited inbound events. |
| OpenRouter | Model gateway for all LLM requests | https://openrouter.ai/docs/quickstart, https://openrouter.ai/docs/guides/routing/provider-selection, https://openrouter.ai/docs/guides/routing/model-fallbacks, https://openrouter.ai/docs/guides/features/structured-outputs | Bearer API key | `ModelGateway` adapter implemented (health, list_models, select_model, complete, complete_structured, estimate_cost) | `NOT_CONFIGURED` (no credential); 16/16 mocked unit tests passing; live test gate present, skipped | 2026-09-29 Phase 4 Compose verification | Nothing has been exercised against a real OpenRouter response yet. Model IDs, structured-output request shape, rate limits, and usage/cost response shape are unverified live — see ADR-012/ADR-013. No caller wired in yet (Phase 5+). |
| Neo4j | Mission graph projection and relationship queries | https://neo4j.com/docs/python-manual/current/ | Username/password or token depending deployment | Local Compose service verified | `LIVE` under `docker compose up` | 2026-09-29 Phase 1 Compose verification | PostgreSQL remains authoritative. Graph projection repair behavior must be implemented. |
| Similarweb | Discoverable digital intelligence tool | https://docs.similarweb.com/api-v5/getting-started/authentication, https://docs.similarweb.com/api-v5/api-reference/website-analysis-api, https://developers.similarweb.com/docs/similarweb-mcp | Similarweb API key; MCP access requires confirmation | `NOT_CONFIGURED` | Not tested | 2026-09-29 docs review | Exact MCP transport/tool schema and account availability are unverified. Demo data must be clearly labeled. |
| PostgreSQL | Transactional application state | Docker Compose local service | Local credentials in `.env`, deployment secrets in Kubernetes | Full domain model migrated (11 tables); Mission create/read API live | `LIVE`, migrations and Mission API verified against a fresh volume | 2026-09-29 Phase 3 Compose verification | Task CRUD API not yet built. |
| Redis | Transient execution state, locks, queues, cache if required | Docker Compose local service | Optional password depending environment | Local Compose service verified | `LIVE` under `docker compose up` | 2026-09-29 Phase 1 Compose verification | Queue semantics not yet selected. |
| Vultr Kubernetes Engine | Deployment target | https://docs.vultr.com/support/products/vke/can-i-run-kubernetes-on-vultr, https://docs.vultr.com/products/compute/kubernetes/management/connection | Vultr API token and VKE kubeconfig | `NOT_CONFIGURED` | Not tested | 2026-09-29 docs review | No infrastructure may be provisioned without explicit human authorization. |

## Status Definitions

- `LIVE`: Authenticated call or connection has succeeded against the real provider.
- `MOCK`: Explicit demo or test provider is active and labeled as mock/demo in API and UI.
- `NOT_CONFIGURED`: Credentials, endpoint, or account setup is missing.
- `FAILED`: Provider is configured but a health check or runtime operation failed.
- `UNVERIFIED`: Documentation or SDK behavior is not confirmed enough to implement safely.

## Phase 1 Result

External providers remain `NOT_CONFIGURED`. API and web are locally verified both outside Docker and under `docker compose up`. PostgreSQL, Redis, and Neo4j are `LIVE` under Docker Compose, and PostgreSQL now runs the full Phase 2 domain-model migration automatically on container start. No mocked integration test is counted as proof of live provider operation.
