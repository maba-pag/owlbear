# React Compiler Integration Cost vs Manual Memoization

> **Owning task:** #969 — Evaluate React Compiler integration cost vs manual memoization maintenance
> **Date:** 2026-04-18 **Status:** Complete

## 1. Context and Question

Research #963 chose manual memoization for KanbanBoard (4 planned memos across 3 components). As the cockpit grows in phase-2, manual `React.memo`/`useMemo`/`useCallback` maintenance scales linearly. React Compiler (`babel-plugin-react-compiler`) auto-memoizes at build time, potentially replacing all manual memos with a single build plugin. Question: should the cockpit adopt React Compiler now, later, or never?

**Current state:** 0 manual memos across 5 component files (App, Shell, KanbanBoard with Card/Column, main). Task #963's 4 planned memos are not yet implemented.

## 2. Sources Studied

| # | Source | Relevance |
|---|--------|-----------|
| S1 | react.dev/learn/react-compiler/introduction — official docs, stability statement | 0.95 |
| S2 | react.dev/learn/react-compiler/installation — Vite integration guide | 0.95 |
| S3 | npmjs.com/package/babel-plugin-react-compiler — v1.0.0, 7.6M weekly downloads | 0.85 |
| S4 | npmjs.com/package/react-compiler-runtime — v1.0.0, 0 dependencies | 0.80 |
| S5 | `serve/cockpit/web/vite.config.ts` — current Vite config with @vitejs/plugin-react | 0.90 |
| S6 | `serve/cockpit/web/src/KanbanBoard.tsx` — 3 components, zero memoization | 0.95 |
| S7 | `serve/cockpit/web/src/Shell.tsx` — PDS Web Components, imperative refs, custom events | 0.90 |
| S8 | `.owlbear/research/963-memoize-kanbanboard.md` — prior research, § 3.4 deferred compiler | 0.85 |

## 3. Analysis

### 3.1 React Compiler Stability Status

| Attribute | Value |
|-----------|-------|
| Package version | 1.0.0 (stable) |
| React team statement | "now stable and tested extensively in production" (S1) |
| Supported React versions | 17, 18, 19 |
| License | MIT |
| Build tool support | Babel, Vite, Next.js, Metro, Rspack, Rsbuild |
| Escape hatch | `"use no memo"` per-component directive |
| SWC/oxc native support | In development (eliminates Babel dependency future) |

**Verdict:** No longer experimental. The #963 assessment ("still experimental as of React 19") is outdated.

### 3.2 Integration Cost — Vite Plugin

Config change in `vite.config.ts` (3 LOC):

```ts
plugins: [react({ babel: { plugins: ['babel-plugin-react-compiler'] } }), pdsPartialsPlugin()],
```

Plus `npm install -D babel-plugin-react-compiler` (1 devDep). No new build tool — `@vitejs/plugin-react` already uses Babel internally.

### 3.3 Maintenance Cost Comparison

| Criterion | Manual Memos | React Compiler |
|-----------|-------------|----------------|
| One-time setup | 0 LOC | 3 LOC config + 1 devDep |
| Per-component cost | memo wrapper + useMemo/useCallback + dep arrays | 0 |
| Dep array bugs | Possible (subtle, hard to detect) | Eliminated |
| Code reviewability | Explicit — intent visible in source | Implicit — trust compiler output |
| Bundle size | Zero (hooks built-in) | Zero (equivalent output) |
| Build time | None | Negligible for <20 components |

**Crossover point:** At 1–3 memoized components, manual memos are trivial to maintain. Beyond ~5 memoized components, the per-component overhead of manual memos (writing, reviewing dep arrays, testing) exceeds the one-time compiler setup cost.

### 3.4 Risks

| Risk | Severity | Mitigation |
|------|----------|-----------|
| PDS Web Component interop unknown | Medium | Shell.tsx uses imperative refs (`setAttribute`), custom DOM events (`tabChange`). Compiler may misanalyze these patterns. Requires validation spike. |
| SWC migration blocked | Low | Adopting Babel plugin cements Babel as required until SWC support ships. Current stack already uses Babel, so no regression — but forecloses faster build path. |
| Subtle rendering bugs | Low | `"use no memo"` escape hatch + rollback is trivial (remove 3 config lines). |
| Cognitive overhead | Low | Developers must understand compiler-optimized output for debugging. React DevTools shows "Memo ✨" badge to aid. |

### 3.5 YAGNI Analysis

The cockpit has **zero manual memos today**. Task #963 plans 4 but hasn't landed. Adopting the compiler now solves a problem that doesn't yet exist. However:

- The compiler doesn't introduce complexity — it *removes* future complexity.
- Integration cost (3 LOC + 1 dep) is the same whether adopted now or in 6 months.
- If adopted before #963 lands, #963 becomes unnecessary (saving 4 manual memos from ever being written).

**Counter:** YAGNI says don't add tooling for hypothetical futures. The compiler is free in cost but not free in dependency surface. A conservative path: implement #963's manual memos, adopt compiler when component count reaches ~5 memoized components.

## 4. Recommendation

**Defer adoption. Proceed with #963 manual memos. Adopt React Compiler when the cockpit reaches ≥5 memoizable components in phase-2.**

Rationale: (a) zero memos exist today — no maintenance burden to solve, (b) PDS Web Component interop is unvalidated — requires a spike before adoption, (c) #963's 4 manual memos are trivial to maintain for 1 component, (d) the compiler will still be 3 LOC when the crossover point arrives.

When adopting: run a validation spike first — enable the plugin, run Vitest + Playwright E2E, verify PDS component behavior (especially Shell.tsx tab switching and imperative ref patterns).

**Confidence: 0.78**

Challenge: `reconsider` — challenger confidence 0.50. Valid concerns accepted: C1 (YAGNI — zero memos today, defer), C2 (SWC lock-in acknowledged), C3 (PDS interop blind spot flagged as required spike). Rejected: C4 (download count was supporting evidence, not primary).

## 5. Follow-up Tasks

1. When phase-2 reaches ≥5 memoizable components: enable React Compiler with PDS interop validation spike
2. #963 proceeds as planned — 4 manual memos for KanbanBoard are the correct near-term approach
