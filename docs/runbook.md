# Runbook

Status: Phase 1 complete. Full local startup verified via `docker compose up`.

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
