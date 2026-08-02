---
id: 1239
title: 'Test: MoveRequest archival fields and route pass-through'
status: archived
priority: medium
created: 2026-05-01T03:07:50.539456+00:00
updated: 2026-05-01T05:40:59.982145+00:00
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

- `MoveRequest` with no `archival_reason`/`archival_refs` fields deserialises correctly (backwards-compatible)
- `MoveRequest` with `archival_reason="completed"` and `archival_refs=[1, 2]` deserialises with correct types and defaults
- `extra="forbid"` still rejects unknown fields (no regression)
- Move route handler calls `view.move_task()` with `archival_reason` and `archival_refs` forwarded from the request
- Move route with default values (`archival_reason=None`, `archival_refs=[]`) passes through without error

## In Scope

- `MoveRequest` Pydantic model field tests
- Route pass-through tests against a mocked `CockpitView`

## Out of Scope

- `CockpitView` validation logic (B3 task #1240)
- Engine-level archival behaviour (already tested)

## Brief reference

Brief: `.owlbear/briefs/draft-archival-ux/brief.md` — Backend Changes B1, B2
[[2026-05-01]]
## Test-Writer Notes
- Test file: tests/test_cockpit_mutation_api_1239.py
- Classes: TestFromAC_MoveRequestArchivalFields, TestFromAC_MoveRouteArchivalPassThrough
- Tests per category:
  - AC1 (backwards-compat defaults): 2 tests — AttributeError on missing fields → RED
  - AC2 (archival fields accepted): 5 tests — ValidationError (extra="forbid" rejects undeclared fields) → RED
  - AC3 (extra="forbid" regression): 1 test — fails on AC2 dependency (archival_reason not yet declared) → RED
  - AC4 (route forwards archival fields): 2 tests — 422 from Pydantic (undeclared fields) → RED
  - AC5 (default pass-through): 2 tests — AssertionError (kwarg absent from route call) → RED
- Total: 12 tests, 12 FAIL, 0 pass — confirmed by quality-runner
- Lint: clean (ruff exit 0)
- AC coverage table:
  | AC | Tests |
  |---|---|
  | AC1 backwards-compat | test_*_has_none_reason, test_*_has_empty_refs |
  | AC2 archival fields | test_accepts_archival_reason_string, test_accepts_archival_refs_list, test_archival_reason_accepts_none, test_archival_refs_accepts_empty_list, test_full_archival_payload |
  | AC3 extra="forbid" | test_extra_forbid_preserved_after_archival_fields_added |
  | AC4 route forwarding | test_move_route_forwards_archival_reason, test_move_route_forwards_archival_refs |
  | AC5 default pass-through | test_move_route_default_archival_reason_forwarded_as_none, test_move_route_default_archival_refs_forwarded_as_empty_list |
[[2026-05-01]]
## Builder Notes
- Implementation: updated MoveRequest and move route forwarding in serve/cockpit/src/owlbear_cockpit/routes/mutation.py.
- Fixes applied:
  - Added `archival_reason: str | None = None` to `MoveRequest`.
  - Added `archival_refs: list[int] = Field(default_factory=list)` to `MoveRequest`.
  - Forwarded `archival_reason` and `archival_refs` kwargs in `move_task()` route call to `view.move_task()`.
- Tests: 12/12 task tests passed in tests/test_cockpit_mutation_api_1239.py.
- Regression check: 43/43 passed in tests/test_cockpit_mutation_api.py.
- Ruff: clean for serve/cockpit/src/owlbear_cockpit/routes/mutation.py and tests/test_cockpit_mutation_api_1239.py.
- Coverage: quality-runner reported target module not present in coverage report for the scoped run (`owlbear_cockpit.routes.mutation`); no failing coverage gate was reported.
- Evidence summary: all RED failures listed by test-writer resolved with a single-file, minimal patch and no test modifications.

## Post-task Reflection
- Problem faced: request schema allowed no archival fields, producing both model-level and route-level failures.
- Workaround applied: added explicit typed fields with safe defaults (`None` and `default_factory=list`) to keep backward compatibility and avoid mutable-default pitfalls.
- Pattern discovered: route pass-through tests in this codebase expect explicit forwarding of optional kwargs even when defaults are used.
- Quality gap: module-specific coverage targeting in quality-runner did not attribute the touched module in the scoped report; relied on passing scoped suites plus lint for gate evidence.
[[2026-05-01]]
## Review Evidence
### Changed Scope
- Reconstructed changed file from Builder Notes + direct inspection because the task body does not record a builder commit hash: serve/cockpit/src/owlbear_cockpit/routes/mutation.py
- Verified the live receiver already accepts the forwarded kwargs: serve/cockpit/src/owlbear_cockpit/view.py:234-259

### Test Results
- pytest: 55 passed, 0 failed
- Scoped suites run independently by quality-runner:
  - tests/test_cockpit_mutation_api_1239.py
  - tests/test_cockpit_mutation_api.py

### Lint
- ruff: clean

### Coverage
- owlbear_cockpit.routes.mutation: 87% (163 statements, 21 misses)
- Missing lines reported by quality-runner: 77, 98-112, 156, 160, 260, 273-274, 298-299, 321, 336, 342, 348, 354
- Diff-scoped review: changed lines in the task are serve/cockpit/src/owlbear_cockpit/routes/mutation.py:33-34 and :152-153; none are in the miss set, so the builder's touched lines are exercised even though the whole module remains below 90%

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---|---|---|---|
| MoveRequest with no archival_reason/archival_refs fields deserialises correctly (backwards-compatible) | test_moverequest_without_archival_fields_has_none_reason (tests/test_cockpit_mutation_api_1239.py:136), test_moverequest_without_archival_fields_has_empty_refs (tests/test_cockpit_mutation_api_1239.py:142) | Yes - exact default assertions at :140 and :146 fail if either default is absent or wrong | COVERED |
| MoveRequest with archival_reason="completed" and archival_refs=[1, 2] deserialises with correct types and defaults | test_moverequest_accepts_archival_reason_string (:150), test_moverequest_accepts_archival_refs_list_of_ints (:160), test_moverequest_archival_reason_accepts_none_explicitly (:170), test_moverequest_archival_refs_accepts_empty_list_explicitly (:180), test_moverequest_full_archival_payload_round_trips (:190) | Yes - exact equality assertions at :158, :168, :178, :188, :199-200 fail if fields are undeclared, wrongly typed, or do not round-trip | COVERED |
| extra="forbid" still rejects unknown fields (no regression) | test_extra_forbid_preserved_after_archival_fields_added (tests/test_cockpit_mutation_api_1239.py:204) | Yes - MoveRequest still declares ConfigDict(extra="forbid") at serve/cockpit/src/owlbear_cockpit/routes/mutation.py:29 and the raises assertion at tests/test_cockpit_mutation_api_1239.py:220 fails if unknown fields are accepted | COVERED |
| Move route handler calls view.move_task() with archival_reason and archival_refs forwarded from the request | test_move_route_forwards_archival_reason_to_view (:237), test_move_route_forwards_archival_refs_to_view (:270) | Yes - route forwards req.archival_reason / req.archival_refs at serve/cockpit/src/owlbear_cockpit/routes/mutation.py:152-153 and tests assert 200 at :266/:299 plus exact forwarded kwargs at :268/:301 | COVERED |
| Move route with default values (archival_reason=None, archival_refs=[]) passes through without error | test_move_route_default_archival_reason_forwarded_as_none (:303), test_move_route_default_archival_refs_forwarded_as_empty_list (:334) | Yes - default request model values come from serve/cockpit/src/owlbear_cockpit/routes/mutation.py:33-34 and tests assert 200 at :328/:359 plus exact default kwargs at :332/:363 | COVERED |

#### Security Review
- No hardcoded secrets, injection sinks, path traversal, unsafe deserialization, or dependency expansion in the changed scope.

#### Test Integrity
| Original Test Set | Change Made | Assessment |
|---|---|---|
| TestFromAC_MoveRequestArchivalFields (tests/test_cockpit_mutation_api_1239.py:131-223) | Current file still contains the 8 methods named in Test-Writer Notes with exact equality / raises assertions | PRESERVED |
| TestFromAC_MoveRouteArchivalPassThrough (tests/test_cockpit_mutation_api_1239.py:234-363) | Current file still contains the 4 methods named in Test-Writer Notes with exact kwarg assertions | PRESERVED |

#### Test Quality
| Dimension | Status | Evidence |
|---|---|---|
| Assertion specificity | STRONG | Exact equality / raises assertions at tests/test_cockpit_mutation_api_1239.py:140, :146, :158, :168, :178, :188, :199-200, :220, :268, :301, :332, :363 |
| Negative / error-path coverage | ADEQUATE | Unknown-field rejection at tests/test_cockpit_mutation_api_1239.py:220 plus live move error-path regression coverage in tests/test_cockpit_mutation_api.py:173, :195, :207, :212, :227 |
| Manual mutation reasoning | STRONG | Removing either new request field or either forwarded kwarg would fail AC1/AC2/AC4/AC5 targeted tests |
| Test independence | ADEQUATE | Per-test request instances plus fixture-isolated clients and mocks |
| Descriptive names | STRONG | Test names state the exact contract under review |

#### Data Safety
- No issue. The change adds typed request fields and keyword pass-through only; the live receiver accepts them at serve/cockpit/src/owlbear_cockpit/view.py:234-259.

#### Implementation-Aware Test Gaps
- No significant untested path in the changed span.
- Mock-view false-green risk is closed by the live move regression suite: the route now always forwards these kwargs, and tests/test_cockpit_mutation_api.py:146-227 passed against the real CockpitView.move_task() signature at serve/cockpit/src/owlbear_cockpit/view.py:234-259.

#### Necessity Check
- Skip: no new dependency, integration, tool, or external capability.

#### Builder Process Quality
- CLEAN: current task body shows one builder cycle and no prior review section.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| MoveRequest with no archival_reason/archival_refs fields deserialises correctly (backwards-compatible) | serve/cockpit/src/owlbear_cockpit/routes/mutation.py:33-34; tests/test_cockpit_mutation_api_1239.py:136-146 | test_moverequest_without_archival_fields_has_none_reason; test_moverequest_without_archival_fields_has_empty_refs | PASS |
| MoveRequest with archival_reason="completed" and archival_refs=[1, 2] deserialises with correct types and defaults | serve/cockpit/src/owlbear_cockpit/routes/mutation.py:33-34; tests/test_cockpit_mutation_api_1239.py:150-200 | test_moverequest_accepts_archival_reason_string; test_moverequest_accepts_archival_refs_list_of_ints; test_moverequest_archival_reason_accepts_none_explicitly; test_moverequest_archival_refs_accepts_empty_list_explicitly; test_moverequest_full_archival_payload_round_trips | PASS |
| extra="forbid" still rejects unknown fields (no regression) | serve/cockpit/src/owlbear_cockpit/routes/mutation.py:29; tests/test_cockpit_mutation_api_1239.py:204-223 | test_extra_forbid_preserved_after_archival_fields_added | PASS |
| Move route handler calls view.move_task() with archival_reason and archival_refs forwarded from the request | serve/cockpit/src/owlbear_cockpit/routes/mutation.py:125, :152-153; tests/test_cockpit_mutation_api_1239.py:237-301 | test_move_route_forwards_archival_reason_to_view; test_move_route_forwards_archival_refs_to_view | PASS |
| Move route with default values (archival_reason=None, archival_refs=[]) passes through without error | serve/cockpit/src/owlbear_cockpit/routes/mutation.py:33-34, :125, :152-153; tests/test_cockpit_mutation_api_1239.py:303-363 | test_move_route_default_archival_reason_forwarded_as_none; test_move_route_default_archival_refs_forwarded_as_empty_list | PASS |

### Deductions
- -0.02: changed-file scope had to be reconstructed from builder notes and direct inspection because the task body does not include a builder commit hash
- -0.01: whole-module coverage is 87%, but the uncovered lines are outside the changed span so this is informational debt rather than a gate failure

### Verdict
- PASS -> docs
- Confidence: 0.95

### Post-task Reflection
- Builder's note about missing coverage attribution did not reproduce in the reviewer run; scoped coverage now reports owlbear_cockpit.routes.mutation directly.
- Mock-based route pass-through tests needed a live-path compatibility check against CockpitView.move_task() to rule out signature false-greens.
- Module-level coverage remains slightly below 90%, but the uncovered lines do not overlap this task's touched span.
[[2026-05-01]]
## Docs Gate

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | Yes | N/A | `serve/cockpit/README.md` move route row describes high-level behavior only; does not enumerate request body fields. New optional `archival_reason`/`archival_refs` fields with safe defaults don't change the documented behavioral contract. No update needed. |
| 2 | Module docstrings | Yes | N/A | `mutation.py` MoveRequest class docstring `"""Request body for POST /tasks/{id}/move."""` remains accurate; no field-level docstring convention in this codebase. No update needed. |
| 3 | External attribution | No | N/A | Builder notes cite no external patterns or sources. |
| 4 | Research doc | No | N/A | No research doc referenced in task body. |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/cockpit.excalidraw` describes `serve/cockpit/src/**` — matches changed file. Footer updated from `Last verified: 2026-05-01 (e11271c1)` → `Last verified: 2026-05-01 (c9ac7a5d)`. Committed: a80f1cdf. |
| 6 | Explicit diagram creation | No | N/A | No diagram creation requested in task body. |
| 7 | Deletion detection | No | N/A | No files deleted; no orphaned IN-scope docs detected. |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| serve/cockpit/src/owlbear_cockpit/routes/mutation.py | IN (docstrings) | No docstring update needed |
| tests/test_cockpit_mutation_api_1239.py | OUT (test file) | No action |

### Files Updated
- share/diagrams/cockpit.excalidraw (footer: e11271c1 → c9ac7a5d)

### Child Tasks Created
- None

### Scratch Files Cleaned
- None found
[[2026-05-01]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| MoveRequest with no archival fields deserialises correctly (backwards-compatible) | mutation.py:42-43 (defaults); tests/test_cockpit_mutation_api_1239.py:136-146 | PASS |
| MoveRequest with archival_reason="completed" and archival_refs=[1,2] deserialises with correct types | mutation.py:42-43; tests/test_cockpit_mutation_api_1239.py:150-200 | PASS |
| extra="forbid" still rejects unknown fields (no regression) | mutation.py:39; tests/test_cockpit_mutation_api_1239.py:204-223 | PASS |
| Move route handler calls view.move_task() with archival_reason and archival_refs forwarded | mutation.py:165-166; tests/test_cockpit_mutation_api_1239.py:237-301 | PASS |
| Move route with default values passes through without error | mutation.py:42-43,165-166; tests/test_cockpit_mutation_api_1239.py:303-363 | PASS |

### Test Results
- pytest full suite: 3378 passed, 108 failed (none in task scope), 4 skipped
- Task tests (12/12): all pass
- Regression suite (test_cockpit_mutation_api.py): all pass
- ruff: 9 violations (none in task files)

### Architect Quality: 5/5
Specific, complete, testable. Each AC maps directly to concrete model/route behavior. Backward compat, type safety, regression guard, and default forwarding all covered. No builder improvisation required.

### Deduction Breakdown
- Start: 1.00
- AC lines without evidence: 0 (none, -0.00)
- Lint violations in task scope: 0 (-0.00)
- AC quality score: 5 (-0.00)
- Reviewer evidence: present, detailed, PASS verdict (-0.00)
- Full-suite failures in task scope: 0 (-0.00)

### Confidence: 1.00
### Action: archive

### Upstream Commits Verified
- 77ef875d feat: forward archival move fields (#1239, builder)