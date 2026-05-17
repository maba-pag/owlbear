---
id: 1626
title: 'P3-06: Focus-visible rings — PDS focus styling'
status: review
priority: important
created: 2026-05-16T03:37:44.792818+00:00
updated: 2026-05-16T18:19:35.919548+00:00
tags:
  - frontend
  - pds
  - phase-3
parent: 1590
depends_on: []
ac:
  - Every element matching `button, [role="button"], [role="menuitem"], input, 
    a` shows a visible :focus-visible outline when it receives keyboard focus 
    (Tab or arrow-key navigation) — Playwright assertion on outline-style and 
    outline-color
  - 'Focus rings use `var(--color-focus)` from PDS Tailwind theme (not custom `--pds-state-focus`
    or hardcoded values); Card.css migrated from `--pds-state-focus` to `--color-focus`
    with `outline-offset: 2px`'
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1590.

PDS focus styling on all interactive elements.

Scope: Focus-visible only.
Out of scope: Dark mode, motion, accessibility sweep.

2026-05-16T15:38:43+00:00
## Research
- Research doc: .owlbear/research/focus-visible-pds-styling.md
- Sources: 7 studied, 5 high-relevance
- Recommendation: Global CSS rule using `var(--color-focus)` from PDS Tailwind theme for native elements; Card.css token migration from `--pds-state-focus` → `--color-focus` (confidence: 0.82)

### Element classification
- PDS components (PButton, PInputText, PSelect, etc.): self-managed focus via Shadow DOM — no action
- Native elements needing focus: `.icon-button`, HealthBadge `button`, ErrorBoundary `button`, `[role="menuitem"]`, `input[type="radio"]`
- Card: existing rule needs token update (`--pds-state-focus` → `--color-focus`) and offset (1px → 2px)

### PDS canonical pattern
```css
:focus-visible {
  outline: 2px solid var(--color-focus);
  outline-offset: 2px;
}
```
Tailwind: `focus-visible:outline outline-focus outline-offset-2`

[[2026-05-16T17:38:58+02:00]]
## Research
- Research doc: .owlbear/research/focus-visible-pds-styling.md
- Sources: 7 studied (PDS v4 Tailwind focus docs, GitHub source for getFocusVisibleStyle/getFocusBaseStyles/TailwindFocusVisible/AGENTS.md, local @theme, SCSS mixin), 5 high-relevance
- Recommendation: Global CSS rule for native elements using `var(--color-focus)` from PDS Tailwind theme (confidence: 0.82)
- Key finding: PDS components handle their own focus via Shadow DOM — only native HTML elements need styling
- Token: `--color-focus` (PDS canonical) replaces our custom `--pds-state-focus`
- Card.css needs token migration + offset alignment (1px → 2px)
- Tier: T1 autonomous — CSS-only change, no arch/security/breaking impact
- No additional follow-up tasks needed

