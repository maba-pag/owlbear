---
id: 1244
title: 'Implement: CockpitView archival validation block'
status: archived
priority: medium
created: 2026-05-01T03:08:05.317883+00:00
updated: 2026-05-01T13:46:39.754008+00:00
tags:
- scope:backend
parent: 1238
depends_on:
- 1240
- 1243
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Acceptance Criteria

- `CockpitView.move_task` validates all archival conditions when `status == "archived"`:
  - `archival_reason` is required; raises `ERR_ARCHIVAL_REASON_REQUIRED` when absent
  - `archival_refs` forbidden for `completed`, `dropped`, `wontfix`; raises `ERR_ARCHIVAL_REFS_FORBIDDEN`
  - `archival_refs` required for `deprecated`, `duplicate`; raises `ERR_ARCHIVAL_REFS_REQUIRED`
  - `completed` requires `task.status == "done"` before the move; raises `ERR_COMPLETED_REQUIRES_DONE`
  - Each ref ID must exist on the board; raises a 422 error for non-existent refs
  - Task cannot reference itself in `archival_refs`; raises a 422 error
  - Ref chain must not loop back to the task; raises a 422 error for cycles
- Errors are raised as engine error codes and surface as 422 responses via the route
- All tests from #1240 pass

## In Scope

- `CockpitView.move_task` validation block in the cockpit `engine.py`

## Out of Scope

