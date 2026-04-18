# Benchmark Tests: Kanban Board 700-Task Mount, Scroll, and Re-Render

> **Owning task:** #964 — Benchmark tests: kanban board 700-task mount, scroll, and re-render
> **Date:** 2026-04-18 **Status:** Complete

## 1. Context and Question

Task #964 was created as a follow-up from #959 research to track benchmark test implementation. Question: are the existing tests sufficient for all ACs, or is additional test code needed?

## 2. Sources Studied

| # | Source | Relevance |
|---|--------|-----------|
| S1 | `serve/cockpit/web/src/__tests__/KanbanBoard_959.test.tsx` — jsdom structural tests (10 tests) | 0.95 |
| S2 | `serve/cockpit/web/e2e/bench_959.spec.ts` — Playwright timing/scroll/re-render (5 tests) | 0.95 |
| S3 | `serve/cockpit/web/src/__tests__/KanbanBoard_963.test.tsx` — memoization validation (10 tests) | 0.85 |
| S4 | `.owlbear/research/959-frontend-perf-virtualization.md` — parent research defining approach | 0.90 |
| S5 | `serve/cockpit/web/src/KanbanBoard.tsx` — component (memo/useMemo/useCallback present) | 0.90 |

All sources are codebase-internal. No external sources needed — parent #959 research already validated the approach.

## 3. Analysis

### 3.1 AC Coverage Mapping

| AC | Test file | Test name(s) | Status |
|----|-----------|-------------|--------|
| jsdom: 700 tasks, DOM <5000 | `KanbanBoard_959.test.tsx` | `total DOM node count within board stays below 5000` (×2 distributions) | PASS |
| Playwright: mount <500ms | `bench_959.spec.ts` | `mount time <500ms — uniform`, `mount time <500ms — skewed` | PASS |
| Playwright: scroll <5% frame drops | `bench_959.spec.ts` | `scroll 400-card backlog column: scrollTop changes and <5% long tasks` | PASS |
| Playwright: re-render <100ms | `bench_959.spec.ts` | `re-render after task move <100ms with 700 cards present` | PASS |
| Uniform + skewed distributions | Both files | Both distributions tested in every applicable test | PASS |
| SEED=42 deterministic fixture | Both files | Identical LCG generator (seed=42, same constants) | PASS |

**All 6 ACs are fully covered by existing, passing tests.** 15 tests total: 10 jsdom + 5 Playwright.

### 3.2 Dependency Satisfied

The body notes "Memoization task (sibling) should land first for realistic measurements." KanbanBoard.tsx line 1 imports `memo`, `useMemo`, `useCallback`. The #963 memoization tests (10/10 passing) confirm the dependency is satisfied.

### 3.3 Minor Observations

| Observation | Severity | Action |
|-------------|----------|--------|
| LCG fixture generator duplicated in `_959.test.tsx` and `bench_959.spec.ts` | Low | Cross-framework (Vitest/Playwright) — extraction to shared util is possible but adds coupling between test toolchains. Not worth a task. |
| Test files use `_959` suffix, not `_964` | None | Tests were written during #959's pipeline cycle. Renaming would break git history and is cosmetic. |
| Playwright `webServer` does full `npm run build` per test run | Low | Acceptable for CI. Could be optimized with `reuseExistingServer` flag (already set for non-CI). |

## 4. Recommendation

**No additional test code needed.** All ACs are satisfied by existing, passing tests. Task #964 should advance through the pipeline as a pass-through — the implementation was completed during #959's test-writer and builder cycles.

**Confidence: 0.95**

Challenge: skip — validation pass with no novel recommendation. All evidence is deterministic (test pass/fail).

## 5. Follow-up Tasks

No follow-up tasks needed. All ACs verified as passing. The DRY concern (§3.3) is below the threshold for a dedicated task.
