---
id: 1538
title: 'P3-01: test — card component CSS: signal border, hover, focus, selected states'
status: archived
priority: important
created: 2026-05-13T18:41:58.279132+00:00
updated: 2026-05-14T01:45:07.119528+00:00
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
- **In:** Tests for card `data-signal` attribute rendering, left-border color mapping, hover/focus/selected visual states
- **Out:** Card CSS implementation, signal computation logic (tested in P1-03), PRIORITY_COLORS removal (P3-02)

## Acceptance Criteria

- AC-1: Vitest/DOM test renders Card with each operational state (dr-pending, blocked, claimed, deps-unmet, ready) and asserts the element receives a matching `data-signal` attribute value — test defines expected state-to-signal mappings inline without importing signal computation
- AC-2: Vitest file-based test verifies Card.css contains `[data-signal="X"]` selectors where each signal maps to the brief-specified left-border color token (dr-pending→orange/warning, blocked→red/error, claimed→purple/custom, deps-unmet→grey/contrast-medium, ready→no explicit border-left-color property)
- AC-3: Vitest file-based test verifies `[data-selected]` selector declares box-shadow or outline styling (PDS success token) distinct from the left-border signal color
- AC-4: Vitest file-based test verifies Card.css contains `:hover` selector with background property referencing PDS state-hover token and `:focus-visible` selector with outline property referencing PDS state-focus token

Proof bundle: behavioral

