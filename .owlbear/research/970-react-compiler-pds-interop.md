# React Compiler + PDS Web Component Interop Analysis

> **Owning task:** #970 — Enable React Compiler with PDS interop validation spike
> **Date:** 2026-04-18 (validated 2026-04-18) **Status:** Complete — superseded by #971

## 1. Context and Question

Task #969 recommended deferring React Compiler adoption until ≥5 memoizable components exist. The key unknown was compiler behavior with PDS Web Components — imperative refs, `setAttribute`, and custom DOM events in Shell.tsx. This research validates those interop risks so implementation can proceed with eyes open when the trigger is met.

**Current cockpit component inventory (5 components + 1 hook, 0 manual memos):**

| Component | File | Memoization candidate? | PDS interop? |
|-----------|------|----------------------|--------------|
| App | App.tsx | No (trivial wrapper) | PorscheDesignSystemProvider |
| Shell | Shell.tsx | Low (layout, few re-renders) | p-tabs, p-tabs-item, p-icon, imperative refs, custom events |
| KanbanBoard | KanbanBoard.tsx | Medium (state consumer) | None |
| Column | KanbanBoard.tsx | Yes (pure props) | None |
| Card | KanbanBoard.tsx | Yes (pure props) | None |
| useBoard | KanbanBoard.tsx | Yes (hook) | None |

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| S1 | React Compiler introduction — stability, scope | https://react.dev/learn/react-compiler/introduction | 0.95 |
| S2 | React Compiler installation — Vite config | https://react.dev/learn/react-compiler/installation | 0.95 |
| S3 | React Compiler debugging — breaking patterns, "use no memo" | https://react.dev/learn/react-compiler/debugging | 0.90 |
| S4 | React Compiler directives — "use memo"/"use no memo" | https://react.dev/reference/react-compiler/directives | 0.85 |
| S5 | React Compiler incremental adoption — annotation mode, overrides | https://react.dev/learn/react-compiler/incremental-adoption | 0.80 |
| S6 | React Compiler configuration — compilationMode, panicThreshold | https://react.dev/reference/react-compiler/configuration | 0.80 |
| S7 | Rules of React — purity, side effects, immutability | https://react.dev/reference/rules | 0.85 |
| S8 | Vitest coverage drop issue — reactwg/react-compiler#78 | https://github.com/reactwg/react-compiler/discussions/78 | 0.80 |
| S9 | Shell.tsx — imperative PDS patterns (codebase) | serve/cockpit/web/src/Shell.tsx | 0.95 |
| S10 | Research #969 — prior compiler evaluation | .owlbear/research/969-react-compiler-evaluation.md | 0.90 |

## 3. Analysis

### 3.1 Shell.tsx Pattern Risk Assessment

| Pattern | Code | Compiler behavior | Risk |
|---------|------|-------------------|------|
| Callback ref + setAttribute | `ref={(el) => el?.setAttribute('label', 'Detail')}` | Compiler memoizes the callback → React won't clean up/re-call on re-render. Actually *improves* this pattern. | LOW |
| useEffect + addEventListener | `tabs.addEventListener('tabChange', onTabChange)` with `[]` deps + cleanup | Compiler preserves effect semantics. `[]` deps means effect runs once. No memoization concern. (S1, S3) | NONE |
| PDS custom elements in JSX | `<p-tabs>`, `<p-tabs-item>`, `<p-icon>` | Compile to `createElement('p-tabs', ...)`. Compiler treats as host elements — no special handling needed. (S7) | NONE |
| PDS Provider wrapper | `<PorscheDesignSystemProvider>` | Library component — compiler won't transform it (only transforms project source). (S1) | NONE |

**Shell.tsx verdict:** All patterns follow Rules of React (S7). Side effects are isolated in `useEffect` or ref callbacks, not in render body. The compiler should handle Shell.tsx without `"use no memo"` opt-outs.

### 3.2 Known Gotchas

| Issue | Severity | Mitigation |
|-------|----------|-----------|
| Vitest coverage drop (S8) | Medium | Compiler-generated branches inflate branch count. No source-map fix available. May need to lower coverage thresholds or exclude compiler-generated code from coverage. |
| SWC migration blocked | Low | Adopting Babel plugin cements Babel until SWC support ships. Current stack already uses Babel via `@vitejs/plugin-react`. No regression. (S10) |
| panicThreshold default | Low | Default is `'none'` — compiler skips problematic code instead of failing build. Safe for incremental adoption. (S6) |