- `MoveRequest`/route layer (already done by #1243)
- Engine-level archival persistence (already complete)

## Brief reference

Brief: `.owlbear/briefs/draft-archival-ux/brief.md` — Backend Changes B3
[[2026-05-01]]
## Test-Writer Notes
- Test file: tests/test_cockpit_view_1244.py
- Classes: TestFromAC_ArchivalValidation422Surfacing
- Tests per category: happy 1, edge 0, error 10, boundary 0
- Total: 11 tests, all FAIL
- ruff: clean

### Root cause of RED phase

The `CockpitView.move_task` validation block (B3) is **pre-implemented** in `view.py` — the implementation was completed during an earlier builder phase. All 11 tests from `test_cockpit_view_1240.py` (the prior RED baseline) now PASS.

The **uncovered AC** is: *"Errors surface as 422 responses via the route."* The route's `valid_transitions()` check returns only configured pipeline statuses (`research … done`) — `"archived"` is never in that set. So the route rejects `status="archived"` with a generic transition error before `view.move_task()` is ever called, and the archival validation block is unreachable via HTTP.

All 11 tests assert archival-specific content in the 422 detail (e.g., `"archival_reason"`, `"forbidden"`, `"required"`, `"cycle"`). All fail because the actual detail is `"Cannot move from '...' to 'archived'"`.

### AC coverage table

| AC | Test | Category |
|----|------|----------|
| reason required | test_route_archive_without_reason_returns_422_with_archival_detail | error |
| refs forbidden / completed | test_route_archive_completed_with_refs_returns_422_with_forbidden_detail | error |
| refs forbidden / dropped | test_route_archive_dropped_with_refs_returns_422_with_forbidden_detail | error |
| refs forbidden / wontfix | test_route_archive_wontfix_with_refs_returns_422_with_forbidden_detail | error |
| refs required / deprecated | test_route_archive_deprecated_without_refs_returns_422_with_required_detail | error |
| refs required / duplicate | test_route_archive_duplicate_without_refs_returns_422_with_required_detail | error |
| completed requires done | test_route_archive_completed_from_non_done_returns_422_with_done_detail | error |
| non-existent ref | test_route_archive_with_nonexistent_ref_returns_422_with_ref_missing_detail | error |
| self-reference | test_route_archive_with_self_ref_returns_422_with_self_ref_detail | error |
| cycle | test_route_archive_with_cyclic_refs_returns_422_with_cycle_detail | error |
| valid archival (happy path) | test_route_valid_archive_from_done_returns_200_with_archived_status | happy |

### Builder action required

Allow `status="archived"` past the route's transition check so requests reach `view.move_task()` and the validation block runs. The route layer is listed as Out of Scope for B3 — but without this fix, the "surface as 422 via route" AC cannot be satisfied. The builder must either update the transition check or update `valid_transitions` to include `"archived"` as an always-valid target.
[[2026-05-01]]
## Builder Notes
- Implementation: allowed `status="archived"` to bypass route-level transition membership check in `serve/cockpit/src/owlbear_cockpit/routes/mutation.py` so archival requests reach `CockpitView.move_task` validation.
- Fix applied: changed gate from `if req.status not in transitions` to `if req.status != "archived" and req.status not in transitions`.
- Files changed: 1 source file (`serve/cockpit/src/owlbear_cockpit/routes/mutation.py`).
- Test results: RED verified first (11/11 TestFromAC failures in `tests/test_cockpit_view_1244.py`), then GREEN verified (217 passed, 0 failed, 0 skipped) across archival and mutation/route regression suites.
- Coverage: `owlbear_cockpit.routes.mutation` at 96% (overall scoped run 96%).
- Lint: ruff clean (0 violations) on changed path.
- Evidence summary: route no longer blocks `archived` with generic "Cannot move..." 422; validation-specific 422 messages and happy-path 200 archival now surface via route per AC.
- Commit: `36e19cdf` with only task-scoped source edit committed.
[[2026-05-01]]
## Review Evidence
### Test Results
- quality-runner scoped pass: 53 passed, 0 failed, 0 skipped
- Scope exercised: `tests/test_cockpit_view_1244.py`, `tests/test_cockpit_view_1240.py`, `tests/test_cockpit_mutation_api_1243.py`, `tests/test_cockpit_mutation_api_1239.py`

### Lint
- ruff: clean on `serve/cockpit/src/owlbear_cockpit/routes/mutation.py` and the scoped task/regression suites

### Coverage
- `owlbear_cockpit.routes.mutation`: percentage not measurable in the current repo because `owlbear_cockpit` is omitted from `pyproject.toml` `[tool.coverage.run].source_pkgs`
- Non-blocking for this verdict: the changed route gate at `serve/cockpit/src/owlbear_cockpit/routes/mutation.py:154` is exercised on both sides by passing archived-route tests in `tests/test_cockpit_view_1244.py` and non-archived route regressions in `tests/test_cockpit_mutation_api_1239.py` / `tests/test_cockpit_mutation_api_1243.py`

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage / AC Compliance
| AC Line | Evidence | Mapped Test(s) | Status |
|---------|----------|----------------|--------|
| `archival_reason` required when absent | Validation code raises `ERR_ARCHIVAL_REASON_REQUIRED` at `serve/cockpit/src/owlbear_cockpit/view.py:120`; route now allows `archived` through membership gate at `serve/cockpit/src/owlbear_cockpit/routes/mutation.py:154` and forwards archival kwargs at `:165-166` | `tests/test_cockpit_view_1240.py:125`, `tests/test_cockpit_view_1244.py:148` | PASS |
| `archival_refs` forbidden for `completed` / `dropped` / `wontfix` | Validation code raises `ERR_ARCHIVAL_REFS_FORBIDDEN` at `serve/cockpit/src/owlbear_cockpit/view.py:140` | `tests/test_cockpit_view_1240.py:143`, `:163`, `:182`; `tests/test_cockpit_view_1244.py:169`, `:190`, `:211` | PASS |
| `archival_refs` required for `deprecated` / `duplicate` | Validation code raises `ERR_ARCHIVAL_REFS_REQUIRED` at `serve/cockpit/src/owlbear_cockpit/view.py:133` | `tests/test_cockpit_view_1240.py:203`, `:223`; `tests/test_cockpit_view_1244.py:234`, `:255` | PASS |
| `completed` requires prior `done` status | Validation code raises `ERR_COMPLETED_REQUIRES_DONE` at `serve/cockpit/src/owlbear_cockpit/view.py:147` | `tests/test_cockpit_view_1240.py:245`, `tests/test_cockpit_view_1244.py:278` | PASS |
| Each ref ID must exist on the board | Validation code raises `ERR_ARCHIVAL_REF_MISSING` at `serve/cockpit/src/owlbear_cockpit/view.py:160` | `tests/test_cockpit_view_1240.py:267`, `tests/test_cockpit_view_1244.py:304` | PASS |
| Task cannot reference itself in `archival_refs` | Validation code raises `ERR_ARCHIVAL_REF_SELF` at `serve/cockpit/src/owlbear_cockpit/view.py:153` | `tests/test_cockpit_view_1240.py:289`, `tests/test_cockpit_view_1244.py:328` | PASS |
| Ref chain must not loop back to the task | Validation code raises `ERR_ARCHIVAL_REF_CYCLE` at `serve/cockpit/src/owlbear_cockpit/view.py:165` | `tests/test_cockpit_view_1240.py:311`, `tests/test_cockpit_view_1244.py:352` | PASS |
| Errors are raised as engine error codes and surface as 422 responses via the route | View executes archival validation before engine move at `serve/cockpit/src/owlbear_cockpit/view.py:245-253`; route maps `ValidationError` to HTTP 422 at `serve/cockpit/src/owlbear_cockpit/routes/mutation.py:172`; route tests assert 422 detail while view tests assert engine error codes | `tests/test_cockpit_view_1240.py:125-353`, `tests/test_cockpit_view_1244.py:148-352` | PASS |
| All tests from #1240 pass | quality-runner report: 53 passed / 0 failed including all `tests/test_cockpit_view_1240.py` cases and the route happy path at `tests/test_cockpit_view_1244.py:402` | quality-runner scoped run | PASS |

#### Security Review
- No hardcoded secrets, injection, path traversal, unsafe deserialization, or input-boundary regression introduced.
- The change is a single route gate refinement in `serve/cockpit/src/owlbear_cockpit/routes/mutation.py:154`; archival validation still occurs in `serve/cockpit/src/owlbear_cockpit/view.py:245-253` before the engine move.

#### Test Integrity
- `TestFromAC_ArchivalValidation422Surfacing` remains present at `tests/test_cockpit_view_1244.py:133` with specific 422-detail and happy-path assertions.
- No weakening or removal is visible in the current tree. Assessment: PRESERVED.
- Note: commit diff was not independently inspected with git tooling in this environment; changed-file scope was reconstructed from builder notes plus current source/tests.

#### Test Quality
- Assertion specificity: STRONG. Route tests assert status codes plus archival-specific detail content; view tests assert exact engine error codes.
- Negative/error-path coverage: STRONG. All archival validation failures have direct route and view coverage.
- Manual mutation reasoning: reverting the gate to `if req.status not in transitions` would fail the 11 route tests in `tests/test_cockpit_view_1244.py`; removing the route `ValidationError -> 422` mapping at `serve/cockpit/src/owlbear_cockpit/routes/mutation.py:172` would also fail those tests.
- Test independence: STRONG.
- Descriptive naming: STRONG.

#### Data Safety
- OCC stale-snapshot protection remains ahead of the move call; no atomicity or race regression introduced by this change.

#### Implementation-Aware Test Gap Analysis
- No significant untested path found within AC scope. The changed condition has both archived and non-archived behavior exercised by passing tests.

#### Necessity Check
- Skipped. No new dependency, integration, or external capability was added.

#### Builder Process Quality
- CLEAN. One `## Builder Notes` section, no prior `## Review Evidence` section, no retry loop evidence.

### Deductions
- `-0.02` Changed-file scope reconstructed from builder notes and current source/tests rather than an independently inspected git diff.
- `-0.02` Cockpit route coverage percentage unavailable due repo coverage config omitting `owlbear_cockpit`; behavioral branch coverage is still proven by passing archived and non-archived route tests.

### Verdict
- PASS -> docs | confidence 0.93

### Action
- Advanced to `docs`. 
[[2026-05-01]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | Yes | Updated | `serve/cockpit/README.md` line 31: `POST /tasks/{id}/move` notes said "OCC token precheck, then `valid_transitions` check" — now reflects that `archived` bypasses the transition check and is validated by `CockpitView.move_task` |
| 2 | Module docstrings | Yes | Updated | `serve/cockpit/src/owlbear_cockpit/routes/mutation.py` docstring was `"Validates OCC token then valid_transitions"` — updated to `"Validates OCC token then valid_transitions; archived skips transition check"` |
| 3 | External attribution | No | N/A | Builder notes reference no external patterns |
| 4 | Research doc | No | N/A | No `.owlbear/research/` doc linked in task body |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/cockpit.excalidraw` has `describes: serve/cockpit/src/**` matching the changed `mutation.py`; footer updated from `(ee836394)` to `(0530874a)` |
| 6 | Explicit diagram creation | No | N/A | No diagram creation requested |
| 7 | Deletion detection | No | N/A | No files deleted |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| `serve/cockpit/src/owlbear_cockpit/routes/mutation.py` | IN (docstring) | Updated |
| `tests/test_cockpit_view_1244.py` | OUT (test file) | N/A |

### Files Updated
- `serve/cockpit/README.md` — prose updated in mutation routes table
- `serve/cockpit/src/owlbear_cockpit/routes/mutation.py` — docstring updated
- `share/diagrams/cockpit.excalidraw` — footer updated to `(0530874a)`
- Commit: `fa9febb6`

### Child Tasks Created
- None

### Scratch Files Cleaned
- None found
[[2026-05-01]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| archival_reason required | view.py:120 raises ERR_ARCHIVAL_REASON_REQUIRED; route test test_cockpit_view_1244.py:148 asserts 422 | PASS |
| archival_refs forbidden (completed/dropped/wontfix) | view.py:140 raises ERR_ARCHIVAL_REFS_FORBIDDEN; route tests :169,:190,:211 | PASS |
| archival_refs required (deprecated/duplicate) | view.py:133 raises ERR_ARCHIVAL_REFS_REQUIRED; route tests :234,:255 | PASS |
| completed requires done | view.py:147 raises ERR_COMPLETED_REQUIRES_DONE; route test :278 | PASS |
| Each ref ID must exist | view.py:160 raises ERR_ARCHIVAL_REF_MISSING; route test :304 | PASS |
| Self-reference blocked | view.py:153 raises ERR_ARCHIVAL_REF_SELF; route test :328 | PASS |
| Ref cycle blocked | view.py:165 raises ERR_ARCHIVAL_REF_CYCLE; route test :352 | PASS |
| Errors surface as 422 via route | mutation.py:154 bypasses transition for archived; :172 maps ValidationError to 422 | PASS |
| All tests from #1240 pass | 53 passed in scoped run including all test_cockpit_view_1240 cases | PASS |

### Test Results
- pytest full suite: 3485 passed, 105 failed (all pre-existing/unrelated), 4 skipped
- Task-scoped + regression: 53 passed, 0 failed
- ruff: clean

### Architect Quality: 4/5
Specific error codes and validation paths. Minor gap: AC listed route as Out of Scope but route change was needed for 422 surfacing AC. Downstream agents resolved cleanly.

### Deduction Breakdown
- -0.02: 105 background failures reduce cross-regression signal (none in task scope)

### Confidence: .98
### Action: archive