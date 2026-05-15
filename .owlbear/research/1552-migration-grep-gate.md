# Migration Verification Grep Gate

> **Owning task:** #1552 — P4-02: migration verification grep gate
> **Date:** 2026-05-14 **Status:** Complete

## 1. Context and Question

Task #1543 and downstream (#1546–#1550) renamed all `--pds-theme-light-*` CSS custom properties to agnostic `--pds-*` names. The grep gate is a regression test that scans the entire `serve/cockpit/web/src/` tree and fails if any legacy token usage persists — preventing accidental re-introduction.

**Key question:** How should the gate handle test files that reference legacy tokens for the purpose of testing their absence (negative assertions, comments, regex patterns)?

## 2. Sources Studied

| Source | Relevance | What was taken |
|--------|-----------|---------------|
| `PDSHexScan_1395.test.ts` (local) | 0.95 | Proven broad-scan Vitest pattern: recursive file discovery, line-level filtering, zero-tolerance assertion with helpful violation reporting |
| `ShellSecondaryCSS_1542.test.tsx` (local) | 0.85 | Existing per-file legacy-token check for Shell.css using same regex pattern `/--pds-theme-light-[a-z0-9-]+/g` |
| Current `grep --pds-theme-light-` across src/ (local) | 1.0 | Identifies 2 real violations + ~20 legitimate test references |

## 3. Analysis

### Current Legacy Token References

| File | Line(s) | Category | Action |
|------|---------|----------|--------|
| `ErrorBoundary.tsx` | 30 | **Runtime usage** — `var(--pds-theme-light-contrast-medium)` in inline style | Fix: replace with `var(--pds-contrast-medium)` |
| `ResponsiveLayout_1391.test.tsx` | 296–309 | **Stale positive assertion** — `.toContain('--pds-theme-light-*')` | Fix: update to agnostic token names |
| `TokenArchitecture_1535.test.ts` | 101,116 | Negative assertion (`.toEqual([])`) | Legitimate — tests absence |
| `ShellSecondaryCSS_1542.test.tsx` | 89–94 | Negative assertion (`.toHaveLength(0)`) | Legitimate — tests absence |
| `CardCSS_1546.test.ts` | 14,83–98 | Comments + `.not.toMatch()` | Legitimate — tests absence |
| `PDSHexScan_1395.test.ts` | 133–156 | Synthetic test fixture data | Legitimate — hex scanner self-test |
| `CardSignalModel_1544.test.tsx` | 240 | Comment only | Legitimate |

### Implementation Approach Comparison

| Approach | Complexity | False Positives | False Negatives | KISS | Confidence |
|----------|-----------|-----------------|-----------------|------|-----------|
| **A: Strict literal scan** (any occurrence = fail) | Low | High (breaks 6 test files) | None | ✗ | 0.40 |
| **B: Smart filtering** (exclude comments + negative assertions) | Medium | None | Very low | ✓ | 0.82 |
| **C: Scope to production only** (exclude `__tests__/`) | Low | None | Moderate (misses stale positive assertions in tests) | ✓ | 0.60 |

### Recommended Approach: Option B — Smart Filtering

Following the PDSHexScan pattern:

1. Recursively collect `.css`, `.tsx`, `.ts` files under `src/` (including `__tests__/`)
2. For each file, find lines matching `--pds-theme-light-`
3. Skip acceptable lines: comment-only (`//`, `/* */`, ` * `), negation patterns (`.not.toMatch`, `.not.toContain`, `.toHaveLength(0)`, `.toEqual([])`), regex literals inside assertion patterns
4. Report remaining violations with file:line detail
5. Assert zero violations

**Filter heuristic (3 rules):**
- Line is comment-only → skip
- Line contains `.not.` followed by assertion keyword → skip
- Line is inside a describe/it string (test name) → skip

This matches how PDSHexScan filters `var(--pds-*)` before checking for hex literals.

## 4. Recommendation

**Confidence: 0.82** — Option B (smart filtering Vitest test)

Challenge: skipped (trivial implementation task — grep gate pattern already proven in codebase at PDSHexScan_1395.test.ts; no architectural decision required).

**Pre-requisites the gate will expose (already known):**
- `ErrorBoundary.tsx:30` needs `var(--pds-theme-light-contrast-medium)` → `var(--pds-contrast-medium)`
- `ResponsiveLayout_1391.test.tsx:296-309` needs stale assertions updated to agnostic tokens

These are migration gaps from #1543 scope (ErrorBoundary was missed). The grep gate builder should fix these as part of making the gate pass GREEN.

## 5. Follow-up Tasks

- Task moves to `backlog` for architecture review → test-writer → builder pipeline
- No additional research tasks needed — implementation is straightforward
