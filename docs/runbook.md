# Runbook

Status: Phase 9 complete. `SimilarwebTool` implemented against the documented interface; deliberately never makes a live call under any credential state (docs require this, not just caution) since MCP/REST schemas remain unconfirmed. First real `ToolDefinition` row in the project, discoverable via `GET /tools` and the Capability Resolver.

## Phase 0 Commands Run

- `pwd`
- `rg --files`
- `git status --short`
- `find . -maxdepth 3 -type f -print`
- `sed` reads of the pasted engineering prompt and existing `README.md`
- `git diff --check`
- `rg -n "PHASE 0|NOT_CONFIGURED|BandAdapter|ModelGateway|GraphService|Similarweb" README.md docs`
- `find docs -maxdepth 1 -type f -print | sort`
- `git diff --stat`
- `git diff -- README.md docs/architecture.md docs/integration-status.md`

## Phase 0 Test Results

No code tests were available because the repository contained no application code or test tooling. Phase 0 verification was limited to repository inspection and provider documentation review.

## Phase 1 Commands Run

- `python3 --version`
- `node --version`
- `npm --version`
- `docker --version`
- `command -v python3 node docker git`
- `npm view next version`
- `npm view react version`
- `npm view react-dom version`
- `npm view tailwindcss version`
- `npm view @tailwindcss/postcss version`
- `npm view @xyflow/react version`
- `npm view lucide-react version`
- `npm view eslint version`
- `npm view eslint-config-next version`

Additional verification commands and final results should be appended after dependency installation/type checks complete.

Phase 1 verification commands:

- `python3 -m unittest discover apps/api/tests`
- `python3 -m compileall -q apps/api/src apps/api/tests`
- `docker compose config`
- `docker-compose version`
- `npm install` from `apps/web`
- `npm --workspace apps/web run typecheck`
- `npm run build` from `apps/web`
- `python3.12 -m venv .venv`
- `.venv/bin/python -m pip install --upgrade pip`
- `.venv/bin/pip install -e apps/api`
- `.venv/bin/uvicorn tasklexa_api.main:app --host 127.0.0.1 --port 8000`
- `curl -sS http://127.0.0.1:8000/health`
- `curl -sS http://127.0.0.1:8000/health/integrations`
- `curl -I -sS http://127.0.0.1:3000`

Phase 1 test results:

- API contract tests: passed, 2 tests.
- API compile check: passed.
- API dependency install under Python 3.12: passed.
- API `/health`: returned `LIVE`.
- API `/health/integrations`: returned expected `FAILED` statuses for Docker-backed local services outside Compose and `NOT_CONFIGURED` for external providers.
- Web dependency install: passed, 0 vulnerabilities reported by npm.
- Web TypeScript check: passed.
- Web production build: passed.
- Web runtime smoke test: passed, HTTP 200.
- Docker install/launch on 2026-09-29: `Docker.app` was already present under `/Applications` but had never been launched (no daemon running, no CLI symlinked to PATH). Launched with `open -a Docker`; daemon became ready within 60s. CLI used via `/Applications/Docker.app/Contents/Resources/bin` on PATH for this session (not yet symlinked into `/usr/local/bin`).
- `docker compose config`: passed.
- `docker compose up -d --build`: initial run failed — host ports 5432/6379/7474/7687 were already bound by pre-existing native PostgreSQL/Redis/Neo4j instances on this machine. Remapped host-side published ports only (`POSTGRES_HOST_PORT=15432`, `REDIS_HOST_PORT=16379`, `NEO4J_HTTP_HOST_PORT=17474`, `NEO4J_BOLT_HOST_PORT=17687` in `.env`); container-to-container networking (service DNS names, internal ports) is unchanged. Re-run succeeded.
- `docker compose ps`: all five containers (`postgres`, `redis`, `neo4j`, `api`, `web`) reached `healthy`.
- `curl http://127.0.0.1:8000/health` via Compose: `LIVE`.
- `curl http://127.0.0.1:8000/health/integrations` via Compose: PostgreSQL, Redis, Neo4j `LIVE`; Band, OpenRouter, Similarweb, Vultr `NOT_CONFIGURED`.
- `curl http://127.0.0.1:3000` via Compose: HTTP 200.

