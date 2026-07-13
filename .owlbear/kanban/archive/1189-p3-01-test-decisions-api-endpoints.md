---
id: 1189
title: 'P3-01: Test decisions API endpoints'
status: archived
priority: medium
created: 2026-04-30T00:52:09.506007+00:00
updated: 2026-04-30T03:02:14.342410+00:00
tags:
- phase-3
- scope:cockpit
- type:test
parent: 1179
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---

## Acceptance Criteria

- Test `GET /api/decisions/pending` returns JSON with `count` and `items` array
- Test response item shape: id, task_id, agent, request_type, created, title, body_preview
- Test body_preview is truncated to ~200 chars
- Test returns empty list when no pending DRs exist
- Test `POST /api/decisions/{id}/resolve` accepts response enum + optional notes
- Test resolve updates file: changes response field, appends ## Response section
- Test resolve returns 404 for non-existent DR id
- Test resolve validates response enum (rejects invalid values)

## Scope

- IN: Cockpit API endpoint tests (`serve/cockpit/`)
- OUT: frontend components, decisions.py unit tests

Brief: see parent #1179

[[2026-04-30]]
## Research
- Research doc: .owlbear/research/1189-decisions-api-test-design.md
- Sources: 7 studied, 4 high-relevance (cockpit test suites, DR format docs)
- Recommendation: Follow existing cockpit test patterns with new `get_decisions_dir` dependency override, TestClient fixture with pre-written DR files in tmp_path (confidence: 0.85)
- Follow-up tasks created: none needed — #1190 already exists
- Decision requests: none (T1 — straightforward test infrastructure)

## Challenge Results
- Challenger: FALLBACK — trivial test-infrastructure research with no competing architectural options
- Confidence in original: 0.85
- Key findings: DR id = filename stem; fixture creates raw YAML files; `get_decisions_dir` DI matches existing `get_engine`/`get_cache`/`get_view` pattern; response enum: approved|needs-info|rejected|completed
[[2026-04-30]]


## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Tests only decisions API endpoints |
| Interface clarity | PASS | Endpoints, shapes, error codes explicit in AC |
| Dependency correctness | PASS | No deps needed; #1190 correctly depends on this |
| Module layering | PASS | Test file only — no production code |
| TDD compliance | PASS | This IS the RED-phase test task |
| KISS/YAGNI | PASS | Straightforward test suite, no abstractions |
| Premise challenge | PASS | Tests required for TDD pipeline |
| Pattern consistency | PASS | Follows existing cockpit test patterns (TestClient + dependency_overrides + tmp_path) |
| Security surface | PASS | No new system boundary (test only) |
| Single domain | PASS | Cockpit domain only |

### AC Assessment
| AC Line | Depth | Notes |
|---------|-------|-------|
| GET returns count + items | td:0 | Test authoring — no meta-test |
| Item shape fields | td:0 | Test authoring |
| body_preview truncated ~200 | td:0 | Test authoring |
| Empty list returns zero | td:0 | Test authoring |
| POST resolve accepts enum + notes | td:0 | Test authoring |
| Resolve updates file | td:0 | Test authoring |
| Resolve 404 nonexistent | td:0 | Test authoring |
| Resolve invalid enum 422 | td:0 | Test authoring |

### Challenge Results
- Challenger: SKIPPED — all td:0
- Architect response: N/A

### Test Depth
- Max depth: 0
- Test-writer: SKIP