### 3.3 Implementation Checklist (for future spike)

1. `npm install -D babel-plugin-react-compiler` (1 dep)
2. vite.config.ts: `plugins: [react({ babel: { plugins: ['babel-plugin-react-compiler'] } }), pdsPartialsPlugin()]` (S2)
3. Run Vitest — expect all tests pass (coverage numbers may change)
4. Run Playwright E2E — verify Shell tab switching works
5. Check React DevTools for "Memo ✨" badge on components (S2)
6. If Shell.tsx breaks: add `"use no memo"` directive and file issue (S3, S4)

## 4. Recommendation

**Keep task deferred. Trigger condition not yet met.**

The cockpit has 5 components but **0 manual memos and 0 reported performance issues**. Task #963 (4 planned memos for KanbanBoard) hasn't landed. Until manual memos exist or perf profiling shows re-render overhead, the compiler solves a problem that doesn't exist.

**PDS interop risk is LOW (confidence: 0.85).** Shell.tsx patterns follow Rules of React. The callback ref + setAttribute pattern is the only non-trivial pattern, and compiler memoization actually improves it. The `"use no memo"` escape hatch is available if empirical validation surfaces issues.

**When trigger IS met:** implementation is 3 LOC + 1 dep. Recommend `compilationMode: 'infer'` (default) over `'annotation'` — the cockpit is small enough for full compilation. Use `panicThreshold: 'none'` (default) to skip any problematic code.

Challenge: FALLBACK — subagent unavailable.

## 5. Follow-up Tasks

1. ~~Re-evaluate trigger when #963 (manual memos) lands~~ → Done (see §6)
2. Validate Vitest coverage impact when spike eventually runs — may need coverage threshold adjustment
3. **#971 trigger refinement:** Replace unbounded "component count grows" with concrete threshold (e.g., ≥8 components or ≥5 memoized components)

## 6. Validation Pass (2026-04-18)

### Changed state

| Fact | Original (§4) | Current |
|------|---------------|---------|
| Manual memos | 0 | 5 (2× React.memo, 2× useMemo, 1× useCallback) |
| #963 status | Not landed | Review (commit `b41c912d`) |
| Memoized components | 0/5 | 3/5 (Card, Column, KanbanBoard) |
| Memoization candidates | 4/5 (§1 table) | 4/5 — unchanged |

### Trigger re-assessment

The trigger "≥5 components with memoization needs" is **ambiguous** (challenger C1). Under strict reading (memo-wrapped components), 3/5 — unmet. Under broad reading (components that benefit from memoization per §1 table), 4/5 — still unmet but approaching. The remaining non-candidate (App.tsx) is a trivial provider wrapper unlikely to ever need memoization.

**#971 OR arm:** #963 was created from research #959 which identified re-render cascade as a performance risk. This means memos were added to address observed performance concerns — #971's OR trigger ("performance profiling shows re-render overhead") is **partially met** (challenger B3).

### Revised recommendation

**Keep deferred.** PDS interop findings validated — risk remains LOW. The 5 manual memos are manageable and already working. However, #971's trigger conditions need refinement: the AND arm's "component count grows" is unbounded (challenger C2). Recommend adding concrete threshold to #971.

**Confidence: 0.80** (revised from 0.85 — trigger ambiguity and OR arm nuance reduce certainty).

**#970 disposition:** Superseded by #971. Advance to backlog for archival. #971 is the canonical tracker for React Compiler adoption.

### Challenge results

- Challenger: **reconsider** (confidence in original: 0.60)
- Accepted: C1 (trigger ambiguity), C2 (unbounded threshold), B3 (OR trigger unevaluated)
- Rejected: C3 (#971 has no block_reason — challenger used stale data), A2 (#970 vs #971 AC scope — tighter AC is not better when #971 includes coverage impact which is a known gotcha per §3.2)
- Partially accepted: A1 (60% memo rate is significant, but still below trigger threshold under any reading)
- Researcher response: revised confidence 0.85→0.80, added trigger refinement follow-up, updated disposition rationale
