# React Compiler + PDS Web Component Interop Analysis

> **Owning task:** #970 — Enable React Compiler with PDS interop validation spike
> **Date:** 2026-04-18 **Status:** Complete

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

1. Re-evaluate trigger when #963 (manual memos) lands or when component count grows in phase-2
2. Validate Vitest coverage impact when spike eventually runs — may need coverage threshold adjustment
