---
id: 1574
title: 'P2-14 RED: Specify column polish and empty-state behavior'
status: archived
priority: needed
created: 2026-05-14T18:33:43.120318+00:00
updated: 2026-05-15T02:02:22.164688+00:00
tags:
  - phase-2
  - scope:cockpit
  - frontend
  - type:test
  - columns
  - empty-states
  - visual-remediation
parent: 1559
depends_on:
  - 1560
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Context
Source of truth: `.owlbear/research/cockpit-visual-audit-consolidated-2026-05-14.md` sections 6 and 8. Planner audit found the initial remediation graph under-owned column polish: empty states, status labels, and scrollable column-body focusability could otherwise be buried inside responsive work.

Design policy: `.owlbear/research/1560-cockpit-design-policy.md` section 6 — "Columns must use polished labels, count badges, focusable scroll regions, and intentional empty states."

Codebase targets: `serve/cockpit/web/src/components/Column.tsx` (column component), `serve/cockpit/web/src/components/Column.css` (column styles).

Current state:
- Header renders raw `{status}` string in DOM (line 63); CSS `text-transform: capitalize` (Column.css line 22) visually capitalizes single words but fails for hyphenated statuses (`in-progress` → `In-progress` not `In Progress`).
- Empty state renders `No {status} tasks` (line 67) with font-size 0.875rem and opacity 0.6 (Column.css lines 51-52). Header font-size is 0.8125rem — empty text is currently LARGER than header.
- `.column-body` has `overflow-y: auto` but no `tabIndex` or ARIA role (line 65).
- Count badge: `.column-count` renders `tasks.length` in 0.75rem with background shading (Column.css lines 25-30).

Existing test patterns: `Column_1539.test.tsx` (unit), `ColumnCSS_1547.test.ts` (CSS structural), `accessibility-1395.spec.ts` (E2E axe).

## Scope
In scope: column headers, status label display names, empty-state treatment, count badge clarity, keyboard focusability for scrollable column bodies, and column/card spacing interaction.
Out of scope: card metadata content, sidecar layout, filter controls, and mobile shell contract beyond column-specific assertions.

## Acceptance Criteria
AC-1: Test-writer adds a vitest unit test rendering Column with each board status and asserting DOM `textContent` of the header label span is a human-readable string with hyphens replaced by spaces and each word capitalized (e.g., `in-progress` → `In Progress`, `todo` → `Todo`) — must be JS-normalized text, not relying on CSS `text-transform`; verify by named test output.
AC-2: Test-writer adds DOM assertions for empty columns verifying: (a) empty-state text uses the polished label from AC-1 rather than raw API strings (rejects `No in-progress tasks`), (b) the container has `data-testid="empty-column"`, and (c) a CSS structural test (per `ColumnCSS_1547.test.ts` pattern) asserts `.column-empty` font-size ≤ `.column header` font-size and opacity < 1; verify by named test output.
AC-3: Test-writer adds an axe proof scoped to column-body elements (include selector: `[data-testid="column-body"]`) asserting zero violations for rule `scrollable-region-focusable` per scrollable column; verify by axe or Playwright output. Must not rely on whole-page axe scans that conflate card-level violations.
AC-4: Test-writer adds a unit test asserting each column header renders a count badge (`data-testid="column-count"`) with numeric task count and font-size smaller than the header label; verify by named test output or CSS structural assertion.
AC-5: Test-writer records current failing/weak evidence from the audit (raw `in-progress` in DOM, empty-state text `No in-progress tasks`, missing `tabIndex` on `.column-body`, empty font-size > header font-size); verify by task-body Test Evidence section.

Proof bundle: behavioral

