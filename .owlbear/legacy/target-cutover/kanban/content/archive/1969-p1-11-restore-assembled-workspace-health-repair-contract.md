---
id: 1969
title: 'P1-11: Restore assembled workspace-health repair contract'
status: archived
priority: high
created: 2026-07-21T10:56:32.901575+02:00
updated: 2026-07-21T11:07:51.190892+02:00
tags:
  - phase-1
  - scope:cockpit-backend
  - api
  - health
  - corrective
parent: 1945
depends_on:
  - 1942
ac:
  - 'AC-1: Given task health with two repairable findings and zero non-repairable
    findings, GET /health and GET /health/tasks return task status `attention`, `repairable_count`
    2, and both findings; given those two findings plus one non-repairable finding,
    both endpoints return `unhealthy`, `repairable_count` 2, and three findings.'
  - 'AC-2: Given an assembled FastAPI app backed by a real KanbanEngine board with
    deterministic task-repair candidates, POST /health/tasks/repair uses the deterministic
    repair boundary and returns `status=completed`, started/completed timestamps,
    removed/moved/quarantined/skipped/failed/unresolved counts, terminal outcomes,
    unresolved findings, and post-repair task health after repair without invoking
    the legacy generic repair workflow.'
  - 'AC-3: Given deterministic task repair raises before a trustworthy post-scan,
    POST /health/tasks/repair returns a non-2xx error without a completed receipt
    or refreshed task-health fields.'
proof_bundle: critical
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Outcome
Restore the accepted Cockpit workspace-health HTTP contract that #1944 requires: module repairability and severity survive projection, and production task repair uses the existing deterministic repair owner with a complete synchronous receipt.

## Scope
In scope: the Cockpit health response model, module-health projection/status mapping, production `/health/tasks/repair` delegation, and assembled FastAPI contract proof. Out of scope: Kanban repair-algorithm changes, frontend rendering, generic Cleanup compatibility, new aliases, and unrelated corruption-module formatting.

## Planning Authority
OpenSpec change `redesign-workspace-health`, especially Evidence-based status states, Module-aware status presentation, Synchronous convergent repair contract, and Design sections 6-7. This is corrective delivery of #1942's accepted contract after fixture-only proof allowed an incomplete production boundary to archive.

## Change Module Map
- `serve/cockpit/src/owlbear_cockpit/models.py`: public health-module response envelope; expose repairable count.
- `serve/cockpit/src/owlbear_cockpit/main.py`: assembled module status projection and deterministic repair delegation.
- `tests/test_cockpit_health_contract.py`: assembled FastAPI and real-engine regression proof.
- `owlbear_kanban.corruption.repair_task_storage`: existing deterministic domain owner, reused without modification.

## Product Invariant Map
- Repairable-only task findings remain actionable attention at the real HTTP boundary.
- Mixed repairable and unresolved task findings remain unhealthy while preserving repair availability evidence.
- The production repair endpoint returns deterministic terminal/post-scan evidence and never falls back to the legacy generic repair workflow.

Proof guidance: run `uv run pytest tests/test_cockpit_health_contract.py -q` plus focused Ruff checks. Keep the real-engine assembled repair case durable because fixture-only proof previously false-archived this public contract.

[[2026-07-21T11:03:30+02:00]]
## Builder Notes

Change envelope: restore only the assembled Cockpit health-module projection and deterministic task-repair HTTP contract required by #1944. No Kanban repair algorithm, frontend, compatibility alias, generic Cleanup, or unrelated corruption formatting changed.

Files changed:
- `serve/cockpit/src/owlbear_cockpit/models.py`
- `serve/cockpit/src/owlbear_cockpit/main.py`
- `tests/test_cockpit_health_contract.py`

Implementation:
- `HealthModule` now exposes `repairable_count` with a stable zero default.
- `_module_health()` preserves repairability evidence, maps repairable-only findings to `attention`, and maps mixed/non-repairable findings to `unhealthy`; aggregate health now preserves `attention` when no red module exists.
- `POST /health/tasks/repair` directly invokes `repair_task_storage(engine.kanban_dir, engine.board_config())`. The legacy `KanbanEngine.repair_storage()` fallback and its compatibility conversion code are removed.
- The assembled contract suite covers repairable-only and mixed module responses through both aggregate and focused endpoints, a real `KanbanEngine` archive-drift repair with the legacy method set to fail if invoked, complete receipt fields and post-scan state, and failure responses without completion or refreshed-health fields.

