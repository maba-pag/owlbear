---
id: 1379
title: 'P2-04: Implement Cockpit task detail edit validation and dirty state'
status: archived
priority: medium
created: 2026-05-06T01:04:34.112524+00:00
updated: 2026-05-09T01:29:05.117398+00:00
tags:
- cockpit
- audit-remediation
- phase-2
- scope:cockpit-web
- type:fix
- frontend
- task-detail
- validation
parent: 1363
depends_on:
- 1378
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---


## Purpose
Implement explicit parent/dependency validation and dirty-state handling for the task detail editor.

## Problem Evidence
- parseDependsOn silently drops invalid dependency entries.
- parseParent turns invalid input into null, risking accidental parent clearing.
- Detail fields are mostly hidden-label or raw controls with no dirty-state model.

## Acceptance Criteria
- Invalid parent input is preserved, shown to the user, and never sent as an accidental clearing update.
- Invalid dependency entries are preserved, shown to the user, and never silently dropped from the intended edit.
- Save controls reflect validation and dirty state so unchanged, invalid, and intentionally changed forms are distinct.
- Validation errors use the frontend error-contract behavior from #1375.
- Existing valid parent and dependency edits continue to save correctly.
- The implementation satisfies #1378 without adding action-gating or conflict-resolution behavior owned by later tasks.

## Scope
- In scope: Cockpit frontend task detail editor validation, dirty-state, and save intent.
- Out of scope: task-detail model expansion from #1377, action gating, conflict resolution, backend lifecycle work, and cache/SSE invalidation from #1346.

## Counterpart
Test task: #1378.

[[2026-05-08]]

## Architecture Review

### AC Assessment
| AC Line | Assessment | Action |
|---------|-----------|--------|
| AC1: Invalid parent preserved, shown, never sent | PASS — verifiable, td:2 | No change |
| AC2: Invalid depends_on preserved, shown, never dropped | PASS — verifiable, td:2 | No change |
| AC3: Save controls reflect validation and dirty state (original) | FAIL — "unchanged, invalid, and intentionally changed forms are distinct" is not testable as written; save button doesn't consult dirty state | **Refined** to match #1378 test contract |
| AC4: Validation errors use error-contract from #1375 | PASS — verifiable via same DOM element, td:1 | No change |
| AC5: Valid parent/dependency edits continue to save | PASS — regression guard, td:1 | No change |
| AC6: No action-gating or conflict-resolution added | PASS — scope guard, td:1 | No change |

### Refined Acceptance Criteria
- Invalid parent input is preserved, shown to the user, and never sent as an accidental clearing update. (td:2)
- Invalid dependency entries are preserved, shown to the user, and never silently dropped from the intended edit. (td:2)
- A dirty-state indicator is visible when form values differ from the loaded task state and absent when all values match. Client-side validation errors prevent save from submitting to the server. (td:2)
- Validation errors use the frontend error-contract behavior from #1375 — both client-side and server-side validation errors render through the same DOM element. (td:1)
- Existing valid parent and dependency edits continue to save correctly. (td:1)
- The implementation satisfies #1378 without adding action-gating or conflict-resolution behavior owned by later tasks. (td:1)

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Validation + dirty state for task detail editor — single concern |
| Interface clarity | PASS | After AC3 refinement, all AC lines are testable against #1378 tests |
| Dependency correctness | PASS | #1378 (test task) archived/done; #1375 (error-contract) archived/done |
| Module layering | PASS | Client-side validation in DetailTab.tsx, server errors via errorMessage.ts — no upward imports |
| TDD compliance | PASS | #1378 wrote 20 RED phase tests covering all AC lines |
| KISS/YAGNI | PASS | No new abstractions — validation in existing parse functions, dirty state via string comparison |
| Premise challenge | CONDITIONAL | Implementation may already exist from #1378 builder cycle (commit e6feb8ac). Builder should verify tests pass; if GREEN is trivial, that confirms prior work. Task remains valid as the formal implementation record. |
| Pattern consistency | PASS | Uses existing error-contract pattern from #1375; dirty indicator follows existing data-testid conventions |
| Security surface | PASS | Client-side only; no new system boundaries |
| Single domain | PASS | Cockpit frontend only |