## Evidence Expectations
Failing column-polish unit tests, axe/focusability evidence scoped to column-body, CSS structural assertions, and screenshot references from `.owlbear/scratch/cockpit-visual-audit/`.
2026-05-14T20:37:16+00:00
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Column polish tests — one coherent visual concern (labels, empty states, focusability, badges) |
| Interface clarity | PASS | After refinement — AC lines name concrete targets, DOM assertions, CSS structural patterns, and scoped axe rules |
| Dependency correctness | PASS | Depends on #1560 (archived/completed). GREEN pair #1575 depends on #1574 |
| Module layering | N/A | Test task — targets Column.tsx/Column.css, no upward imports |
| TDD compliance | PASS | This IS the RED task; GREEN pair is #1575 |
| KISS/YAGNI | PASS | Minimal scope for column-surface tests |
| Premise challenge | PASS | Audit section 6 confirms: raw API strings leak, empty states are plain, column bodies lack keyboard focus. Verified in Column.tsx lines 63/67 and Column.css (no tabIndex) |
| Pattern consistency | PASS | Follows existing test patterns: Column_1539.test.tsx (unit), ColumnCSS_1547.test.ts (CSS structural), accessibility-1395.spec.ts (E2E axe) |
| Security surface | N/A | No system boundaries |
| Single domain | PASS | Cockpit frontend only |
| User-action detection | NOT DETECTED | Counter-signals C1 (DOM assertion targets), C2 (expected test outcomes), C3 (tagged type:test) all present |

### AC Assessment (post-refinement)
| AC Line | Assessment | Action |
|---------|-----------|--------|
| AC-1 (label normalization) | PASS — B1: names Column + header span; B2: input=status strings, output=Title Case DOM textContent; B3: no naked quantifiers. Explicitly distinguishes JS normalization from CSS text-transform | Refined to specify DOM textContent, not CSS visual |
| AC-2 (empty state) | PASS — B1: names empty-column container, ColumnCSS pattern; B2: concrete assertions (text, data-testid, font-size ≤ header, opacity < 1) | Refined with CSS structural pattern and concrete thresholds |
| AC-3 (focusability) | PASS — B1: names column-body + axe rule; B2: zero violations scoped to selector. Explicitly excludes whole-page scans | Refined with include selector isolation |
| AC-4 (count badge) | PASS — B1: names column-count badge; B2: numeric count + font-size < header. Closes the scope/AC gap identified by challenger | Added (was missing from original AC) |
| AC-5 (evidence record) | PASS — P1: names test-writer; P2: Test Evidence section; P3: artifact inspection | Renumbered from AC-4, lists specific current failures |

### Challenge Results
- Challenger: reconsider (confidence 0.57)
- Findings addressed: (1) count-badge AC gap → added AC-4, (2) DOM vs CSS ambiguity → AC-1 specifies DOM textContent explicitly, (3) AC-2 non-decidable criteria → replaced with concrete CSS structural assertions, (4) AC-3 page-level conflation → scoped to column-body selector, (5) normalization boundary → context section documents CSS capitalize limitation
- Architect response: accepted all findings, revised AC accordingly

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED

### Design Diverge
- Trigger: skipped — single clear approach (unit tests + CSS structural + scoped axe)

### Verdict: APPROVE
### Action Taken: Refined AC-1/AC-2/AC-3 for mechanical decidability, added AC-4 (count badge), renumbered AC-5 (evidence). Advanced to todo. Pass-through tag `type:test` already present.
2026-05-14T21:27:30+00:00
## Test-Writer Notes

**Test file:** `serve/cockpit/web/src/__tests__/ColumnPolish_1574.test.tsx`
**E2E scratch file:** `.owlbear/scratch/1574-column-body-a11y.spec.ts` (builder must move to `serve/cockpit/web/e2e/column-body-a11y-1574.spec.ts`)

### Classes and test counts
| Class | AC | Tests | Status |
|---|---|---|---|
| `TestFromAC_ColumnHeaderLabel` | AC-1 | 3 | FAIL ✓ |
| `TestFromAC_ColumnEmptyStatePolish` | AC-2 | 3 | FAIL ✓ |
| `TestFromAC_ColumnCountBadge` | AC-4 | 3 | FAIL ✓ |
| `TestFromAC_ColumnBodyFocusability` (E2E) | AC-3 | 2 | Pending (scratch) |

**Total vitest: 9 tests, 9 FAIL, 0 pass — confirmed by quality-runner.**