Change Module Map deviations: none. The existing deterministic Kanban repair owner is reused without modification; unrelated dirty `serve/kanban/src/owlbear_kanban/corruption.py` changes remain outside this task.

Proof:
- `uv run pytest tests/test_cockpit_health_contract.py -q`: 6 passed with 4 existing Starlette/httpx deprecation warnings.
- `uv run pytest tests/test_cockpit_health_contract.py tests/test_cockpit_routes.py tests/test_cockpit_launch.py -q`: 35 passed with the same warnings.
- Focused Ruff check passed; Ruff format check reports all three owned files formatted.
- VS Code diagnostics and scoped `git diff --check` are clean.

Durable-test justification: the real-engine assembled regression protects a public shared repair boundary that previously false-archived after fixture-only proof. It fails if production reverts to the legacy generic repair workflow or drops receipt/post-scan evidence.

Builder-challenger: PASS with fresh focused pytest and Ruff reruns; no blocker, scope drift, or auto-fix.

Follow-up risks: none within the corrective contract. #1944 remains the frontend consumer and is intentionally blocked until verifier closure.

[[2026-07-21T11:06:46+02:00]]
## Verify Notes

Verified delivered commit `5f711cabec6870f413834c924bcca44ce809b562` from a detached disposable checkout. No verifier patch was applied.

Evidence and authority:
- Compared the implementation and fixtures with OpenSpec `redesign-workspace-health`: repairable-only task findings are attention; mixed repairable and unresolved findings remain unhealthy while repairability survives; synchronous deterministic repair returns terminal timing/count/outcome/unresolved/post-health evidence.
- Exact commit scope is the task record plus `models.py`, `main.py`, and `test_cockpit_health_contract.py`. No Kanban repair algorithm, frontend, compatibility, Cleanup, or unrelated corruption change is included.
- Exact source inspection confirms `HealthModule.repairable_count`, repairability/status projection, aggregate attention propagation, direct `repair_task_storage(engine.kanban_dir, engine.board_config())`, and no legacy `repair_storage` fallback.

Normal-path proof:
- At the exact SHA, `uv run pytest tests/test_cockpit_health_contract.py tests/test_cockpit_routes.py -q` passed 14 tests with 4 existing Starlette/httpx deprecation warnings.
- AC-1 is exercised through assembled FastAPI aggregate and focused GET boundaries for two repairable findings and for those findings plus one unresolved finding.
- AC-2 uses a real `KanbanEngine` archive-drift board through the assembled POST endpoint, makes legacy `repair_storage` fail if called, asserts timestamps, all six terminal counts, moved outcome, empty unresolved findings, clean post-repair health, and the real filesystem move.
- AC-3 forces deterministic repair failure and asserts HTTP 500 without `status`, `completed_at`, or `task_health_result`.
- Exact-SHA Ruff check passed; format check reports all three owned files formatted. VS Code diagnostics are clean. Pending and resolved request scans are empty.

Neighbor check classification:
- An initial exact-checkout run including `tests/test_cockpit_launch.py` produced 13 launch failures and 22 passes because the disposable checkout lacks gitignored `serve/cockpit/dist/`. Every launch failure exited at the unchanged missing-dist precondition before server startup. The task-owned HTTP contract and route suites do not require that build artifact; the same broader slice passed 35 tests in the working tree where `dist/` exists.

Change Module Map deviations: none. Lower-layer deterministic repair is the real existing domain owner and was not replaced.

Verifier-challenger: PASS. It found AC-1 through AC-3 covered at the assembled HTTP boundary, accepted the real-engine durable regression and missing-dist classification, and found no scope or proof defect.

Final route: PASS to collect.

[[2026-07-21T11:07:51+02:00]]
## Collect Notes

Classification: leaf corrective task. It has no children and one bounded Cockpit backend contract outcome under parent #1945.

Leaf verification evidence: latest Verify Notes record PASS and verifier-challenger PASS at exact delivered commit `5f711cabec6870f413834c924bcca44ce809b562`. The detached-checkout proof passed 14 assembled health/route tests plus focused Ruff checks, exercised a real `KanbanEngine` deterministic repair through FastAPI, and confirmed no legacy repair fallback.

Closure state: dependency #1942 is completed and `dep_status` is `ok`; no pending structured request, block, or unresolved Required Follow-up exists. The missing-dist launch-test prerequisite is explicitly classified as unrelated environment context and does not weaken the task-owned HTTP proof.

Archive rationale: AC-1 through AC-3 and the corrective contract are verifier-closed. Archive as completed so dependent frontend task #1944 can resume against the delivered boundary.
