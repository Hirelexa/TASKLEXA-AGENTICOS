# Phase 10 Report

Status: complete. Approval blocking and resume commands implemented — but the more consequential outcome of this phase was discovering and fixing a real bug in Phase 3's mission state machine, found while implementing the `WAITING_APPROVAL` transitions this phase actually needs.

## A Correction Found Before the New Work: the Mission State Machine Was Wrong

`docs/architecture.md` contains a "Mission State Machine" section (its own mermaid `stateDiagram-v2`, present since the document was first written) that is the actual authoritative transition map. Phase 3 never found it — its research didn't read that far into the document — and built a plausible-looking map instead, explicitly flagged as "provisional" in ADR-010. Re-reading that section closely while implementing this phase's `WAITING_APPROVAL` edges surfaced three real divergences:

1. `DRAFT`, `PLANNING`, `ASSEMBLING`, and `VERIFYING` each had an extra `→ CANCELLED` edge that isn't in the diagram. The diagram reaches `CANCELLED` **only** via `WAITING_APPROVAL` rejection.
2. `WAITING_APPROVAL → FAILED` existed in the old map but isn't drawn — rejection has exactly one destination (`CANCELLED`), not a choice of two.
3. `RUNNING → PLANNING` ("bounded_replan_requested") was completely missing.

Fixed in `domain/state_machine.py`, and — since this exact kind of silent divergence had already happened once without anything catching it — `apps/api/tests/test_mission_state_machine.py` now pins every edge in the diagram against `MISSION_TRANSITIONS` directly (`test_no_undocumented_edges_exist` asserts the two sets are exactly equal, not just that known-good edges validate). See ADR-021, which supersedes ADR-010.

One consequence worth naming plainly: **`CANCELLED` is now reachable only by rejecting an approval.** There is no direct cancel path from `DRAFT`, `PLANNING`, `ASSEMBLING`, `RUNNING`, or `VERIFYING` in the documented diagram. This might be a real gap in the diagram itself — but implementing what the docs actually specify, and flagging the apparent gap rather than quietly patching around it, is the more honest choice.

## Deliverables

- **Approval blocking**: `run_dispatch_cycle()` now checks mission status first and raises the new `MissionPausedError` (→ HTTP 409) if the mission is `WAITING_APPROVAL`, directly enforcing `docs/domain-model.md`'s rule: *"PENDING approvals pause mission execution for the relevant action... No action gated by approval may execute before approval or modification is recorded."* This also happens to close half of a Known Limitation flagged in `docs/phase-8.md` ("dispatch does not check mission status") — for this one specific status, not in general.
- **Resume commands**: `POST /missions/{id}/approvals/{id}/approve` and `.../modify` both resolve the approval and transition the mission `WAITING_APPROVAL → RUNNING` — these *are* the "resume commands" Phase 10 asks for, matching the diagram's own combined trigger name `approval_approved_or_modified`. `.../reject` transitions to `CANCELLED` instead (`approval_rejected_terminal` — terminal, no resume).
- `repositories/decisions.create_decision()`: the first place in this codebase that creates a `Decision` row through a normal API call (previously read-only, per Phase 6's known limitations). When `approval_required=true`, it also creates the `PENDING` `Approval` row and drives the mission's `RUNNING → WAITING_APPROVAL` transition — all in one atomic commit (`DECISION_CREATED` and `APPROVAL_REQUESTED` events included). If the mission isn't `RUNNING`, the transition itself rejects with `InvalidMissionTransitionError` (409) — decision creation doesn't invent its own policy for "what if the mission isn't running"; the state machine already is that policy.
- `repositories/approvals.py`: `approve_approval()`, `modify_approval()`, `reject_approval()` — each validates the approval is still `PENDING` (409 `InvalidApprovalTransitionError` otherwise, so an approval can't be resolved twice), records `approved_by`/`approved_at`/`comments`, emits `APPROVAL_GRANTED` (approve or modify) or `APPROVAL_REJECTED`, and drives the corresponding mission transition.
- New API: `POST`/`GET /missions/{id}/decisions`, `GET /missions/{id}/decisions/{id}`, `GET /missions/{id}/approvals`, `GET /missions/{id}/approvals/{id}`, plus the three resolve endpoints.
- `apps/api/tests/test_mission_state_machine.py`: 9 pure tests, described above — this is genuinely load-bearing regression protection now, not just coverage padding.
- `tests/integration/test_human_approval.py`: two live tests. One drives the full happy path — dispatch works while `RUNNING`, a decision with `approval_required=true` correctly moves the mission to `WAITING_APPROVAL`, dispatch is rejected with 409 while paused, *creating a second gated decision while paused is also correctly rejected* (since that transition requires `RUNNING`, which the mission no longer is), approving resumes the mission and dispatch works again, and re-approving an already-resolved approval correctly 409s. The other proves rejection is genuinely terminal: the mission moves to `CANCELLED`, dispatch still runs (empty) since dispatch only guards `WAITING_APPROVAL` specifically, and no transition back to `RUNNING` is possible from `CANCELLED`.

## Design Notes

**Decision creation doubles as the `WAITING_APPROVAL` trigger, not a separate "request approval" endpoint.** The diagram's trigger name is literally `approval_required` on the `RUNNING → WAITING_APPROVAL` edge — and `Decision.approval_required` is already a field from Phase 2. Treating "create a decision with `approval_required=true`" as *the* thing that fires this edge is a direct reading of the existing schema, not new design.

**Approve and modify are deliberately the same resume path**, differing only in the `Approval.status` value they write (`APPROVED` vs `MODIFIED`) and reusing the same `APPROVAL_GRANTED` event type for both — matching the diagram's own combined trigger `approval_approved_or_modified`, which doesn't distinguish the two at the mission-transition level. The `Approval` row itself is where the APPROVED-vs-MODIFIED distinction actually lives.

## Verification Status

- 9 state-machine unit tests: passing, including the specific regression test for the bug found this phase (`test_rejecting_an_approval_is_terminal_not_a_return_to_running`).
- Full mocked suite (97 tests): passing, no regressions from the state-machine correction — nothing in the existing test suite exercised any of the three removed-but-wrong edges.
- Live approval lifecycle test: passing against the actual running containers — dispatch blocking, decision-creation-while-paused rejection, resume via approve, double-resolve rejection, and the full event trail all verified through real HTTP and real Postgres.
- Live rejection-is-terminal test: passing — `CANCELLED` confirmed unreachable-from via any resume transition.
- Fresh-volume verification: all containers `healthy` (no new PostgreSQL migration this phase — pure application logic).
- Full combined regression — every mocked test file and every live integration test file across all ten phases, run together in one process: all passing.
- `alembic check`: no drift.
- `python -m compileall` across all new/changed modules: passed.

## Known Limitations

- Dispatch's mission-status guard covers only `WAITING_APPROVAL` specifically — it still doesn't check for `RUNNING` in general (Phase 8's broader known limitation stands; a `CANCELLED` or `DRAFT` mission can still have `dispatch` called on it harmlessly, since there's nothing to dispatch).
- No endpoint exists to list *all* pending approvals across every mission (an operator dashboard's likely first query) — approvals are only listable per-mission (`GET /missions/{id}/approvals`). Scoped this way because nothing in this codebase yet has an operator-facing view to serve; Phase 12 (Mission Control UI) is the more natural place to decide what a cross-mission approval queue actually needs to return.
- `Conflict` (preserving agent disagreements) still has no create/lifecycle API — domain-model.md defines it, Phase 2 persisted it, but nothing in Phases 3–10 has needed to create one yet.