### AC coverage table
| AC | Tests | Covered? |
|---|---|---|
| AC-1: header label JS normalization | `TestFromAC_ColumnHeaderLabel` × 3 | ✓ |
| AC-2a: empty-state polished text | `TestFromAC_ColumnEmptyStatePolish` × 2 | ✓ |
| AC-2b: `data-testid="empty-column"` | Combined in AC-2a tests (not.toBeNull) | ✓ |
| AC-2c: CSS font-size ≤ header, opacity < 1 | `TestFromAC_ColumnEmptyStatePolish` CSS test | ✓ |
| AC-3: axe `scrollable-region-focusable` scoped | E2E in scratch (builder move required) | Partial |
| AC-4: count badge + CSS font-size hierarchy | `TestFromAC_ColumnCountBadge` × 3 | ✓ |
| AC-5: test evidence | Documented below | ✓ |

### AC-5: Current Test Evidence (pre-remediation)
- **AC-1 evidence:** `header span:first-child` textContent = `"in-progress"` (raw) — CSS `text-transform: capitalize` produces `"In-progress"` visually, NOT `"In Progress"`. JS normalization missing.
- **AC-2 evidence:** `[data-testid="empty-column"]` textContent = `"No in-progress tasks"` (raw API string, not polished). Empty text font-size = 0.875rem > header 0.8125rem (empty text is LARGER than header).
- **AC-3 evidence:** `.column-body` has `overflow-y: auto` (Column.css line 39) but no `tabIndex` in Column.tsx line 65 → not keyboard-focusable. axe rule `scrollable-region-focusable` fires on overflowing columns.
- **AC-4 evidence:** Badge and count correct (existing), CSS font-size hierarchy correct (existing). AC-4 tests fail via AC-1 label assertion in combined tests.

### Failure modes confirmed
```
TestFromAC_ColumnHeaderLabel: "todo" ≠ "Todo" | "in-progress" ≠ "In Progress" | "done" ≠ "Done"
TestFromAC_ColumnEmptyStatePolish: "No in-progress tasks" ≠ "No In Progress tasks" | font-size 0.875 > 0.8125
TestFromAC_ColumnCountBadge: AC-1 label failures drive combined AC-1+AC-4 tests
```

### Builder instructions for AC-3 E2E
1. Move scratch file: `cp .owlbear/scratch/1574-column-body-a11y.spec.ts serve/cockpit/web/e2e/column-body-a11y-1574.spec.ts`
2. Verify it fails: `cd serve/cockpit/web && npm run test:e2e -- column-body-a11y-1574`
3. Fix: add `tabIndex={0}` to `.column-body` div in `Column.tsx` line 65
2026-05-14T22:23:34+00:00
## Builder Notes
- Status: REJECT (test-assumption mismatch in durable suite)
- Attempted implementation (not kept):
  - `serve/cockpit/web/src/components/Column.tsx`: JS label normalization + polished empty-state text + `tabIndex={0}` on `data-testid="column-body"`
  - `serve/cockpit/web/src/components/Column.css`: reduced `.column-empty` font-size to be <= header font-size
  - Copied scratch E2E spec to `serve/cockpit/web/e2e/column-body-a11y-1574.spec.ts`
- Task-scoped GREEN evidence during attempt:
  - Quality-runner (scoped) on `serve/cockpit/web/src/__tests__/ColumnPolish_1574.test.tsx` + `serve/cockpit/web/e2e/column-body-a11y-1574.spec.ts`: **11 passed, 0 failed**, lint clean
- Blocking mismatch discovered:
  - Quality-runner (scoped regression baseline) on durable tests:
    - `serve/cockpit/web/src/__tests__/Column_1539.test.tsx`
    - `serve/cockpit/web/src/__tests__/ColumnCSS_1547.test.ts`
  - Result: 3 failures in `TestFromAC_ColumnEmptyState` expecting legacy raw/lowercase strings (`No todo tasks`, `No in-progress tasks`) that conflict with AC-1/AC-2 polish contract (`No Todo tasks`, `No In Progress tasks`).