### Verdict: APPROVE
### Action Taken: AC is precise and maps 1:1 to specific test assertions. Research validates fixture approach (get_decisions_dir DI override, tmp_path with pre-written YAML DR files). Response enum confirmed: approved|needs-info|rejected|completed. DR id = filename stem. Approved to todo.
[[2026-04-30]]
Architecture review complete. All 10 criteria PASS. AC is precise — each line maps to one test function with clear assertion targets. Existing cockpit test patterns (get_decisions_dir DI override, TestClient, tmp_path YAML fixtures) validated against codebase. Response enum confirmed from .owlbear/decisions/README.md. type:test tag present — test-writer SKIP.
[[2026-04-30]]
## Test-Writer Notes
- Non-implementation task (tagged type:test) — no tests applicable.
- The deliverable IS a test file; the builder writes the test suite as the implementation artifact.
- Passing through to builder.
- Architecture review confirmed: all AC lines td:0, test-writer SKIP.
[[2026-04-30]]
## Builder Notes
- Implementation: added failing RED-phase endpoint suite in tests/test_cockpit_decisions_api_1189.py.
- Scope covered: GET /api/decisions/pending envelope + item shape + preview truncation + empty state; POST /api/decisions/{id}/resolve happy path + file mutation contract + 404 + enum validation.
- Test evidence (quality-runner scoped): 8 tests total, 1 passed / 7 failed.
- Failure pattern: unresolved endpoints currently return 404, matching expected RED state for downstream implementation task #1190.
- Lint (quality-runner scoped): clean.
- Coverage (scoped run): owlbear_cockpit 22% for this single RED file run.
- Commit: f3ed0dcc8bd682d81ca8d7edb161ab8514c8571f (test: add decisions api endpoint tests (#1189, builder)).

### Post-task Reflection
- Problem faced: fixture had one ruff RET504 issue on first draft.
- Workaround applied: simplified helper return path to satisfy lint without changing behavior.
- Pattern discovered: optional dependency override via getattr keeps task tests resilient while DI callables land in implementation phase.
- Quality gap: endpoint implementation does not exist yet, so RED failures are route-level 404 rather than deeper contract checks until #1190 lands.
[[2026-04-30]]
## Review Evidence
### Test Results
- Quality-runner scoped run on `tests/test_cockpit_decisions_api_1189.py`: 8 collected, 1 passed, 7 failed, 0 errors.
- All 7 failures are route-level 404s on `/api/decisions/pending` and `/api/decisions/{id}/resolve`. This is acceptable RED evidence for the downstream implementation task, not the reason for rejection.
- Collection succeeded. No import, fixture, or setup errors.

### Lint
- Ruff: clean on `tests/test_cockpit_decisions_api_1189.py`.

### Coverage
- Informational only for this RED `type:test` task: quality-runner reported 19% overall in the scoped run because the cockpit decisions endpoints do not exist yet.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Evidence | Status |
|---------|----------|--------|
| GET returns JSON with `count` and `items` array | `TestFromAC_DecisionsPending.test_pending_returns_count_and_items` asserts 200, `count` int, `items` list, and `count == len(items) == 1` | COVERED |
| Response item shape includes `id, task_id, agent, request_type, created, title, body_preview` | `TestFromAC_DecisionsPending.test_pending_item_shape` asserts required keys are present | COVERED |
| `body_preview` is truncated to ~200 chars | `TestFromAC_DecisionsPending.test_body_preview_is_truncated_to_around_200_chars` only asserts `isinstance(preview, str)` and `len(preview) <= 200` | LAX |
| Empty pending list returns zero items | `TestFromAC_DecisionsPending.test_pending_empty_returns_zero_and_empty_items` asserts exact payload `{"count": 0, "items": []}` | COVERED |
| Resolve accepts response enum + optional notes | Current suite proves `approved` + notes and `rejected` + notes only. No successful request omits `notes`, and task-body authority confirms enum values `approved|needs-info|rejected|completed` | MISSING |
| Resolve updates file response and appends `## Response` section | `TestFromAC_DecisionsResolve.test_resolve_updates_response_field_and_appends_response_section` asserts persisted file exists, YAML `response == "rejected"`, and response section text exists | COVERED |
| Resolve returns 404 for non-existent DR id | `TestFromAC_DecisionsResolve.test_resolve_returns_404_for_unknown_decision_id` asserts 404 | COVERED |
| Resolve rejects invalid enum values | `TestFromAC_DecisionsResolve.test_resolve_rejects_invalid_response_enum` asserts 422 for `invalid-status` | COVERED |

#### Security Review
- No security issues in scope. Test-only file writes to `tmp_path` and does not introduce new runtime dependencies or unsafe boundary handling.

#### Test Integrity
- N/A. No prior `TestFromAC_*` suite existed for this task to compare against.

#### Test Quality
- FAIL: preview proof is too weak. The dedicated truncation test would still pass if the endpoint returned an unrelated short string or an empty preview instead of a body-derived preview.
- FAIL: resolve happy-path proof is incomplete. The suite does not prove that `notes` is optional on a successful request, and it does not cover the remaining documented valid enum values from the task body / DR README.

#### Data Safety
- No issues found in scope.

#### Implementation-Aware Test Gap Analysis
- Rejection is test-proof only. The current 404s are expected because the cockpit app does not yet expose the decisions endpoints. That implementation work belongs to #1190.

#### Builder Process Quality
- CLEAN. One builder pass, clean lint, no loop pattern.

### Deductions
-0.08 preview assertion does not prove body-derived truncation.
-0.08 successful resolve path does not prove optional notes or the full documented valid enum set.

### Verdict
- FAIL -> in-progress | confidence 0.84

### Required Follow-up
1. Strengthen the `body_preview` test so it proves the preview is derived from the DR body while remaining capped around 200 characters.
2. Add successful resolve coverage without `notes` and cover the remaining documented valid enum members, or explicitly narrow the task authority if those values are intentionally out of scope.
3. Keep the current RED 404 behavior as-is; missing route registration is downstream implementation work, not a defect in this test task.
[[2026-04-30]]
## Builder Notes
- Files changed: tests/test_cockpit_decisions_api_1189.py
- Fixes applied (review follow-up):
  - Strengthened `body_preview` proof to assert preview is non-empty, starts with a known body token, and is a prefix of the source body while remaining `<= 200` chars.
  - Expanded resolve-success coverage with parameterized valid enums: `approved`, `needs-info`, `rejected`, `completed`.
  - Added explicit successful case with optional notes omitted (`needs-info`, `notes` absent from payload).
- Test results (quality-runner, scoped): 11 collected, 1 passed, 10 failed.
- Failure pattern: all failures remain expected RED route-level 404/422 mismatches because decisions endpoints are not implemented yet (downstream task #1190).
- Lint status (quality-runner, scoped): ruff clean.
- Coverage (quality-runner, scoped): 19% overall (informational for RED test task).
- Module-level durable test file check: no `tests/test_cockpit_decisions_api.py` exists, so module baseline run skipped.
- Commit: 3c5aa926 (test: strengthen decisions api red proofs (#1189, builder)).

### Post-task Reflection
- Problem faced: prior truncation assertion allowed false positives from unrelated short preview strings.
- Workaround applied: anchored preview assertions to a unique body prefix and body-prefix relationship.
- Pattern discovered: valid-response enum completeness is best expressed as parameterized success cases, including omitted optional fields.
- Quality gap: until #1190 lands, all endpoint assertions stay route-level RED (404) rather than contract-level behavior checks.
[[2026-04-30]]
## Review Evidence
### Scope Checked
- Changed file reconstructed from builder notes and current snapshot: `tests/test_cockpit_decisions_api_1189.py`
- No production files changed in this task.

### Test Results
- Quality-runner scoped run: 11 collected, 10 failed, 1 passed.
- Collection succeeded with no import/setup errors.
- Failure pattern: all 10 failures are expected route-level 404s on `/api/decisions/pending` and `/api/decisions/{id}/resolve`, which is acceptable RED evidence for downstream implementation task #1190.
- Passing test: `test_resolve_returns_404_for_unknown_decision_id`.

### Lint
- Ruff: clean on `tests/test_cockpit_decisions_api_1189.py`.

### Coverage
- Skipped for review gating. Task AC is td:0 / `type:test`, so coverage is informational only here.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Evidence | Status |
|---------|----------|--------|
| Test `GET /api/decisions/pending` returns JSON with `count` and `items` array | `test_pending_returns_count_and_items` at `tests/test_cockpit_decisions_api_1189.py:161` asserts 200 plus `count` int, `items` list, and `count == len(items) == 1` | COVERED |
| Test response item shape: id, task_id, agent, request_type, created, title, body_preview | `test_pending_item_shape` at `tests/test_cockpit_decisions_api_1189.py:178`; required-field assertion at line 200 | COVERED |
| Test body_preview is truncated to ~200 chars | `test_body_preview_is_truncated_to_around_200_chars` at `tests/test_cockpit_decisions_api_1189.py:202`; strengthened assertions at lines 222-225 prove non-empty, body-derived preview capped at 200 chars | COVERED |
| Test returns empty list when no pending DRs exist | `test_pending_empty_returns_zero_and_empty_items` at `tests/test_cockpit_decisions_api_1189.py:227`; exact payload assertion at line 235 | COVERED |
| Test `POST /api/decisions/{id}/resolve` accepts response enum + optional notes | Parameterized `test_resolve_accepts_response_enum_and_optional_notes` at `tests/test_cockpit_decisions_api_1189.py:250`; valid enum cases at lines 244-247 and optional-notes branch at lines 266-267 | COVERED |
| Test resolve updates file: changes response field, appends ## Response section | `test_resolve_updates_response_field_and_appends_response_section` at `tests/test_cockpit_decisions_api_1189.py:277`; persisted response and appended section assertions at lines 301 and 304-305 | COVERED |
| Test resolve returns 404 for non-existent DR id | `test_resolve_returns_404_for_unknown_decision_id` at `tests/test_cockpit_decisions_api_1189.py:307`; 404 assertion at line 314 | COVERED |
| Test resolve validates response enum (rejects invalid values) | `test_resolve_rejects_invalid_response_enum` at `tests/test_cockpit_decisions_api_1189.py:316`; 422 assertion at line 335 | COVERED |

#### Security Review
- No security issues in scope. This task adds a test-only file writing to `tmp_path` fixtures and introduces no runtime dependency or unsafe boundary behavior.

#### Test Integrity
- PASS. No prior `TestFromAC_*` suite existed for this task, so there was no protected upstream proof to weaken.

#### Test Quality
- PASS. The prior review’s two blockers are resolved in the live snapshot:
  - Preview proof is now tied to source-body content and capped at 200 chars (`tests/test_cockpit_decisions_api_1189.py:208`, `:222-225`).
  - Resolve success now covers all documented valid enum values and includes a successful omission-path for optional `notes` (`tests/test_cockpit_decisions_api_1189.py:244-247`, `:266-275`).
- Residual risk: the AC’s `~200 chars` wording is approximate, so the test does not enforce a numeric lower-bound window. That is non-blocking under the current task authority.

#### Data Safety
- No issues found in scope.

#### Implementation-Aware Test Gap Analysis
- No AC-blocking test gap remains in the current snapshot.
- The 404 failures are expected because the cockpit backend does not yet register decisions endpoints; that implementation belongs to #1190, not this test-authoring task.

#### Builder Process Quality
- CLEAN. One follow-up cycle after the first review; the builder changed approach to address the exact cited proof gaps.

### AC Compliance Table
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| GET returns `count` + `items` | `tests/test_cockpit_decisions_api_1189.py:161-176` | `test_pending_returns_count_and_items` | PASS |
| Item shape fields | `tests/test_cockpit_decisions_api_1189.py:178-200` | `test_pending_item_shape` | PASS |
| body_preview truncated | `tests/test_cockpit_decisions_api_1189.py:202-225` | `test_body_preview_is_truncated_to_around_200_chars` | PASS |
| Empty pending list | `tests/test_cockpit_decisions_api_1189.py:227-235` | `test_pending_empty_returns_zero_and_empty_items` | PASS |
| Resolve accepts enum + optional notes | `tests/test_cockpit_decisions_api_1189.py:243-275` | `test_resolve_accepts_response_enum_and_optional_notes` | PASS |
| Resolve updates file | `tests/test_cockpit_decisions_api_1189.py:277-305` | `test_resolve_updates_response_field_and_appends_response_section` | PASS |
| Resolve 404 nonexistent | `tests/test_cockpit_decisions_api_1189.py:307-314` | `test_resolve_returns_404_for_unknown_decision_id` | PASS |
| Resolve invalid enum rejected | `tests/test_cockpit_decisions_api_1189.py:316-335` | `test_resolve_rejects_invalid_response_enum` | PASS |

### Deductions
-0.03 residual ambiguity from approximate `~200 chars` wording; non-blocking because the current assertions satisfy the written AC and the prior review follow-up.

### Verdict
- PASS -> docs | confidence 0.93

### Action
- Advance to `docs`. Downstream implementation task #1190 remains responsible for turning the current RED endpoint assertions green.
[[2026-04-30]]
## Docs Gate

| Check | Applies? | Status | Evidence |
|-------|----------|--------|----------|
| 0a — Review Evidence present | Yes | PASS | `## Review Evidence` section present in task body (two passes) |
| 0b — Doc-index loaded | Yes | PASS | `.owlbear/doc-index.md` loaded; no 1189 entry (test files excluded by index config) |
| 1 — Prose docs | No | N/A | Only changed file is `tests/test_cockpit_decisions_api_1189.py` — OUT of scope; no IN-scope descriptive docs reference test internals |
| 2 — Module docstrings | No | N/A | No Python modules created or modified; task deliverable is a test file only |
| 3 — External attribution | No | N/A | All 7 research sources are internal codebase files and internal docs (no external repos or articles) |
| 4 — Research doc | Yes | PASS | `.owlbear/research/1189-decisions-api-test-design.md` exists and is linked from task body |
| 5 — Diagram maintenance | No | N/A | No `describes` glob in doc-index matches `tests/test_cockpit_decisions_api_1189.py`; closest is `serve/cockpit/src/**` which does not cover test files |
| 6 — Explicit diagram creation | No | N/A | No explicit diagram creation request in task body |
| 7 — Deletion detection | No | N/A | No deleted files in changed-files set |

**Files updated:** none  
**Child tasks created:** none  
**Scratch files cleaned:** none found for task 1189

No docs impact — all checklist items N/A or confirmed passing. Advancing to done.
[[2026-04-30]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| GET returns count + items array | test_pending_returns_count_and_items:L161 asserts 200, count int, items list, len match | PASS |
| Item shape fields | test_pending_item_shape:L178 asserts required_fields subset of keys | PASS |
| body_preview truncated ~200 chars | test_body_preview:L202 anchors to unique_prefix, startswith body, len <=200 | PASS |
| Empty list returns zero | test_pending_empty:L227 exact payload assertion | PASS |
| Resolve accepts enum + optional notes | parametrized test:L243 covers all 4 enum values + notes-omitted case | PASS |
| Resolve updates file | test_resolve_updates:L277 checks YAML response field + appended section | PASS |
| Resolve 404 nonexistent | test_resolve_404:L307 asserts 404 | PASS |
| Resolve invalid enum rejected | test_resolve_rejects:L316 asserts 422 | PASS |

### Test Results
- pytest full suite: 3258 passed, 74 failed (10 are this task's expected RED, 64 pre-existing RED from other tasks), 4 skipped. No regressions.
- ruff: clean on task file. 4 pre-existing violations in unrelated packages.

### Architect Quality: 5/5
AC is precise, each line maps 1:1 to a specific test assertion. Covers happy path, empty state, error codes, and mutation contract. No gaps requiring builder improvisation.

### Deduction Breakdown
- AC lines without evidence: 0 (all 8 covered)
- Lint violations in scope: 0
- AC quality <=3: N/A (score 5)
- Missing reviewer section: 0 (present, detailed, two-pass)
- Full-suite failures in scope: 0 (task failures are expected RED)

### Confidence: 0.98
- Applied -.02 for approximate AC wording (~200 chars) creating minor lower-bound ambiguity, mitigated by unique_prefix anchoring (28+ chars guaranteed).

### Action: archive
Commits verified: f3ed0dcc, 3c5aa926. Reviewer two-pass evidence detailed and accepted.