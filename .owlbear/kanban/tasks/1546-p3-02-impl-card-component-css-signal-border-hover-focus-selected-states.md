---
id: 1546
title: 'P3-02: impl — card component CSS: signal border, hover, focus, selected states'
status: todo
priority: important
created: 2026-05-13T18:43:23.784270+00:00
updated: 2026-05-14T03:31:26.309216+00:00
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
claimed_at: 2026-05-14T03:31:26.309216+00:00
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