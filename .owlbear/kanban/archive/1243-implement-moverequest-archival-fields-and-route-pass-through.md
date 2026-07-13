---
id: 1243
title: 'Implement: MoveRequest archival fields and route pass-through'
status: archived
priority: medium
created: 2026-05-01T03:08:02.839683+00:00
updated: 2026-05-01T09:14:13.544984+00:00
tags:
- scope:backend
parent: 1238
depends_on:
- 1239
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Acceptance Criteria

- `MoveRequest` has `archival_reason: str | None = None` and `archival_refs: list[int] = []` fields
- `extra="forbid"` is preserved on `MoveRequest` (unknown fields are still rejected)
- Move route handler passes `req.archival_reason` and `req.archival_refs` through to `view.move_task()`
- Existing move requests without archival fields are unaffected (backwards-compatible)
- All tests from #1239 pass

## In Scope

- `routes/mutation.py`: `MoveRequest` model and move handler

## Out of Scope

- `CockpitView` validation logic (B3 task #1244)
- Frontend changes

## Brief reference

Brief: `.owlbear/briefs/draft-archival-ux/brief.md` — Backend Changes B1, B2
[[2026-05-01]]
## Test-Writer Notes
- Test file: tests/test_cockpit_mutation_api_1243.py
- Classes: TestFromAC_MoveRequestArchivalReason, TestFromAC_MoveRequestArchivalRefs, TestFromAC_ExtraForbidPreserved, TestFromAC_RouteArchivalPassThrough, TestFromAC_BackwardsCompatibility
- Tests per category: happy 12, edge 2, error 1, boundary 4
- Total: 19 tests
- ruff: clean

### Pre-implementation notice
**All 19 tests PASS at time of test-writer phase.** The implementation was pre-completed during #1239's builder phase. Verification:
- `MoveRequest.archival_reason: str | None = None` — present in mutation.py (line 40)
- `MoveRequest.archival_refs: list[int] = Field(default_factory=list)` — present (line 41)
- `extra="forbid"` preserved — ConfigDict(extra="forbid") unchanged
- Route passes both kwargs to `view.move_task(archival_reason=..., archival_refs=...)` — lines 153–154
- `test_cockpit_mutation_api_1239.py` (12 tests) — all GREEN, confirmed before writing this file

RED baseline for this feature was established by #1239's test-writer phase. The tests here serve as task-scoped regression guards.

**Builder action:** Verify tests pass (`uv run pytest tests/test_cockpit_mutation_api_1243.py -q`) and advance directly to review — no implementation work needed.

### AC Coverage
| AC | Tests |
|----|-------|
| archival_reason field + default | TestFromAC_MoveRequestArchivalReason (4 tests) |
| archival_refs field + default | TestFromAC_MoveRequestArchivalRefs (5 tests) |
| extra="forbid" preserved | TestFromAC_ExtraForbidPreserved (2 tests) |
| Route pass-through both fields | TestFromAC_RouteArchivalPassThrough (3 tests) |
| Backwards-compatible | TestFromAC_BackwardsCompatibility (5 tests) |
[[2026-05-01]]
## Builder Notes
- Implementation: no code changes required; `MoveRequest` archival fields and route pass-through were already present in `serve/cockpit/src/owlbear_cockpit/routes/mutation.py` from prior task #1239 work.
- Tests: 19/19 `TestFromAC_*` tests passed in `tests/test_cockpit_mutation_api_1243.py`.
- Coverage: `owlbear_cockpit.routes.mutation` reported 40% in scoped quality-runner output; this task is a non-edit pass-through verification with pre-existing implementation.
- ruff: clean for `serve/cockpit/src/owlbear_cockpit/routes/mutation.py` and `tests/test_cockpit_mutation_api_1243.py`.
- Evidence summary: AC behaviors (archival fields, `extra="forbid"`, move-route kwargs pass-through, backwards compatibility) validated by the task-scoped suite.

- Reflection: pass-through builder task matched test-writer pre-implementation notice; no missing edge-case blockers were found.
- Reflection: scoped quality-runner verification produced sufficient regression signal without requiring broad-suite execution.
- Reflection: no workaround was needed; task proceeded directly from verification to handoff.
[[2026-05-01]]
## Review Evidence
### Changed File Scope
- No builder commit hash or diff was recorded in the task body.
- Reconstructed review scope from task notes and live repo state: serve/cockpit/src/owlbear_cockpit/routes/mutation.py, tests/test_cockpit_mutation_api_1243.py, and tests/test_cockpit_mutation_api_1239.py.
- Builder notes state no implementation edits were required for #1243; live source confirms the scoped behavior already exists.

### Test Results
- quality-runner: 31 passed, 0 failed, 0 skipped.
- Suites exercised: tests/test_cockpit_mutation_api_1243.py and tests/test_cockpit_mutation_api_1239.py.
- Note: quality-runner's per-file breakdown was inconsistent with live test-definition counts. Direct inspection shows 19 test methods in test_cockpit_mutation_api_1243.py and 12 in test_cockpit_mutation_api_1239.py, which reconciles to the reported total of 31.

### Lint
- Ruff: clean for serve/cockpit/src/owlbear_cockpit/routes/mutation.py, tests/test_cockpit_mutation_api_1243.py, and tests/test_cockpit_mutation_api_1239.py.

### Coverage
- No task-scoped coverage gate applied for this td:1/pass-through review.
- quality-runner reported non-focused package coverage at 28%; treated as informational only because no builder diff was present and the report was not diff-scoped.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| MoveRequest has archival_reason and archival_refs fields | 1243: TestFromAC_MoveRequestArchivalReason (lines 124-146) and TestFromAC_MoveRequestArchivalRefs (lines 161-194) | Yes — missing fields, wrong defaults, wrong accepted values, or shared mutable list state would fail exact None/equality/list-isolation assertions | COVERED |
| extra="forbid" is preserved on MoveRequest | 1243: tests at lines 205 and 215; 1239: regression guard at line 204 | Yes — unknown field rejection would stop raising, or archival fields would be treated as extra | COVERED |
| Move route handler passes req.archival_reason and req.archival_refs through to view.move_task() | 1243: tests at lines 239, 269, 299; source forwarding at mutation.py lines 161-166 | Yes — omitted kwargs, wrong kwarg names, or wrong values would fail exact call_args assertions | COVERED |
| Existing move requests without archival fields are unaffected | 1243: tests at lines 339, 345, 350, 355, 378; 1239 defaults at lines 303 and 334 | Yes — plain payload deserialisation, 200 response, and forwarded None/[] defaults are asserted directly | COVERED |
| All tests from #1239 pass | quality-runner: 31 total passed, 0 failed; includes tests/test_cockpit_mutation_api_1239.py | Yes — this AC is directly satisfied by the green scoped run including the inherited #1239 suite | COVERED |

#### Security Review
- No issues found.
- Evidence: the reviewed code only declares Pydantic request fields and forwards validated values into view.move_task(); no new filesystem access, shelling out, dynamic execution, deserialization hazards, or secrets exposure were introduced in the scoped code.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| TestFromAC_MoveRequestArchivalReason | No builder-authored weakening evidenced; live file still contains the 4 exact-value/default assertions described by Test-Writer Notes | PRESERVED |
| TestFromAC_MoveRequestArchivalRefs | No builder-authored weakening evidenced; live file still contains the 5 assertions, including mutable-default isolation | PRESERVED |
| TestFromAC_ExtraForbidPreserved | No weakening evidenced; unknown-field rejection and declared-field acceptance are both still asserted | PRESERVED |
| TestFromAC_RouteArchivalPassThrough | No weakening evidenced; separate archival_reason, archival_refs, and combined-pass-through assertions remain | PRESERVED |
| TestFromAC_BackwardsCompatibility | No weakening evidenced; plain request, 200 response, and forwarded None/[] assertions remain | PRESERVED |

#### Test Quality
- Assertion specificity: STRONG — assertions use exact equality, explicit kwarg presence, and exact None/[] defaults rather than truthy checks.
- Negative/error-path coverage: ADEQUATE — unknown-field rejection is covered; unrelated move-route error branches are outside this task's AC and unchanged by the scoped behavior.
- Manual mutation reasoning: STRONG — removing either field, relaxing extra=forbid, omitting either forwarded kwarg, or using a shared mutable default would all fail targeted tests.
- Test independence: STRONG — tests construct fresh MoveRequest instances or fresh mocked client/view fixtures.
- Descriptive naming: STRONG.

#### Data Safety
- No issues found.
- Evidence: MoveRequest.archival_refs uses Field(default_factory=list) at mutation.py line 43, and the non-shared default behavior is asserted in test_cockpit_mutation_api_1243.py line 188.

#### Implementation-Aware Test Gaps
- No AC-scoped gaps found.
- The task-owned behavior is limited to request-model fields plus move-route kwarg forwarding, and those paths are directly exercised by exact-value tests.

#### Necessity Check
- Skipped: no new dependency, tool, integration, or external capability was introduced.

#### Builder Process Quality
- CLEAN — one builder handoff section, no retry loop, no evidence of repeated identical attempts.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| MoveRequest has archival_reason: str | None = None and archival_refs: list[int] = [] fields | mutation.py lines 42-43 declare both fields; 1243 tests at lines 127-188 assert existence, defaults, accepted values, and list isolation | TestFromAC_MoveRequestArchivalReason; TestFromAC_MoveRequestArchivalRefs | PASS |
| extra="forbid" is preserved on MoveRequest | mutation.py line 38 keeps ConfigDict(extra="forbid"); 1243 line 205 and 1239 line 204 assert unknown fields still raise ValidationError | TestFromAC_ExtraForbidPreserved; TestFromAC_MoveRequestArchivalFields | PASS |
| Move route handler passes req.archival_reason and req.archival_refs through to view.move_task() | mutation.py lines 161-166 pass both kwargs; 1243 lines 239, 269, 299 assert exact kwargs received by the mocked view | TestFromAC_RouteArchivalPassThrough | PASS |
| Existing move requests without archival fields are unaffected | 1243 lines 339-378 assert plain deserialisation, 200 route result, and forwarded None/[] defaults; 1239 lines 303 and 334 independently assert default forwarding | TestFromAC_BackwardsCompatibility; TestFromAC_MoveRouteArchivalPassThrough | PASS |
| All tests from #1239 pass | quality-runner: scoped run green with both 1243 and 1239 suites, 31 passed / 0 failed | tests/test_cockpit_mutation_api_1239.py | PASS |

### Deductions
- -0.03 confidence: no builder commit hash or diff was supplied, so changed-file scope had to be reconstructed from task notes plus live code.
- -0.02 confidence: quality-runner's per-file suite breakdown was inconsistent and required manual reconciliation against live test definitions, though total pass count and green status were consistent.

### Verdict
- PASS -> docs
- Confidence: 0.95

### Action
- Advance to docs.

### Reflection
- quality-runner's per-file test breakdown was not trustworthy here; live file inspection was needed to reconcile suite counts.
- The task is a true pass-through review: no builder diff, but the live implementation in mutation.py cleanly matches the scoped AC.
- The duplicate 1239 and 1243 suites both provide binding proof; the stronger exact-kwarg assertions in 1243 governed the review bar.
[[2026-05-01]]
## Docs Gate

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | serve/cockpit/README.md mutation-routes table describes route behaviour (OCC, transitions) but does not enumerate MoveRequest fields — no update required. No other IN-scope doc references MoveRequest, archival_reason, or archival_refs. |
| 2 | Module docstrings | No | N/A | Builder notes confirm no code changes were made; mutation.py was not modified by this task (pre-existing implementation from #1239). No new or altered public interface to document. |
| 3 | External attribution | No | N/A | No external patterns, articles, or repos cited in task body or builder notes. |
| 4 | Research doc | No | N/A | No research doc referenced in task body. |
| 5 | Diagram maintenance (describes match) | No | N/A | share/diagrams/cockpit.excalidraw describes serve/cockpit/src/** — glob matches mutation.py — but builder made zero file edits (no commit hash, no diff); footer update is not triggered by a pass-through verification with no changed files. |
| 6 | Explicit diagram creation | No | N/A | No diagram creation request in task body. |
| 7 | Deletion detection | No | N/A | No files deleted. No orphaned IN-scope docs detected. |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| serve/cockpit/src/owlbear_cockpit/routes/mutation.py | OUT (source, no builder edits) | N/A |
| tests/test_cockpit_mutation_api_1243.py | OUT (test file) | N/A |
| tests/test_cockpit_mutation_api_1239.py | OUT (test file) | N/A |

### Files Updated
- None

### Child Tasks Created
- None

### Scratch Files Cleaned
- None found (.owlbear/scratch/1243-* search returned no results)
[[2026-05-01]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| MoveRequest has archival_reason: str \| None = None and archival_refs: list[int] = [] | mutation.py L42-43 declare both fields; test_cockpit_mutation_api_1243.py L124-194 assert existence, defaults, types, list isolation | PASS |
| extra="forbid" preserved on MoveRequest | mutation.py L38 ConfigDict(extra="forbid"); tests L205,215 assert unknown fields raise ValidationError | PASS |
| Move route passes archival_reason and archival_refs to view.move_task() | mutation.py L161-166 forward both kwargs; tests L239,269,299 assert exact kwargs received by mocked view | PASS |
| Existing move requests without archival fields unaffected | tests L339-378 assert plain deserialization, 200 response, forwarded None/[] defaults | PASS |
| All tests from #1239 pass | quality-runner: 31 passed (19+12), 0 failed across both scoped suites | PASS |

### Test Results
- pytest full suite: 3308 passed, 108 failed, 4 skipped — all 108 failures in unrelated packages (kanban engine model migration, decisions, mcp-kanban); 0 failures in task scope
- task-scoped: 19/19 passed
- ruff: 4 violations, all outside task scope (knowledge, mcp-knowledge, mcp-memory, orchestrator)
- frontend: N/A (scope:backend, no frontend AC)

### Upstream Commits
- 03fdb33e test: add regression guards for MoveRequest archival fields (#1243, test-writer)
- 77ef875d feat: forward archival move fields (#1239, builder) — implementation source

### Architect Quality: 4/5
5 AC lines, all specific and testable. Clear scope boundaries. Proper dependency on #1239. Minor: AC5 is a process gate rather than behavior spec, but reasonable for dependency task.

### Deduction Breakdown
- Start: 1.00
- AC lines without evidence: 0 → no deduction
- Lint violations in scope: 0 → no deduction
- AC quality 4/5 (>3): → no deduction
- Reviewer evidence: present, detailed, PASS → no deduction
- Full-suite failures in scope: 0 → no deduction
- -0.02: frontend vitest unverifiable (quality-runner timeout); mitigated by scope:backend tag and zero frontend AC

### Confidence: 0.98
### Action: archive