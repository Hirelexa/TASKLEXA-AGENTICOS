# Phase 12 Report

Status: complete. Mission Control now has a real, working UI over every backend capability built in Phases 2–11: a dashboard, mission creation, an 8-tab mission detail view (Overview, Tasks, Team, Decisions & Approvals, Evidence, Timeline, Verification, Graph), and an Agent/Tool registry — verified by actually driving it with a headless browser, not just `npm run build`.

## Deliverables

- `apps/web/src/lib/types.ts` / `lib/api.ts`: a typed client for every endpoint built across Phases 2–11 (missions, tasks, orchestrator dispatch, agents, tools, decisions, approvals, evidence, verification, graph). One `request()` wrapper handles error parsing (surfaces the backend's `detail` message) consistently everywhere.
- Dashboard (`/`): mission list, integration health panel (the same data Phase 1 exposed, now properly laid out), and a mission-creation form.
- Agents & Tools (`/agents`): the Phase 5 Agent Registry and Phase 9's `ToolDefinition` row, both read from the real API, plus a form to register new agents.
- Mission detail (`/missions/[id]`), one page with eight tabs, each backed by real API calls:
  - **Overview** — mission fields plus a status-transition control that lets the server's state machine (Phase 3, corrected in ADR-021) be the only authority on what's valid.
  - **Tasks** — create tasks, run the dispatch cycle (Phase 8) and see its `DispatchReport` inline, complete/fail/replan individual tasks.
  - **Team** — run the Capability Resolver (Phase 5) against arbitrary capabilities and see which seeded agents/tools it selects.
  - **Decisions & Approvals** — create a decision, optionally requiring approval (Phase 10), and approve/modify/reject it inline.
  - **Evidence** — read-only; see Known Limitations for why it needed a new backend endpoint.
  - **Timeline** — the full immutable `ExecutionEvent` audit trail (Phase 2), payloads rendered as formatted JSON.
  - **Verification** — trigger the Phase 11 Verifier and see its criteria-by-criteria breakdown.
  - **Graph** — the Phase 6 Neo4j projection, rendered with React Flow using a simple label-based column layout (no new dependency), with its own "Project / Repair" button.
- **One small necessary backend addition**: `GET /missions/{id}/evidence` and `GET /missions/{id}/evidence/{id}` didn't exist before this phase — nothing had ever needed to read `Evidence` through the API (Phase 6/9's repositories only ever read it internally, for graph projection and verification). The Evidence tab needed something to call, so a minimal read-only router was added, mirroring the same shape as every other read-only registry endpoint (Phase 9's `/tools`).

## Verification Status — Actually Driven, Not Just Built

`npm run typecheck` and `npm run build` both pass, but per this project's own standing instruction ("start the dev server and use the feature in a browser before reporting a UI change complete"), that alone doesn't prove the app renders correctly. No headless-browser tool was available in this environment by default, so:

- Playwright was installed into the **scratchpad directory**, deliberately kept out of the project's own `package.json` — it's a one-time verification tool, not a project dependency.
- The actual running `docker compose` `web` container (rebuilt with this phase's code) was driven end-to-end: dashboard load → Agents & Tools page → create a mission → walk all eight tabs (empty-state pass), then a second run → transition a mission `DRAFT→PLANNING→ASSEMBLING→RUNNING` → create a task with a real capability → run dispatch (confirmed `DISPATCHED` to `research-agent`) → project the graph (confirmed real `Mission→Task→Agent→Capability` nodes and labeled relationship edges rendered by React Flow) → create a decision requiring approval (confirmed mission moved to `WAITING_APPROVAL`) → approve it (confirmed mission resumed to `RUNNING`).
- **Zero browser console errors** across every step of both runs.
- Screenshots were inspected directly, not just checked for "didn't crash" — per the run skill's own instruction that a blank frame is a failure to launch even with no thrown error.
- One screenshot briefly appeared to show a stale pending-approval state after clicking Approve; cross-checked directly against the API (`GET /missions/{id}` showed `RUNNING`, the approval row showed `APPROVED`) and confirmed it was a screenshot-timing artifact in the verification script itself, not an application bug — documented here rather than silently discarded, consistent with this project's practice of naming findings even when they turn out not to be real.
- All test missions and their projected Neo4j nodes were cleaned up afterward; the dashboard was confirmed empty (`GET /missions` → `[]`) before finishing.

## A Real Milestone, Found Mid-Build

While this phase was in progress, a real `OPENROUTER_API_KEY` was added to the local `.env` file for the first time in this project's history. `GET /health/integrations` immediately reported OpenRouter as `LIVE` — "Authenticated call to GET /models succeeded" — and Phase 4's `test_model_gateway_live.py`, which had been skipping since it was written, ran and passed both of its tests for the first time. This is the first external provider in this entire project to be verified against its real API rather than only mocked. See the updated `docs/phase-4.md` and `docs/integration-status.md`.

## Known Limitations

- The Graph tab's layout is a simple fixed-column heuristic keyed by node label, not a real force-directed or hierarchical layout — it's legible for a handful of nodes (as verified) but wasn't tested against a large, densely-connected mission graph.
- No client-side form validation beyond HTML `required` attributes — every validation error the backend can produce (invalid transitions, already-resolved approvals, unresolvable capabilities, etc.) surfaces as the raw `detail` string from the API, not a polished inline message. This is honest and functional, not refined.
- No auth/session of any kind — matches every prior phase; `created_by`/`requested_by`/`approved_by` are free-text fields the operator types in, exactly mirroring how the backend API itself has no auth layer.
- Only OpenRouter has a real credential configured. Band and Similarweb remain `NOT_CONFIGURED` (and Similarweb will show `UNVERIFIED` rather than `LIVE` even once configured, per ADR-020) — the UI correctly displays whatever `/health/integrations` reports for each, live.
