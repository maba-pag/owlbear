---
id: 1539
title: 'P3-03: test — column component CSS: fixed header, scroll body, empty text
  fallback'
status: archived
priority: medium
created: 2026-05-13T18:41:58.306824+00:00
updated: 2026-05-13T23:04:13.726561+00:00
tags:
  - phase-3
  - scope:cockpit
  - css
  - test
  - frontend
parent: 1534
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
Brief: see parent #1534 (`.owlbear/briefs/draft-board-visual-design/brief.md`)

## Scope
- **In:** Tests for column header/body separation, overflow scrolling, empty state text rendering, surface styling
- **Out:** Column CSS implementation, empty state illustrations

## Acceptance Criteria

- AC-1: Vitest renders Column → column root has a `<header>` direct child AND a separate sibling body container (identified by `data-testid="column-body"` or CSS class) — proving structural separation (header is NOT inside the scrollable region)
- AC-2: Vitest dual-proof for overflow: (a) rendered Column body container element has the expected CSS class via `classList`; (b) Column.css file read contains `overflow-y: auto` on that class (regex match)
- AC-3: Vitest dual-proof for empty state: (a) Column rendered with status="todo" and empty tasks array displays text "No todo tasks"; (b) Column.css file read contains centering declarations (flex centering or `text-align: center`) on the empty-state class

Proof bundle: behavioral

