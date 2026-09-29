# Phase 3 Report

Status: complete. Mission create/read API implemented, backed by the Phase 2 persistence layer, with mission status transitions enforced by a deterministic state machine and recorded to the immutable execution-event log.

## Deliverables

- `tasklexa_api.domain.state_machine`: `MISSION_TRANSITIONS`, a complete adjacency map covering every `MissionStatus` (including the three terminal states, which allow no further transitions), and `validate_transition()`, which raises `InvalidMissionTransitionError` on any edge not in the map. The map is total — every status has an explicit entry, so there is no status this function can be silently wrong about.
- `tasklexa_api.domain.errors`: `MissionNotFoundError`, `InvalidMissionTransitionError` — repository-layer exceptions, translated to HTTP status codes only at the API layer, so the repository stays HTTP-agnostic.
- `tasklexa_api.repositories.missions`: `create_mission`, `get_mission`, `list_missions`, `transition_mission`. `create_mission` inserts the `Mission` row and its `MISSION_CREATED` execution event in a single transaction (atomic — not two separate commits). `transition_mission` validates the edge, updates `started_at`/`completed_at` when entering `RUNNING` or a terminal state, and records a `MISSION_STATUS_CHANGED` event with a `{"from", "to"}` payload.
- `tasklexa_api.api.missions`: `POST /missions`, `GET /missions`, `GET /missions/{id}`, `POST /missions/{id}/transitions`, `GET /missions/{id}/events` — mounted into `main.py`. 404 on unknown mission, 409 on an invalid transition.
- `tests/integration/test_mission_api.py`: live end-to-end test hitting the real FastAPI app (via `httpx.ASGITransport`, no separate server process) against the Compose Postgres — create, read, list, an invalid transition rejected with 409, a valid transition, the event log showing both `MISSION_CREATED` and `MISSION_STATUS_CHANGED`, and a 404 on an unknown id. Skips itself cleanly if Postgres or `httpx` isn't available, consistent with the existing no-Docker-required test philosophy.
- `apps/api/migrations/versions/0df726797cf0_add_mission_status_changed_event_type.py`: adds `MISSION_STATUS_CHANGED` to the `execution_event_type` Postgres enum (see Design Notes).

## Design Notes

**Mission state machine.** `docs/domain-model.md` lists the nine `MissionStatus` values but does not specify the allowed transitions between them. Phase 3 defines one explicitly (`DRAFT → PLANNING → ASSEMBLING → RUNNING ⇄ WAITING_APPROVAL`, `RUNNING → VERIFYING → COMPLETED`, with `FAILED`/`CANCELLED` reachable from every non-terminal state). This is a reasonable reading of the `GOAL → MISSION → ... → OUTCOME` flow in `docs/domain-model.md`, not a value taken from the spec — Phase 8 (Mission Orchestrator) is the actual authority on real transition triggers and may need to revise this map once the orchestrator's failure/replan logic exists.

**New execution event type.** `docs/domain-model.md`'s `ExecutionEvent` list is explicitly headed "Examples," not an exhaustive enumeration, so Phase 3 adds `MISSION_STATUS_CHANGED` as a generic transition event. The existing `MISSION_PLANNED` and `MISSION_COMPLETED` types were deliberately *not* reused for the transition endpoint: those names imply a real plan was produced or verification actually passed, neither of which Phase 3 does. Reserving them for Phase 4/5 (planner) and Phase 8 (orchestrator) keeps the audit log honest about what actually happened at each phase. Adding a Postgres enum value requires an `ALTER TYPE ... ADD VALUE` migration (plain `CREATE TYPE` diffing doesn't cover it) — this is not reversible; the migration's `downgrade()` raises rather than silently no-op, so a rollback attempt fails loudly instead of leaving the enum inconsistent with the code.

**Atomicity of mission creation.** The existing `record_event()` helper from Phase 2 commits on its own, which is fine for a standalone event write but would make mission creation two separate transactions (mission could persist with no `MISSION_CREATED` event if the second commit failed). `create_mission()` instead adds both rows to one session and commits once.

## Verification Status

- Fresh-volume verification (`docker compose down -v` then `up -d --build`): passed — all three migrations (Phase 2's two plus this phase's enum addition) applied automatically before Uvicorn started.
- `alembic check`: passed, no drift.
- Live Mission API test (`tests/integration/test_mission_api.py`): passed — full lifecycle through real HTTP calls against the running app and Compose Postgres.
- Live persistence test from Phase 2 (`test_postgres_persistence.py`): still passing, unaffected.
- Direct `curl` against the actual running `api` container (not just the test harness): `POST /missions` returned a valid `MissionRead` with `status: "DRAFT"`.
- Existing health contract tests: still passing.
- `python -m compileall` across all API and test modules: passed.

## Known Limitations

- No Task API yet — Phase 3 scope was explicitly "Mission API," per `docs/architecture.md`'s phase list.
- The state machine is not yet exercised by anything other than the transition endpoint; Phase 8's orchestrator is the real caller once it exists, and may need additional transitions (e.g., automatic `RUNNING → WAITING_APPROVAL` triggered by a gated `Decision`, not a client-initiated call).
- No auth: `created_by` is accepted directly from the request body. Authentication/authorization is out of scope for every phase so far and hasn't been scheduled yet.