- Action taken:
  - Rolled back all implementation edits and removed copied E2E file to avoid partial GREEN residue.
  - Re-verified baseline after rollback:
    - Durable tests: **24 passed, 0 failed**, lint clean
    - Task RED file `serve/cockpit/web/src/__tests__/ColumnPolish_1574.test.tsx`: **0 passed, 9 failed** (expected RED state)

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Reconcile legacy durable empty-state assertions with #1574 AC polish contract (title-case/normalized status labels) so builder can implement without cross-suite contract conflict. | `serve/cockpit/web/src/__tests__/Column_1539.test.tsx`, `serve/cockpit/web/src/__tests__/ColumnPolish_1574.test.tsx` | quality-runner regression run: `Column_1539.test.tsx::TestFromAC_ColumnEmptyState` expected `No todo tasks` / `No in-progress tasks` while #1574 AC-2 expects `No Todo tasks` / `No In Progress tasks` |
| 2 | test-writer | Provide/restore tracked AC-3 E2E proof artifact path strategy in task body (scratch->tracked handoff currently operationally fragile) before next builder pass. | `.owlbear/scratch/1574-column-body-a11y.spec.ts`, `serve/cockpit/web/e2e/` | builder run required manual scratch lookup/copy; file presence/path should be explicitly stabilized for repeatable reruns |

2026-05-14T22:48:16+00:00
## Test-Writer Notes

**Retry cycle — reconciliation pass.**

### Changes

