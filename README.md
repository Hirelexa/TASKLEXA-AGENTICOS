# TASKLEXA AGENTICOS

**One Goal. The Right Agents. Governed Execution.**

Tasklexa Agenticos is planned as a sector-agnostic AI agent orchestration
platform. The platform owns mission planning, agent selection, approvals,
verification, and state transitions. External systems provide capabilities
through adapters and must be clearly marked as `LIVE`, `MOCK`,
`NOT_CONFIGURED`, or `FAILED`.

## Current Phase

Phase 10 (Human approval) is complete. Creating a `Decision` with
`approval_required=true` moves a mission to `WAITING_APPROVAL` and blocks
task dispatch until an operator resolves it via `approve`/`modify` (resumes
to `RUNNING`) or `reject` (terminal `CANCELLED`). This phase also found and
fixed a real bug from Phase 3: the mission state machine didn't actually
match `docs/architecture.md`'s own documented diagram — see ADR-021.
Awaiting approval to begin Phase 11 (Verifier).

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
