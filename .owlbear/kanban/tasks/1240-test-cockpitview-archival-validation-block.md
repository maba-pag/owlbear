---
id: 1240
title: 'Test: CockpitView archival validation block'
status: review
priority: needed
created: 2026-05-01T03:07:52.852822+00:00
updated: 2026-05-01T04:04:03.646358+00:00
tags:
- scope:backend
parent: 1238
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Acceptance Criteria

- `CockpitView.move_task` with `status="archived"` and `archival_reason=None` raises `ERR_ARCHIVAL_REASON_REQUIRED` (422)
- `CockpitView.move_task` with `reason="completed"` and non-empty `archival_refs` raises `ERR_ARCHIVAL_REFS_FORBIDDEN`
- `CockpitView.move_task` with `reason="dropped"` and non-empty refs raises `ERR_ARCHIVAL_REFS_FORBIDDEN`
- `CockpitView.move_task` with `reason="wontfix"` and non-empty refs raises `ERR_ARCHIVAL_REFS_FORBIDDEN`
- `CockpitView.move_task` with `reason="deprecated"` and empty refs raises `ERR_ARCHIVAL_REFS_REQUIRED`
- `CockpitView.move_task` with `reason="duplicate"` and empty refs raises `ERR_ARCHIVAL_REFS_REQUIRED`
- `CockpitView.move_task` with `reason="completed"` when `task.status != "done"` raises `ERR_COMPLETED_REQUIRES_DONE`
- `CockpitView.move_task` raises a 422 error when any ref ID does not exist on the board
- `CockpitView.move_task` raises a 422 error when `archival_refs` contains the task's own ID (self-reference)
- `CockpitView.move_task` raises a 422 error when `archival_refs` creates a dependency cycle
- Valid archival (e.g., `reason="completed"`, task `status == "done"`, empty refs) succeeds and persists both fields

## In Scope

- All validation paths in `CockpitView.move_task` for the `status == "archived"` case

## Out of Scope

- Non-archival moves (plain status changes)
- `MoveRequest`/route layer (B1+B2 task #1239)

## Brief reference

Brief: `.owlbear/briefs/draft-archival-ux/brief.md` — Backend Changes B3
[[2026-05-01]]
## Test-Writer Notes
- Test file: tests/test_cockpit_view_1240.py
- Classes: TestFromAC_CockpitViewArchivalValidation
- Tests per category:
  - Error paths (validation rejects invalid input): 10
  - Happy path (AC11): SKIPPED — engine pass-through already satisfies valid archival; no RED test possible per w-tdd-red §5
- Total: 10 tests, all FAIL (DID NOT RAISE ValidationError)
- Lint: clean (ruff exit 0)

### AC coverage table

| AC line | Test method |
|---|---|
| AC1: reason=None → ERR_ARCHIVAL_REASON_REQUIRED | test_archive_without_reason_raises_archival_reason_required |
| AC2: completed + refs → ERR_ARCHIVAL_REFS_FORBIDDEN | test_archive_completed_with_refs_raises_archival_refs_forbidden |
| AC3: dropped + refs → ERR_ARCHIVAL_REFS_FORBIDDEN | test_archive_dropped_with_refs_raises_archival_refs_forbidden |
| AC4: wontfix + refs → ERR_ARCHIVAL_REFS_FORBIDDEN | test_archive_wontfix_with_refs_raises_archival_refs_forbidden |
| AC5: deprecated + empty refs → ERR_ARCHIVAL_REFS_REQUIRED | test_archive_deprecated_without_refs_raises_archival_refs_required |
| AC6: duplicate + empty refs → ERR_ARCHIVAL_REFS_REQUIRED | test_archive_duplicate_without_refs_raises_archival_refs_required |
| AC7: completed + task.status != done → ERR_COMPLETED_REQUIRES_DONE | test_archive_completed_from_non_done_status_raises_completed_requires_done |
| AC8: non-existent ref → ERR_ARCHIVAL_REF_MISSING | test_archive_with_nonexistent_ref_raises_archival_ref_missing |
| AC9: self-reference → ERR_ARCHIVAL_REF_SELF | test_archive_with_self_ref_raises_archival_ref_self |
| AC10: cycle → ERR_ARCHIVAL_REF_CYCLE | test_archive_with_cyclic_refs_raises_archival_ref_cycle |
| AC11: valid archival persists fields | SKIPPED — passes at RED (engine already handles) |

### Failure reason
All 10 tests fail with "DID NOT RAISE ValidationError" — CockpitView.move_task currently delegates directly to KanbanEngine.move_task with no validation block. The engine stores archival_reason/archival_refs unconditionally without any reason/refs/cycle checks.
[[2026-05-01]]
## Builder Notes
- Implementation: Added archival validation block in `serve/cockpit/src/owlbear_cockpit/view.py` for `CockpitView.move_task` when `status == "archived"`.
- Validation enforced: `ERR_ARCHIVAL_REASON_REQUIRED`, `ERR_ARCHIVAL_REASON_INVALID`, `ERR_ARCHIVAL_REFS_REQUIRED`, `ERR_ARCHIVAL_REFS_FORBIDDEN`, `ERR_COMPLETED_REQUIRES_DONE`, `ERR_ARCHIVAL_REF_MISSING`, `ERR_ARCHIVAL_REF_SELF`, `ERR_ARCHIVAL_REF_CYCLE`.
- Approach: Performed pre-validation in cockpit view before delegating to engine move, reusing same rule set as engine AgentView behavior while keeping OCC delegation unchanged.
- Files changed: `serve/cockpit/src/owlbear_cockpit/view.py`.
- Tests: `tests/test_cockpit_view_1240.py` -> 10 passed, 0 failed.
- Lint: ruff clean on touched source + task test file.
- Coverage: quality-runner reports `owlbear_cockpit` not tracked by current coverage source package config in scoped mode.
- Commit: `0f890cc5` (`feat: add cockpit archival validation block (#1240, builder)`).

## Post-task Reflection
- Private helper access (`engine.agent_view()._validate_move_archival_for_archive`) triggered `SLF001`; cockpit view now uses local equivalent helper methods.
- Canonical archival validation parity was preserved by mirroring engine rule order and error codes.
- Cycle detection and ref-existence checks were implemented using public `show_task` reads to avoid private API coupling.
- Coverage instrumentation for cockpit module is still not configured for module-level percentages in current scoped quality-runner output.
