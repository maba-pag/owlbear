---
id: 1546
title: 'P3-02: impl — card component CSS: signal border, hover, focus, selected states'
status: archived
priority: important
created: 2026-05-13T18:43:23.784270+00:00
updated: 2026-05-14T05:57:16.395452+00:00
tags:
  - phase-3
  - scope:cockpit
  - css
  - frontend
parent: 1534
depends_on:
  - 1538
  - 1543
  - 1544
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
Brief: see parent #1534 (`.owlbear/briefs/draft-board-visual-design/brief.md`)

## Scope
- **In:** Card CSS: 4px left border from signal model, hover/focus/selected visual states, `data-signal` and `data-selected` attributes in JSX, `overflow-wrap: break-word`, transparent background, drag muted state, `resolveSignal` → `computeSignal` import consolidation
- **Out:** Signal computation logic (done in P1-04 #1544), column/shell CSS

## Acceptance Criteria

- AC-1: Card renders with 4px left border colored by signal model via `[data-signal]` CSS selectors (orange/red/purple/grey/theme-default)
- AC-2: Card has hover state (PDS `state-hover` token), focus state (PDS focus ring), and selected state (`[data-selected]` box-shadow) — selected styling is additive, not replacing the signal border
- AC-3: Card uses `overflow-wrap: break-word` for title text with no fixed height constraint; background is transparent
- AC-4: Card element has `opacity: 0.5` while being dragged, triggered by a `data-dragging` attribute set in JSX during the drag lifecycle; CSS selector `[data-dragging="true"]` applies the opacity

Proof bundle: behavioral

## Builder Guidance

1. **Remove legacy token shadowing** — Card.css lines 5–11 re-declare `--pds-*` with `--pds-theme-light-*` values, breaking dark mode. Delete all 7 lines; global agnostic tokens from #1543 resolve correctly.
2. **Fix base border** — `var(--pds-theme-light-contrast-medium)` → `var(--pds-contrast-medium)`
3. **Move `--pds-signal-claimed`** to tokens.css with dark override (`hsl(270 80% 70%)`)
4. **Remove `max-height: 56px`** (violates AC-3 / brief D7)
5. **Add `overflow-wrap: break-word`** to `.card` (AC-3)
6. **Remove `--card-priority-border`** intermediate variable (redundant)
7. **Add drag state** — `data-dragging` attr in Card.tsx + `[data-dragging="true"] { opacity: 0.5 }` CSS (AC-4)
8. **Replace `resolveSignal()` with `computeSignal()` import** — Card.tsx has a local `resolveSignal()` (lines 17–32) that duplicates `src/utils/computeSignal.ts` (created by #1536, verified by #1544 with 17 passing tests). Replace with `import { computeSignal } from '../utils/computeSignal'` and delete the local function. Functionally identical — same 5-signal precedence order.
9. **Test gaps** — AC-3 and AC-4 have no test coverage from #1538 (test file uses different AC numbering). Test-writer will add RED tests for these ACs.

## Research
- Research doc: .owlbear/research/card-css-impl-1546.md
- Sources: 8 studied, 6 high-relevance
- Recommendation: Clean up existing Card.css — remove legacy token shadowing, fix height/overflow-wrap, add drag state (confidence: .90)
2026-05-14T03:26:07+00:00
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Card component CSS + minimal JSX (drag attr, import swap) — single component scope |
| Interface clarity | PASS | 4 ACs with named CSS selectors, token references, exact opacity value, and specific data attributes |
| Dependency correctness | PASS | All 3 deps archived: #1538 (tests), #1543 (tokens), #1544 (signal model) |
| Module layering | PASS | Card.css + Card.tsx; no cross-layer imports. computeSignal import follows utils → component direction |
| TDD compliance | PASS | #1538 provides RED tests for AC-1/AC-2; test-writer will add AC-3/AC-4 tests before builder |
| KISS/YAGNI | PASS | CSS cleanup + 2 additions (drag state, overflow-wrap); no abstractions |
| Premise challenge | PASS | Card CSS has real defects (legacy token shadowing breaks dark mode, fixed height, missing overflow-wrap) |
| Pattern consistency | PASS | Follows established Card.css/Card.tsx patterns; file-based CSS test approach from #1538 |
| Security surface | N/A | CSS styling and visual states; no system boundaries |
| Single domain | PASS | Frontend CSS only |

### Design Diverge
- Trigger: skipped — single approach (CSS cleanup), no competing valid approaches

### Challenge Results
- Challenger: reconsider (confidence 0.66)
- Challenges raised: (1) proof sufficiency — existing tests don't cover 4px width or selected additivity; (2) task-contract drift — #1544 defers resolveSignal→computeSignal to #1546 but ACs didn't capture it; (3) AC-4 ambiguity with "or similar"/"or equivalent"; (4) research skipped challenge step
- Architect response: ACCEPTED (2) — added builder guidance #8 for computeSignal import replacement and updated scope line. ACCEPTED (3) — refined AC-4 to pin exact `data-dragging` attribute and `opacity: 0.5`. REBUTTED (1) — test-writer stage fills proof gaps; existing coverage is acknowledged as partial, not claimed as complete. NOTED (4) — trivial CSS with no competing approaches; challenge skip proportionate.

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED (AC-3 and AC-4 need new RED tests; AC-1/AC-2 partially covered by #1538)

### Refinements Applied
- AC-4: pinned `data-dragging` attribute and `opacity: 0.5` (removed "or similar"/"or equivalent" ambiguity)
- Scope: added `resolveSignal → computeSignal import consolidation`
- Builder Guidance: added #8 (computeSignal import replacement, deferred from #1544) and #9 (test gap awareness)

### Verdict: APPROVE
### Action Taken: Refined AC-4 wording, expanded scope and builder guidance for computeSignal consolidation, advanced to todo.
2026-05-14T03:39:35+00:00
## Test-Writer Notes
- Test files:
  - `serve/cockpit/web/src/__tests__/CardCSS_1546.test.ts`
  - `serve/cockpit/web/src/__tests__/CardDrag_1546.test.tsx`
- Classes:
  - `TestFromAC_CardCSSTextOverflow` — AC-3 CSS (overflow-wrap, max-height removal)
  - `TestFromAC_CardCSSBaseToken` — AC-1 base token correctness (no legacy --pds-theme-light-* shadows, direct --pds-contrast-medium reference)
  - `TestFromAC_CardCSSDragState` — AC-4 CSS ([data-dragging="true"] selector + opacity: 0.5)
  - `TestFromAC_CardDragAttribute` — AC-4 JSX (drag state lifecycle: initial false, true on dragStart, reset on dragEnd, callback + state simultaneous)
- Tests per category: happy 5, edge 2, boundary 0, error 0, regression-guard 5
- Total: 12 tests, all FAIL (0 passed, 12 failed)
- ruff: N/A (TypeScript) — ESLint: clean

AC coverage table:
| AC | Tests | Coverage |
|----|-------|---------|
| AC-1 (4px border, signal model, dark mode tokens) | 4 (base token + no shadowing ×3) | Supplements #1538 signal selector tests |
| AC-3 (overflow-wrap, no max-height) | 2 | Full |
| AC-4 CSS ([data-dragging] + opacity) | 2 | Full |
| AC-4 JSX (drag lifecycle in DOM) | 4 | Full |

Note: AC-2 (hover/focus/selected states) is already covered by Card.css.test.ts from #1538 — not duplicated here.
2026-05-14T03:54:27+00:00
## Builder Notes
- Implementation: updated `serve/cockpit/web/src/components/Card.tsx`, `serve/cockpit/web/src/components/Card.css`, and `serve/cockpit/web/src/tokens.css`.
- AC coverage:
  - AC-1: `.card` now uses `border-left: 4px solid var(--pds-contrast-medium)` with signal-specific `border-left-color` selectors and no legacy `--pds-theme-light-*` shadowing in `Card.css`.
  - AC-2: existing hover/focus/selected state styling preserved; selected state remains additive to signal border.
  - AC-3: removed `max-height`, added `overflow-wrap: break-word`, and kept transparent card background.
  - AC-4: added `data-dragging` lifecycle in JSX (`false` initial, `true` on drag start, `false` on drag end) and `[data-dragging="true"] { opacity: 0.5; }` CSS.
- Signal consolidation: removed local `resolveSignal()` and imported shared `computeSignal` from `src/utils/computeSignal.ts`.
- Token move: added `--pds-signal-claimed` to `src/tokens.css` in `:root` and dark-mode overrides (`[data-theme="dark"]` and `@media (prefers-color-scheme: dark)` fallback).
- Tests (quality-runner, scoped): 116 passed / 0 failed across card-focused suites including task tests (`CardCSS_1546`, `CardDrag_1546`) and durable card/board regressions.
- Coverage (quality-runner): `Card.tsx` 90.9% (gate satisfied for touched module).
- Lint: clean (eslint/stylelint clean in scoped run).
- Commit: `4a680f66c76f87fd25962bc1a95a9f0712099f5d` (`feat: implement card css signal/drag states (#1546, builder)`).
2026-05-14T04:06:11+00:00
## Review Evidence
- Verdict: FAIL to todo.
- Builder evidence reviewed first: scoped quality-runner note reports 116 passed / 0 failed, lint clean, and 90.9% coverage for `serve/cockpit/web/src/components/Card.tsx`.
- Direct code review indicates the implementation itself is aligned with the task AC: `serve/cockpit/web/src/components/Card.css:3-4,31-46`, `serve/cockpit/web/src/components/Card.tsx:25,60-76`, and `serve/cockpit/web/src/utils/computeSignal.ts:8-26` all match the intended behavior.
- Blocking findings:

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC-1 | The current tests do not prove the required `4px` left border width. The task-specific assertion only proves that the base `border-left` declaration references `var(--pds-contrast-medium)`, so a `1px` or `8px` border would still pass. | Implementation: `serve/cockpit/web/src/components/Card.css:3`. Current proof: `serve/cockpit/web/src/__tests__/CardCSS_1546.test.ts:60-66`. Task history: Architecture Review in the task body explicitly called out width proof as a gap for the test-writer stage. | todo |
| 2 | AC-2 | The current tests do not falsify regressions where selected styling replaces the signal border. The selected-state test only requires a `[data-selected]` block with `box-shadow` or `outline` using the success token, while the signal-color tests inspect separate `[data-signal]` blocks. A selected rule that also overrides `border-left-color` would still pass. | Implementation: `serve/cockpit/web/src/components/Card.css:31-34`. Current selected proof: `serve/cockpit/web/src/__tests__/Card.css.test.ts:96-111`. Separate signal proof surface: `serve/cockpit/web/src/__tests__/Card.css.test.ts:50-88`. Task history: Architecture Review in the task body explicitly called out selected-additivity proof as a gap for the test-writer stage. | todo |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Add a falsifiable assertion that the base `.card` rule keeps a `4px` left border, not just a `border-left` token reference. | serve/cockpit/web/src/__tests__/CardCSS_1546.test.ts | Review finding 1; `serve/cockpit/web/src/components/Card.css:3`; `serve/cockpit/web/src/__tests__/CardCSS_1546.test.ts:60-66` |
| 2 | test-writer | Add a falsifiable assertion that selected styling is additive and does not replace the signal border, for example by proving the selected rule does not introduce a `border-left-color` override against the `[data-signal]` selectors. | serve/cockpit/web/src/__tests__/Card.css.test.ts | Review finding 2; `serve/cockpit/web/src/components/Card.css:31-34`; `serve/cockpit/web/src/__tests__/Card.css.test.ts:96-111`; `serve/cockpit/web/src/__tests__/Card.css.test.ts:50-88` |

## Observations
- AC-3's transparent base background is present directly in source at `serve/cockpit/web/src/components/Card.css:4`, but the current tests do not assert it. I did not use that as a blocking finding because the stronger false-green risks are the AC-1 width and AC-2 additivity gaps.
- I did not find a scoped implementation defect in `Card.tsx`, `Card.css`, or `tokens.css`; this rejection is proof-only and should be handled by the test-writer.
- No scoped editor diagnostics were present in the reviewed implementation and task-test files.
2026-05-14T04:10:34+00:00
## Test-Writer Notes
- Retry: added 2 tests for reviewer gaps. All tests pass against current impl.
- Builder skip: test-only retry, all tests green.

**New tests added:**
1. `CardCSS_1546.test.ts` — `TestFromAC_CardCSSBaseToken`: `.card border-left declaration specifies 4px width — falsifiable against 1px or 8px (AC-1)`. Falsifies a border that references the correct token but uses a wrong width value.
2. `Card.css.test.ts` — `TestFromAC_CardCSSSelectedState`: `[data-selected] block does not introduce border-left-color — selected state is additive to signal border (AC-2)`. Falsifies a selected rule that overrides the signal border color.

**Quality-runner (scoped):** 23 passed / 0 failed across CardCSS_1546, Card.css, CardDrag_1546 — all pre-existing + new tests green against current impl. ESLint clean.
**Commit:** d0e81c31 (test: add retry tests for card CSS border width and selected additivity (#1546, test-writer))
2026-05-14T04:37:26+00:00
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1546 -> docs | AC mapped to code and evidence sufficient.
- Builder evidence reviewed first: task body reports scoped quality-runner evidence of 116 passed / 0 failed, lint clean, and 90.9% coverage for Card.tsx; the test-writer retry reports 23 passed / 0 failed across CardCSS_1546, Card.css, and CardDrag_1546 with ESLint clean.
- AC evidence map:

| AC | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC-1 | `serve/cockpit/web/src/components/Card.css:3` keeps the 4px base border; `serve/cockpit/web/src/components/Card.tsx:61` emits `data-signal`; signal-specific selectors remain in `serve/cockpit/web/src/components/Card.css:13-29`. | `serve/cockpit/web/src/__tests__/CardCSS_1546.test.ts:69` proves the 4px width; `serve/cockpit/web/src/__tests__/Card.css.test.ts:53`, `:60`, `:67`, `:74`, `:81` cover the signal-color selector contract; durable DOM proof in `serve/cockpit/web/src/__tests__/Card.signal.test.tsx:73`, `:81`, `:89`, `:97`, `:105` proves runtime `data-signal` emission. | PASS |
| AC-2 | `serve/cockpit/web/src/components/Card.tsx:60` emits `data-selected`; selected styling is additive in `serve/cockpit/web/src/components/Card.css:31`; hover/focus rules are present at `serve/cockpit/web/src/components/Card.css:36` and `:40`. | `serve/cockpit/web/src/__tests__/Card.css.test.ts:101` proves selected styling uses the success token and `:116` closes the previously requested additivity gap; `serve/cockpit/web/src/__tests__/Card.css.test.ts:132` and `:139` cover hover/focus token usage; durable runtime `data-selected` proof exists in `serve/cockpit/web/src/__tests__/Shell.card-selection.integration.test.tsx:185` and `:212`. | PASS |
| AC-3 | Base rule keeps `background: transparent` at `serve/cockpit/web/src/components/Card.css:4` and `overflow-wrap: break-word` with no `max-height` in the same block. | `serve/cockpit/web/src/__tests__/CardCSS_1546.test.ts:42` proves `overflow-wrap: break-word`; `serve/cockpit/web/src/__tests__/CardCSS_1546.test.ts:49` proves the fixed-height constraint was removed. | PASS |
| AC-4 | `serve/cockpit/web/src/components/Card.tsx:62`, `:70`, and `:74` implement the `data-dragging` lifecycle; `serve/cockpit/web/src/components/Card.css:45` applies the drag opacity rule. | `serve/cockpit/web/src/__tests__/CardCSS_1546.test.ts:110` proves `[data-dragging="true"] { opacity: 0.5 }`; `serve/cockpit/web/src/__tests__/CardDrag_1546.test.tsx:53`, `:69`, `:89`, and `:112` prove the JSX drag lifecycle. | PASS |
- Challenger cross-check: a stronger second-cycle FAIL was not supported. The retry satisfied the previously assigned proof gaps, and the durable frontend suites already cover the runtime `data-signal` / `data-selected` hooks.
- Blocking findings: none.

## Observations
- `serve/cockpit/web/src/components/Card.css:4` is source-aligned for the transparent base background, but there is still no direct named assertion for that declaration. I am not treating that as a blocker on this retry because the prior review explicitly routed only the 4px-width and selected-additivity gaps, and those gaps are now closed.
- `serve/cockpit/web/src/__tests__/Card.css.test.ts:132` and `:139` are not selector-scoped to `.card:hover` / `.card:focus-visible`; they are acceptable for this task, but a future proof-hardening pass could make those assertions more specific.
- `serve/cockpit/web/src/__tests__/Card.css.test.ts:116` guards against `border-left-color` overrides in the selected rule. If the team wants a stronger long-term regression net, a later follow-up could also reject `border-left` / `border` shorthand in that block.
- No scoped editor diagnostics were present in `Card.css`, `Card.tsx`, `tokens.css`, or the reviewed test files.
2026-05-14T04:39:08+00:00
## Docs Gate

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | README verification | Yes | N/A | `serve/cockpit/README.md` covers API, stack, and launch — no card CSS implementation details documented there. Grep on `resolveSignal`, `data-dragging`, `data-signal`, `Card.css`, `computeSignal` returned no matches in the README. No task-caused drift detected. |
| 2 | External attribution | Yes | N/A — already updated | `sources/overview.md` already contains a "Card CSS Implementation Research (Task #1546)" section at lines 97–102 with 2 entries (MDN drag-and-drop, Penpot design tokens). No further update needed. |
| 3 | Research doc | Yes | N/A | Research file `.owlbear/research/card-css-impl-1546.md` exists and is linked in the task body under "Research". |
| 4 | Deletion detection | Yes | N/A | No source files deleted — only code within `Card.tsx`, `Card.css`, and `tokens.css` was modified. No orphaned references. |

### Verification Layers
- Layer 1 — grep: `serve/cockpit/README.md` contains no references to the changed symbols (`resolveSignal`, `computeSignal`, `data-dragging`, `data-signal`, `Card.css`). `sources/overview.md` already carries the #1546 attribution block.
- Layer 2 — editorial: The cockpit README is API/stack/launch-scoped; internal component CSS states are implementation details not documented at this level. Consistent with adjacent tasks (#1538, #1543, #1544) which also added no README entries for CSS-level changes.

### Scratch cleanup
No `.owlbear/scratch/1546-*` files found — nothing to clean.
2026-05-14T04:57:30+00:00
## Audit
### Regression Detection
- quality-runner mode full: Python 6301 passed / 10 failed, Frontend 20 passed / 10 failed, lint clean
- 3 failures confirmed as regressions introduced by #1546: `TokenArchitecture_1535.test.ts` (AC-1: :root declares 19 tokens) and `TokenArchitecture_1543.test.ts` (AC-2 happy: media query block, AC-2 boundary: exactly 19 tokens). Root cause: builder guidance #3 moved `--pds-signal-claimed` to `tokens.css`, bumping color token count from 19 to 20, but neither builder nor test-writer updated the sibling token-architecture tests.
- Remaining 17 failures are pre-existing (cockpit_view kanban cleanup, ideation diagram, server status, engine accessor migration, ThemeToggle, ResponsiveLayout shell tokens, KanbanBoard filter) — unrelated to card CSS domain.
- regression verdict: FAIL

### Intent Verification
- scope alignment: PASS (changed files: Card.tsx, Card.css, tokens.css — all cockpit frontend component domain)
- purpose match: PASS (card CSS signal borders, hover/focus/selected states, drag opacity, computeSignal consolidation — matches AC intent)
- extraneous scope: none
- boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 4/5
ACs are specific with named CSS selectors, exact data attributes, and concrete values. Challenger engagement produced useful refinements (AC-4 wording, computeSignal scope addition). Minor gap: architect guidance #3 directed adding a token to tokens.css but didn't flag the downstream impact on TokenArchitecture test suites from #1535/#1543. Score 4 — adequate, minor gap filled at audit.

### Commit Integrity
- upstream commit presence: PASS (builder: 4a680f66, test-writer: be2b24ab + d0e81c31 — all verified via git log)
- kanban commit packaging: PASS (auditor will commit kanban state after end_work)

### Deduction Breakdown
- Regression failures (3 token architecture tests broken by #1546): -.10

### Confidence: 0.90
### Action: reject-to-backlog

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Update TokenArchitecture_1535.test.ts EXPECTED_COLOR_TOKENS to include --pds-signal-claimed (20 tokens); update TokenArchitecture_1543.test.ts boundary assertion from 19 to 20 tokens in both media-query and data-theme dark blocks | serve/cockpit/web/src/__tests__/TokenArchitecture_1535.test.ts, serve/cockpit/web/src/__tests__/TokenArchitecture_1543.test.ts | Regression detection: 3 failures caused by adding --pds-signal-claimed to tokens.css without updating existing token-count assertions |
2026-05-14T04:59:34+00:00

## Architecture Re-Review (Audit Return)

### Context
Auditor rejected to backlog: 3 token-architecture test regressions caused by builder guidance #3 (moving `--pds-signal-claimed` to `tokens.css`). Implementation and original ACs remain sound — reviewer PASS, docs PASS, audit PASS on intent/scope. Only gap: sibling token-count assertions not updated.

### Evaluation
- Regression root cause is mechanical: `EXPECTED_COLOR_TOKENS` in `TokenArchitecture_1535.test.ts` has 19 entries, missing `--pds-signal-claimed`; `TokenArchitecture_1543.test.ts` asserts `19` tokens in boundary check.
- No AC change needed — original AC-1 through AC-4 remain valid and verified.
- No new architectural risk — updating test expectations to reflect the actual token set.

### Builder Guidance (Audit Fix)
10. **Fix token-architecture test regressions** — Add `'--pds-signal-claimed'` to `EXPECTED_COLOR_TOKENS` in `serve/cockpit/web/src/__tests__/TokenArchitecture_1535.test.ts` (19 → 20 entries). Update the "declares exactly 19 tokens" assertion in `serve/cockpit/web/src/__tests__/TokenArchitecture_1543.test.ts` to 20, in both the media-query and data-theme boundary checks. Run the full card + token test suites to confirm zero regressions.

### Proof-Bundle Validation
- Bundle: behavioral (unchanged)
- Test-writer: SKIP for this return — fix is to existing test expectations, not new RED tests.

### Verdict: APPROVE (re-review)
### Action Taken: Added builder guidance #10 for token-architecture test regression fix. Advanced to todo.
2026-05-14T04:59:38+00:00
Re-review after audit rejection. 3 token-architecture test regressions (TokenArchitecture_1535, TokenArchitecture_1543) caused by builder guidance #3 adding --pds-signal-claimed to tokens.css without updating expected token counts. Added builder guidance #10 for the mechanical fix. Original ACs, implementation, and review evidence remain valid. Test-writer SKIP — no new RED tests needed, only test expectation updates.
2026-05-14T05:10:46+00:00
## Test-Writer Notes
- Pass-through per architect re-review: no new RED tests required.
- Fix is updating existing token-count expectations in `TokenArchitecture_1535.test.ts` and `TokenArchitecture_1543.test.ts` (19 → 20), not writing new RED tests.
- Passing through to builder for guidance #10.
2026-05-14T05:16:18+00:00
## Builder Notes
- Scope: applied architect audit-fix guidance #10 only (token-architecture expectation updates).
- Files changed:
  - `serve/cockpit/web/src/__tests__/TokenArchitecture_1535.test.ts`
  - `serve/cockpit/web/src/__tests__/TokenArchitecture_1543.test.ts`
- RED verification (quality-runner, scoped before edits): 9 passed / 3 failed / 0 skipped.
  - Failures were exactly the expected regressions:
    - `TokenArchitecture_1535` AC-1 exact token set mismatch (extra `--pds-signal-claimed`)
    - `TokenArchitecture_1543` AC-2 happy exact token set mismatch (extra `--pds-signal-claimed`)
    - `TokenArchitecture_1543` AC-2 boundary expected 19 vs actual 20
- Fixes applied:
  - Added `--pds-signal-claimed` to `EXPECTED_COLOR_TOKENS` in both token-architecture suites.
  - Updated token-count assertions/messages from 19 to 20 where applicable.
- GREEN verification (quality-runner, scoped card+token suites): 35 passed / 0 failed / 0 skipped.
  - Tests run: `TokenArchitecture_1535.test.ts`, `TokenArchitecture_1543.test.ts`, `CardCSS_1546.test.ts`, `CardDrag_1546.test.tsx`, `Card.css.test.ts`
- Lint status (quality-runner, scoped lint-compatible rerun): clean (`eslint` clean, no violations).
- Coverage: not required for this mechanical test-expectation correction; no source implementation changes.
- Commit: `8ca1dfb188ee9813fcb77f77ab325d3d7e9f5243` (`fix: update token architecture counts for claimed signal token (#1546, builder)`).
2026-05-14T05:34:22+00:00
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1546 -> docs | audit-return regression fix verified; AC mapped to code and evidence sufficient.
- Builder evidence reviewed first: the audit-return builder note scoped this retry to `serve/cockpit/web/src/__tests__/TokenArchitecture_1535.test.ts` and `serve/cockpit/web/src/__tests__/TokenArchitecture_1543.test.ts`, with RED verification `9 passed / 3 failed / 0 skipped` before edits, GREEN verification `35 passed / 0 failed / 0 skipped` across the token+card suites after edits, and ESLint clean.
- Current-cycle evidence map:

| Review Item | Evidence | Status |
|---|---|---|
| Audit regression fix | `serve/cockpit/web/src/tokens.css:28`, `serve/cockpit/web/src/tokens.css:75`, and `serve/cockpit/web/src/tokens.css:103` declare `--pds-signal-claimed` in `:root`, `[data-theme="dark"]`, and the dark-media fallback. `serve/cockpit/web/src/__tests__/TokenArchitecture_1535.test.ts:30`, `serve/cockpit/web/src/__tests__/TokenArchitecture_1535.test.ts:101`, `serve/cockpit/web/src/__tests__/TokenArchitecture_1535.test.ts:120`, `serve/cockpit/web/src/__tests__/TokenArchitecture_1543.test.ts:30`, `serve/cockpit/web/src/__tests__/TokenArchitecture_1543.test.ts:110`, `serve/cockpit/web/src/__tests__/TokenArchitecture_1543.test.ts:119`, and `serve/cockpit/web/src/__tests__/TokenArchitecture_1543.test.ts:126` now encode the 20-token contract that previously failed at audit. | PASS |
| Original task ACs | The prior reviewer PASS for AC-1 through AC-4 remains intact because this return changed only token-architecture tests and introduced no new implementation edits; I found no contradiction between that retained Card evidence and the current regression fix. | PASS |
- Challenger cross-check: proceed (confidence 0.83). Strongest concern was scoped retry breadth after a full-audit catch, but no new blocking defect was proven.
- Blocking findings: none.

## Observations
- The retry evidence is narrower than the original full-audit run, but it covers the exact suites that failed (`TokenArchitecture_1535`, `TokenArchitecture_1543`) plus the related card suites, which is proportionate for this mechanical expectation update.
- AC-3 transparent-background proof and broader selected-state shorthand guards remain non-blocking hardening opportunities already recorded in the earlier review cycle; I am not re-opening scope on the same unchanged AC reading.
- No scoped editor diagnostics were present in `serve/cockpit/web/src/__tests__/TokenArchitecture_1535.test.ts`, `serve/cockpit/web/src/__tests__/TokenArchitecture_1543.test.ts`, or `serve/cockpit/web/src/tokens.css`.
2026-05-14T05:41:00+00:00
## Docs Gate (Audit-Return)

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | README verification | Yes | N/A | Audit-return builder changed only `TokenArchitecture_1535.test.ts` and `TokenArchitecture_1543.test.ts` — mechanical token-count expectation update (19→20). Grep on `signal-claimed`, `TokenArchitecture`, `token count` in `serve/cockpit/README.md` returned no matches. No task-caused drift. |
| 2 | External attribution | N/A | N/A — no external attribution needed | Audit-return fix required no external sources; mechanical test expectation update only. |
| 3 | Research doc | N/A | N/A — no research doc linkage needed | No new research artifact for this retry cycle. Prior research doc `.owlbear/research/card-css-impl-1546.md` already linked in task body from first cycle. |
| 4 | Deletion detection | N/A | N/A — no deletion impact | No files deleted in audit-return builder scope. |

### Verification Layers
- Layer 1 — grep: `serve/cockpit/README.md` contains no references to `--pds-signal-claimed`, `TokenArchitecture`, token count values, or any of the changed test symbols. Confirmed clean.
- Layer 2 — editorial: Cockpit README is API/stack/launch-scoped; token-count test expectations are internal verification detail not documented at this level. Consistent with prior docs gate pass.

### Scratch cleanup
No `.owlbear/scratch/1546-*` files found — nothing to clean.
2026-05-14T05:57:16+00:00
## Audit (Re-audit)
### Regression Detection
- quality-runner mode full: Python 4587 passed / 20 failed, Frontend vitest instrument failure (pdsVersionCheckPlugin CSS asset verification, pre-existing environment issue), lint clean (ruff exit 0, eslint exit 0)
- All 20 Python failures are in unrelated domains: engine accessor migration (7), cockpit view cleanup (3), ideation diagram (1), server status (1), engine rebind containment (1), dep guidance (1), lazy agent map (1), edit task contract (1), react compiler build (1), engine dispatch validation (1), cockpit react compiler (1). None in card CSS or token architecture domain.
- Prior audit's 3 token-architecture regressions (TokenArchitecture_1535, TokenArchitecture_1543) are now resolved: zero failures in those suites.
- Vitest environment failure is pre-existing (pdsVersionCheckPlugin buildStart hook), not caused by #1546. Builder scoped frontend runs confirmed 35 passed / 0 failed across card+token suites.
- Regression verdict: PASS

### Intent Verification
- Scope alignment: PASS (changed files: Card.tsx, Card.css, tokens.css, TokenArchitecture_1535.test.ts, TokenArchitecture_1543.test.ts, Card.css.test.ts, CardCSS_1546.test.ts, CardDrag_1546.test.tsx -- all cockpit frontend domain)
- Purpose match: PASS (card CSS signal borders, hover/focus/selected states, drag opacity, computeSignal consolidation, token-count test fix -- matches AC intent and audit-return guidance)
- Extraneous scope: none
- Boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 4/5
ACs are specific with named CSS selectors, exact data attributes, and concrete values. Challenger engagement produced useful refinements (AC-4 wording, computeSignal scope addition). Minor gap: guidance #3 directed adding a token to tokens.css without flagging downstream impact on token-architecture test suites, causing first-cycle audit rejection. Addressed in re-review with guidance #10. Score 4: adequate, minor gap identified and corrected in cycle.

### Commit Integrity
- Upstream commit presence: PASS (test-writer: be2b24ab, d0e81c31; builder: 4a680f66, 8ca1dfb1 -- all verified via git log)
- Kanban commit packaging: PASS (auditor will commit kanban state after end_work)

### Deduction Breakdown
- No task-related regressions: no deduction
- Intent aligned, no extraneous scope: no deduction
- Reviewer evidence present and detailed (two review cycles with explicit AC mapping): no deduction
- Lint clean: no deduction
- AC quality 4/5 (above 3): no deduction

### Confidence: 1.00
### Action: archive