## Phase 2 Commands Run

- `.venv/bin/pip install --upgrade -e apps/api` (adds SQLAlchemy, asyncpg, Alembic)
- `alembic init migrations` (under `apps/api`)
- `alembic revision --autogenerate -m "initial domain model"`
- `alembic revision -m "execution events immutability trigger"` (hand-written trigger DDL)
- `alembic upgrade head`
- `alembic check`
- `docker compose down -v` then `docker compose up -d --build` (fresh-volume verification)
- `docker compose logs api` (confirm Alembic runs before Uvicorn starts)
- `docker compose exec postgres psql ... \dt` (table listing)
- Manual SQL: insert Mission + ExecutionEvent, then attempt `UPDATE`/`DELETE`/cascade-`DELETE` against `execution_events`
- `python -m unittest tests.integration.test_postgres_persistence`
- `python -m unittest discover apps/api/tests`
- `python -m compileall apps/api/src apps/api/tests apps/api/migrations tests/integration`

Phase 2 test results:

- Migration autogenerate + apply: passed against the live Compose Postgres, zero manual SQL edits needed for the schema migration.
- `alembic check`: passed, no drift between ORM models and applied schema.
- Fresh-volume verification (`docker compose down -v` then `up -d --build`): passed. API container ran both migrations automatically via `docker-entrypoint.sh` before starting Uvicorn; all 12 tables (11 domain tables + `alembic_version`) present with no manual step.
- Immutability trigger: passed. Direct `UPDATE` and `DELETE` on `execution_events` both rejected; cascade `DELETE` from `missions` also rejected (mission has to be cancelled via status, not deleted, once it has events — see ADR-009).
- Live persistence roundtrip test: passed (insert Mission, insert ExecutionEvent via `record_event`, confirm mutation rejected, clean up).
- Existing health contract tests: still passing, unaffected by Phase 2 changes.
- Compile check across new modules: passed.

## Phase 3 Commands Run

- `.venv/bin/pip install --upgrade -e "apps/api[test]"` (adds `httpx` for API-layer testing)
- `alembic revision -m "add mission_status_changed event type"` (new Postgres enum value)
- `alembic upgrade head`
- `alembic check`
- `docker compose down -v` then `docker compose up -d --build` (fresh-volume verification, three migrations)
- `docker compose logs api` (confirm all three migrations run before Uvicorn starts)
- `python -m unittest tests.integration.test_mission_api`
- `python -m unittest tests.integration.test_postgres_persistence tests.integration.test_mission_api`
- `curl -X POST http://127.0.0.1:8000/missions ...` (direct call against the actual running container, not just the test harness)
- `python -m unittest discover apps/api/tests`
- `python -m compileall apps/api/src apps/api/tests apps/api/migrations tests/integration`

Phase 3 test results:

