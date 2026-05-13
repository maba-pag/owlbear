# Card Signal Data Model — Implementation Research

> **Owning task:** #1544 — P1-04: impl — card signal data model
> **Date:** 2026-05-14 **Status:** Complete

## 1. Context and Question

Task #1544 is the implementation pair to test task #1536 (archived). Scope: add `dep_status` to the frontend `Task` type, ensure `computeSignal()` exists, remove legacy `PRIORITY_COLORS` map and emoji badges from Card.tsx.

**Research questions:**
1. What is already implemented vs what remains?
2. What existing tests will break from AC-3 removals?
3. Are there any CSS/rendering side-effects from dropping `PRIORITY_COLORS`?

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| S1 | `serve/cockpit/web/src/hooks/useBoard.ts` L19-28 | Codebase | 1.0 — `Task` type lacks `dep_status` |
| S2 | `serve/cockpit/web/src/utils/computeSignal.ts` (full) | Codebase | 1.0 — AC-2 already implemented |
| S3 | `serve/cockpit/web/src/components/Card.tsx` (full) | Codebase | 1.0 — `PRIORITY_COLORS`, emoji badges, local `resolveSignal()` |
| S4 | `serve/cockpit/web/src/components/Card.css` L1-60 | Codebase | 1.0 — signal-based border selectors already present |
| S5 | `serve/kanban/src/owlbear_kanban/models.py` L499-522 | Codebase | 0.9 — `TaskSummary.dep_status` served to API |
| S6 | `serve/cockpit/web/src/__tests__/KanbanBoard.test.tsx` L317-365 | Codebase | 1.0 — tests asserting block-badge/running-indicator |
| S7 | `serve/cockpit/web/src/__tests__/ResponsiveLayout_1391.test.tsx` L170-222 | Codebase | 0.9 — test asserting `var(--pds-...)` in inline style |
| S8 | `.owlbear/briefs/draft-board-visual-design/brief.md` L52-72 | Brief | 1.0 — signal model spec (D10, D14) |
| S9 | `.owlbear/research/card-signal-data-model-1536.md` | Prior research | 1.0 — sibling task design (function sig, precedence, file placement) |
| S10 | `serve/cockpit/web/src/api/tasks.ts` L4-18 | Codebase | 0.8 — `TaskDetail` already has `dep_status` |

## 3. Analysis

### 3.1 AC-by-AC Implementation State

| AC | Description | Current State | Work Needed |
|----|-------------|---------------|-------------|
| AC-1 | `Task` type includes `dep_status` | `useBoard.ts` Task lacks field; backend `TaskSummary` already serves it; `Card.tsx` casts via `as Task & { dep_status?: ... }` | Add `dep_status: string \| null` to `Task` interface in `useBoard.ts` |
| AC-2 | `computeSignal()` returns correct signals | `src/utils/computeSignal.ts` exists with correct signature + logic; 17 passing tests in `computeSignal.test.ts` | **None** — built and verified via #1536 |
| AC-3 | `PRIORITY_COLORS` and emoji badges removed | `Card.tsx` L6-12 defines `PRIORITY_COLORS`; L113-116 renders ⛔ and ▶ spans | Remove map, inline style setter, and emoji badge spans from Card.tsx |

### 3.2 CSS Side-Effect of Removing PRIORITY_COLORS

Current rendering chain:
1. `Card.tsx` sets `--card-priority-border` inline via `PRIORITY_COLORS[task.priority]`
2. `Card.css` L3: `border-left: 4px solid var(--card-priority-border, var(--pds-theme-light-contrast-medium))`
3. `Card.css` L23-37: `[data-signal="*"]` selectors override `border-left-color`

After removal:
1. No inline `--card-priority-border` → CSS fallback `var(--pds-theme-light-contrast-medium)` applies as base
2. Signal selectors still override `border-left-color` for dr-pending/blocked/claimed/deps-unmet
3. "Ready" state gets medium-grey border (fallback) — theme task #1545 may refine to white/black

**Risk: none.** The signal selectors already control all non-ready states. The ready fallback is acceptable for this task's scope.

### 3.3 Test Breakage from AC-3

| Test File | Test(s) | Impact | Resolution |
|-----------|---------|--------|------------|
| `KanbanBoard.test.tsx` L317 | "blocked card shows block badge" | FAIL — `block-badge` span removed | Update: assert `data-signal="blocked"` instead |
| `KanbanBoard.test.tsx` L325 | "block badge exposes block_reason text" | FAIL — `block-badge` span removed | Update: assert `block_reason` via `title`/`aria-label` on card or remove |
| `KanbanBoard.test.tsx` L351 | "claimed card shows running indicator" | FAIL — `running-indicator` span removed | Update: assert `data-signal="claimed"` instead |
| `KanbanBoard.test.tsx` L343, L359 | "no block badge" / "no running indicator" | PASS — element correctly absent | No update needed |
| `ResponsiveLayout_1391.test.tsx` L206 | "renders critical priority borderLeft using PDS CSS var" | FAIL — inline style no longer sets `--card-priority-border` | Update: assert signal-based CSS or remove priority-specific assertion |

**Total: 4 tests will break** (3 in KanbanBoard, 1 in ResponsiveLayout). Builder must update these.

### 3.4 Card.tsx Redundant `resolveSignal()` Function

`Card.tsx` L24-40 contains a local `resolveSignal()` that duplicates `computeSignal()` from `src/utils/computeSignal.ts`. Both have identical logic. Replacing the local function with an import of `computeSignal` is the cleanest approach:
- Eliminates DRY violation
- Removes the `as Task & { dep_status?: ... }` type cast (unnecessary after AC-1 adds `dep_status` to `Task`)

However: this wiring is also covered by Card CSS task #1546's scope. Builder for #1544 should **either** do the replacement (minimal, within scope) **or** document it as deferred to #1546.

## 4. Recommendation

Proceed with all three ACs. Confidence: **0.92**.

- AC-1: 1-line type extension. No risk.
- AC-2: Already complete. Verify with existing test suite only.
- AC-3: Remove ~20 lines. 4 test updates needed. Low risk — signal-based rendering already works.

Challenge: skipped — trivial task with single obvious approach per AC, no competing designs.

## 5. Follow-up Tasks

None needed. The decomposition #1534→#1544 is correct. Test breakage from AC-3 is builder-scope work (updating sibling test files), not a separate task.

### Tier Classification

All findings are **T1 (autonomous)** — refactoring and code removal within existing architecture. No new capabilities, no architecture changes, no security implications.
