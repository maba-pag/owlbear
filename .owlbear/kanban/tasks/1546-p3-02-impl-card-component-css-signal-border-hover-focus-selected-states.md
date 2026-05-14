---
id: 1546
title: 'P3-02: impl — card component CSS: signal border, hover, focus, selected states'
status: review
priority: important
created: 2026-05-13T18:43:23.784270+00:00
updated: 2026-05-14T04:21:33.084046+00:00
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
claimed_at: 2026-05-14T04:21:33.084046+00:00
archival_reason:
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