# Domain Model

Status: Phase 0 architecture.

## Core Flow

```text
GOAL -> MISSION -> TASKS -> CAPABILITIES -> AGENTS -> MODELS -> TOOLS
-> EVIDENCE -> DECISIONS -> APPROVAL -> ACTION -> VERIFICATION -> OUTCOME
```

## Mission

Purpose: authoritative container for the user's objective and execution state.

Fields:

- `id`
- `title`
- `objective`
- `description`
- `status`
- `constraints`
- `success_criteria`
- `created_by`
- `created_at`
- `started_at`
- `completed_at`

Statuses:

- `DRAFT`
- `PLANNING`
- `ASSEMBLING`
- `RUNNING`
- `WAITING_APPROVAL`
- `VERIFYING`
- `COMPLETED`
- `FAILED`
- `CANCELLED`

## Task

Purpose: executable unit in a mission dependency graph.

Fields:

- `id`
- `mission_id`
- `title`
- `description`
- `status`
- `priority`
- `required_capabilities`
- `dependencies`
- `assigned_agent`
- `tool_requirements`
- `expected_output`
- `actual_output`
- `confidence`
- `created_at`
- `completed_at`

## AgentDefinition

Purpose: reusable description of an agent capability.

Fields:

- `id`
- `name`
- `description`
- `capabilities`
- `allowed_tools`
- `preferred_model_policy`
- `permissions`
- `risk_level`
- `provider`
- `status`

## AgentExecution

Purpose: record of one reusable agent participating in one mission or task.

Fields:

- `id`
- `mission_id`
- `agent_definition_id`
- `task_id`
- `status`
- `model_used`
- `started_at`
- `completed_at`
- `token_usage`
- `estimated_cost`
- `output`
- `confidence`

## Capability

Purpose: sector-agnostic ability used for planning, agent matching, and tool matching.

Initial generic capabilities:

- `research`
- `analysis`
- `planning`
- `technical_analysis`
- `verification`
- `external_intelligence`
- `digital_market_intelligence`
- `website_analysis`
- `competitive_intelligence`
- `summarization`
- `risk_analysis`

Rule: core orchestration must not encode sector-specific capability names unless they are optional tool metadata.

## ToolDefinition

Purpose: metadata for capability-to-tool discovery.

Fields:

- `id`
- `name`
- `description`
- `provider`
- `capabilities`
- `authentication_type`
- `risk_level`
- `requires_approval`
- `status`

Statuses:

- `AVAILABLE`
- `NOT_CONFIGURED`
- `DISABLED`
- `FAILED`

## Evidence

Purpose: supportable record used by agents and decisions.

Fields:

- `id`
- `mission_id`
- `task_id`
- `agent_execution_id`
- `source`
- `source_type`
- `content`
- `confidence`
- `created_at`

Evidence rules:

- Evidence must identify source and provenance.
- Demo evidence must include `demo=true` metadata and must be displayed as `DEMO DATA`.
- Evidence from failed or unverified live calls must not be marked live.

## Decision

Purpose: recommendation or choice point backed by evidence.

Fields:

- `id`
- `mission_id`
- `title`
- `description`
- `options`
- `recommendation`
- `evidence_ids`
- `confidence`
- `risk_level`
- `approval_required`
- `status`

## Approval

Purpose: human-in-the-loop control for gated decisions.

Fields:

- `id`
- `mission_id`
- `decision_id`
- `requested_by`
- `reason`
- `status`
- `approved_by`
- `approved_at`
- `comments`

Statuses:

- `PENDING`
- `APPROVED`
- `REJECTED`
- `MODIFIED`

Rules:

- `PENDING` approvals pause mission execution for the relevant action.
- No action gated by approval may execute before approval or modification is recorded.
- Approval decisions emit immutable events.

## Conflict

Purpose: preserve agent disagreements rather than hiding them.

Fields:

- `id`
- `mission_id`
- `decision_id`
- `detected_by`
- `summary`
- `original_recommendations`
- `conflicting_evidence_ids`
- `resolution`
- `status`
- `created_at`
- `resolved_at`

## VerificationReport

Purpose: independent final check before mission completion.

Fields:

- `id`
- `mission_id`
- `verification_status`
- `criteria_results`
- `issues`
- `confidence`
- `created_at`

Rules:

- A mission can become `COMPLETED` only after verification passes.
- Verification must inspect objective, success criteria, task outputs, evidence, decisions, actions, failures, contradictions, and constraints.

## ExecutionEvent

Purpose: immutable audit trail for meaningful actions.

Examples:

- `MISSION_CREATED`
- `MISSION_PLANNED`
- `AGENT_SELECTED`
- `AGENT_STARTED`
- `AGENT_MESSAGE`
- `TOOL_SELECTED`
- `TOOL_CALLED`
- `TOOL_RESULT`
- `EVIDENCE_CREATED`
- `DECISION_CREATED`
- `APPROVAL_REQUESTED`
- `APPROVAL_GRANTED`
- `APPROVAL_REJECTED`
- `TASK_FAILED`
- `TASK_REPLANNED`
- `VERIFICATION_STARTED`
- `MISSION_COMPLETED`

Required event metadata:

- `mission_id`
- `task_id` when applicable
- `agent_execution_id` when applicable
- `correlation_id`
- `provider` when an external provider is involved
- `status`
- `error_category` when failed

## MissionPlan

Purpose: validated planner output; never free-form executable workflow state.

Fields:

- `objective`
- `constraints`
- `success_criteria`
- `required_capabilities`
- `tasks`
- `dependencies`
- `risk_level`
- `approval_points`

Rules:

- Pydantic validation is mandatory.
- Invalid planner output is retried within a bounded limit.
- Persistent failure results in safe planning failure.

## AgentTeamPlan

Purpose: deterministic output of capability resolution.

Fields:

- `mission_id`
- `required_capabilities`
- `selected_agents`
- `selected_tools`
- `unresolved_capabilities`
- `risk_notes`

Rules:

- Agents are selected by capabilities, permissions, and status.
- Tools are selected by capabilities, authentication, risk, and policy.
- Missing required capabilities block assembly unless policy permits degraded execution.

## Graph Projection

PostgreSQL is authoritative. Neo4j receives an idempotent projection with these relationships:

- `(Mission)-[:REQUIRES]->(Capability)`
- `(Mission)-[:CONTAINS]->(Task)`
- `(Task)-[:DEPENDS_ON]->(Task)`
- `(Task)-[:ASSIGNED_TO]->(Agent)`
- `(Agent)-[:HAS_CAPABILITY]->(Capability)`
- `(Agent)-[:CAN_USE]->(Tool)`
- `(Agent)-[:PRODUCED]->(Evidence)`
- `(Evidence)-[:SUPPORTS]->(Decision)`
- `(Decision)-[:REQUIRES_APPROVAL]->(Approval)`
- `(Decision)-[:PRODUCES]->(Action)`
- `(Action)-[:PRODUCES]->(Outcome)`
