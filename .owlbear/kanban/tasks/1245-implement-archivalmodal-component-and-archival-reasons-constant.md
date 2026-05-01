---
id: 1245
title: 'Implement: ArchivalModal component and ARCHIVAL_REASONS constant'
status: backlog
priority: needed
created: 2026-05-01T03:08:07.623554+00:00
updated: 2026-05-01T20:19:01.181068+00:00
tags:
- scope:frontend
parent: 1238
depends_on:
- 1241
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Acceptance Criteria

- `ARCHIVAL_REASONS` constant defined with order: `completed → dropped → wontfix → deprecated → duplicate`
- `ArchivalModal` component created at `components/ArchivalModal.tsx`
- All state, rendering, a11y, submission, and error-handling behaviours specified in brief F2 are implemented:
  - `role="dialog"`, `aria-modal="true"`, `aria-labelledby` pointing to visible title
  - Focus on reason dropdown at open; focus trap for Tab/Shift+Tab; Escape closes without move
  - `completed` option hidden when `taskStatus !== "done"`
  - Refs field visible only for `deprecated` and `duplicate`; refs state cleared on reason change
  - Submit disabled when no reason, when refs required and empty, or when `isSubmitting`
  - Hint text displayed below refs field when visible: "Required — enter at least one task ID"
  - Client-side NaN guard before firing POST; inline error shown on validation failure
  - 422: stays open, renders `error.detail` verbatim; 409: stays open, stale error; success: close and refresh
- All tests from #1241 pass

## In Scope

- `components/ArchivalModal.tsx` (new file)
- `ARCHIVAL_REASONS` constant (in `KanbanBoard.tsx` or a shared constants file)

## Out of Scope

