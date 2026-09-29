# TASKLEXA AGENTICOS

**One Goal. The Right Agents. Governed Execution.**

Tasklexa Agenticos is planned as a sector-agnostic AI agent orchestration
platform. The platform owns mission planning, agent selection, approvals,
verification, and state transitions. External systems provide capabilities
through adapters and must be clearly marked as `LIVE`, `MOCK`,
`NOT_CONFIGURED`, or `FAILED`.

## Current Phase

Phase 2 (domain model and PostgreSQL persistence) is complete. The full
domain model is migrated automatically on `docker compose up`, with
immutable execution events enforced at the database level. Awaiting
approval to begin Phase 3 (Mission API and state machine).

- [Architecture](docs/architecture.md)
- [Domain model](docs/domain-model.md)
- [Integration status](docs/integration-status.md)
- [Runbook](docs/runbook.md)
- [Vultr deployment architecture](docs/vultr-deployment.md)
- [Architecture decisions](docs/decisions.md)
- [Phase 1 report](docs/phase-1.md)
- [Phase 2 report](docs/phase-2.md)

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
