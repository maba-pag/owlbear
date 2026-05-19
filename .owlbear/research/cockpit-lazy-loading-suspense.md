# Cockpit Lazy Loading — React.lazy() with Suspense Boundary

> **Owning task:** #1644 — P1-04: Lazy loading — React.lazy() with Suspense boundary for tab components
> **Date:** 2026-05-19 **Status:** Complete

## 1. Context and Question

Task #1644 requires wrapping route-config tab components in `React.lazy()` for code-splitting and adding a `<Suspense>` fallback around `<Routes>` in Shell.tsx. KanbanBoard remains eagerly loaded (default route).

**Key questions:** Which pattern fits React 19 + React Router 7 declarative routes + Vite 8? Any conflicts with React Compiler? What type/test changes are needed?

## 2. Sources Studied

| # | Source | Relevance | What was taken |
|---|--------|-----------|----------------|
| 1 | [React docs — Code Splitting](https://legacy.reactjs.org/docs/code-splitting.html) | 0.9 | `React.lazy()` + `<Suspense>` canonical pattern |
| 2 | [Remix blog — Faster Lazy Loading in RR v7.5+](https://remix.run/blog/faster-lazy-loading) | 0.8 | Confirmed granular `route.lazy` is Data Mode only; declarative `<Routes>` uses `React.lazy()` |
| 3 | [Vite chunking strategy](https://runebook.dev/en/articles/vite/guide/build/chunking-strategy) | 0.7 | Dynamic `import()` auto-creates separate chunks; no Vite config needed |
| 4 | Local verification — `typeof React.lazy(...)` | 1.0 | Returns `'object'`, not `'function'`; existing test will break |
| 5 | Local verification — TypeScript assignability | 1.0 | `LazyExoticComponent<ComponentType<P>>` assignable to `ComponentType<P>` |

## 3. Analysis

### Pattern Comparison

| Approach | Applicability | Complexity | Notes |
|----------|--------------|------------|-------|
| `React.lazy()` + `<Suspense>` | ✅ declarative `<Routes>` | Low | Standard pattern, no config |
| React Router `route.lazy` (object API) | ❌ requires Data Mode (`createBrowserRouter`) | Medium | Not applicable to our setup |
| Manual dynamic import + state | ❌ reinvents the wheel | High | YAGNI |

### Implementation Shape

| File | Change |
|------|--------|
| `routes.ts` | Replace static `import DecisionsPage` with `React.lazy(() => import('./pages/DecisionsPage'))` |
| `Shell.tsx` | Wrap `<Routes>` in `<Suspense fallback={<div data-testid="route-loading" />}>` |
| `RouteConfigEntry` type | No change needed — TS allows the assignment |
| Existing test | Fix `typeof entry.component === 'function'` — lazy entries are objects |

### Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| Existing test breakage (`typeof === 'function'`) | Medium | Update test to check renderability instead of typeof |
| React Compiler conflict | None | Verified — compiler ignores lazy wrappers |
| Suspense flash on fast connections | Low | Minimal fallback (empty div); chunk is tiny |
| Vite chunk naming | Low | Vite auto-names chunks from import path |

## 4. Recommendation

**Use `React.lazy()` + `<Suspense>` in the route config.** Confidence: **0.92**

- Keep `KanbanBoard` eagerly imported (default route, always rendered first)
- Wrap `DecisionsPage` (and future tab components) via `React.lazy()`
- Single `<Suspense>` boundary around `<Routes>` in Shell.tsx
- Fallback: minimal `<div data-testid="route-loading" />` (visible only during chunk download)
- No Vite config changes needed — dynamic `import()` triggers automatic code splitting

Challenge: skipped — trivial standard pattern, no architectural trade-offs.

## 5. Follow-up Tasks

No follow-up tasks needed — implementation is straightforward and covered by existing task #1644 AC lines. The builder should:
1. Update `routes.ts` to lazy-load non-default routes
2. Add `<Suspense>` in Shell.tsx
3. Fix the breaking test (`typeof` check → rendered/JSX check)
4. Verify AC2 via `npm run build` output showing separate chunk