- `handleTransitionClick` intercept (F3 task #1246)
- Backend changes

## Brief reference

Brief: `.owlbear/briefs/draft-archival-ux/brief.md` — Frontend Changes F1, F2
[[2026-05-01]]
## Test-Writer Notes
- Test file: serve/cockpit/web/src/__tests__/ArchivalModal_1245.test.tsx
- Classes: TestFromAC_ArchivalModal_RefsPlaceholder
- Tests per category: happy 2, edge 0, error 0, boundary 1
- Total: 3 tests, all FAIL
- lint (eslint): clean

**Coverage gap addressed:**
`ArchivalModal_1241.test.tsx` (46 tests, all green) covers every AC sub-bullet already, since the component was pre-built. The only gap from brief F2 not in 1241: the refs `<input>` must have `placeholder="e.g., 1230, 1229"`. The current component omits this attribute entirely. All 3 new tests confirm RED via `expected null to be 'e.g., 1230, 1229'`.

**AC coverage:**
| AC line | Covered by |
|---|---|
| ARCHIVAL_REASONS constant order | ArchivalModal_1241 |
| Component created at components/ArchivalModal.tsx | ArchivalModal_1241 (import) |
| role/aria-modal/aria-labelledby | ArchivalModal_1241 AC2 |
| Focus on open / focus trap / Escape | ArchivalModal_1241 AC3/15/16 |
| completed hidden / refs visibility / refs clear | ArchivalModal_1241 AC4/5/6 |
| Submit disabled states (3 conditions) | ArchivalModal_1241 AC7/8/9 |
| Hint text / NaN guard / 422/409/success | ArchivalModal_1241 AC10/11/12/13/14 |
| refs input placeholder "e.g., 1230, 1229" | **ArchivalModal_1245.test.tsx** (new, RED) |

Commit: 0c375f91

[[2026-05-01]]
## Builder Notes
- Files changed: `serve/cockpit/web/src/components/ArchivalModal.tsx`
- Fix applied: added `placeholder="e.g., 1230, 1229"` to the refs `<input>` shown for `deprecated`/`duplicate` reasons.
- Scope discipline: single-line surgical fix for the known AC gap from #1241/#1245; no unrelated edits.

### Test Results
- Targeted frontend tests (Vitest): 49 passed, 0 failed
  - `serve/cockpit/web/src/__tests__/ArchivalModal_1245.test.tsx` (3 tests)
  - `serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx` (46 tests)
- Evidence: prior RED reproduced (`expected null/'' to be 'e.g., 1230, 1229'`), then GREEN after fix.

### Lint Status
- ESLint (scoped to changed files): clean, 0 violations.
- Ruff: not applicable for this TypeScript frontend change.

### Coverage
- Frontend coverage not measured in quality-runner scoped TS flow for this task; correctness gate satisfied via full relevant Vitest suite pass.

### Evidence Summary
- AC gap closed: refs input now includes exact placeholder string required by brief F2 and enforced by #1245 tests.
- Regression safety: #1241 archival modal test suite remains green after change.
[[2026-05-01]]
## Review Evidence
### Test Results
- quality-runner scoped run on `serve/cockpit/web/src/__tests__/ArchivalModal_1245.test.tsx` and `serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx`: 3 passed, 46 failed, 0 skipped.
- The only passing tests were the non-render constant-order checks. All render-dependent assertions aborted at `render()` with `ReferenceError: document is not defined`, including the new placeholder proofs at `serve/cockpit/web/src/__tests__/ArchivalModal_1245.test.tsx:68`, `:75`, `:82` and the broader ArchivalModal behavior suite at `serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx:119`, `:145`, `:155`, `:185`, `:224`, `:250`, `:260`, `:289`, `:313`, `:358`, `:395`, `:425`, `:477`, `:493`, `:540`, `:559`, `:582`.
- Repo wiring indicates jsdom should be available: `serve/cockpit/web/vite.config.ts:51-57` sets `environment: 'jsdom'` with `setupFiles`, and `serve/cockpit/web/vitest.setup.ts:1-44` installs the cockpit jsdom polyfills. Other frontend suites in this package also use React Testing Library render helpers. This makes the failure a review-runner/context problem, not a proved ArchivalModal defect.

### Lint
- quality-runner: clean for `serve/cockpit/web/src/components/ArchivalModal.tsx`, `serve/cockpit/web/src/__tests__/ArchivalModal_1245.test.tsx`, and `serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx`.

### Coverage
- Not measurable. The render-dependent tests aborted during environment bootstrap before meaningful component execution.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| `ARCHIVAL_REASONS` ordered `completed -> dropped -> wontfix -> deprecated -> duplicate` | `serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx:97` | Yes — exact array equality | COVERED |
| `ArchivalModal` file exists at `components/ArchivalModal.tsx` | direct file presence + imports in `serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx:29` and `serve/cockpit/web/src/__tests__/ArchivalModal_1245.test.tsx:14` | Yes | COVERED |
| Render/a11y/submission/error behaviors from brief F2, including placeholder | `serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx` and `serve/cockpit/web/src/__tests__/ArchivalModal_1245.test.tsx:68`, `:75`, `:82` | Yes — the tests are discriminating, but they never reached component behavior because the runner had no `document` | UNVERIFIED (runner failure) |

#### Security Review
- No security issues found in the inspected component. The request target is fixed (`serve/cockpit/web/src/components/ArchivalModal.tsx:153`), there is no dynamic code execution, and no unsafe HTML rendering.

#### Test Integrity
- No TestFromAC edits were identified from task evidence. Builder notes scoped changes to `serve/cockpit/web/src/components/ArchivalModal.tsx` only.
- The task body does not include a builder commit hash, so changed-file scope was reconstructed from builder notes and live file inspection.

#### Test Quality
- The mapped tests are strong. They use exact-value assertions for placeholder text (`serve/cockpit/web/src/__tests__/ArchivalModal_1245.test.tsx:68`, `:75`, `:82`), exact stale/422 strings (`serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx:395`, `:425`), exact success callbacks and payload assertions (`serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx:477`, `:493`), and exact focus-trap / Escape behavior (`serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx:540`, `:559`, `:582`).

#### Data Safety
- No issues found in inspected code.

#### Implementation-Aware Test Gap Analysis
- Live implementation includes the placeholder at `serve/cockpit/web/src/components/ArchivalModal.tsx:223` and the broader F2 logic across `serve/cockpit/web/src/components/ArchivalModal.tsx:60-247`.
- Because quality-runner never initialized jsdom, the review could not independently prove those render-based paths.

#### Necessity Check
- N/A. No new dependency, integration, or external capability was added.

#### Builder Process Quality
- CLEAN. One `## Builder Notes` section exists in `.owlbear/kanban/tasks/1245-implement-archivalmodal-component-and-archival-reasons-constant.md:74`.
- No prior `## Review Evidence` section exists in `.owlbear/kanban/tasks/1245-implement-archivalmodal-component-and-archival-reasons-constant.md`.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| `ARCHIVAL_REASONS` constant order | `serve/cockpit/web/src/components/ArchivalModal.tsx:3-8`; `serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx:97` | `TestFromAC_ArchivalModal` AC1 | PASS |
| `components/ArchivalModal.tsx` created | File exists at `serve/cockpit/web/src/components/ArchivalModal.tsx`; imported by both test files | import/compile contract | PASS |
| Brief F2 render/a11y/submission/error behavior bundle | Source present at `serve/cockpit/web/src/components/ArchivalModal.tsx:60-247`; intended proofs at `serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx:119`, `:145`, `:155`, `:185`, `:224`, `:250`, `:260`, `:289`, `:313`, `:358`, `:395`, `:425`, `:477`, `:493`, `:540`, `:559`, `:582` | `TestFromAC_ArchivalModal` | UNVERIFIED — runner failed before render |
| Placeholder `e.g., 1230, 1229` | Source at `serve/cockpit/web/src/components/ArchivalModal.tsx:223`; intended proofs at `serve/cockpit/web/src/__tests__/ArchivalModal_1245.test.tsx:68`, `:75`, `:82` | `TestFromAC_ArchivalModal_RefsPlaceholder` | UNVERIFIED — runner failed before render |

### Deductions
- `-0.55` required independent frontend proof did not execute under quality-runner because jsdom was not initialized.
- `-0.08` builder commit hash absent from the task body, so diff scoping relied on notes rather than a builder commit reference.

### Verdict
- FAIL with confidence `0.37`.
- Reason: the required review harness did not provide usable frontend evidence. This is not a proved component regression, but it also is not a reviewable green state.

### Action
- Stayed in `review` via `end_work(outcome="fail")`.
- Re-run the review once `quality-runner` launches the cockpit Vitest suite with the repo's jsdom config active.
[[2026-05-01]]
## Review Evidence
### Test Results
- quality-runner scoped frontend run: 49 passed, 0 failed, 0 skipped.
- `serve/cockpit/web/src/__tests__/ArchivalModal_1245.test.tsx`: 3 passed.
- `serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx`: 46 passed.
- Prior review blocker resolved: the current quality-runner run executed the frontend suite successfully with no `document is not defined` failure.
- One non-fatal React `act()` warning was emitted from `serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx:289`; it did not affect pass/fail outcome.

### Lint
- quality-runner ESLint: clean for `serve/cockpit/web/src/components/ArchivalModal.tsx`, `serve/cockpit/web/src/__tests__/ArchivalModal_1245.test.tsx`, and `serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx`.
- VS Code diagnostics: no errors in the same three files.

### Coverage
- Not measured. Cockpit frontend TypeScript/Vitest coverage is outside the current quality-runner scope, so this gate rests on targeted Vitest proof plus zero diagnostics on the touched files.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| `ARCHIVAL_REASONS` ordered `completed -> dropped -> wontfix -> deprecated -> duplicate` | `serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx:97` | Yes — exact array equality | COVERED |
| `ArchivalModal` exists/exported from `components/ArchivalModal.tsx` | imports at `serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx:29` and `serve/cockpit/web/src/__tests__/ArchivalModal_1245.test.tsx:15` | Yes — import/render would fail | COVERED |
| `role="dialog"`, `aria-modal="true"`, `aria-labelledby` | `serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx:119`, `:125`, `:131` | Yes — exact attribute checks | COVERED |
| Focus on open; focus trap; Escape closes without move | `serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx:145`, `:540`, `:559`, `:582`, `:594` | Yes — exact `document.activeElement`, callback, and no-fetch assertions | COVERED |
| `completed` hidden when `taskStatus !== "done"` | `serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx:155`, `:164` | Yes — option absence/presence assertions | COVERED |
| Refs visible only for `deprecated`/`duplicate`; refs cleared when switching to non-refs reason | `serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx:185`, `:191`, `:203`, `:224`, `:235` | Yes — direct DOM visibility and value-reset assertions | COVERED |
| Submit disabled when no reason, when refs required and empty, or when `isSubmitting` | `serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx:250`, `:260`, `:266`, `:289` | Yes — disabled/enabled state asserted across each branch | COVERED |
| Hint text shown with refs field | `serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx:313`, `:319`, `:325` | Yes — exact content presence/absence | COVERED |
| Client-side NaN guard before POST; inline error on validation failure | `serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx:340`, `:358`, `:375` | Yes — invalid refs prevent fetch, valid refs allow fetch | COVERED |
| 422 verbatim detail; 409 stale error; success closes and refreshes | `serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx:395`, `:425`, `:450`, `:477`, `:517` | Yes — exact text/callback/payload assertions | COVERED |
| Placeholder `e.g., 1230, 1229` when refs field is visible | `serve/cockpit/web/src/__tests__/ArchivalModal_1245.test.tsx:68`, `:75`, `:82` | Yes — exact placeholder equality, including boundary text | COVERED |

#### Security Review
- No issues found. The component posts only to the fixed route at `serve/cockpit/web/src/components/ArchivalModal.tsx:153`, validates refs client-side at `:145`, and does not render unsafe HTML or execute dynamic code.

#### Test Integrity
- No TestFromAC weakening observed in the current files.
- Task body builder notes scope changes to `serve/cockpit/web/src/components/ArchivalModal.tsx` only.
- Git metadata confirms the test-writer commit `0c375f9102c31f90c453397a06a1259a142f4d38` in `.git/logs/refs/heads/dev:1257`; no explicit `#1245, builder` commit was found in `.git/logs/**`, so changed-file provenance carries a small confidence deduction.

#### Test Quality
- STRONG. Assertions are discriminating: exact placeholder text at `serve/cockpit/web/src/__tests__/ArchivalModal_1245.test.tsx:68`, `:75`, `:82`; exact a11y attributes at `serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx:119`, `:125`, `:131`; exact stale/422 strings at `:395`, `:450`; exact success callbacks/payload at `:477`, `:517`; and exact focus-trap / Escape behavior at `:145`, `:540`, `:559`, `:582`, `:594`.

#### Data Safety
- No issues found.

#### Implementation-Aware Test Gap Analysis
- Source matches the tested contract: export/order at `serve/cockpit/web/src/components/ArchivalModal.tsx:3`, initial focus at `:77`, key handling at `:94-121`, refs visibility at `:60` and `:218-223`, refs clearing at `:127-134`, submit disable rules at `:63-70`, client-side validation at `:145`, POST payload at `:153-159`, 409/422/success handling at `:165-179`, and hint text at `:230`.
- Brief F2 wording on stale refs is satisfied as implemented: `.owlbear/briefs/draft-archival-ux/brief.md:194` requires clearing only when switching from a refs-requiring reason to any other reason, which matches `serve/cockpit/web/src/components/ArchivalModal.tsx:133` and the proofs at `serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx:224`, `:235`.
- No significant untested path found for the changed placeholder fix or the surrounding F2 logic already covered by #1241.

#### Necessity Check
- N/A. No new dependency or external integration.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Prior Review Evidence sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- One non-fatal React `act()` warning was emitted during `serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx:289`. The assertion still proves the `isSubmitting` branch, but the test could be tightened later to eliminate stderr noise.
- Builder commit provenance is incomplete; functional proof is still strong enough to pass.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| `ARCHIVAL_REASONS` constant order | `serve/cockpit/web/src/components/ArchivalModal.tsx:3`; `serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx:97` | `TestFromAC_ArchivalModal` AC1 | PASS |
| `components/ArchivalModal.tsx` created/exported | `serve/cockpit/web/src/components/ArchivalModal.tsx:44`; `serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx:29`; `serve/cockpit/web/src/__tests__/ArchivalModal_1245.test.tsx:15` | import/compile contract | PASS |
| Modal a11y, initial focus, focus trap, Escape-close | `serve/cockpit/web/src/components/ArchivalModal.tsx:77`, `:94-121`, `:191`; `serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx:119`, `:125`, `:131`, `:145`, `:540`, `:559`, `:582`, `:594` | `TestFromAC_ArchivalModal` AC2/3/15/16 | PASS |
| `completed` gating, refs visibility/reset, submit disable states, hint text | `serve/cockpit/web/src/components/ArchivalModal.tsx:60`, `:63-70`, `:127-134`, `:205`, `:218-230`; `serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx:155`, `:164`, `:185`, `:191`, `:203`, `:224`, `:235`, `:250`, `:260`, `:266`, `:289`, `:313`, `:319`, `:325` | `TestFromAC_ArchivalModal` AC4-10 | PASS |
| Client-side validation + 422/409/success behaviors | `serve/cockpit/web/src/components/ArchivalModal.tsx:145`, `:153`, `:165-179`; `serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx:340`, `:358`, `:375`, `:395`, `:425`, `:450`, `:477`, `:517` | `TestFromAC_ArchivalModal` AC11-14 | PASS |
| Placeholder `e.g., 1230, 1229` | `serve/cockpit/web/src/components/ArchivalModal.tsx:223`; `serve/cockpit/web/src/__tests__/ArchivalModal_1245.test.tsx:68`, `:75`, `:82` | `TestFromAC_ArchivalModal_RefsPlaceholder` | PASS |
| All tests from #1241 pass | quality-runner: 46/46 passing in `serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx` | suite gate | PASS |

### Deductions
- `-0.02` no builder commit hash recorded in the task body and no explicit `#1245, builder` commit found in `.git/logs/**`.
- `-0.02` one non-fatal React `act()` warning in the AC9 test.

### Confidence: 0.94
### Verdict: PASS
[[2026-05-01]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | Changed files are TypeScript component/tests; no IN-scope README references ArchivalModal internals |
| 2 | Module docstrings | No | N/A | No Python modules modified |
| 3 | External attribution | No | N/A | Fix is a single `placeholder` attribute addition; no external patterns used |
| 4 | Research doc | No | N/A | No research doc produced or referenced in task body |
| 5 | Diagram maintenance (describes match) | No | N/A | No IN-scope diagram describes `serve/cockpit/web/src/components/**` |
| 6 | Explicit diagram creation | No | N/A | No diagram creation request in task body |
| 7 | Deletion detection | No | N/A | No files deleted |

**No docs impact.** All seven items resolve to N/A.

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| serve/cockpit/web/src/components/ArchivalModal.tsx | OUT | N/A (TypeScript frontend component) |
| serve/cockpit/web/src/__tests__/ArchivalModal_1245.test.tsx | OUT | N/A (TypeScript test file) |
| serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx | OUT | N/A (TypeScript test file) |

### Files Updated
- None

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no `.owlbear/scratch/1245-*` files found)
[[2026-05-01]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| ARCHIVAL_REASONS constant order | Committed at ArchivalModal.tsx:3-8; test at ArchivalModal_1241.test.tsx:97 passes | PASS |
| ArchivalModal component at components/ArchivalModal.tsx | File committed; imports succeed in both test files | PASS |
| Brief F2 render/a11y/submission/error behaviors | Source committed at ArchivalModal.tsx:60-247; 46 tests pass in ArchivalModal_1241.test.tsx | PASS |
| Placeholder "e.g., 1230, 1229" on refs input | Working-tree-only fix at line 223; NOT in git HEAD. 3 tests pass in working tree but would FAIL on clean checkout | FAIL (uncommitted) |
| All tests from 1241 pass | 46/46 pass | PASS |

### Test Results
- Frontend (vitest, working tree): 49 passed, 0 failed
- Frontend (git HEAD state): 3 tests would fail (placeholder assertions get null)
- Python (full suite): pre-existing failures in unrelated modules; no regressions from this task
- ESLint (task files): clean

### Reviewer Evidence
- Present, detailed, PASS verdict with confidence 0.94
- Reviewer flagged "no builder commit hash" but underestimated the severity (file is actually uncommitted, not just missing a reference)

### Architect Quality: 4/5
AC was specific and verifiable. Test-writer correctly identified a brief F2 gap (placeholder) not in the original AC. All items testable.

### Deduction Breakdown
- -.05: Builder deliverable uncommitted. Tests pass in working tree but fail on HEAD (3 placeholder assertions). This is a full-suite regression on committed state.
- -.02: No builder commit exists anywhere in git history for task 1245.

### Confidence: .93
### Action: reject to backlog

### Reason
Builder's 1-line fix (placeholder attribute) exists in working tree but was never committed. On a clean checkout of HEAD, ArchivalModal_1245.test.tsx fails 3/3 tests. The auditor cannot commit source code belonging to upstream agents per protocol. Builder must commit their change before this task can be archived.