# P2-12: Migrate unowned simple swaps (option→PSelectOption, anchor→PLinkPure)

> **Owning task:** #1634 — P2-12: Migrate unowned simple swaps
> **Date:** 2026-05-17 **Status:** Complete

## 1. Context and Question

Task #1608 (component complexity inventory) identified two raw HTML elements with no owning Phase 2 task: `<option>` inside `<PSelect>` in TaskFieldsEditor and `<a>` in DecisionViewport. Both need PDS React wrapper replacements.

**Question:** Are the PDS wrappers available, what's the migration pattern, and are there test implications?

## 2. Sources Studied

| # | Source | Relevance |
|---|--------|-----------|
| 1 | `FilterPanel.tsx` lines 199–205 — live PSelectOption usage pattern | 1.0 |
| 2 | `FilterPanel.pds-controls.test.tsx` lines 134–190 — PDS option test pattern | 0.9 |
| 3 | PDS React wrapper `link-pure.wrapper.mjs` — PLinkPure props and defaults | 1.0 |
| 4 | PDS docs `designsystem.porsche.com/v3/components/link-pure/examples` — usage patterns | 0.8 |
| 5 | `DecisionViewport.test.tsx` lines 155–160, 287–292 — tag assertions | 1.0 |
| 6 | `@porsche-design-system/components-react` v4.1.0 `public-api.mjs` — export verification | 0.9 |

## 3. Analysis

### Swap 1: `<option>` → `PSelectOption` (TaskFieldsEditor.tsx:235)

| Criterion | Assessment |
|-----------|-----------|
| Wrapper available? | Yes — `PSelectOption` exported from `@porsche-design-system/components-react` |
| Proven pattern? | Yes — FilterPanel.tsx lines 199–205 (exact same pattern from #1617) |
| LOC delta | ~3 lines (add import, replace element tag) |
| Test impact | None — no tests directly query `<option>` inside TaskFieldsEditor's PSelect |
| Risk | Minimal |

### Swap 2: `<a>` → `PLinkPure` (DecisionViewport.tsx:55–63)

| Criterion | Assessment |
|-----------|-----------|
| Wrapper available? | Yes — `PLinkPure` exported, confirmed in `public-api.mjs` |
| Props compatible? | `href`, `onClick`, `data-testid` all pass through via rest spread |
| Default icon | `arrow-right` — adds visual arrow to what was plain text link |
| jsdom tag | Renders as `<p-link-pure>` (custom element, not `<a>`) |
| Test impact | **2 assertions break** (see below) |
| Risk | Low–moderate (test updates required) |

**Breaking test assertions in `DecisionViewport.test.tsx`:**

1. **Line ~157** — "task-id reference is a clickable element (button or link)": checks `tag === 'button' || tag === 'a'` — `p-link-pure` matches neither.
2. **Line ~289** — AC5 "each decision task reference is reachable via keyboard": `expect(tagName).toBe('a')` — will be `p-link-pure`.

**Pattern to fix:** Update assertions to also accept `p-link-pure` tag, following FilterPanel.pds-controls.test.tsx precedent (query `p-select-option` not `option`).

### PLinkPure icon consideration

PLinkPure defaults to `icon="arrow-right"`. For a compact task-id reference link (just a number), the arrow may be undesirable. Options:
- Set `icon="none"` — PDS v4 may not support this (needs runtime check)
- Use `hideLabel={true}` — hides text, wrong direction
- Accept the arrow — consistent PDS styling
- Use slotted anchor pattern: `<PLinkPure><a href=...>text</a></PLinkPure>` — preserves `<a>` in light DOM (tests pass, PDS styling applied)

The **slotted anchor** pattern is documented in PDS v3 for framework routing and avoids both the test breakage and icon concern. Recommended for builder evaluation.

## 4. Recommendation (confidence: 0.85)

Proceed as two independent swaps. Both wrappers are available and the patterns are established.

- **PSelectOption:** Direct swap following FilterPanel pattern. No complications.
- **PLinkPure:** Builder should evaluate slotted anchor vs. direct replacement. The slotted anchor (`<PLinkPure><a ...>`) preserves test compatibility and avoids icon questions but is slightly more verbose. Direct `<PLinkPure href=...>` is cleaner but requires 2 test assertion updates and an icon decision.

Challenge: skipped — trivial swap task with no architectural implications.

## 5. Follow-up Tasks

No additional tasks needed. Task #1634 itself is the implementation task, advancing to backlog.

**AC note for builder:** The task AC says "Existing test contracts preserved (DecisionViewport test already accepts button or a)." Two assertions hardcode `<a>` tag checks; the builder should update these to accept `p-link-pure` regardless of which PLinkPure pattern is chosen.