**1. Durable test reconciliation (Required Follow-up #1)**
- File: `serve/cockpit/web/src/__tests__/Column_1539.test.tsx`
- Updated `TestFromAC_ColumnEmptyState` (3 tests) to expect polished Title Case labels:
  - `No todo tasks` → `No Todo tasks`
  - `No research tasks` → `No Research tasks`
  - `No in-progress tasks` → `No In Progress tasks`
- Contract now consistent: `Column_1539` durable suite and `ColumnPolish_1574` task suite both assert the same polished label contract. Builder can implement once and both suites pass.

**2. E2E scratch file stability (Required Follow-up #2)**
- `.owlbear/scratch/1574-column-body-a11y.spec.ts` — updated BUILDER INSTRUCTION block to a "MANDATORY FIRST STEP" box with numbered commands (file exists on disk; scratch/ is gitignored by design).
- Scratch file contains `TestFromAC_ColumnBodyFocusability` with 2 axe tests for AC-3.

### Quality-runner evidence

| File | Class | Tests | Result |
|------|-------|-------|--------|
| `ColumnPolish_1574.test.tsx` | `TestFromAC_ColumnHeaderLabel` | 3 | FAIL ✓ |
| `ColumnPolish_1574.test.tsx` | `TestFromAC_ColumnEmptyStatePolish` | 3 | FAIL ✓ |
| `ColumnPolish_1574.test.tsx` | `TestFromAC_ColumnCountBadge` | 3 | FAIL ✓ |
| `Column_1539.test.tsx` | `TestFromAC_ColumnStructure` | 3 | PASS (durable baseline) |
| `Column_1539.test.tsx` | `TestFromAC_ColumnOverflow` | 3 | PASS (durable baseline) |
| `Column_1539.test.tsx` | `TestFromAC_ColumnEmptyState` | 3 | FAIL ✓ (now asserting polished strings — RED until builder implements) |

**ColumnPolish_1574: 9 tests, all FAIL. ESLint: clean.**

### Builder instructions for AC-3 E2E (MANDATORY FIRST STEP)

```bash
cp .owlbear/scratch/1574-column-body-a11y.spec.ts \
   serve/cockpit/web/e2e/column-body-a11y-1574.spec.ts
git add serve/cockpit/web/e2e/column-body-a11y-1574.spec.ts
cd serve/cockpit/web && npm run test:e2e -- column-body-a11y-1574
# → both tests must FAIL before touching Column.tsx (RED gate)
```

### Commit
`af5c926a` — `test: reconcile Column_1539 empty-state assertions with #1574 polish contract (#1574, test-writer)`
2026-05-14T23:31:16+00:00
## Builder Notes
- Implementation:
  - serve/cockpit/web/src/components/Column.tsx
  - serve/cockpit/web/src/components/Column.css
  - serve/cockpit/web/e2e/column-body-a11y-1574.spec.ts (tracked from scratch per task instruction)
- Approach:
  - Added JS status-label normalization (hyphens -> spaces, Title Case) via `toDisplayStatus()` and used normalized labels in both header and empty-state text.
  - Added `tabIndex={0}` on `[data-testid="column-body"]` to satisfy scoped axe `scrollable-region-focusable` expectations for overflowing columns.
  - Reduced `.column-empty` font-size from `0.875rem` to `0.75rem` so empty-state typography is <= header font-size and remains visually subordinate.
- RED verification (before implementation):
  - quality-runner scoped unit RED: 0 passed, 9 failed (`ColumnPolish_1574.test.tsx`)
  - quality-runner scoped E2E RED: 0 passed, 2 failed (`column-body-a11y-1574.spec.ts`)
- GREEN verification (after implementation):
  - quality-runner scoped tests:
    - `serve/cockpit/web/src/__tests__/ColumnPolish_1574.test.tsx`
    - `serve/cockpit/web/e2e/column-body-a11y-1574.spec.ts`
    - `serve/cockpit/web/src/__tests__/Column_1539.test.tsx`
    - `serve/cockpit/web/src/__tests__/ColumnCSS_1547.test.ts`
  - Result: 35 passed, 0 failed, 0 skipped
  - Lint: clean (`eslint` + `stylelint` clean from quality-runner output)
  - Coverage: not reported by quality-runner for this frontend scoped run
- Commit:
  - dd4b666956ed5d91d721dc22ae58ab17f6c27e90
  - `feat: polish column labels, empty state, and focusability (#1574, builder)`
2026-05-15T00:12:03+00:00
## Review Evidence
- Verdict: FAIL
- Routing verdict: FAIL #1574 to todo | AC-1 and AC-3 proof remains insufficient even though the scoped implementation run passes.
- Independent verification: quality-runner rerun on `serve/cockpit/web/src/__tests__/ColumnPolish_1574.test.tsx`, `serve/cockpit/web/src/__tests__/Column_1539.test.tsx`, `serve/cockpit/web/src/__tests__/ColumnCSS_1547.test.ts`, and `serve/cockpit/web/e2e/column-body-a11y-1574.spec.ts` reported 35 passed, 0 failed, 0 skipped; eslint clean; stylelint clean; Playwright clean; frontend coverage overall 57.14 with `Column.tsx` at 66.21. This points to a proof gap for test-writer, not an implementation defect for builder.
- Blocking findings:
| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC-1 | Header-label proof does not cover each board status as required. The added named tests only exercise `todo`, `in-progress`, and `done`. | AC-1 in `.owlbear/kanban/tasks/1574-p2-14-red-specify-column-polish-and-empty-state-behavior.md:45`; named tests in `serve/cockpit/web/src/__tests__/ColumnPolish_1574.test.tsx:89`, `:103`, `:115`; current status set includes `research`, `backlog`, `todo`, `in-progress`, `review`, `docs`, `done` in `serve/cockpit/web/e2e/column-body-a11y-1574.spec.ts:37`. | todo |
| 2 | AC-3 | The scoped axe proof can pass vacuously because it never proves any scanned `[data-testid="column-body"]` is actually scrollable before asserting zero `scrollable-region-focusable` violations. | AC-3 in `.owlbear/kanban/tasks/1574-p2-14-red-specify-column-polish-and-empty-state-behavior.md:47`; `serve/cockpit/web/e2e/column-body-a11y-1574.spec.ts:55` only comments that 20 tasks should overflow; the current guard only checks non-empty scope at `:169` and `:172` before zero-violation assertions at `:152` and `:183`. The stronger repo pattern asserts scrollableCount > 0 in `serve/cockpit/web/e2e/responsive-contract-1566.spec.ts:155` through `:176`. | todo |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Add named AC-1 header-label cases for the remaining board statuses so the suite proves normalization across the full status set. | `serve/cockpit/web/src/__tests__/ColumnPolish_1574.test.tsx`; `serve/cockpit/web/e2e/column-body-a11y-1574.spec.ts` | AC-1 line 45 versus current cases at `ColumnPolish_1574.test.tsx:89`, `:103`, `:115`; status list at `column-body-a11y-1574.spec.ts:37` |
| 2 | test-writer | Add a non-vacuous scrollability guard to AC-3 before the axe assertion, reusing the responsive-contract pattern if helpful. | `serve/cockpit/web/e2e/column-body-a11y-1574.spec.ts`; `serve/cockpit/web/e2e/responsive-contract-1566.spec.ts` | AC-3 line 47; current spec assumes overflow at `column-body-a11y-1574.spec.ts:55` and only checks scope count at `:169` through `:172` |

## Observations
- `serve/cockpit/web/src/components/Column.tsx:20`, `:62`, `:87`, `:88`, and `:92` do implement the intended behavior for the narrow cases under review, and the scoped reviewer rerun passed. The rejection is about proof completeness, not an observed implementation defect.
- The builder note at `.owlbear/kanban/tasks/1574-p2-14-red-specify-column-polish-and-empty-state-behavior.md:232` says coverage was not reported. The reviewer rerun did produce coverage, so that note is stale, but it is not a standalone blocker.
- `serve/cockpit/web/src/__tests__/KanbanBoard.filter-e2e.test.tsx:197` still expects `No todo tasks`. I did not use that as a blocking finding because an adjacent rerun shows that suite is already red for broader filter behavior, but the assertion is stale relative to this polished-label contract.
2026-05-15T00:38:00+00:00
## Test-Writer Notes

**Retry cycle — proof-gap fill, direct-to-review advance.**

### Required Follow-up addressed

**#1 — AC-1 full status coverage (unit tests)**
- File: `serve/cockpit/web/src/__tests__/ColumnPolish_1574.test.tsx`
- Added 4 tests to `TestFromAC_ColumnHeaderLabel` for the missing canonical statuses: `backlog` → `Backlog`, `research` → `Research`, `review` → `Review`, `docs` → `Docs`
- `TestFromAC_ColumnHeaderLabel` now covers all 7 board statuses: research, backlog, todo, in-progress, review, docs, done
- All 4 new tests PASS against current code (builder's `toDisplayStatus()` implementation handles all statuses correctly)

**#2 — AC-3 non-vacuous scrollability guard (E2E)**
- File: `serve/cockpit/web/e2e/column-body-a11y-1574.spec.ts` (also updated scratch)
- Replaced weak count-only scope guard with non-vacuous guard using `page.addStyleTag` (max-height: 100px) + `page.evaluate()` scrollHeight > clientHeight check
- Pattern reused from `responsive-contract-1566.spec.ts`
- `scrollableCount > 0` asserted before axe scan — axe zero-violation result can no longer be vacuously true
- Updated test name: "at least one [data-testid="column-body"] is scrollable before axe scan — non-vacuous AC-3 scope guard"

### Quality-runner evidence (scoped unit pass)
| File | Tests | Pass | Fail | Lint |
|------|-------|------|------|------|
| `ColumnPolish_1574.test.tsx` | 13 | 13 | 0 | clean |

### Step 1b.1 rationale (direct-to-review)
- Reviewer's Required Follow-up: test-proof gaps only (no implementation fixes needed)
- All 4 new unit tests PASS (builder's `toDisplayStatus()` normalizes all statuses)
- No lint issues
- Builder has no work to do — advancing directly to review

### Commit
`87a167b5` — `test: add full-status AC-1 coverage and non-vacuous AC-3 guard (#1574, test-writer)`
2026-05-15T01:04:00+00:00
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1574 -> docs | AC mapped to code and evidence sufficient.
- Builder evidence reviewed first: prior scoped builder run covered ColumnPolish, Column_1539, ColumnCSS_1547, and the tracked AC-3 Playwright spec; the retry note then closed the previously-rejected AC-1 and AC-3 proof gaps.
- Independent verification was warranted because the direct-to-review retry only logged fresh unit-pass evidence. I ran a scoped reviewer quality pass on the updated proof surface plus a separate CSS-suite verification to remove the remaining path ambiguity.

| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC-1 | `serve/cockpit/web/src/components/Column.tsx:20`, `:47` normalize and render display labels | `serve/cockpit/web/src/__tests__/ColumnPolish_1574.test.tsx:89`, `:103`, `:115`, `:124`, `:136`, `:148`, `:160` cover all seven board statuses; reviewer quality run passed | PASS |
| AC-2 | `serve/cockpit/web/src/components/Column.tsx:92` uses normalized empty-state text; `serve/cockpit/web/src/components/Column.css:20`, `:51`, `:52` enforce header/empty-state hierarchy and dimming | `serve/cockpit/web/src/__tests__/ColumnPolish_1574.test.tsx:185`, `:200`, `:211` assert polished empty text, `data-testid="empty-column"`, font-size <= header, and opacity < 1; durable alignment in `serve/cockpit/web/src/__tests__/Column_1539.test.tsx:171`, `:183`, `:194`, `:204` | PASS |
| AC-3 | `serve/cockpit/web/src/components/Column.tsx:62`, `:90` make `[data-testid="column-body"]` keyboard-focusable | `serve/cockpit/web/e2e/column-body-a11y-1574.spec.ts:134`, `:147` run scoped axe on `[data-testid="column-body"]`; `:167`, `:183`, `:190`, `:196`, `:206`, `:212` add the non-vacuous scrollability guard before zero-violation assertions; reviewer Playwright run passed | PASS |
| AC-4 | `serve/cockpit/web/src/components/Column.tsx:88` renders the numeric count badge; `serve/cockpit/web/src/components/Column.css:20`, `:27` keep badge text smaller than the header label | `serve/cockpit/web/src/__tests__/ColumnPolish_1574.test.tsx:253`, `:278`, `:298` assert badge presence/count and font hierarchy; reviewer CSS-suite run confirmed `serve/cockpit/web/src/__tests__/ColumnCSS_1547.test.ts` passing cleanly | PASS |
| AC-5 | Pre-remediation weak/failing evidence remains recorded in task body at `.owlbear/kanban/tasks/1574-p2-14-red-specify-column-polish-and-empty-state-behavior.md:124` and below | Task body contains the required audit evidence summary | PASS |

- Reviewer quality evidence:
  - Scoped rerun: `ColumnPolish_1574.test.tsx`, `Column_1539.test.tsx`, and `column-body-a11y-1574.spec.ts` all passed; eslint and stylelint clean; coverage produced for `Column.tsx` (Statements 66.21%, Branches 44.23%, Functions 60.00%, Lines 76.74%).
  - Targeted CSS rerun: `ColumnCSS_1547.test.ts` passed 14/14; stylelint clean.
- Challenger cross-check: proceed, confidence 0.84; no blocking concerns found.
- Blocking findings: none.

## Observations
- The earlier review blockers are closed: AC-1 now proves all seven statuses, and AC-3 now proves at least one scrollable column-body before the scoped axe assertion.
- Adjacent suite hygiene remains imperfect: `serve/cockpit/web/src/__tests__/KanbanBoard.filter-e2e.test.tsx:197` still expects `No todo tasks`. I did not treat that as blocking here because that suite was already red for broader filter behavior and sits outside this task's scoped proof packet.
2026-05-15T01:30:53+00:00
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | README verification | Yes | N/A | Convention maps `serve/cockpit/web/src/**` → `serve/cockpit/README.md`. Full README read performed. Layer 1 (grep): no references to `column-body`, `toDisplayStatus`, `tabIndex`, `column-empty`, or Column.css font-size in the README — no stale or orphaned references. Layer 2 (LLM editorial): README covers backend API surface, engine allowlist, error envelope, decisions API, sessions model, config, and dependencies. The #1574 changes (JS label normalization, CSS font-size reduction, tabIndex on column-body) are internal component details not documented at the README level. Accessibility section ("after #1396") covers test gate infrastructure, not per-component attributes. No contradictions or stale content introduced. |
| 2 | External attribution | No | N/A | No external sources referenced in task body; no new libraries or frameworks introduced. |
| 3 | Research doc | Yes | N/A | Task body cites `.owlbear/research/cockpit-visual-audit-consolidated-2026-05-14.md` and `.owlbear/research/1560-cockpit-design-policy.md`. Grep confirms `1560-cockpit-design-policy.md:134` lists `#1574, #1575` under "Column polish and empty states". Cross-reference is intact. |
| 4 | Deletion detection | No | N/A | No source files deleted in this task. No orphaned references in mapped docs. |

### Verification Layers
- Layer 1 — grep on `serve/cockpit/README.md` for `column-body`, `toDisplayStatus`, `tabIndex`, `column-empty`: zero matches. No stale symbols introduced or removed.
- Layer 2 — Full-file read of `serve/cockpit/README.md` (250 lines). Content covers backend/API/config/deps surface only. Column-level UI behavior is not and was not documented there. No contradictions with the task's implementation.

### Scratch Cleanup
Deleted: `.owlbear/scratch/1574-column-body-a11y.spec.ts`, `1574-eslint-output.txt`, `1574-vitest-output.txt` — all 3 files removed.
2026-05-15T02:02:22+00:00
## Audit\n### Regression Detection\n- quality-runner mode full: Python 4613 passed / 228 failed / 5 errors; Vitest 1819 passed / 13 failed / 11 skipped; ESLint clean; Stylelint clean; Ruff clean\n- All failures pre-existing and unrelated to #1574 scope (Python: engine_lazy_agent_map, end_work_success, memory_engine, etc.; Vitest: FilterAccessibilityPanel, ShellSecondaryCSS, KanbanBoard.performance, DetailTab, PdsMigration)\n- Task-scoped rerun: ColumnPolish_1574 (13), Column_1539 (10), ColumnCSS_1547 (14) — 37 passed, 0 failed\n- regression verdict: PASS\n\n### Intent Verification\n- scope alignment: PASS (all changed files within cockpit frontend column domain: Column.tsx, Column.css, Column_1539.test.tsx, ColumnPolish_1574.test.tsx, column-body-a11y-1574.spec.ts)\n- purpose match: PASS (JS label normalization via toDisplayStatus(), polished empty-state text, tabIndex for focusability, CSS font-size fix — all directly serve stated AC purpose)\n- extraneous scope: none\n- boundary check: function-level behavior verification deferred to reviewer\n\n### Architect Quality: 4/5\nAC-1 through AC-5 are well-specified with concrete DOM targets, CSS structural patterns, and scoped axe rules. Challenger round was effective — added AC-4, clarified DOM vs CSS text-transform distinction, scoped AC-3 to avoid whole-page conflation. Minor gap: AC-1 \"each board status\" was clear but didn't enumerate the status set, requiring reviewer to catch incomplete test coverage. Overall: adequate with minor gaps filled downstream.\n\n### Commit Integrity\n- upstream commit presence: PASS\n  - af5c926a — test: reconcile Column_1539 empty-state assertions (#1574, test-writer)\n  - 87a167b5 — test: add full-status AC-1 coverage and non-vacuous AC-3 guard (#1574, test-writer)\n  - dd4b6669 — feat: polish column labels, empty state, and focusability (#1574, builder)\n- All commits properly attributed with (#1574, agent-role) format\n- Scratch cleanup verified: no .owlbear/scratch/1574-* files remain\n- kanban commit packaging: pending (this step)\n\n### Deduction Breakdown\nNo deductions applied.\n- Regression: no task-caused regressions (pre-existing failures documented)\n- Intent: scope and purpose aligned\n- AC quality: 4/5 (deduction threshold is ≤ 3)\n- Reviewer evidence: detailed PASS verdict with AC mapping table, challenger cross-check, and independent quality-runner rerun\n- Lint: clean across all linters\n- Commit integrity: all upstream commits present\n\n### Confidence: 1.00\n### Action: archive