[[2026-05-16T18:23:06+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Focus-visible styling only; dark mode, motion, a11y sweep explicitly out of scope |
| Interface clarity | PASS (after refinement) | AC refined to name exact selectors and token; mechanically testable |
| Dependency correctness | PASS | #1621 archived-as-deprecated into #1626; test-writer handles RED phase in pipeline |
| Module layering | PASS | CSS-only change, no module imports |
| TDD compliance | PASS | Standard pipeline: test-writer processes in `todo` |
| KISS/YAGNI | PASS | Global CSS rule (Approach A from research) — simplest mechanism |
| Premise challenge | PASS | PDS global-styles does NOT style native element focus; task fills a real gap |
| Pattern consistency | PASS | Uses PDS canonical `var(--color-focus)` token and 2px/2px pattern |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | Frontend CSS only |

### AC Refinement
| Original AC | Issue | Refined AC |
|-------------|-------|------------|
| Tab through interactive elements… | \"Tab\" excludes arrow-key roving-focus widgets (menuitems) | Every element matching `button, [role=\"button\"], [role=\"menuitem\"], input, a` — keyboard focus (Tab or arrow-key) |
| Focus rings use PDS focus tokens | Ambiguous which token (--color-focus vs --p-color-focus) | Explicitly names `var(--color-focus)` from PDS Tailwind theme; Card.css migration specified |

### Challenge Results
- Challenger: reconsider (confidence 0.38)
- Findings addressed:
  - AC-1 imprecision: ACCEPTED — refined to name selectors and navigation methods
  - Exhaustiveness: REBUTTED — global selector covers all additional surfaces (HistorySubtab role=\"button\", DecisionViewport role=\"button\", ActivityTab button)
  - Token ambiguity: ACCEPTED — AC2 now names exact token
  - Dependency #1621 archived: NOTED — standard pipeline TDD, no structural issue
  - Regression surface: MINOR — builder updates existing token-referencing tests
- Architect response: accepted 2/5, rebutted 2/5, noted 1/5 → revised AC and approved

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED

### Verdict: APPROVE
### Action Taken: Refined AC for precision (selector scope + exact token name), advanced to todo

[[2026-05-16T19:21:59+02:00]]
## Test-Writer Notes

**Test files:**
- `serve/cockpit/web/e2e/focus-visible-pds-1626.spec.ts` — Playwright E2E (AC-1 + AC-2 behavioral proxy)
- `serve/cockpit/web/src/__tests__/FocusVisibleCssSource_1626.test.ts` — Vitest CSS source contract (AC-2)

**Test classes and counts:**

| Class | File | Category | Count |
|-------|------|----------|-------|
| `TestFromAC_FocusVisibleOutline` | E2E spec | AC-1 | 8 |
| `TestFromAC_CardFocusTokenMigration` | E2E spec | AC-2 behavioral | 1 |
| `TestFromAC_FocusTokenSource` | Vitest | AC-2 CSS source | 5 |

**Total: 14 tests, all FAIL in RED.**

**Category breakdown:**
- Happy (outline-style + outline-color for button, article[role="button"], [role="menuitem"], a): 8 E2E
- Boundary (Card outline-offset: 2px vs current 1px): 1 E2E
- CSS source (Card.css token migration + global rule presence): 4 Vitest
- Error (no legacy token in any :focus-visible block): 1 Vitest

**AC coverage:**

| AC | Tests | RED reason |
|----|-------|-----------|
| AC-1: button/role-button/menuitem/input/a show solid outline + PDS color | 8 E2E | No global :focus-visible CSS rule — UA gives `outline:auto` (not 'solid') and system accent color (not rgb(26,68,234)) |
| AC-2: var(--color-focus) not --pds-state-focus; Card.css offset 2px | 1 E2E (offset) + 4 Vitest (source) | Card.css has `outline-offset:1px` + `var(--pds-state-focus)`; no global rule in any CSS file |

**Verification:** quality-runner confirmed 9/9 E2E FAIL, 5/5 Vitest FAIL, 0 lint errors.
**Commit:** `91e75c49` — test: focus-visible PDS rings — outline style/color/offset E2E + CSS source contract (#1626, test-writer)

[[2026-05-16T20:19:35+02:00]]
## Builder Notes
- Implementation:
  - serve/cockpit/web/src/components/Card.css
  - serve/cockpit/web/src/custom-tokens.css
- Changes applied:
  - Migrated `.card:focus-visible` token from `var(--p-color-focus)` to `var(--color-focus)`.
  - Updated Card outline offset from `1px` to `2px`.
  - Added global focus styling rule for `button`, `[role="button"]`, `[role="menuitem"]`, `input`, `a` using `outline: 2px solid var(--color-focus)` and `outline-offset: 2px`.
  - Added minimal fallback selector `[role="menuitem"]:focus` to satisfy programmatic roving-focus behavior in context menu while keeping `:focus-visible` styling in place.
- Tests:
  - quality-runner scoped Vitest: `serve/cockpit/web/src/__tests__/FocusVisibleCssSource_1626.test.ts` -> 5 passed, 0 failed.
  - Playwright behavioral spec: `serve/cockpit/web/e2e/focus-visible-pds-1626.spec.ts` -> 9 passed, 0 failed (direct execution fallback due quality-runner webServer startup issues in this workspace).
- Coverage: N/A for this frontend CSS behavioral path.
- Lint status:
  - quality-runner lint on touched files -> clean (eslint/stylelint no violations).
- Commit:
  - `b9c5e09c` feat: add PDS focus-visible ring styling (#1626, builder)
- Evidence summary:
  - AC-1 satisfied via behavioral Playwright assertions across target selector categories.
  - AC-2 satisfied via source-contract Vitest checks plus Card.css migration and global rule token alignment.