### Provenance Note
Challenger identified that #1378 builder (not #1377) implemented the production changes (commit e6feb8ac). The current DetailTab.tsx already contains parseDependsOn/parseParent with error returns, clientValidationMessage, isDirty, dirty indicator, and validation message display. The builder's GREEN phase may confirm tests already pass — this is acceptable and validates the TDD cycle.

### Challenge Results
- Challenger verdict: reconsider (confidence 0.57)
- Key finding: AC3 was vague ("distinct" not testable) — addressed via refinement
- Provenance correction: implementation attributed to #1378 builder, not #1377 — noted
- Lexical dirty check concern: accepted as minor; raw string comparison is appropriate for this scope
- Architect response: AC3 refined, provenance noted, APPROVE sustained

### Test Depth
- Max depth: 2
- Test-writer: tests already written by #1378

### Verdict: APPROVE → todo
AC3 refined for testability. All criteria pass. Implementation may already exist from #1378 builder cycle — builder verifies.

[[2026-05-08]]
Architecture review complete. AC3 refined from vague "distinct" to testable: dirty indicator + validation-blocks-save. All 10 criteria pass. Challenger raised AC3 vagueness (addressed) and provenance correction (#1378 builder implemented, not #1377). Implementation may already exist — builder verifies via GREEN phase.
[[2026-05-08]]
## Test-Writer Notes
- Test file: serve/cockpit/web/src/__tests__/DetailTab_1379.test.tsx
- Pre-existing coverage: serve/cockpit/web/src/__tests__/DetailTab_1378.test.tsx (AC1–AC4, 20 tests, all passing)
- New tests in this file: AC5 and AC6 (4 tests, all passing)
- Classes: TestFromAC_ValidEditsStillSave (2 tests), TestFromAC_NoExtraActionGating (2 tests)
- Tests per category: happy 4, edge 0, error 0, boundary 0
- Total new: 4 tests — all PASS (pre-complete implementation from #1378 builder)
- ESLint: clean
- AC coverage:
  | AC Line | Test class | Count |
  |---------|-----------|-------|
  | AC1: Invalid parent → error + save blocked | TestFromAC_InvalidParentValidation (#1378) | 6 |
  | AC2: Invalid depends_on → error + save blocked | TestFromAC_InvalidDependsOnValidation (#1378) | 6 |
  | AC3: Save blocked while validation error present + dirty-state signal | TestFromAC_SaveBlockedOnValidationError + TestFromAC_DirtyStateSignal (#1378) | 6 |
  | AC4: Validation errors use same DOM element (error-contract) | TestFromAC_ValidationErrorVisibility (#1378) | 2 |
  | AC5: Valid edits continue to save correctly | TestFromAC_ValidEditsStillSave (#1379) | 2 |
  | AC6: No action-gating or conflict-resolution added | TestFromAC_NoExtraActionGating (#1379) | 2 |

**Builder note:** All 24 tests (20 from #1378 + 4 from #1379) pass against current DetailTab.tsx. The implementation was pre-completed by the #1378 builder (commit e6feb8ac, per architect provenance note). Builder phase: run both test files to confirm green, then advance directly to review.
[[2026-05-08]]
## Builder Notes
- Files changed: none (implementation already present from prior #1378 builder cycle; this pass verified GREEN evidence for #1379 scope).
- Target tests: 24 passed, 0 failed.
  - `serve/cockpit/web/src/__tests__/DetailTab_1378.test.tsx`: 20 passed
  - `serve/cockpit/web/src/__tests__/DetailTab_1379.test.tsx`: 4 passed
- Lint status:
  - Task-scoped eslint on `serve/cockpit/web/src/components/DetailTab.tsx`, `serve/cockpit/web/src/__tests__/DetailTab_1378.test.tsx`, `serve/cockpit/web/src/__tests__/DetailTab_1379.test.tsx`: clean (no findings).
  - Broad frontend lint run reported pre-existing unrelated issues outside #1379 scope (`src/hooks/usePolling.ts` missing `react-hooks/exhaustive-deps` rule definition and unrelated unused vars in other tests).
- Coverage evidence (targeted run): `DetailTab.tsx` ~76.1% statements, 80.51% branches, 36.11% functions, 71.5% lines.
- Evidence summary:
  - AC1/AC2: invalid parent/dependency preserved + surfaced and not submitted when invalid.
  - AC3: dirty-state indicator behavior present; client-side validation blocks submit.
  - AC4: client/server validation errors use shared error-contract rendering path.
  - AC5/AC6: valid parent/dependency edits still save; no action-gating/conflict behavior added.
- Fixes applied: none required for this task.
[[2026-05-08]]
## Review Evidence
### Test Results
- quality-runner scoped frontend pass from serve/cockpit/web: 55 passed, 0 failed, 0 skipped.
- Files exercised: serve/cockpit/web/src/__tests__/DetailTab_1378.test.tsx, serve/cockpit/web/src/__tests__/DetailTab_1379.test.tsx, serve/cockpit/web/src/__tests__/ErrorContract_1374.test.tsx, serve/cockpit/web/src/__tests__/DetailTab_1344.test.tsx.

### Lint Results
- Scoped lint clean for serve/cockpit/web/src/components/DetailTab.tsx and the four review test files.
- VS Code diagnostics: no errors in the component or reviewed test files.

### Coverage
- DetailTab.tsx coverage from the scoped run: 87.73% statements, 90.73% branches, 55.55% functions, 86.02% lines.
- Uncovered lines were 367, 405-409, 419. These are body-edit and conflict-modal branches and are not the reject basis for this task.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| AC1: Invalid parent input is preserved, shown, and never sent | The live component keeps raw input in controlled state at DetailTab.tsx:342-344 and blocks submit via clientValidationMessage at DetailTab.tsx:125-137. The current task tests prove only error visibility and no-submit at DetailTab_1378.test.tsx:124-131 and DetailTab_1378.test.tsx:166-173. No reviewed test reads the parent field value back after invalid input, so the literal preserved clause is not executable proof yet. | TestFromAC_InvalidParentValidation | FAIL |
| AC2: Invalid dependency entries are preserved, shown, and never silently dropped | The live component keeps raw depends_on input in controlled state at DetailTab.tsx:333-335 and blocks submit via clientValidationMessage at DetailTab.tsx:125-137. The current task tests prove only error visibility and no-submit at DetailTab_1378.test.tsx:260-267 and DetailTab_1378.test.tsx:321-328. No reviewed test reads the depends_on field value back after invalid input, so the literal preserved clause is not executable proof yet. | TestFromAC_InvalidDependsOnValidation | FAIL |
| AC3: Dirty indicator visible, cleared on restore, and validation blocks submit | Green execution on DetailTab_1378.test.tsx plus direct code review of isDirty and validation merge at DetailTab.tsx:125-137. | TestFromAC_SaveBlockedOnValidationError; TestFromAC_DirtyStateSignal | PASS |
| AC4: Client-side and server-side validation errors use the same DOM element and error-contract path | Shared render point at DetailTab.tsx:137 and DetailTab.tsx:412. Client path proven in DetailTab_1378.test.tsx:540-574. Server path proven in ErrorContract_1374.test.tsx:341-384 and DetailTab_1344.test.tsx:457-489. | TestFromAC_ValidationErrorVisibility plus adjacent durable DetailTab error-contract suites | PASS |
| AC5: Existing valid parent and dependency edits continue to save correctly | Task-local valid-save proofs at DetailTab_1379.test.tsx:109-145, with adjacent durable payload coverage in DetailTab_1344.test.tsx:160-227 and live-edit payload coverage in DetailTab.test.tsx:905-916 and DetailTab.test.tsx:983-995. | TestFromAC_ValidEditsStillSave plus adjacent durable payload suites | PASS |
| AC6: No new action-gating or later-task conflict behavior | Clean-form save remains ungated in DetailTab_1379.test.tsx:158-182. The existing 409 conflict path is already covered in the durable suite at DetailTab.test.tsx:312-365 and DetailTab.test.tsx:580-612, and the task artifact says this builder cycle changed no files. I did not use the pre-existing 409 branch as a fail basis because the task scope marks later conflict behavior out of scope. | TestFromAC_NoExtraActionGating plus durable pre-existing 409 coverage | PASS |

### Deductions
- 0.06: AC1 preserved clause is not regression-pinned by an executable readback assertion.
- 0.06: AC2 preserved clause is not regression-pinned by an executable readback assertion.
- 0.02: changed-file ownership and TestFromAC immutability are lower-confidence because direct git diff was not available in this review surface. Commit presence for e6feb8ac was verified in .git/logs and the task body records no file changes in this cycle.

### Verdict
- Confidence: 0.86
- FAIL
- Route: todo
- Reason: implementation evidence is green, but AC1 and AC2 remain under-proven. The tests show validation and blocked submit, yet they do not execute the preserved raw-input requirement that the refined AC explicitly names.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|---|---|---|---|
| 1 | test-writer | Add readback assertions proving invalid parent text remains in the parent field after validation fires and after save is blocked | serve/cockpit/web/src/__tests__/DetailTab_1378.test.tsx | AC1 fail; current proofs at DetailTab_1378.test.tsx:124-131 and DetailTab_1378.test.tsx:166-173 cover error and no-submit only; live binding is at DetailTab.tsx:342-344 |
| 2 | test-writer | Add readback assertions proving invalid depends_on text remains in the depends_on field after validation fires and after save is blocked | serve/cockpit/web/src/__tests__/DetailTab_1378.test.tsx | AC2 fail; current proofs at DetailTab_1378.test.tsx:260-267 and DetailTab_1378.test.tsx:321-328 cover error and no-submit only; live binding is at DetailTab.tsx:333-335 |

No builder retry is needed unless the strengthened tests expose a real implementation regression.
[[2026-05-08]]
## Test-Writer Notes
- Retry: added 4 readback assertions for reviewer gaps (AC1 + AC2 preserved clause).
- Test file: serve/cockpit/web/src/__tests__/DetailTab_1378.test.tsx
- New tests added to existing classes: TestFromAC_InvalidParentValidation (+2), TestFromAC_InvalidDependsOnValidation (+2)
- Tests per category: happy 4, edge 0, error 0, boundary 0
- All 28 tests (24 existing + 4 new) pass against current DetailTab.tsx — Step 1b.1 applies.
- ESLint: clean (exit 0)
- AC coverage:
  | AC Line | Test(s) | Status |
  |---------|---------|--------|
  | AC1: Invalid parent preserved, shown, never sent | TestFromAC_InvalidParentValidation (8 tests incl. 2 new readbacks) | PASS |
  | AC2: Invalid depends_on preserved, shown, never dropped | TestFromAC_InvalidDependsOnValidation (8 tests incl. 2 new readbacks) | PASS |
  | AC3–AC6 | Unchanged from prior cycle | PASS |
- Builder skip: test-only retry, all tests green. Advance directly to review.
[[2026-05-08]]
Test-only retry — builder skip. All 28 tests green (24 existing + 4 new readback proofs). Advancing to review directly per Step 1b.1.
[[2026-05-09]]
## Review Evidence
### Test Results
- quality-runner scoped frontend pass from serve/cockpit/web: 107 passed, 0 failed.
- Files exercised: serve/cockpit/web/src/__tests__/DetailTab_1378.test.tsx, serve/cockpit/web/src/__tests__/DetailTab_1379.test.tsx, serve/cockpit/web/src/__tests__/ErrorContract_1374.test.tsx, serve/cockpit/web/src/__tests__/DetailTab_1344.test.tsx, serve/cockpit/web/src/__tests__/DetailTab.test.tsx.

### Lint Results
- ESLint clean for serve/cockpit/web/src/components/DetailTab.tsx and the five review suites.
- VS Code diagnostics clean for serve/cockpit/web/src/components/DetailTab.tsx, serve/cockpit/web/src/__tests__/DetailTab_1378.test.tsx, serve/cockpit/web/src/__tests__/DetailTab_1379.test.tsx, serve/cockpit/web/src/__tests__/ErrorContract_1374.test.tsx, serve/cockpit/web/src/__tests__/DetailTab_1344.test.tsx, and serve/cockpit/web/src/__tests__/DetailTab.test.tsx.

### Coverage
- DetailTab.tsx coverage from the scoped run: 94.33% statements, 93.29% branches, 80.55% functions, 93.54% lines.
- Uncovered lines: 353, 367, 379, 405, 419. These are edge paths and do not invalidate the task acceptance criteria.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| AC1: Invalid parent input is preserved, shown, and never sent | Raw parent text remains in local string state and the controlled input at DetailTab.tsx:61 and 342; client validation blocks submit at DetailTab.tsx:127 and 193; retry-added readback proofs are at DetailTab_1378.test.tsx:241 and 267, with no-submit proofs at DetailTab_1378.test.tsx:155, 178, and 219. | TestFromAC_InvalidParentValidation | PASS |
| AC2: Invalid dependency entries are preserved, shown, and never silently dropped | Raw depends_on text remains in local string state and the controlled input at DetailTab.tsx:60 and 333; client validation blocks submit at DetailTab.tsx:127 and 193; retry-added readback proofs are at DetailTab_1378.test.tsx:433 and 459, with no-submit proofs at DetailTab_1378.test.tsx:364, 387, and 410. | TestFromAC_InvalidDependsOnValidation | PASS |
| AC3: Dirty indicator is visible when values differ, clears on restore, and validation blocks save | Dirty-state comparison is at DetailTab.tsx:129 and renders at DetailTab.tsx:376; validation blocks save at DetailTab.tsx:193; DOM proofs are at DetailTab_1378.test.tsx:550, 570, 589, and 608, with validation-block proofs in the same suite. | TestFromAC_DirtyStateSignal and TestFromAC_SaveBlockedOnValidationError | PASS |
| AC4: Client-side and server-side validation errors use the same DOM element | Shared validation message render point is at DetailTab.tsx:412 with merged client and server message flow at DetailTab.tsx:127 and 137; client-side proofs are at DetailTab_1378.test.tsx:639 and 660; server-side error-contract proofs are at ErrorContract_1374.test.tsx:341, 375, 575, and 674. | TestFromAC_ValidationErrorVisibility plus adjacent error-contract suites | PASS |
| AC5: Existing valid parent and dependency edits continue to save correctly | Task-local payload proofs are at DetailTab_1379.test.tsx:96 and 122; the edit payload still uses parsed parent and dependency values at DetailTab.tsx:202 and 203. | TestFromAC_ValidEditsStillSave | PASS |
| AC6: No new action-gating or later-task conflict behavior was added | Save remains ungated on a clean valid form at DetailTab_1379.test.tsx:158 and 170; the conflict modal behavior is pre-existing and proven in DetailTab.test.tsx:312, 331, and 351, so this task did not add new conflict ownership. | TestFromAC_NoExtraActionGating plus durable conflict coverage | PASS |

### Critical Checks
- Test-writer audit: all AC lines covered with discriminating assertions.
- Test integrity: strengthened. The retry added four exact readback assertions in DetailTab_1378.test.tsx and no weakened or removed TestFromAC assertions were found.
- Security review: no issues found in scope.
- Data safety: no issues found in scope.
- Necessity check: not applicable for this bug-fix task.

### Deductions
- 0.02: Direct git diff and dirty-tree status checks were not available in this tool surface. Ownership was reconstructed from the task body, the builder-skip retry note, and git log evidence for commit e6feb8ac.

### Verdict
- Confidence: 0.96
- PASS
- Route: docs
- Reason: The retry-added readback assertions close the prior AC1 and AC2 proof gap, the scoped and adjacent suites are green, and no critical review issue remains.
[[2026-05-09]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | No README or setup doc references task detail validation. |
| 2 | Module docstrings | No | N/A | No Python modules created or modified. Task is Cockpit frontend only. |
| 3 | External attribution | No | N/A | No external patterns cited in task body. |
| 4 | Research doc | No | N/A | No research doc produced. |
| 5 | Diagram maintenance (describes match) | No | N/A | No diagram describes-glob matches frontend test files. |
| 6 | Explicit diagram creation | No | N/A | No diagram creation requested. |
| 7 | Deletion detection | No | N/A | No files deleted; no orphaned IN-scope docs. |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| serve/cockpit/web/src/components/DetailTab.tsx | OUT | App source (TypeScript) — not IN-scope |
| serve/cockpit/web/src/__tests__/DetailTab_1378.test.tsx | OUT | Test file — not IN-scope |
| serve/cockpit/web/src/__tests__/DetailTab_1379.test.tsx | OUT | Test file — not IN-scope |

**No docs impact.** All changed files are frontend TypeScript (app source and tests). Builder cycle changed no files (implementation pre-completed by #1378 builder). All seven checklist items resolve to N/A.

### Files Updated
- None

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no 1379-* scratch files found)
[[2026-05-09]]
## Audit\n### AC Verification\n| AC Line | Evidence | Status |\n|---------|----------|--------|\n| AC1: Invalid parent preserved, shown, never sent | Readback assertions at DetailTab_1378.test.tsx:241,267; no-submit proofs at :155,:178,:219; implementation at DetailTab.tsx:342-344 | PASS |\n| AC2: Invalid depends_on preserved, shown, never dropped | Readback assertions at DetailTab_1378.test.tsx:433,459; no-submit proofs at :364,:387,:410; implementation at DetailTab.tsx:333-335 | PASS |\n| AC3: Dirty indicator visible, validation blocks save | DOM proofs at DetailTab_1378.test.tsx:550,570,589,608; validation block at DetailTab.tsx:193 | PASS |\n| AC4: Validation errors use error-contract DOM element | Client proofs at DetailTab_1378.test.tsx:639,660; server proofs in ErrorContract_1374.test.tsx | PASS |\n| AC5: Valid parent/dependency edits continue to save | DetailTab_1379.test.tsx:96,122 | PASS |\n| AC6: No action-gating or conflict-resolution added | DetailTab_1379.test.tsx:158,170; builder changed no files | PASS |\n\n### Test Results\n- Task-scoped: 28/28 passed (DetailTab_1378 24, DetailTab_1379 4)\n- Full Python suite: 4702 passed, 460 failed (all outside scope: kanban engine, mcp-kanban, mcp-knowledge)\n- Full frontend suite: 1163 passed, 17 failed (all outside scope: DecisionContract, ErrorContract, PdsMigration, ResolveModal, Shell)\n- Lint: all violations pre-existing and outside scope\n\n### Architect Quality: 4/5\nOriginal AC3 was vague; architect self-corrected after challenger. Refined ACs were specific enough to drive the review gap detection on AC1/AC2 preserved clause.\n\n### Deduction Breakdown\n- Start: 1.00\n- AC lines without evidence: 0 (all 6 PASS)\n- Lint violations in scope: 0\n- AC quality (4/5, above threshold): 0\n- Reviewer evidence section: present and detailed, 0\n- Full-suite failures in task scope: 0\n- Pre-existing suite noise (460 Python, 17 frontend outside scope): -0.01\n\n### Confidence: 0.99\n### Action: archive