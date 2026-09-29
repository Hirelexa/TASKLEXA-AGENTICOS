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
