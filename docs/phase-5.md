# Phase 5 Report

Status: complete. Agent Registry (persisted, queryable, seeded with five generic reusable agent definitions covering every capability in `docs/domain-model.md`) and a deterministic Capability Resolver that dynamically assembles a team from a mission's required capabilities.

## Deliverables

- `tasklexa_api.repositories.agents`: `create_agent_definition`, `get_agent_definition`, `list_agent_definitions` (optional `active_only` filter).
- `tasklexa_api.repositories.tools`: `list_tool_definitions` (optional `available_only` filter) — read-only for now; no tool rows exist yet (Similarweb is Phase 9), but the Capability Resolver needs to query tools alongside agents per the Component Responsibility Matrix ("Capability Resolver | Capability extraction, agent/tool matching").
- `tasklexa_api.domain.capability_resolver.resolve_team()`: a pure function (no DB access, no I/O) that matches each required capability against a candidate list of agents and tools, returning the `AgentTeamPlan` schema Phase 2 already defined. Deduplicates repeated matches, collects `unresolved_capabilities` for anything nothing can satisfy, and emits a risk note for any `HIGH`-risk agent or any tool that `requires_approval`.
- `tasklexa_api.repositories.team_plans.resolve_team_for_mission()`: fetches only `ACTIVE` agents and `AVAILABLE` tools (the "permissions/status" and "authentication, risk, policy" filtering domain-model.md calls for), calls the pure resolver, and records one `AGENT_SELECTED` execution event per selected agent — atomically, in the same transaction.
- API: `POST /agents`, `GET /agents`, `GET /agents/{id}` (Agent Registry CRUD, mirroring the Mission API's shape) and `POST /missions/{mission_id}/team-plan` (the resolver endpoint, mounted under missions since the output is mission-scoped).
- `apps/api/migrations/versions/eb6c6327bc81_seed_generic_agent_definitions.py`: seeds five sector-agnostic agent definitions — `research-agent`, `analysis-agent`, `planning-agent`, `verification-agent`, `market-intelligence-agent` — covering all eleven capabilities from `docs/domain-model.md`'s "Initial generic capabilities" list with no overlap. IDs are deterministic (`uuid5`), so they're stable across environments and directly assertable in tests.
- `apps/api/tests/test_capability_resolver.py`: 7 pure unit tests (no DB) covering full match, unresolved capability, dedup, empty input, risk notes, tool+agent combined resolution, and pass-through of `required_capabilities`/`mission_id`.
- `tests/integration/test_agent_registry_and_team_plan.py`: live end-to-end test — lists the actual seeded agents through real HTTP, resolves a team plan against them (2 matched, 1 deliberately unresolved), confirms two `AGENT_SELECTED` events landed in the mission's event log, and checks the 404 paths.

## Design Notes

**Why five agents, not eleven.** `docs/domain-model.md` lists eleven generic capabilities but doesn't say how many agent definitions should exist. Grouping related capabilities onto one agent (e.g., `analysis`, `technical_analysis`, and `risk_analysis` all belong to `analysis-agent`) is a judgment call, not a spec value — it's a reasonable single team member per broad skill area, not one agent per capability. If a real usage pattern needs analysis and risk analysis assigned separately, splitting `analysis-agent` later is a normal follow-up, not a migration disaster (seed data, not schema).

**No model policy on seed agents.** `AgentDefinition.preferred_model_policy` is left `NULL` for every seeded agent, deliberately extending [[ADR-013]]'s reasoning from Phase 4: there is still no live-verified OpenRouter model catalog, so hard-coding a model ID into seed data would be the same mistake `select_model()` already refuses to make.

**The resolver takes pre-filtered candidates, not raw DB rows.** `resolve_team()` in `domain/capability_resolver.py` accepts `list[AgentDefinitionRead]` / `list[ToolDefinitionRead]` — Pydantic schemas, not SQLAlchemy ORM instances — so it has zero DB dependency and is trivially unit-testable with plain constructed objects. Filtering by `status == ACTIVE` / `status == AVAILABLE` happens one layer up, in the repositories, which is also where domain-model.md's "Agents are selected by capabilities, permissions, and status" rule is actually enforced.

**`team-plan` takes `required_capabilities` directly in the request body**, not from a stored `MissionPlan`. `Mission` itself has no `required_capabilities` field (see `docs/domain-model.md`) — that field lives on `Task` and on the transient `MissionPlan`/`AgentTeamPlan` schemas. Since the Mission Compiler that would produce a real `MissionPlan` isn't built yet (it isn't a numbered phase in `docs/architecture.md`'s sequence — Phase 8's Orchestrator is the first consumer of a plan), Phase 5 accepts the capability list explicitly from the caller rather than fabricating a stored-plan pipeline that doesn't exist yet.

## Bug Fixed Along the Way

`tasklexa_api.db.session.get_engine()` was `@lru_cache`d with no arguments, so it returned the *same* `AsyncEngine` (and therefore the same asyncpg connection pool, bound to whatever event loop was running when it was first created) for the lifetime of the Python process. That's correct for the real deployed app (uvicorn keeps one event loop alive for its whole life), but broke as soon as a single test process ran more than one `asyncio.run()`-based integration test that touched the FastAPI app — the second test's fresh event loop tried to reuse a connection pool tied to the first test's already-closed loop, producing `RuntimeError: ... attached to a different loop`. This surfaced while adding this phase's second live-integration test file (once two independent `asyncio.run()` calls in the same process both went through `tasklexa_api.main.app`). Fixed by keying the engine cache on `id(asyncio.get_event_loop())` instead of caching unconditionally — recorded as [[ADR-014]]. Production behavior is unchanged; the test suite is now robust to however many integration test files touch the app in one process.

## Verification Status

- 7 pure `resolve_team()` unit tests: passing, zero DB/network dependency.
- Fresh-volume verification (`docker compose down -v` then `up -d --build`): all four migrations (Phase 2's two, Phase 3's enum addition, this phase's agent seed) ran automatically; API container reached `healthy`.
- Live Agent Registry + team-plan test: passing against the actual running container — `GET /agents` returns all five seeded agents, `POST /missions/{id}/team-plan` correctly resolves `research`+`planning` to the two matching seeded agents while flagging a nonexistent capability as unresolved, and exactly two `AGENT_SELECTED` events land in the mission's event log.
- `alembic check`: no drift.
- Full combined regression — every mocked test file and every live integration test file run together in one process (the scenario that exposed the event-loop bug): all passing.
- `python -m compileall` across all new/changed modules: passed.

## Known Limitations

- Only five seed agents exist; there's no admin UI or process yet for reviewing/updating the registry beyond direct API calls or a new migration.
- The Tool Registry side of the resolver is exercised only by the unit tests (with a fabricated tool) — no real `ToolDefinition` rows exist in this database yet. That's expected; Phase 9 (Similarweb) is the first phase that registers a real tool.
- `team-plan` has no concept of "block mission assembly on unresolved capabilities" — it just reports `unresolved_capabilities` in the response. `docs/domain-model.md`'s rule ("Missing required capabilities block assembly unless policy permits degraded execution") is an orchestrator-level decision; Phase 8 is where that policy actually gets enforced.
