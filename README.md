# TASKLEXA AGENTICOS

**One Goal. The Right Agents. Governed Execution.**

Tasklexa Agenticos is planned as a sector-agnostic AI agent orchestration
platform. The platform owns mission planning, agent selection, approvals,
verification, and state transitions. External systems provide capabilities
through adapters and must be clearly marked as `LIVE`, `MOCK`,
`NOT_CONFIGURED`, or `FAILED`.

## Current Phase

Phase 12 (Mission Control UI) is complete — this closes the full planned
build (Phases 1–12). The Next.js frontend at `apps/web` now has a real
dashboard, mission creation, an 8-tab mission detail view (Overview, Tasks,
Team, Decisions & Approvals, Evidence, Timeline, Verification, Graph), and
an Agent/Tool registry, all backed by the live API — browser-verified end
to end (see `docs/phase-12.md`). OpenRouter also went `LIVE` for the first
time in this project with a real credential.

- [Architecture](docs/architecture.md)
- [Domain model](docs/domain-model.md)
- [Integration status](docs/integration-status.md)
- [Runbook](docs/runbook.md)
- [Vultr deployment architecture](docs/vultr-deployment.md)
- [Architecture decisions](docs/decisions.md)
- [Phase 1 report](docs/phase-1.md)
- [Phase 2 report](docs/phase-2.md)
- [Phase 3 report](docs/phase-3.md)
- [Phase 4 report](docs/phase-4.md)
- [Phase 5 report](docs/phase-5.md)
- [Phase 6 report](docs/phase-6.md)
- [Phase 7 report](docs/phase-7.md)
- [Phase 8 report](docs/phase-8.md)
- [Phase 9 report](docs/phase-9.md)
- [Phase 10 report](docs/phase-10.md)
- [Phase 11 report](docs/phase-11.md)
- [Phase 12 report](docs/phase-12.md)

## Local Development

```bash
cp .env.example .env
docker compose up
```

Local URLs once the stack is up:

- Mission Control: http://localhost:3000
- API health: http://localhost:8000/health
- Integration health: http://localhost:8000/health/integrations

If ports 5432/6379/7474/7687 are already used by other local services (common
on dev machines), override `POSTGRES_HOST_PORT`, `REDIS_HOST_PORT`,
`NEO4J_HTTP_HOST_PORT`, and `NEO4J_BOLT_HOST_PORT` in `.env`; only the
host-published ports change, container-to-container networking is unaffected.