## Research
- Research doc: .owlbear/research/1538-card-css-test-approach.md
- Sources: 8 studied, 5 high-relevance (Card.tsx, tokens.css, PDSHexScan, #1535 research, #1536 research)
- Recommendation: split test approach — AC-1 as DOM render test (Card.signal.test.tsx), AC-2+AC-3+AC-4 as file-based CSS parsing (Card.css.test.ts) (confidence: 0.75)
- Follow-up tasks created: none needed — task scope already correct
- Decision requests: none

## Key Findings
- JSDOM cannot resolve CSS from stylesheets or custom properties — getComputedStyle returns empty for stylesheet-applied styles
- File-based CSS parsing (readFileSync + regex) follows established PDSHexScan and #1535 token test pattern
- PDS tokens lack a purple color — test expects custom `--pds-signal-claimed` token, fails RED until added
- Hover/focus pseudo-selectors untestable via DOM in jsdom — file-based selector existence check is the Vitest-scoped approach
- Existing Shell.card-selection.integration.test.tsx tests interaction (data-selected attribute), not CSS styling — no duplication with AC-3
- ~16 test cases across 2 files: 5 signal render (AC-1), 5 CSS border-color (AC-2), 2 selected styling (AC-3), 2 hover (AC-4), 2 focus (AC-4)

## Challenge Results
- Challenger: reconsider (confidence in original: 0.57)
- Key challenges: purple color dilution, computeSignal import coupling, hover/focus demotion, Playwright dismissal
- Researcher response: accepted/revised — purple requires specific token expectation, tests self-contained (no computeSignal import), hover/focus promoted to first-class, Playwright acknowledged but out of scope per AC text ("Vitest verifies")
2026-05-13T19:49:54+00:00
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Test-only task: card CSS visual states |
| Interface clarity | PASS | 4 ACs with specific signal values, token references, and assertion targets |
| Dependency correctness | PASS | No deps — intentional TDD RED (tests fail until #1543/#1546 create Card.css) |
| Module layering | PASS | Test files only; no upward imports |
| TDD compliance | PASS | This IS the RED phase task; #1546 depends on it |
| KISS/YAGNI | PASS | ~16 test cases across 2 files, proportionate to scope |
| Premise challenge | PASS | No existing card CSS tests; needed for signal model contract |
| Pattern consistency | PASS | Follows PDSHexScan file-based readFileSync+regex pattern (established precedent) |
| Security surface | PASS | CSS tests — no system boundaries |
| Single domain | PASS | Frontend CSS testing only |

### Challenge Results
- Challenger: reconsider (confidence: 0.56)
- Challenges raised: (1) artifact drift — accepted, persisted refined ACs; (2) AC-2 ready-state ambiguity — accepted, specified "no explicit border-left-color property"; (3) hidden impl coupling — rebutted (intentional TDD RED design); (4) regression surface — noted as out-of-scope (impl task responsibility)
- Architect response: accepted 2 of 4, rebutted 2 — refinement landed in task body before advancing

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED (tagged `test` — pass-through; builder writes test files as deliverable)

### Refinements Applied
- AC-1: removed `computeSignal()` import coupling; tests define inline mappings
- AC-2: specified ready signal = absence of explicit border-left-color (resolves ambiguity)
- AC-4: added for hover/focus pseudo-selector coverage (was in scope but missing AC)
- Scope Out: added PRIORITY_COLORS removal note (belongs to #1546)
- Test count updated: ~16 cases (was ~14)

### Verdict: APPROVE
### Action Taken: Refined ACs (AC-1 decoupled, AC-2 ready-state specified, AC-4 added), advanced to todo
2026-05-13T20:14:42+00:00
## Test-Writer Notes
- Test file 1: serve/cockpit/web/src/__tests__/Card.signal.test.tsx
- Test file 2: serve/cockpit/web/src/__tests__/Card.css.test.ts
- Classes: TestFromAC_CardSignalAttribute, TestFromAC_CardCSSBorderSignal, TestFromAC_CardCSSSelectedState, TestFromAC_CardCSSHoverFocus
- Tests per category: happy 14, edge 0, error 0, boundary 0
- Total: 14 tests, all FAIL
- ruff: clean (ESLint: clean)
- AC coverage:
  - AC-1: 5 tests (Card.signal.test.tsx) — one per signal state (dr-pending, blocked, claimed, deps-unmet, ready); assert data-signal attribute; fail AssertionError (null ≠ signal) since Card lacks data-signal
  - AC-2: 5 tests (Card.css.test.ts) — [data-signal="X"] border-left-color token per brief; fail ENOENT (Card.css missing)
  - AC-3: 2 tests (Card.css.test.ts) — [data-selected] selector exists + box-shadow/outline with pds-notification-success; fail ENOENT
  - AC-4: 2 tests (Card.css.test.ts) — :hover background + pds-state-hover; :focus-visible outline + pds-state-focus; fail ENOENT
- Split approach: DOM render (Card.signal.test.tsx) for AC-1 attribute rendering; file-based CSS parsing (Card.css.test.ts) for AC-2/3/4
- Purple token: tests expect --pds-signal-claimed (custom, no PDS purple); builder must add it
- Commit: 44f47c7d
2026-05-13T20:40:59+00:00
## Builder Notes
- Files changed:
  - serve/cockpit/web/src/components/Card.tsx
  - serve/cockpit/web/src/components/Card.css
- Implementation summary:
  - Added `pendingDRIds?: Set<number>` to `CardProps` and computed `data-signal` on card render with precedence `dr-pending > blocked > claimed > deps-unmet > ready`.
  - Added `data-signal` attribute and imported `Card.css`.
  - Added `Card.css` selectors required by AC:
    - `[data-signal="dr-pending"]` -> `border-left-color: var(--pds-notification-warning)`
    - `[data-signal="blocked"]` -> `border-left-color: var(--pds-notification-error)`
    - `[data-signal="claimed"]` -> `border-left-color: var(--pds-signal-claimed)`
    - `[data-signal="deps-unmet"]` -> `border-left-color: var(--pds-contrast-medium)`
    - `[data-selected="true"]` with success token styling
    - `.card:hover` using `var(--pds-state-hover)`
    - `.card:focus-visible` using `var(--pds-state-focus)`
  - Preserved compatibility with existing responsive test by keeping inline `borderLeft` style mapping for priority-based expectations.
- RED verification (quality-runner):
  - Scoped tests failed initially: 14 failed / 0 passed (missing `Card.css`, missing `data-signal`).
  - Lint clean.
- GREEN verification (quality-runner):
  - Final scoped run: 79 passed / 0 failed across:
    - src/__tests__/Card.signal.test.tsx
    - src/__tests__/Card.css.test.ts
    - src/__tests__/ResponsiveLayout_1391.test.tsx
    - src/__tests__/KeyboardA11y_1395.test.tsx
    - src/__tests__/KanbanBoard.error-body.test.tsx
    - src/__tests__/KanbanBoard.archive-handler.test.tsx
  - Lint status: clean (eslint/stylelint clean)
  - Coverage: `src/components/Card.tsx` = 90%
- Commit:
  - c0ad8fc561fd517cb69a9a6799ef065ee79db022
- AC evidence summary:
  - AC-1: `data-signal` rendered per expected states; Card.signal test class now passing.
  - AC-2: Card.css signal selector/token mappings present; Card.css border-signal tests passing.
  - AC-3: `[data-selected="true"]` block includes success-token visual styling; selected-state tests passing.
  - AC-4: `:hover` and `:focus-visible` selectors include required PDS state tokens; hover/focus tests passing.
2026-05-13T21:10:04+00:00
## Review Evidence
- Verdict: FAIL
- Builder evidence reviewed: scoped GREEN run 79 passed / 0 failed, eslint/stylelint clean, Card.tsx coverage 90%.
- Challenger cross-check: reconsider; fail basis narrowed to the runtime CSS/token defects below rather than broader board-plumbing concerns.
- Blocking findings:
| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC-2 | The new signal-border rules cannot take effect because Card still sets an inline `borderLeft`, which outranks the stylesheet `border-left-color` selectors. The current task tests only parse CSS text, so they do not prove the rendered signal border changes. | `serve/cockpit/web/src/components/Card.tsx:98`; `serve/cockpit/web/src/components/Card.css:15-28`; `serve/cockpit/web/src/__tests__/Card.css.test.ts:53-87`; `serve/cockpit/web/src/__tests__/ResponsiveLayout_1391.test.tsx:216-223` | in-progress |
| 2 | AC-2, AC-3, AC-4 | Card.css references unresolved `--pds-*` tokens (`--pds-notification-*`, `--pds-state-*`, `--pds-signal-claimed`) that are not defined in the loaded token sheet, which still exposes only `--pds-theme-light-*` names. The file-based tests assert string presence only, so they miss the runtime style failure. | `serve/cockpit/web/src/components/Card.css:16,20,24,28,32,33,37,41`; `serve/cockpit/web/src/tokens.css:24-34`; `serve/cockpit/web/src/__tests__/Card.css.test.ts:53-130`; `serve/cockpit/web/src/__tests__/TokenArchitecture_1535.test.ts:10-28` | in-progress |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Reconcile signal-border styling with the existing inline border so the rendered card can actually display signal-driven left-border colors, or revert the premature CSS behavior from this task. | serve/cockpit/web/src/components/Card.tsx; serve/cockpit/web/src/components/Card.css | Finding #1 |
| 2 | builder | Replace unsupported token references with currently defined tokens or land the missing token definitions, including the claimed-state token, before relying on them in Card.css. | serve/cockpit/web/src/components/Card.css; serve/cockpit/web/src/tokens.css | Finding #2 |

## Observations
- `pendingDRIds` is only added at `CardProps`; the board render path still does not pass it (`serve/cockpit/web/src/components/Column.tsx:69-76`), even though pending DR items already expose `task_id` upstream (`serve/cockpit/web/src/hooks/usePendingDRs.ts:8`; `serve/cockpit/web/src/hooks/CockpitProvider.tsx:61`). I did not use this as the blocking basis for #1538 because AC-1 is component-scoped.
- `Card` currently reaches `dep_status` via a cast instead of a typed board-task shape (`serve/cockpit/web/src/components/Card.tsx:24-37`; `serve/cockpit/web/src/hooks/useBoard.ts:15-24`).
2026-05-13T21:45:09+00:00
## Builder Notes
- Files changed:
  - serve/cockpit/web/src/components/Card.tsx
  - serve/cockpit/web/src/components/Card.css

- Fixes applied (review follow-up):
  - Reconciled signal border behavior with inline styles by removing inline `borderLeft` and switching to inline custom property `--card-priority-border` in `Card.tsx`. The rendered border is now controlled by CSS `border-left` and can be overridden by `[data-signal]` rules.
  - Added runtime token alias definitions on `.card` so `--pds-*` signal/state variables resolve against existing `--pds-theme-light-*` tokens, including custom claimed-state token `--pds-signal-claimed`.
  - Preserved AC-required selectors/declarations exactly:
    - `[data-signal="dr-pending"]` -> `border-left-color: var(--pds-notification-warning)`
    - `[data-signal="blocked"]` -> `border-left-color: var(--pds-notification-error)`
    - `[data-signal="claimed"]` -> `border-left-color: var(--pds-signal-claimed)`
    - `[data-signal="deps-unmet"]` -> `border-left-color: var(--pds-contrast-medium)`
    - `[data-selected="true"]` success styling
    - `.card:hover` / `.card:focus-visible` state token usage

- Verification (quality-runner):
  - Scoped AC run (with frontend cwd hint): 39 passed, 0 failed, lint clean.
  - Broader scoped regression run:
    - Tests: 79 passed / 0 failed
    - Lint: clean (eslint + stylelint)
    - Coverage: `src/components/Card.tsx` = 90%

- Evidence summary:
  - AC-1 remains passing (`data-signal` attribute assertions in Card.signal test file).
  - AC-2 selectors still present and now can affect rendered border color (no inline border color override).
  - AC-3 selected-state success styling present and passing.
  - AC-4 hover/focus selectors and state tokens present and passing.
2026-05-13T22:02:08+00:00
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1538 -> docs | AC mapped to code and evidence sufficient.
- Builder evidence reviewed first: second-pass quality-runner reported 39 passed / 0 failed on the scoped AC run, 79 passed / 0 failed on the broader regression run, eslint/stylelint clean, and 90% coverage on serve/cockpit/web/src/components/Card.tsx. No independent rerun was required.
- Prior blocking defects are resolved: Card now exposes the signal on render and hands border color control back to CSS (serve/cockpit/web/src/components/Card.tsx:24, serve/cockpit/web/src/components/Card.tsx:54, serve/cockpit/web/src/components/Card.tsx:91; serve/cockpit/web/src/components/Card.css:3, serve/cockpit/web/src/components/Card.css:23, serve/cockpit/web/src/components/Card.css:27, serve/cockpit/web/src/components/Card.css:31, serve/cockpit/web/src/components/Card.css:35), and the required --pds-* names now resolve locally on .card (serve/cockpit/web/src/components/Card.css:5, serve/cockpit/web/src/components/Card.css:10, serve/cockpit/web/src/components/Card.css:11, serve/cockpit/web/src/components/Card.css:12).
- Challenger cross-check: reconsider. Resolved as non-blocking because the live pending-DR plumbing concern sits in adjacent signal-model/data-wiring work, while the AC-4 regex breadth is a hardening opportunity rather than a current contract miss.
- Blocking findings: none.

| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC-1 | serve/cockpit/web/src/components/Card.tsx:24, serve/cockpit/web/src/components/Card.tsx:91 | serve/cockpit/web/src/__tests__/Card.signal.test.tsx:73, :81, :89, :97, :105 | PASS |
| AC-2 | serve/cockpit/web/src/components/Card.css:3, :23, :24, :27, :31, :32, :35 | serve/cockpit/web/src/__tests__/Card.css.test.ts:53, :60, :67, :74, :81 | PASS |
| AC-3 | serve/cockpit/web/src/components/Card.css:39, :40, :41 | serve/cockpit/web/src/__tests__/Card.css.test.ts:96, :101, :113 | PASS |
| AC-4 | serve/cockpit/web/src/components/Card.css:44, :45, :48, :49 | serve/cockpit/web/src/__tests__/Card.css.test.ts:120, :124, :127, :130 | PASS |

## Observations
- pendingDRIds is still only consumed inside Card and the component test (serve/cockpit/web/src/components/Card.tsx:16, serve/cockpit/web/src/components/Card.tsx:45; serve/cockpit/web/src/__tests__/Card.signal.test.tsx:60). The live board path still runs CockpitProvider pending DR state through Shell/KanbanBoard/Column without passing it into Card (serve/cockpit/web/src/hooks/CockpitProvider.tsx:61; serve/cockpit/web/src/Shell.tsx:165; serve/cockpit/web/src/KanbanBoard.tsx:315; serve/cockpit/web/src/components/Column.tsx:69). Given the sibling signal-model tasks and this task's CSS/component-scoped ACs, I treated that as adjacent scope, not a blocker here.
- The AC-4 assertions in serve/cockpit/web/src/__tests__/Card.css.test.ts:120-130 are broad regex checks and would be stronger if they anchored to .card:hover / .card:focus-visible explicitly. Current implementation does use those exact selectors (serve/cockpit/web/src/components/Card.css:44, serve/cockpit/web/src/components/Card.css:48), so this is non-blocking proof hardening.
- Safety/security review: no auth, storage, shell, path, or injection surface is in scope for this task.
2026-05-13T22:21:46+00:00
## Docs Gate

**Verdict: PASS**

**Item 1 — README Verification:** serve/cockpit/README.md read in full. No section documents individual React component behavior (Card, data-signal, CSS selectors). Layer 1 grep: zero matches for Card/data-signal/signal/border-left. Layer 2 editorial: no contradictions or staleness introduced. No docs impact.

**Item 2 — External Attribution:** All listed sources (Card.tsx, tokens.css, PDSHexScan, #1535/#1536 research) are internal project artifacts. N/A — no external attribution needed.

**Item 3 — Research Doc:** .owlbear/research/1538-card-css-test-approach.md exists and is linked in task body. Verified.

**Item 4 — Deletion Detection:** No files deleted. Builder added Card.css and two test files, modified Card.tsx. N/A — no deletion impact.

**Scratch cleanup:** No .owlbear/scratch/1538-* files found.
2026-05-13T22:51:24+00:00
## Audit
### Regression Detection
- quality-runner mode full: Python 208 failed (pre-existing/other tasks), Vitest 16 failed (mix of RED-phase sibling tasks and #1538 regressions)
- #1538-specific regressions: 2 tests in `KanbanBoard.both-or-nothing.test.tsx` — `card has a non-empty borderLeft style` and `different priorities yield different left border colors` both assert `style.borderLeft` is truthy, but the builder's second pass replaced inline `borderLeft` with CSS custom property `--card-priority-border` (JSDOM cannot resolve CSS variables to `style.borderLeft`)
- These tests were not in the builder/reviewer scoped verification set (79 tests across 6 files; `KanbanBoard.both-or-nothing` was excluded)
- Other Vitest failures are from sibling RED-phase tasks: ThemeToggle (#1540), TokenArchitecture (#1535), SidecarCollapse (#1541), ShellSecondaryCSS (#1542)
- regression verdict: FAIL (2 existing tests broken by #1538)

### Intent Verification
- scope alignment: PASS (Card.tsx, Card.css — correct domain for card CSS signal states)
- purpose match: PASS (signal border, hover, focus, selected states match task purpose)
- extraneous scope: none
- boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 4/5
- ACs were specific and well-refined through challenger and architect review
- Minor gap: no consideration of existing tests relying on inline borderLeft pattern; builder's fix for reviewer FAIL broke established tests not covered in scoped verification

### Commit Integrity
- upstream commit presence: FAIL
  - 3 #1538 commits found: f6efa6c1 (researcher), 44f47c7d (test-writer), c0ad8fc5 (builder first pass)
  - Builder's second pass (resolving reviewer blocking findings: inline borderLeft removal, token alias additions) was NEVER COMMITTED
  - `git status --porcelain -- serve/cockpit/web/src/components/Card.tsx serve/cockpit/web/src/components/Card.css` shows both files as modified in working tree
  - Committed code (`c0ad8fc5`) still has the reviewer's original FAIL defects (inline borderLeft overrides CSS selectors, unresolved token names)
  - The code that received the reviewer's second PASS exists only in the working tree
- kanban commit packaging: N/A (reject — no archive commit)

### Deduction Breakdown
| Criterion | Deduction |
|-----------|-----------|
| Regression failures (2 tests in KanbanBoard.both-or-nothing broken by borderLeft→CSS variable migration) | -.10 |
| Evidence integrity concern (builder second pass uncommitted; committed code has reviewer-FAIL'd defects) | -.05 |

### Confidence: 0.85
### Action: reject-to-backlog

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Commit the second-pass fix (Card.tsx + Card.css changes currently in working tree) as a proper git commit before advancing | serve/cockpit/web/src/components/Card.tsx; serve/cockpit/web/src/components/Card.css | `git status --porcelain` shows uncommitted modifications |
| 2 | builder | Update or replace the 2 borderLeft tests in KanbanBoard.both-or-nothing.test.tsx to work with the new CSS custom property approach (--card-priority-border), or ensure the priority border is still testable via inline style | serve/cockpit/web/src/__tests__/KanbanBoard.both-or-nothing.test.tsx:289-314 | Tests assert `style.borderLeft` truthy; Card now sets `--card-priority-border` CSS var instead |
2026-05-13T23:08:56+00:00

## Architecture Review (Re-entry)

**Context:** Auditor rejected to backlog — execution defects, not architectural issues. Prior architecture review (ACs, proof bundle, evaluation) remains valid and unchanged.

### Auditor Remediation Required
| # | Issue | Required Fix |
|---|-------|-------------|
| 1 | Builder second-pass fix (inline borderLeft removal + token aliases) was never committed | Commit Card.tsx + Card.css changes as a proper git commit |
| 2 | 2 tests in `KanbanBoard.both-or-nothing.test.tsx` broken by borderLeft→CSS variable migration | Update assertions to verify `--card-priority-border` custom property instead of `style.borderLeft` |

### Evaluation
- Prior architecture review: PASS (all 10 criteria) — unchanged
- AC quality: unchanged — 4 ACs remain specific and testable
- Proof bundle: behavioral (unchanged)

### Proof-Bundle Validation
- Final bundle: behavioral
- Test-writer: SKIP (test files already exist from prior cycle)

### Verdict: APPROVE (re-entry)
### Action Taken: Re-approved with auditor remediation guidance; advanced to todo

2026-05-13T23:09:01+00:00
Re-approved after auditor rejection. Architecture and ACs unchanged — defects are execution-level (uncommitted fix, 2 regression tests). Builder must: (1) commit Card.tsx+Card.css second-pass changes, (2) update KanbanBoard.both-or-nothing.test.tsx assertions to use --card-priority-border custom property.
2026-05-13T23:21:44+00:00
## Test-Writer Notes
- Retry cycle — architect re-entry explicitly marked Test-writer: SKIP (test files already exist from prior cycle).
- Existing test files intact:
  - serve/cockpit/web/src/__tests__/Card.signal.test.tsx
  - serve/cockpit/web/src/__tests__/Card.css.test.ts
- All Required Follow-up items from reviewer and auditor target builder only:
  - builder: Commit second-pass Card.tsx+Card.css changes (currently in working tree, uncommitted)
  - builder: Update/replace 2 borderLeft assertions in KanbanBoard.both-or-nothing.test.tsx to use --card-priority-border
- No new tests required — passing through to builder.
2026-05-14T00:01:49+00:00
## Builder Notes
- Files changed:
  - serve/cockpit/web/src/components/Card.tsx
  - serve/cockpit/web/src/components/Card.css

- Fixes applied:
  - Restored inline border evidence expected by existing regression tests by setting `borderLeft` inline in Card using a signal-aware CSS variable with priority fallback.
  - Preserved runtime signal behavior by keeping AC-required `[data-signal="..."]` `border-left-color` declarations and additionally setting `--card-priority-border` in each signal selector so inline border resolution follows signal state.
  - Kept token alias layer on `.card` for `--pds-*` compatibility from prior reviewer remediation.

- RED verification:
  - Reproduced failing regression before change: 2 failures in KanbanBoard.both-or-nothing (`style.borderLeft` assertions empty).

- GREEN verification (quality-runner):
  - Scoped run: 25 passed / 0 failed (both-or-nothing + Card signal/CSS tests)
  - Broader scoped regression run: 90 passed / 0 failed
  - Lint: clean (eslint/stylelint clean)
  - Coverage: src/components/Card.tsx = 90%

- Commit:
  - 4fac5a28

- AC evidence summary:
  - AC-1: Card `data-signal` behavior remains intact (Card.signal tests passing).
  - AC-2: Required `[data-signal]` selectors and border token mappings remain present; rendered border remains testable and no longer regresses existing board tests.
  - AC-3: `[data-selected]` success styling unchanged and passing.
  - AC-4: `:hover` / `:focus-visible` token-based styling unchanged and passing.
2026-05-14T00:19:34+00:00
## Review Evidence
- Verdict: PASS
- PASS confirmation: task 1538 advances to docs; AC mapped to code and evidence sufficient.
- Builder evidence reviewed first: latest scoped proof reports 25 passing tests with no failures, broader scoped proof reports 90 passing tests with no failures, lint clean, and Card.tsx coverage at 90 percent. The packet was internally consistent, so no independent quality rerun was required.
- Commit presence verified in .git/logs/HEAD:2997 and .git/logs/refs/heads/dev:2787.
- Challenger cross-check: proceed with confidence 0.82. No blocking AC, proof, or safety defect surfaced.
- Blocking findings: none.

| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC-1 | serve/cockpit/web/src/components/Card.tsx:24-38,52,92 | serve/cockpit/web/src/__tests__/Card.signal.test.tsx:73-110 | PASS |
| AC-2 | serve/cockpit/web/src/components/Card.css:23-40; serve/cockpit/web/src/components/Card.tsx:54 | serve/cockpit/web/src/__tests__/Card.css.test.ts:53-88; serve/cockpit/web/src/__tests__/KanbanBoard.both-or-nothing.test.tsx:289-308 | PASS |
| AC-3 | serve/cockpit/web/src/components/Card.css:43-46 | serve/cockpit/web/src/__tests__/Card.css.test.ts:96-113 | PASS |
| AC-4 | serve/cockpit/web/src/components/Card.css:48-53 | serve/cockpit/web/src/__tests__/Card.css.test.ts:120-130 | PASS |

## Observations
- AC-4 proof is slightly broader than ideal: serve/cockpit/web/src/__tests__/Card.css.test.ts:120-130 matches any hover or focus-visible block in Card.css, while the current implementation uses the intended card selectors at serve/cockpit/web/src/components/Card.css:48-53. This is a future hardening opportunity, not a present contract miss.
- AC-1 covers the five named operational states directly but does not add overlap-case precedence assertions beyond the isolated state checks in serve/cockpit/web/src/__tests__/Card.signal.test.tsx:73-110. Given the current AC wording, that is acceptable but not exhaustive.
- Safety and security review: no auth, storage, shell, path, or untrusted-input surface is in scope for this task.
2026-05-14T01:24:36+00:00
## Docs Gate

**Verdict: PASS**

**Item 1 — README Verification:** `serve/cockpit/README.md` read in full (two passes). Convention mapping: `serve/cockpit/web/src/components/Card.tsx` and `Card.css` map to `serve/cockpit/README.md`. Layer 1 grep: zero matches for Card, data-signal, border-left, signal, or hover/focus selectors. Layer 2 editorial: README covers backend routes, engine surface, and tooling versions only — no individual React component documentation exists or is expected. No contradictions or staleness introduced. **No docs update required.**

**Item 2 — External Attribution:** All sources listed in task Research section (Card.tsx, tokens.css, PDSHexScan, #1535/#1536 research) are internal project artifacts. N/A — no external attribution needed.

**Item 3 — Research Doc:** `.owlbear/research/1538-card-css-test-approach.md` confirmed present on disk and linked in task body. Verified.

**Item 4 — Deletion Detection:** No files deleted this task cycle. Builder added `Card.css`, `Card.signal.test.tsx`, `Card.css.test.ts`; modified `Card.tsx` and `KanbanBoard.both-or-nothing.test.tsx`. N/A — no deletion impact, no orphaned references.

**Scratch cleanup:** No `.owlbear/scratch/1538-*` files found — clean.
2026-05-14T01:45:07+00:00
## Audit\n### Regression Detection\n- quality-runner mode full: Python 2826 passed / 20 failed (pre-existing/other-task), Vitest 1649 passed / 15 failed across 5 files\n- #1538-specific regression check: 88 passed / 2 failed in KanbanBoard.both-or-nothing.test.tsx\n- Root cause: the 2 both-or-nothing failures are NOT #1538 regressions — commit 4fac5a28 (#1538 builder) restored inline borderLeft, but commit 7e4acfeb (#1544 builder) subsequently removed it. git diff 4fac5a28..7e4acfeb confirms #1544 deleted the borderLeft inline style and PRIORITY_COLORS map. These failures belong to #1544's audit scope.\n- All #1538-specific tests (Card.signal.test.tsx, Card.css.test.ts) pass\n- Remaining frontend failures from sibling RED-phase tasks (#1540, #1535, #1541, #1542)\n- regression verdict: PASS (no #1538-caused regressions)\n\n### Intent Verification\n- scope alignment: PASS (Card.tsx, Card.css — correct domain for card CSS signal states)\n- purpose match: PASS (signal border, hover, focus, selected states match task purpose)\n- extraneous scope: none\n- boundary check: function-level behavior verification deferred to reviewer\n\n### Architect Quality: 4/5\n- ACs were specific and well-refined through two challenger rounds and architect review\n- AC-2 ready-state ambiguity resolved, AC-4 added for hover/focus completeness\n- Minor gap: no AC consideration of existing tests relying on inline borderLeft pattern, though builder handled it in re-entry\n\n### Commit Integrity\n- upstream commit presence: PASS\n  - f6efa6c1 (researcher)\n  - 44f47c7d (test-writer)\n  - c0ad8fc5 (builder first pass)\n  - 4fac5a28 (builder fix pass — regression stabilization)\n  - git status --porcelain: clean for all task files\n- kanban commit packaging: pending (this archive)\n\n### Review Evidence\n- Present and thorough across two review cycles\n- Second-cycle PASS with full AC mapping table, challenger cross-check (proceed, 0.82), and non-blocking observations\n- Docs gate: PASS (no docs impact, research doc present, no deletions)\n\n### Deduction Breakdown\nNo deductions applied.\n\n### Confidence: 1.00\n### Action: archive