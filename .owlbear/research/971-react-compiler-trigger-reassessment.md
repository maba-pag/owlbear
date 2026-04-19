# React Compiler Trigger Reassessment

> **Owning task:** #971 — Run React Compiler validation spike when memoization trigger is met
> **Date:** 2026-04-19 **Status:** Complete

## 1. Context and Question

Task #971 gates React Compiler adoption on "≥5 components with active memoization." Previous assessment (2026-04-18) found 2–3 and deferred. This reassessment checks current state after #963 landed and cockpit grew.

**Key question:** Is the trigger met? Should we proceed with the compiler spike?

## 2. Sources Studied

| # | Source | URL/Path | Relevance |
|---|--------|----------|-----------|
| S1 | React Compiler installation docs | https://react.dev/learn/react-compiler/installation | 0.95 |
| S2 | Prior research #970 (PDS interop) | .owlbear/research/970-react-compiler-pds-interop.md | 0.95 |
| S3 | KanbanBoard.tsx — memos in source | serve/cockpit/web/src/KanbanBoard.tsx | 1.00 |
| S4 | usePolling.ts — useCallback | serve/cockpit/web/src/hooks/usePolling.ts | 0.90 |
| S5 | useConnectionHealth.ts — useCallback | serve/cockpit/web/src/hooks/useConnectionHealth.ts | 0.90 |
| S6 | vite.config.ts — current plugin setup | serve/cockpit/web/vite.config.ts | 0.85 |
| S7 | package.json — React 19, Vite 6 | serve/cockpit/web/package.json | 0.85 |

## 3. Analysis

### 3.1 Current Memoization Inventory

| Module | memo() | useMemo | useCallback | Type |
|--------|--------|---------|-------------|------|
| Card (KanbanBoard.tsx) | ✓ | — | — | Component |
| Column (KanbanBoard.tsx) | ✓ | ✓ (sorted) | ✓ (handleCardDragStart) | Component |
| KanbanBoard (KanbanBoard.tsx) | — | ✓ (tasksByStatus) | ✓×3 (context menu, drag start/end) | Component |
| usePolling (hooks/) | — | — | ✓ (poll) | Hook |
| useConnectionHealth (hooks/) | — | — | ✓×2 (markHealthy, updateHealth) | Hook |

**Total: 5 modules, 9 manual memoization callsites.**

### 3.2 Trigger Interpretation

| Reading | Threshold | Met? |
|---------|-----------|------|
| Strict: memo()-wrapped components only | ≥5 | 2/5 — NO |
| Medium: components using any memo API | ≥5 | 3/5 — NO |
| Broad: modules (components + hooks) using any memo API | ≥5 | 5/5 — YES |

### 3.3 Cost/Benefit Assessment

| Factor | Value |
|--------|-------|
| Implementation cost | 1 npm dep + 1 LOC in vite.config.ts (S1) |
| Risk | LOW — PDS interop validated (S2, confidence 0.85) |
| Benefit (current) | Remove 9 manual callsites, prevent future omissions |
| Benefit (future) | All new components auto-optimized |
| Maintenance saved | Marginal — cockpit is 9 components + 4 hooks |
| Downside | Locks Babel (already using it), possible Vitest coverage shift (S2 §3.2) |

### 3.4 Component Growth Trajectory

| When | Components | Hooks | Memoized modules |
|------|-----------|-------|------------------|
| 2026-04-18 (initial) | 5 | 1 | 0 |
| 2026-04-18 (#963 lands) | 5 | 1 | 3 |
| 2026-04-19 (now) | 9 | 4 | 5 |
| Future (TaskDetail, FilterBar, etc.) | 12+ | 5+ | 7+ (projected) |

## 4. Recommendation

**Proceed with the compiler spike.** Confidence: 0.75.

Rationale:
- Broad trigger interpretation (5 memoized modules) is met
- Cost is trivially low (1 dep, 1 LOC), easily reversible
- Risk validated as LOW by prior research #970
- Prevents memoization debt as cockpit grows
- Already on React 19 + `@vitejs/plugin-react` (Babel) — zero migration friction

The primary uncertainty is whether the benefit justifies the effort *now* versus waiting for organic growth. Given the spike is <30 min of work and fully reversible, the opportunity cost of waiting is higher than the opportunity cost of doing it.

Challenge: FALLBACK — subagent unavailable in this context.

## 5. Follow-up Tasks

1. **Execute compiler spike** — install `babel-plugin-react-compiler`, update vite.config.ts, verify tests pass (T1 — autonomous)
2. **Validate coverage impact** — run Vitest with compiler enabled, document branch count delta, adjust thresholds if needed (T1)
