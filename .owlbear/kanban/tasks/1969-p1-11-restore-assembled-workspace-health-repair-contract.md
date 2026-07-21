---
id: 1969
title: 'P1-11: Restore assembled workspace-health repair contract'
status: verify
priority: high
created: 2026-07-21T10:56:32.901575+02:00
updated: 2026-07-21T11:03:30.793423+02:00
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
archival_reason:
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
