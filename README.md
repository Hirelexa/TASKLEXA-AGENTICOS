# TASKLEXA AGENTICOS

**One Goal. The Right Agents. Governed Execution.**

Tasklexa Agenticos is planned as a sector-agnostic AI agent orchestration
platform. The platform owns mission planning, agent selection, approvals,
verification, and state transitions. External systems provide capabilities
through adapters and must be clearly marked as `LIVE`, `MOCK`,
`NOT_CONFIGURED`, or `FAILED`.

## Current Phase

Phase 9 (Similarweb tool integration) is complete. `SimilarwebTool`
implements the full documented interface but — per `docs/architecture.md`'s
own explicit rule, since neither MCP nor REST schemas are confirmed for this
provider — never makes a live network call under any credential state; only
`DEMO_MODE` returns labeled data. Similarweb is also the project's first
real `ToolDefinition` row, discoverable via `GET /tools` and by the Phase 5
Capability Resolver. Awaiting approval to begin Phase 10 (Human approval).

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