## Builder Guidance
- Column.css does not exist yet — RED tests should import/read `Column.css` path and expect it to exist (will fail until impl task #1547 creates it)
- The dual-proof pattern is established in `ResponsiveLayout_1391.test.tsx` — use `fs.readFileSync` for CSS source-contract assertions
- Current Column.tsx has "No tasks" (static) — test expects "No {status} tasks" (parameterized), which will fail until impl changes it
- Existing KanbanBoard.test.tsx already covers count-badge presence and empty-state non-blank — do NOT duplicate those checks; focus on structural separation and CSS wiring
- Use discriminating assertions: the test should fail if header is nested inside the scrollable body, or if the overflow class is missing from the body container

## Research
- Research doc: .owlbear/research/1539-column-css-test-approach.md
- Sources: 7 studied, 4 high-relevance
- Recommendation: dual-proof approach (rendered class wiring + CSS file regex) for all 3 ACs (confidence: 0.75)
- Follow-up tasks created: none needed — task correctly scoped
- Decision requests: none

## Challenge Results
- Challenger: reconsider (0.57 confidence in original)
- Key challenges: coverage reduction (DOM-only doesn't prove CSS), false-green wiring risk (CSS-only doesn't prove DOM wiring), precedent mismatch (file-based CSS is fallback not general proof)
- Researcher response: accepted — revised to dual-proof approach that closes both gaps. Confidence revised from initial estimate to 0.75.

## Key Findings
- jsdom does NOT implement CSS cascade — getComputedStyle returns empty for class-based styles
- AC-1 (header/body separation): DOM structure queries, straightforward
- AC-2 (overflow-y): dual-proof — class presence on rendered element + CSS file regex
- AC-3 (empty text + centered): text content check + CSS centering source-contract (geometry needs Playwright)
- Existing KanbanBoard tests already cover count badge and empty-state presence — new tests must be discriminating
- Current Column.tsx has "No tasks" not "No {status} tasks" — implementation task must change this
2026-05-13T19:47:16+00:00
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Tests one component's CSS behaviors only |
| Interface clarity | PASS (after refinement) | ACs now specify exact assertion strategies (DOM structure, classList, fs regex) |
| Dependency correctness | PASS | No deps — correct for RED test task; impl #1547 depends on this |
| Module layering | PASS | Frontend test, no layering concerns |
| TDD compliance | PASS | This IS the test task preceding impl #1547 |
| KISS/YAGNI | PASS | 3 focused ACs, dual-proof is minimum viable for jsdom limitation |
| Premise challenge | PASS | No existing coverage for structural separation or CSS wiring |
| Pattern consistency | PASS | Follows ResponsiveLayout_1391.test.tsx dual-proof pattern |
| Security surface | N/A | Frontend tests, no security boundary |
| Single domain | PASS | Pure frontend test domain |

### Challenge Results
- Challenger: reconsider (0.72 confidence)
- Key issues: AC lines not independently verifiable, "non-scrolling container" ambiguous, "centered layout" undefined, AC-2 claims runtime behavior jsdom can't prove
- Architect response: ACCEPTED — refined all 3 ACs to specify exact proof mechanisms (DOM structure for AC-1, dual-proof with classList + CSS regex for AC-2/AC-3). Removed runtime behavior claims; ACs now describe source-contract proofs.

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED

### Verdict: APPROVE (after REFINE)
### Action Taken: Refined AC wording to embed assertion strategies directly in AC lines (eliminating dependency on research doc for pass/fail clarity). Added Builder Guidance section. Advanced to todo.
2026-05-13T20:11:12+00:00
## Test-Writer Notes
- Test file: serve/cockpit/web/src/__tests__/Column_1539.test.tsx
- Classes: TestFromAC_ColumnStructure, TestFromAC_ColumnOverflow, TestFromAC_ColumnEmptyState
- Tests per category: happy 4, edge 2, error 2, boundary 2
- Total: 10 tests, all FAIL
- ESLint: clean

### AC Coverage
| AC | Tests | Failure reason |
|----|-------|----------------|
| AC-1 (structural separation) | 3 | `data-testid="column-body"` absent in Column.tsx |
| AC-2 (overflow dual-proof) | 3 | `column-body` absent; Column.css does not exist (ENOENT) |
| AC-3 (empty text + centering) | 4 | "No tasks" ≠ "No {status} tasks"; Column.css does not exist (ENOENT) |

### Failure types observed
- AssertionError: `column-body` missing, text "No tasks" ≠ expected parameterized forms
- ENOENT: Column.css does not exist (impl task #1547 creates it)

### Builder guidance
- Add `data-testid="column-body"` wrapper around tasks/empty-state (sibling to `<header>`)
- Add CSS class to column-body element wired to Column.css
- Create Column.css with `overflow-y: auto` on body class + centering on empty-state class
- Change `"No tasks"` to `` `No ${status} tasks` ``
2026-05-13T20:40:11+00:00
## Builder Notes
### Files Changed
- serve/cockpit/web/src/components/Column.tsx
- serve/cockpit/web/src/components/Column.css

### Implementation Summary
- Added dedicated stylesheet import in `Column` and introduced a direct child body container (`data-testid="column-body"`) as a sibling of `<header>`.
- Moved task/empty rendering into the new body container with class wiring for CSS contract checks.
- Parameterized empty-state text to `No ${status} tasks`.
- Added `Column.css` with:
  - `.column-body { overflow-y: auto; }`
  - `.column-empty` centering declarations (`display:flex`, `align-items:center`, `justify-content:center`, `text-align:center`)

### Quality Evidence
- RED verification (quality-runner, scoped):
  - test file `src/__tests__/Column_1539.test.tsx`: 0 passed / 10 failed (expected RED)
  - lint: clean
- GREEN verification (quality-runner, scoped):
  - test file `src/__tests__/Column_1539.test.tsx`: 10 passed / 0 failed
  - lint: clean (eslint/stylelint)
  - coverage snapshot: overall 58.4%, `Column.tsx` 62.5%, `Column.css` 0%
- Additional regression-focused scoped run:
  - tests: `src/__tests__/Column_1539.test.tsx` + `src/__tests__/KanbanBoard.test.tsx`
  - result: 45 passed / 0 failed, lint clean
  - coverage snapshot: `Column.tsx` 73.21%, `Column.css` 0%
- Full frontend run (context only): unrelated pre-existing failures in other task-scoped suites; `Column.tsx` observed at 80.4%. CSS files are not V8-instrumented (reported 0% by JS coverage).

### Commit
- 20bbecb4 feat: implement column body split and empty-state css fallback (#1539, builder)
2026-05-13T21:09:13+00:00
## Review Evidence
- Verdict: FAIL
- AC-1 is adequately mapped: the component keeps `<header>` as a direct child and renders a sibling body container (`serve/cockpit/web/src/components/Column.tsx:60`, `serve/cockpit/web/src/components/Column.tsx:64`), and the task-scoped tests assert both direct-child structure and non-nesting (`serve/cockpit/web/src/__tests__/Column_1539.test.tsx:71`, `serve/cockpit/web/src/__tests__/Column_1539.test.tsx:89`).
- Builder evidence is internally consistent with the current files: `Column.tsx` wires `.column-body` / `.column-empty` (`serve/cockpit/web/src/components/Column.tsx:64`, `serve/cockpit/web/src/components/Column.tsx:66`) and `Column.css` defines the intended rules (`serve/cockpit/web/src/components/Column.css:5`, `serve/cockpit/web/src/components/Column.css:10`).
- Blocking findings:
| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC-2 | Overflow dual-proof is too weak. The test only proves the body has some CSS class and that `Column.css` contains `overflow-y: auto` somewhere; it does not prove that the overflow declaration is attached to the body container's class, so the suite can false-green if overflow moves to another selector. | AC-2 requires `overflow-y: auto` "on that class" (`.owlbear/kanban/tasks/1539-p3-03-test-column-component-css-fixed-header-scroll-body-empty-text-fallback.md:32`). Task guidance also says the test should fail if the overflow class is missing from the body container (`.owlbear/kanban/tasks/1539-p3-03-test-column-component-css-fixed-header-scroll-body-empty-text-fallback.md:42`). Current proof only checks `classList.length` (`serve/cockpit/web/src/__tests__/Column_1539.test.tsx:131`) plus a file-wide regex for `overflow-y: auto` (`serve/cockpit/web/src/__tests__/Column_1539.test.tsx:147`). | todo |
| 2 | AC-3 | Empty-state CSS proof is too weak. The text assertions are good, but the CSS assertion scans the whole file for centering declarations and never proves they belong to the empty-state class, so unrelated centered selectors could false-green. | AC-3 requires centering declarations "on the empty-state class" (`.owlbear/kanban/tasks/1539-p3-03-test-column-component-css-fixed-header-scroll-body-empty-text-fallback.md:33`). Current proof only checks `hasFlex || hasTextAlign` from file-wide regexes (`serve/cockpit/web/src/__tests__/Column_1539.test.tsx:201`). The live implementation currently uses `.column-empty` at `serve/cockpit/web/src/components/Column.tsx:66` and `serve/cockpit/web/src/components/Column.css:10`, which is why this routes to test strengthening rather than builder rework. | todo |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Tighten AC-2 so the rendered body assertion names the expected selector/class and the CSS regex proves `overflow-y: auto` is attached to that same selector. | serve/cockpit/web/src/__tests__/Column_1539.test.tsx | AC-2 finding above; current loose checks at `serve/cockpit/web/src/__tests__/Column_1539.test.tsx:131` and `serve/cockpit/web/src/__tests__/Column_1539.test.tsx:147` |
| 2 | test-writer | Tighten AC-3 so the CSS-source assertion proves the centering declarations are attached to `.column-empty`, not just present somewhere in `Column.css`. | serve/cockpit/web/src/__tests__/Column_1539.test.tsx | AC-3 finding above; current loose check at `serve/cockpit/web/src/__tests__/Column_1539.test.tsx:201` |

## Observations
- This is a test-proof gap, not an implementation defect. The current source appears to satisfy the intended selectors and strings, so a test-writer retry can likely use the builder-skip path if strengthened tests pass against the existing code.
- The repo already uses more discriminating selector-aware CSS-source assertions in `ResponsiveLayout_1391.test.tsx` (for example `@media ... shell__sidecar` and `@media ... grid-template-columns` checks at `serve/cockpit/web/src/__tests__/ResponsiveLayout_1391.test.tsx:257` and `serve/cockpit/web/src/__tests__/ResponsiveLayout_1391.test.tsx:268`).
2026-05-13T21:48:56+00:00
## Test-Writer Notes
- Retry: tightened AC-2 and AC-3 CSS assertions per reviewer Required Follow-up.
- Test file: serve/cockpit/web/src/__tests__/Column_1539.test.tsx
- Classes: TestFromAC_ColumnStructure, TestFromAC_ColumnOverflow, TestFromAC_ColumnEmptyState
- Tests per category: happy 4, edge 2, error 2, boundary 2
- Total: 10 tests, all PASS against current impl

### Changes
- AC-2 classList test: `classList.length > 0` → `classList.contains('column-body')` (names the expected selector class)
- AC-2 CSS regex: file-wide `/overflow-y: auto/` → selector-scoped `/\.column-body\s*\{[^}]*overflow-y\s*:\s*auto/s` (proves rule is inside `.column-body {}`)
- AC-3 CSS regex: file-wide `hasFlex || hasTextAlign` → selector-scoped `/\.column-empty\s*\{[^}]*display\s*:\s*flex[^}]*align-items\s*:\s*center/s` or `text-align` within `.column-empty {}` (proves centering is on empty-state class, not unrelated selectors)

### Builder skip: test-only retry, all tests green
- Commit: 8c241c96
- ESLint: clean
2026-05-13T22:11:36+00:00
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1539 -> docs | AC mapped to code and evidence sufficient.
- AC evidence map:
| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC-1 | `serve/cockpit/web/src/components/Column.tsx:60` keeps `<header>` as a direct child of the column root and `serve/cockpit/web/src/components/Column.tsx:64` renders a sibling body container with both `data-testid="column-body"` and `.column-body`. | `serve/cockpit/web/src/__tests__/Column_1539.test.tsx:71`, `serve/cockpit/web/src/__tests__/Column_1539.test.tsx:89`, and `serve/cockpit/web/src/__tests__/Column_1539.test.tsx:106` assert direct-child structure, non-nesting, and empty-state structural separation. | PASS |
| AC-2 | `serve/cockpit/web/src/components/Column.tsx:64` wires the body container to `.column-body`; `serve/cockpit/web/src/components/Column.css:5` and `serve/cockpit/web/src/components/Column.css:6` attach `overflow-y: auto` to that selector. | `serve/cockpit/web/src/__tests__/Column_1539.test.tsx:127` requires `classList.contains('column-body')`; `serve/cockpit/web/src/__tests__/Column_1539.test.tsx:139` asserts `Column.css` exists; `serve/cockpit/web/src/__tests__/Column_1539.test.tsx:149` requires a selector-scoped `.column-body { ... overflow-y: auto ... }` regex. | PASS |
| AC-3 | `serve/cockpit/web/src/components/Column.tsx:66` renders parameterized empty-state text inside `.column-empty`; `serve/cockpit/web/src/components/Column.css:10` through `serve/cockpit/web/src/components/Column.css:14` place centering declarations on `.column-empty`. | `serve/cockpit/web/src/__tests__/Column_1539.test.tsx:169`, `serve/cockpit/web/src/__tests__/Column_1539.test.tsx:181`, and `serve/cockpit/web/src/__tests__/Column_1539.test.tsx:190` cover parameterized empty text across statuses; `serve/cockpit/web/src/__tests__/Column_1539.test.tsx:200` requires selector-scoped centering declarations inside `.column-empty {}`. | PASS |
- Upstream evidence is internally consistent with the current files. Builder commit `20bbecb4` and test-writer retry commit `8c241c96` are present in `.git/logs/HEAD` and `.git/logs/refs/heads/dev`; scoped editor diagnostics for `Column.tsx`, `Column.css`, and `Column_1539.test.tsx` are clean.
- Behavioral-bundle challenger cross-check was reviewed. The remaining concerns do not block PASS because the refined contract for AC-3 is text proof plus selector-scoped CSS source proof (`.owlbear/kanban/tasks/1539-p3-03-test-column-component-css-fixed-header-scroll-body-empty-text-fallback.md:33`; `.owlbear/research/1539-column-css-test-approach.md:49`), not runtime geometry proof.

## Observations
- AC-1 text allows the body container to be identified by `data-testid="column-body"` or a CSS class (`.owlbear/kanban/tasks/1539-p3-03-test-column-component-css-fixed-header-scroll-body-empty-text-fallback.md:31`), while the structural tests currently use the `data-testid` hook (`serve/cockpit/web/src/__tests__/Column_1539.test.tsx:71`, `serve/cockpit/web/src/__tests__/Column_1539.test.tsx:89`, `serve/cockpit/web/src/__tests__/Column_1539.test.tsx:106`). This is non-blocking here because builder guidance explicitly requested that hook and the implementation ships both the hook and the class, but future refactors should keep the AC and tests aligned if the hook becomes optional.
- Shell access was unavailable in this reviewer session, so I could confirm the cited commits via `.git/logs/**` but could not independently run `git show` / `git status` for a shell-level contamination check. No scoped editor diagnostics were present on the reviewed files.
2026-05-13T22:28:31+00:00
## Docs Gate

### Checklist

| Item | Result | Evidence |
|------|--------|----------|
| README Verification | N/A — no docs impact | Changed files: `Column.tsx`, `Column.css`, `Column_1539.test.tsx`. Convention maps `serve/cockpit/web/src/**` → `serve/cockpit/README.md`. Full read performed. The cockpit README documents launch commands, frontend tech-stack table, product boundary, and engine API surface — none of which reference individual component layouts, CSS selectors, or empty-state text. Internal component refactor has no README-visible surface. |
| External Attribution | PASS | `.owlbear/sources/overview.md` section "Column CSS Test Research (Task #1539)" at line 39 already records both external sources (SO #76571158, jsdom/jsdom#2690) with task linkage and date 2026-05-13. No update needed. |
| Research Doc | PASS | Task body links `.owlbear/research/1539-column-css-test-approach.md`; file confirmed present. |
| Deletion Detection | N/A | No files deleted; two files added (`Column.css`, `Column_1539.test.tsx`) and one modified (`Column.tsx`). No orphaned references. |

### Scratch Cleanup
No `.owlbear/scratch/1539-*` files found — nothing to clean.
2026-05-13T23:04:13+00:00
## Audit
### Regression Detection
- quality-runner mode full: Python 4605 passed / 209 failed, Frontend 1625 passed / 16 failed, lint clean (ruff/eslint/stylelint all pass)
- All 225 failures are pre-existing and unrelated to #1539: Python failures in test_cockpit_view.py, test_ideation_diagram.py, test_server.py, test_engine_accessor_migration.py (kanban accessor migration, cockpit view cleanup); Frontend failures in TokenArchitecture_1535, ShellSecondaryCSS_1542, SidecarCollapse_1541, ThemeToggle, PdsMigration, ResponsiveLayout_1391, KanbanBoard filter/both-or-nothing (other in-flight tasks' RED tests and pre-existing issues)
- Column_1539.test.tsx: 10 passed / 0 failed
- regression verdict: PASS

### Intent Verification
- scope alignment: PASS (changed files: Column.tsx, Column.css, Column_1539.test.tsx — all in serve/cockpit/web/src/, cockpit frontend domain)
- purpose match: PASS (task adds structural separation tests and CSS contract proofs for column component — matches stated purpose)
- extraneous scope: none
- boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 4/5
ACs were specific after refinement (dual-proof with classList + CSS regex). Initial "on that class" wording was clear in intent but didn't prescribe selector-scoped regex patterns; reviewer caught this test-proof gap on first pass, test-writer tightened in retry. Challenge results were properly incorporated at both research and arch review stages. Builder guidance was helpful and specific.

### Commit Integrity
- upstream commit presence: PASS
  - 140111b0 test: add failing tests for Column CSS structure (#1539, test-writer) — 1 file
  - 20bbecb4 feat: implement column body split and empty-state css fallback (#1539, builder) — 2 files
  - 8c241c96 test: tighten AC-2/AC-3 CSS selector-scoped assertions (#1539, test-writer) — 1 file
  - All three commits properly scoped to task files only
- kanban commit packaging: pending (this audit)

### Deduction Breakdown
- Regression failures: -.00 (all 225 failures pre-existing, unrelated to task)
- Intent mismatch: -.00
- Evidence integrity: -.00
- Lint violations: -.00
- AC quality ≤ 3: -.00 (scored 4/5)
- Missing reviewer evidence: -.00 (detailed, two-cycle review with AC mapping)

### Confidence: 1.00
### Action: archive