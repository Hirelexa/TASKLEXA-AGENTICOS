# Phase 11 Report

Status: complete. An independent, deterministic Verifier evaluates a mission against `docs/domain-model.md`'s inspection rules and gates `COMPLETED` behind an actual pass — matching `docs/architecture.md`'s MVP acceptance criteria 15–16 ("See independent verification" / "See completed missions only after verification passes").

## Deliverables

- `tasklexa_api.domain.verification.evaluate_verification()`: a pure function (no DB, no I/O) — the same pattern as the Capability Resolver (Phase 5) and task readiness (Phase 8). Takes already-fetched summaries (task list, evidence count, unresolved-conflict count, pending-approval count, decision count, mission success criteria) and returns a `VerificationEvaluation` (status, per-criterion results, issues, confidence). Inspects every category `docs/domain-model.md` names except "actions" (no persisted entity anywhere — [[ADR-015]]) and produces a real, if usually-empty, check for "contradictions" (`Conflict`, never populated by anything yet, but genuinely inspected rather than skipped).
- `tasklexa_api.repositories.verification.run_verification()`: the thin DB-fetching wrapper — gathers tasks/evidence/decisions/conflicts/approvals, calls the pure evaluator, persists a `VerificationReport`, emits `VERIFICATION_STARTED` (already an event type since Phase 2 — no new enum value needed this time), and applies the mission-completing side effect only when it's actually earned.
- Deterministic status logic, not a fabricated "AI judgment": `FAILED` if any hard criterion fails (unsettled tasks, any `FAILED` task, unresolved conflicts, pending approvals); `PASSED` if all hard criteria pass and there's nothing soft to flag; `PARTIAL` if hard criteria pass but the mission declared `success_criteria` with zero `Evidence` recorded to substantiate it — a real, distinct trigger condition for the third status value, not dead code. This exact rule set is an inference, not a spec value — see [[ADR-022]].
- The state-machine mapping this phase's `COMPLETED`/`FAILED`/`PARTIAL` results actually apply: `PASSED → VERIFYING→COMPLETED`, `FAILED → VERIFYING→FAILED`, `PARTIAL → no transition` (stays `VERIFYING` — the diagram has no third edge, so `PARTIAL` deliberately leaves the mission where a caller can re-verify after doing something about it). Running verification outside `VERIFYING` still produces a real report; it just never carries a mission-level side effect, the same permissive-diagnostic design as Phase 6's `project_mission()`.
- New API: `POST /missions/{id}/verify`, `GET /missions/{id}/verification-reports`, `GET /missions/{id}/verification-reports/{report_id}`.
- `apps/api/tests/test_verification_evaluation.py`: 10 pure unit tests covering every status outcome, including the specific `PARTIAL` trigger and confirming the `decisions_reviewed` informational criterion only appears when there are decisions to review.
- `tests/integration/test_verifier.py`: three live tests against the actual running containers — a full `PASSED` lifecycle ending in `COMPLETED`, a `FAILED` lifecycle from a genuinely failed task, and a `PARTIAL` lifecycle proving the mission stays in `VERIFYING` (and that calling `/verify` again is safe and produces a second report).

## A Finding From Writing the Live Test, Not the Implementation

The first draft of the live test created tasks with no `required_capabilities` at all. Every one of them silently stayed `PENDING` forever — `resolve_team()` (Phase 5) only ever populates `selected_agents` by iterating `required_capabilities`; an empty list means that loop body never runs, so a task with no stated capability requirement can never be matched to any agent, no matter how many dispatch cycles run. This isn't a bug in the resolver — a task that doesn't say what skill it needs genuinely can't be assigned by a system that assigns purely on capability match — but it's worth naming as a real, mildly surprising behavior rather than letting it hide as "eventually consistent." Fixed by giving every task in the test a real `required_capabilities` entry, matching how every other phase's tests already do it. Nothing in the implementation changed; this is purely a note for whoever builds the Mission Compiler that will someday generate real `Task` rows and needs to always populate this field.

## Verification Status

- 10 pure evaluation unit tests: passing, zero DB dependency.
- Live `PASSED` test: passing — full dispatch→complete→dispatch (auto-transition to `VERIFYING`)→verify→`COMPLETED` cycle, plus report listing/fetching and a `VERIFICATION_STARTED` event check.
- Live `FAILED` test: passing — one completed task, one explicitly failed task, verification correctly reports `FAILED` and the mission moves to `FAILED`.
- Live `PARTIAL` test: passing — a mission with `success_criteria` set and zero evidence stays in `VERIFYING` after two separate `/verify` calls, each producing its own report.
- Fresh-volume verification: all containers `healthy` (no new PostgreSQL migration this phase — pure application logic, like Phase 10).
- Full combined regression — every mocked test file and every live integration test file across all eleven phases, run together in one process: all passing (107 mocked + 13 live).
- `alembic check`: no drift.
- `python -m compileall` across all new/changed modules: passed.

## Known Limitations

- `Conflict` inspection (`no_unresolved_conflicts`) is real code, but nothing in this codebase creates a `Conflict` row yet (unchanged from Phase 10's known limitation) — the criterion always passes today because there is never anything to find, not because it's stubbed out.
- No caller re-runs verification automatically after a `PARTIAL` result and some new evidence gets recorded — a human or future orchestrator logic has to call `/verify` again explicitly.
- `has_evidence`/`decisions_reviewed` are informational criteria (visible in `criteria_results`, never block a `PASSED` outcome by themselves) except in the one specific combination that produces `PARTIAL`. This is a deliberately small, legible rule set rather than a scoring system with tunable weights — the kind of thing a real Verifier Agent (an LLM-backed judgment call, which doesn't exist anywhere in this codebase — there's still no Agent Runtime) would eventually need to replace or extend, not this phase's job to anticipate.