- Fresh-volume verification: passed. All three migrations (Phase 2's two, plus the new `MISSION_STATUS_CHANGED` enum value) applied automatically via `docker-entrypoint.sh` before Uvicorn started.
- `alembic check`: passed, no drift.
- Live Mission API test: passed. Full lifecycle exercised over real HTTP against the running FastAPI app and Compose Postgres — create (201), read (200), list (200, includes created mission), invalid transition DRAFT→COMPLETED (409), valid transition DRAFT→PLANNING (200), event log shows both `MISSION_CREATED` and `MISSION_STATUS_CHANGED`, unknown mission id (404).
- Direct `curl` against the running `api` container: passed, returned a valid `MissionRead` JSON body.
- Existing Phase 2 persistence test and health contract tests: still passing, unaffected.
- Compile check across all new modules: passed.

## Phase 4 Commands Run

- `.venv/bin/pip install --upgrade -e apps/api` (httpx moved from test-only to a core dependency)
- `python -m unittest discover apps/api/tests` (16 mocked gateway tests + 2 live-gated, plus existing health contract tests)
- `docker compose build api` (rebuild image with httpx + gateway code)
- `docker compose up -d api`
- `curl http://127.0.0.1:8000/health/integrations` (confirm OpenRouter goes through the real adapter path)
- `python -m unittest tests.integration.test_mission_api` (regression against the rebuilt container)
- `python -m compileall apps/api/src apps/api/tests apps/api/migrations tests/integration`

Phase 4 test results:

- Mocked `ModelGateway` unit tests: 16/16 passing. `NOT_CONFIGURED` cases assert zero HTTP calls were made (not just the returned status), using a mock transport handler that raises if invoked.
- Live test gate (`test_model_gateway_live.py`): 2/2 skipped, correctly, with an explicit reason — no `OPENROUTER_API_KEY` in this environment.
- `GET /health/integrations` in the rebuilt container: OpenRouter still reports `NOT_CONFIGURED`, now via the real `ModelGateway.health()` call path instead of the Phase 1 placeholder.
- Existing Phase 2/3 tests (persistence roundtrip, Mission API lifecycle, health contract): all still passing against the rebuilt image.
- Compile check across all new/changed modules: passed.

## Phase 5 Commands Run

- `alembic revision -m "seed generic agent definitions"` then hand-written `op.bulk_insert` with explicit Postgres enum casts (`agent_definition_risk_level`, `agent_definition_status`)
- `alembic upgrade head`
- `alembic check`
- `python -m unittest apps.api.tests.test_capability_resolver` (pure, no DB)
- `docker compose down -v` then `docker compose up -d --build` (fresh-volume verification, four migrations including the seed)
- `docker compose logs api` (confirm all four migrations run before Uvicorn starts)
- `python -m unittest tests.integration.test_agent_registry_and_team_plan`
- Full combined run: every mocked test file (`apps/api/tests`) plus every live integration test file (`tests/integration`) together in one process — this is what exposed the event-loop engine-caching bug (ADR-014)
- `python -m compileall apps/api/src apps/api/tests apps/api/migrations tests/integration`

Phase 5 test results:

- Pure capability resolver unit tests: 7/7 passing, no DB dependency.
- Fresh-volume verification: passed. All four migrations applied automatically, including the agent-definition seed; five rows present with `psql` confirming exact capability arrays.
- `alembic check`: passed, no drift (data-only migration, no schema change expected).
- Live Agent Registry + team-plan test: passed against the real running container — `GET /agents` lists all five seeds, `POST /missions/{id}/team-plan` correctly matches 2 of 3 requested capabilities and reports the third as unresolved, exactly two `AGENT_SELECTED` events recorded.
- Full combined regression (all mocked + all live test files in one process): passed after fixing the event-loop-scoped engine cache (ADR-014); this combination is exactly what had failed before the fix.
- Compile check across all new/changed modules: passed.

## Phase 6 Commands Run

- `.venv/bin/pip install --upgrade -e apps/api` (adds the `neo4j` official Python driver)
- `python -m unittest apps.api.tests.test_graph_service_mocked` (13 tests against a hand-rolled fake driver, no network)
- `docker compose build api` then `docker compose up -d api`
- `curl http://127.0.0.1:8000/health/integrations` (confirm Neo4j goes through the real `GraphService.health()` Cypher query)
- `python -m unittest tests.integration.test_neo4j_mission_graph` (live projection, repair-idempotency check, capability lookup, cleanup of both databases)
- `docker compose down -v` then `docker compose up -d --build` (fresh volumes for both PostgreSQL and Neo4j)
- Full combined run: every mocked test file plus every live integration test file (persistence, Mission API, Agent Registry, Neo4j graph) together in one process
- `alembic check` (confirm Phase 6 introduced no PostgreSQL schema drift)
- `python -m compileall apps/api/src apps/api/tests apps/api/migrations tests/integration`

Phase 6 test results:

- Mocked `GraphService` unit tests: 13/13 passing, zero network access. Caught a real bug (`_mutate()`'s `summary` parameter colliding with the Cypher `summary` param in `add_outcome`) before it ever reached a live query.
- Live projection/repair test: passing against the actual containers. Second projection call on the same mission produces byte-for-byte identical node and relationship counts to the first — idempotency verified, not assumed.
- `GET /health/integrations` in the rebuilt container: Neo4j reports `LIVE` via `RETURN 1` over an authenticated driver session.
- Fresh-volume verification with both PostgreSQL and Neo4j starting empty: all containers `healthy`, all four PostgreSQL migrations applied automatically.
- Full combined regression (every mocked + every live test file, one process): passing — confirms the event-loop-scoped caching pattern (ADR-014) also covers the new Neo4j driver cache.
- `alembic check`: no drift (Phase 6 made no PostgreSQL schema changes).
- Compile check across all new/changed modules: passed.

## Phase 7 Commands Run

- `.venv/bin/pip install --upgrade -e apps/api` (no new dependency — `websockets` was already present transitively via `uvicorn[standard]`)
- `python -m unittest apps.api.tests.test_band_adapter_mocked` (15 tests, offline, including a hand-rolled fake WebSocket connection for the `subscribe()`/`disconnect()` lifecycle)
- `docker compose build api` then `docker compose up -d api`
- `curl http://127.0.0.1:8000/health/integrations` (confirm Band goes through the real adapter path)
- `python -m unittest tests.integration.test_mission_api tests.integration.test_agent_registry_and_team_plan` (regression against the rebuilt container)
- `python -m compileall apps/api/src apps/api/tests apps/api/migrations tests/integration`

Phase 7 test results:

- Mocked `BandAdapter` unit tests: 15/15 passing. `NOT_CONFIGURED` cases assert zero HTTP calls (same pattern as Phase 4's OpenRouter tests). The WebSocket test proves actual message dispatch (handler fires only for its matching `event_type`) and actual connection cleanup (`disconnect()` really closes it), using an injected fake connection rather than a real socket.
- Live test gate (`test_band_adapter_live.py`): 2/2 skipped, correctly — no `BAND_AGENT_KEY`/`BAND_API_KEY` in this environment. The skip message itself carries the ADR-017 warning about unverified REST paths.
- `GET /health/integrations` in the rebuilt container: Band still reports `NOT_CONFIGURED`, now via the real `BandAdapter.health()` call path instead of the Phase 1 placeholder.
- Existing Phase 2–6 regression (persistence, Mission API, Agent Registry, Neo4j graph, health contract, OpenRouter): all still passing against the rebuilt image.
- Compile check across all new/changed modules: passed.

## Phase 8 Commands Run

- `.venv/bin/pip install --upgrade -e apps/api` (adds the `redis` official Python client)
- `alembic revision -m "add task_completed event type"` then `alembic upgrade head`
- `python -m unittest apps.api.tests.test_orchestrator_readiness` (11 pure tests, including cycle detection)
- `python -m unittest apps.api.tests.test_redis_lock_mocked` (6 tests, hand-rolled fake Redis client)
- `python -m unittest tests.integration.test_mission_orchestrator` (full lifecycle + Redis lock contention, against real containers)
- `docker compose down -v` then `docker compose up -d --build` (fresh volumes, five migrations)
- Full combined run: every mocked test file plus every live integration test file (persistence, Mission API, Agent Registry, Neo4j graph, orchestrator) together in one process
- `alembic check`
- `python -m compileall apps/api/src apps/api/tests apps/api/migrations tests/integration`

Phase 8 test results:

- Pure readiness/cycle-detection unit tests: 11/11 passing, no DB dependency. Cycle detection verified against a direct 2-task cycle, a 3-task cycle, a self-dependency, and confirmed to not falsely block unrelated tasks sharing the same mission.
- Mocked `RedisLock` unit tests: 6/6 passing, no network dependency.
- Live orchestrator lifecycle test: passing against the actual running containers — dependency-gated dispatch, an unresolvable-capability task correctly reported as `NO_AGENT_AVAILABLE` rather than force-assigned, a failure with a verified-empty cascade list, mission auto-transition to `VERIFYING` fired at exactly the right moment (only once every task settled), replan, a six-event-type audit trail check, and a 409 rejecting a fail attempt on an already-completed task.
- Live Redis lock contention test: passing — a second lock attempt on the same key genuinely fails against the real Redis container while the first still holds it, not just against the mock.
- Fresh-volume verification: all five PostgreSQL migrations applied automatically; all containers `healthy`.
- Full combined regression (every mocked + every live test file across all eight phases, one process): passing.
- `alembic check`: no drift.
- Compile check across all new/changed modules: passed.

## Phase 9 Commands Run

- `alembic revision -m "seed similarweb tool definition"` then hand-written `op.bulk_insert` with explicit Postgres enum casts, matching Phase 5's agent-seed pattern
- `alembic upgrade head`
- `python -m unittest apps.api.tests.test_similarweb_tool_mocked` (16 tests, offline)
- `python -m unittest tests.integration.test_tool_registry_api`
- `docker compose down -v` then `docker compose up -d --build` (fresh volumes, six migrations)
- `curl http://127.0.0.1:8000/tools` and `curl http://127.0.0.1:8000/health/integrations` against the rebuilt container
- Full combined run: every mocked test file plus every live integration test file across all nine phases, together in one process
- `alembic check`
- `python -m compileall apps/api/src apps/api/tests apps/api/migrations tests/integration`

Phase 9 test results:

- Mocked `SimilarwebTool` unit tests: 16/16 passing, zero network access. Every status branch (`NOT_CONFIGURED`, `UNVERIFIED`, `MOCK`) and every call method's refusal/demo-data path covered.
- Live Tool Registry test: passing against the actual running container — seeded tool listed and fetchable by id with correct capabilities and `NOT_CONFIGURED` status, 404 on an unknown id, `/health/integrations` cross-checked.
- Fresh-volume verification: all six migrations applied automatically (five prior phases' plus this phase's tool seed); all containers `healthy`.
- Full combined regression (every mocked + every live test file across all nine phases, one process): passing.
- Fixed a real bug surfaced by adding the `UNVERIFIED` status: `test_health_contract.py`'s label-visibility check hardcoded a scan of `health.py` alone, which broke as soon as a status label started living in a provider adapter module instead. Rewrote to derive expected labels from `IntegrationStatus` itself and scan `health.py` plus every `integrations/*/*.py` module.
- `alembic check`: no drift.
- Compile check across all new/changed modules: passed.

## Local Development Target

Phase 1 should make this command the primary local startup path:

```bash
docker compose up
```

Expected local services after Phase 1:

- Web app
- FastAPI backend
- PostgreSQL
- Neo4j
- Redis

Expected health endpoints after Phase 1 or Phase 3:

- `GET /health`
- `GET /health/integrations`

`docker compose up` is verified on this machine. No current blocker for local startup.

## Required Local Prerequisites

- Docker Desktop or compatible Docker Engine
- Docker Compose v2
- Node.js LTS
- Python 3.12+
- Avoid the local system Python `3.14.0a6` for project runtime. The API Dockerfile pins Python 3.12.
- Python package manager selected in Phase 1
- `kubectl` for later deployment validation

## Required Secrets

Secrets must come from environment variables or secret managers. Real credentials must not be committed.

- `OPENROUTER_API_KEY`
- `BAND_AGENT_KEY`
- `BAND_USER_KEY`, if human/platform automation is needed
- `SIMILARWEB_API_KEY`
- Similarweb MCP access details, if separate from API key
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `NEO4J_URI`
- `NEO4J_USERNAME`
- `NEO4J_PASSWORD`
- `REDIS_URL`
- `VULTR_API_TOKEN`
- VKE kubeconfig, stored outside source control

## Safe Failure Rules

- Missing external credentials produce `NOT_CONFIGURED`.
- Configured but failing providers produce `FAILED`.
- Demo data appears only when demo mode is explicitly enabled.
- Demo data must be labeled `DEMO DATA`.
- Live integrations are never silently replaced with mocks.
- Raw provider errors are logged securely but converted to safe user-facing messages.

## Phase Exit Checklist

At the end of every implementation phase:

1. Run available tests.
2. Report files created or changed.
3. Report commands executed.
4. Report test results.
5. Report unresolved issues.
6. Update `docs/integration-status.md`.
7. Update this runbook.
8. Stop if a required external capability cannot be verified.

## Build Approval Gate

Phase 1 must not begin until the operator approves the Phase 0 architecture.
