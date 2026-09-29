# Phase 2 Report

Status: complete. Domain model persisted to PostgreSQL, Pydantic schemas implemented, migrations verified against a live container (including a fresh volume with no manual setup), and execution events are enforced immutable at the database level.

## Deliverables

- `tasklexa_api.domain.enums`: Python enums for every status/priority/risk field in `docs/domain-model.md`, used by both the ORM layer and the Pydantic schemas so persisted and validated values can never drift apart.
- `tasklexa_api.db`: async SQLAlchemy engine/session setup (`asyncpg` driver) and a shared declarative `Base` with `UUIDPrimaryKeyMixin` / `CreatedAtMixin`.
- `tasklexa_api.models`: SQLAlchemy ORM models for all 11 persisted domain entities — `Mission`, `Task`, `AgentDefinition`, `AgentExecution`, `ToolDefinition`, `Evidence`, `Decision`, `Approval`, `Conflict`, `VerificationReport`, `ExecutionEvent` — with foreign keys matching the relationships in `docs/domain-model.md`.
- `tasklexa_api.schemas`: Pydantic read/create schemas mirroring the ORM models, plus `MissionPlan` and `AgentTeamPlan` as standalone validation schemas (no table — they are transient planner/resolver output per ADR-005, not persisted state).
- `tasklexa_api.repositories.execution_events.record_event`: the only write path provided for `ExecutionEvent`; there is no update/delete function, so the append-only contract is enforced in application code as well as in the database.
- Alembic migrations under `apps/api/migrations`:
  - `fc060ed3957d_initial_domain_model.py`: creates all 11 tables, matching the ORM exactly (`alembic check` reports no diff after applying).
  - `47623db881b8_execution_events_immutability_trigger.py`: adds a Postgres trigger (`prevent_execution_event_mutation`) that raises on any `UPDATE` or `DELETE` against `execution_events`, including cascade deletes from a parent `missions` row.
- `apps/api/docker-entrypoint.sh`: the API container now runs `alembic upgrade head` before starting `uvicorn`, so `docker compose up` alone brings a fresh database to the current schema with no manual step.
- `tests/integration/test_postgres_persistence.py`: live-database roundtrip test (Mission insert, `record_event` insert, trigger blocking an `UPDATE`, cleanup). Skips itself with a clear reason if Postgres is unreachable, matching this repo's existing no-Docker-required test philosophy.

## Design Notes / Inferred Decisions

`docs/domain-model.md` does not enumerate status values for `Task`, `AgentDefinition`, `AgentExecution`, `Decision`, `Conflict`, or `VerificationReport`. Reasonable enums were defined for each (see `tasklexa_api/domain/enums.py`) and recorded as ADR-008 in `docs/decisions.md`. Revisit these once Phase 3 (state machine) and Phase 8 (orchestrator) define the actual transition rules — the enum values may need to change.

`Capability` is represented as free-text array columns (`ARRAY(Text)`) on `Task.required_capabilities`, `AgentDefinition.capabilities`, and `ToolDefinition.capabilities`, not a first-class table. This matches the domain model's own rule that "core orchestration must not encode sector-specific capability names" — capabilities stay open-ended strings rather than a fixed lookup table with foreign keys.

A hard-delete of a `Mission` that has any `ExecutionEvent` rows will fail (the cascade delete is itself blocked by the immutability trigger). This is intentional: mission lifecycle should move through `MissionStatus.CANCELLED`, not row deletion, once execution history exists. No cancel/soft-delete API exists yet — that is Phase 3 scope.

## Verification Status

- `alembic upgrade head` against the live Compose Postgres: passed, from a completely empty volume (`docker compose down -v` then `up -d --build`).
- `alembic check`: passed — ORM models match the applied migrations exactly, no drift.
- Live roundtrip test (`tests/integration/test_postgres_persistence.py`): passed — insert Mission, insert ExecutionEvent via the repository, confirm `UPDATE` on `execution_events` is rejected by the trigger.
- Manual SQL verification: direct `UPDATE` and `DELETE` against `execution_events` both rejected by the trigger; cascade `DELETE` from `missions` also rejected.
- Existing API contract tests (`apps/api/tests/test_health_contract.py`): still passing, unaffected.
- `python -m compileall` across `apps/api/src`, `apps/api/tests`, `apps/api/migrations`, `tests/integration`: passed.
- Full `docker compose down -v && docker compose up -d --build`: all five containers reached `healthy`, API logs show Alembic running both migrations before Uvicorn starts.

## Known Limitations

- No Mission/Task CRUD API yet — Phase 3 scope ("Mission API and state machine").
- Inferred enums (see Design Notes) are a best-effort placeholder pending Phase 3/8 state-machine design.
- No repository/service layer exists yet beyond `record_event`; Phase 3 will add the actual persistence-backed Mission API.
