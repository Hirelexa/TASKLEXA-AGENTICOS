# Architecture Decisions

Status: Phase 0.

## ADR-001: Tasklexa Owns Orchestration

Decision: The Mission Orchestrator is the only workflow authority.

Rationale: Band, OpenRouter, Similarweb, Neo4j, Redis, and Vultr each solve infrastructure or capability problems, but none should own mission state transitions.

Consequence: Every integration is hidden behind an adapter. LLMs and agents can recommend state changes, but application services apply them.

## ADR-002: PostgreSQL Is Authoritative

Decision: PostgreSQL stores mission state, tasks, executions, approvals, decisions, evidence, and immutable execution events.

Rationale: The system needs transactional guarantees and deterministic state transitions.

Consequence: Neo4j is a projection. Projection failures must be visible and repairable.

## ADR-003: Neo4j Is the Relationship Graph

Decision: Neo4j represents connected operational intelligence, not transactional truth.

Rationale: Mission graphs and evidence relationships benefit from graph traversal without making graph persistence the workflow engine.

Consequence: Graph writes should be idempotent and replayable from PostgreSQL events.

## ADR-004: External Integrations Must Show Status

Decision: Every provider reports `LIVE`, `MOCK`, `NOT_CONFIGURED`, or `FAILED`.

Rationale: The product must not confuse demo behavior with real integrations.

Consequence: UI and API responses must expose integration status, and demo data must be visibly labeled.

## ADR-005: Strict Structured Planning

Decision: Mission Compiler output must validate against a Pydantic schema before persistence or execution.

Rationale: Free-form LLM output is not safe executable workflow state.

Consequence: Invalid output triggers bounded retries and then safe failure.

## ADR-006: Band Requires Real-Time Design

Decision: Band integration must account for WebSocket inbound events, not just REST polling.

Rationale: Official docs describe WebSocket as the primary channel for receiving messages and room events.

Consequence: BandAdapter must include subscription, reconnection, and backlog sync behavior.

## ADR-007: Similarweb Is Optional and Discoverable

Decision: Similarweb is a tool selected by capability resolution, not a global dependency.

Rationale: Tasklexa is sector-agnostic; digital intelligence is one possible mission capability.

Consequence: Missions that do not require digital intelligence should never initialize or require Similarweb.

## ADR-008: Inferred Status Enums for Unspecified Domain Fields

Decision: `docs/domain-model.md` defines explicit status enums for `Mission`, `Approval`, and `ToolDefinition`, but not for `Task`, `AgentDefinition`, `AgentExecution`, `Decision`, `Conflict`, or `VerificationReport`. Phase 2 defines reasonable enum values for these in `tasklexa_api/domain/enums.py` so the columns can be typed rather than left as free text.

Rationale: Untyped status columns would let invalid values reach PostgreSQL silently. A typed placeholder, clearly flagged as inferred, is safer than no constraint and cheaper to revise than a text column once real transition rules exist.

Consequence: These specific enum values are not authoritative. Phase 3 (Mission API and state machine) and Phase 8 (Mission Orchestrator) must review and, if needed, migrate them once actual state-transition rules are designed. Treat them as a placeholder, not a locked contract.

## ADR-009: Execution Events Are Immutable at the Database Level

Decision: `execution_events` has a Postgres trigger that raises on any `UPDATE` or `DELETE`, including cascade deletes triggered by removing a parent `Mission` row.

Rationale: ADR-002 requires immutable execution events for audit purposes. Enforcing this only in application code (e.g., no update method) is not sufficient — a future direct SQL fix, admin script, or ORM misuse could silently violate it. A database-level constraint makes the guarantee unconditional.

Consequence: A `Mission` that has any recorded `ExecutionEvent` can never be hard-deleted; it must be moved to `MissionStatus.CANCELLED` instead. No API for hard-deleting missions should be built.

## ADR-010: Mission State Machine Is a Provisional, Total Transition Map

Decision: `docs/domain-model.md` lists `MissionStatus` values but not the allowed transitions between them. Phase 3 defines one explicit map (`tasklexa_api.domain.state_machine.MISSION_TRANSITIONS`) covering every status, including the three terminal states (`COMPLETED`, `FAILED`, `CANCELLED`), which allow no further transitions.

Rationale: "Enforce deterministic transitions" (Phase 3 scope, `docs/architecture.md`) requires *some* map to exist and be enforced now, even though the real transition triggers depend on components that don't exist yet (planner, orchestrator, approval gates).

Consequence: Treat this map as provisional. Phase 8 (Mission Orchestrator) is the actual authority on real transition triggers and may need to revise it — for example, an automatic `RUNNING → WAITING_APPROVAL` transition triggered by a gated `Decision`, rather than only a client-initiated `POST /missions/{id}/transitions` call.

## ADR-011: `MISSION_STATUS_CHANGED` Added as a Generic Execution Event

Decision: Added `ExecutionEventType.MISSION_STATUS_CHANGED` for the Phase 3 transition endpoint, rather than reusing `MISSION_PLANNED` or `MISSION_COMPLETED` from the existing list.

Rationale: `docs/domain-model.md`'s `ExecutionEvent` type list is headed "Examples," not a closed enumeration, so extending it is within scope. `MISSION_PLANNED` and `MISSION_COMPLETED` specifically imply a real plan was produced or verification actually passed — Phase 3 does neither; it only flips a status field. Reusing those names would make the audit log claim something happened that didn't.

Consequence: Phase 4/5 (planner) should emit `MISSION_PLANNED` when a validated `MissionPlan` is actually produced, and Phase 8/verification should emit `MISSION_COMPLETED` when verification actually passes — both in addition to, not instead of, the generic `MISSION_STATUS_CHANGED` a status-field update always produces. Adding a Postgres enum value requires an `ALTER TYPE ... ADD VALUE` migration; downgrading past it is not supported (Postgres cannot remove an enum value cleanly), so the migration's `downgrade()` raises rather than silently no-op.
