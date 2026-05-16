# Research: Formatting Utilities Implementation

> **Owning task:** #1604 — P1-05: Formatting utilities
> **Date:** 2026-05-16 **Status:** Complete

## 1. Context and Question

Task #1604 is the implementation task for `utils/format.ts` null-safe formatters, depending on #1598 (tests). The question: what work remains after #1598's builder already created `format.ts` with all 4 exports and 37/37 tests passing? Specifically, does AC3 (C7: config-driven enum vocabularies) hold?

## 2. Sources Studied

| Source | Relevance | What was taken |
|--------|-----------|----------------|
| `format.ts` (current impl) | 0.95 | 4 exported formatters, `PRIORITY_LABELS` hardcoded map, `SIGNAL_LABELS` map, `toTitleCaseWords` fallback |
| `topology.py` L42-49 | 0.95 | Actual backend priorities: `someday`, `nice-to-have`, `important`, `needed`, `critical` |
| `format_1598.test.ts` | 0.90 | 37 tests — happy paths use `toBeTruthy()`, null/undefined use exact `toBe('—')` assertions |
| Brief data stance (`stances/data.md`) | 0.90 | C7: "Accept any string value, not switch on a fixed set." Lookup tables allowed for visual treatments (color/icon). |
| Board API route (`routes/read.py`) | 0.85 | Returns `priorities: string[]` from `board_config()` — raw keys, no display labels |
| Component scan (Card, Column, DetailTab, FilterPanel, TaskFieldsEditor) | 0.80 | Inline formatters still exist; production code does NOT import `format.ts` |
| #1598 task body | 0.85 | Full pipeline (archived): builder created `format.ts`, 37 tests pass, 100% coverage |

## 3. Analysis

### 3.1 AC Status Assessment

| AC | Status | Evidence |
|----|--------|----------|
| AC1: format.ts exports null-safe formatters | DONE | `format.ts` exports 4 functions, 37 tests pass (commit 79b420c6 via #1598 builder) |
| AC2: No formatter in mutation call path | DONE | Guardrail test scans 13 mutation-graph files; no production code imports `format.ts` |
| AC3: Enum values from board API, not hardcoded | VIOLATED | `PRIORITY_LABELS` is hardcoded, stale, and divergent from backend |

### 3.2 PRIORITY_LABELS Vocabulary Drift

| `PRIORITY_LABELS` key | In backend topology? | `toTitleCaseWords` output | Map output |
|------------------------|---------------------|--------------------------|------------|
| `low` | NO — stale | `Low` | `Low` |
| `normal` | NO — stale | `Normal` | `Normal` |
| `needed` | YES | `Needed` | `Needed` |
| `important` | YES | `Important` | `Important` |
| `critical` | YES | `Critical` | `Critical` |
| `someday` | YES — MISSING from map | `Someday` | (falls to `toTitleCaseWords`) |
| `nice-to-have` | YES — MISSING from map | `Nice To Have` | (falls to `toTitleCaseWords`) |

The map contains 2 phantom values and misses 2 real ones. For overlapping entries, output is identical to `toTitleCaseWords`. The map is **redundant AND stale**.

### 3.3 SIGNAL_LABELS — Not a C7 Concern

Signals come from `computeSignal` (domain logic joining task fields + DR data), not from the board API. The data stance scopes C7 to "statuses and priorities." `SIGNAL_LABELS` provides semantic descriptions (`"deps-unmet"` → `"Dependencies blocked"`) that can't be derived from title-casing. Retaining `SIGNAL_LABELS` is correct.

### 3.4 Test Regression Risk

Tests use `toBeTruthy()` for happy-path formatPriority calls (not exact label assertions). Null/undefined tests assert exact fallback `"—"`. Removing `PRIORITY_LABELS` changes no observable test output.

### 3.5 Production Impact

`format.ts` is currently imported only by `format_1598.test.ts`. No production component uses the formatters yet — component migration is Batch 2 scope (#1609–#1618). Inline formatters still exist in Card.tsx (`formatUpdatedAge`), Column.tsx (`toDisplayStatus`), DecisionViewport.tsx (`formatAge`), DRStatusIndicator.tsx (`formatAge`).

## 4. Recommendation

**Remove `PRIORITY_LABELS` from `format.ts`; let `formatPriority` use `toTitleCaseWords` for all values.** The map is stale (vocabulary drift from backend), redundant (identical output for overlapping entries), and violates C7 (hardcoded enum vocabulary).

Retain `SIGNAL_LABELS` — signals are not board API enums, and their semantic labels aren't derivable from title-casing.

Confidence: 0.80

Challenge: proceed — challenger identified vocabulary drift (stale map with phantom `low`/`normal`, missing `someday`/`nice-to-have`), which STRENGTHENED the removal recommendation. Confidence in original revised from 0.47 (challenger) → 0.80 (post-re-evaluation: drift evidence reinforces removal, not weakens it).

## 5. Follow-up Tasks

None needed. Inline formatter consolidation in components is already scoped to Batch 2 tasks (#1609–#1618). The builder's scope for #1604 is: remove `PRIORITY_LABELS`, verify tests pass.
