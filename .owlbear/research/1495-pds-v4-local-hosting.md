# PDS v4 Local Hosting and CDN Patch Scoping

> **Owning task:** #1495 — Cockpit: Research PDS v4 local hosting and scope CDN patch
> **Date:** 2026-05-12 **Status:** Complete

## 1. Context and Question

The Cockpit frontend patches `Element.prototype.appendChild` globally to redirect PDS CDN script loads to localhost. This monkeypatch is active for the entire app lifetime — a prototype pollution concern. The question: can PDS v4 natively serve from a custom URL, and if not, what's the least-invasive way to handle local hosting?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| S1 | PDS v4 CDN docs | designsystem.porsche.com/v4/must-know/performance/cdn/ | 0.95 |
| S2 | PDS v4 migration guide | designsystem.porsche.com/v4/news/migration-guide/porsche-design-system/ | 0.80 |
| S3 | PDS GitHub `load()` source | github.com/.../with-prefix.ts | 0.95 |
| S4 | PDS shipped npm `index.mjs` | node_modules/@porsche-design-system/components-js/esm/index.mjs | 1.00 |
| S5 | PDS GitHub issue #2701 | github.com/.../issues/2701 — "Make Components-JS Prod Build configurable" | 0.90 |
| S6 | PDS React provider source | node_modules/@porsche-design-system/components-react/esm/provider.mjs | 0.95 |
| S7 | PDS core chunk (shipped) | public/porsche-design-system/components/porsche-design-system.v4.0.0.*.js | 1.00 |

## 3. Analysis

### Finding 1: No native self-hosting config in PDS v4

`load()` accepts only `cdn: 'auto' | 'cn'` [S1, S3, S4]. Internally it hardcodes `document.porscheDesignSystem.cdn.url` to `https://cdn.ui.porsche.com` or `.cn` [S4]. PDS issue #2701 (open since Aug 2023, "to be refined") confirms custom CDN URLs are not yet supported [S5].

### Finding 2: Current monkeypatch has a latent timing bug

The React `PorscheDesignSystemProvider` calls `load()` in a `useEffect` after mount [S6]. Every `load()` call unconditionally resets `document.porscheDesignSystem.cdn.url` to the CDN [S4]. After the provider's second `load()`, `cdn.url` points back to CDN. Non-JS asset components (icons, flags, crest, model-signatures) read `cdn.url` at runtime [S7] — so these assets could fail under strict CSP or if local-only serving is expected.

### Finding 3: Core chunk caches webpack public path once

The core chunk sets `__webpack_public_path__` from `document.porscheDesignSystem.cdn.url` at module evaluation time [S7]. Once cached, JS component chunk loading is unaffected by subsequent `cdn.url` changes. Non-JS assets are not cached this way.

### Finding 4: PDS loader has idempotency guard

The `isInjected` flag prevents re-injection of the core chunk `<script>` on second `load()` calls [S4]. Only the first call actually appends a script element.

### Trade-Off Matrix

| Criterion | A: Property trap | B: Scoped patch + trap | C: Keep current |
|-----------|-----------------|----------------------|-----------------|
| Lines of code | ~15 | ~35 | ~20 |
| Prototype pollution | None | During init only | Global, permanent |
| Handles double `load()` | Yes | Yes | No (latent bug) |
| Non-JS asset URLs | Always correct | Always correct | Intermittent |
| PDS internal dependency | `cdn` structure | `cdn` + `appendChild` | `cdn` regex + struct |
| Breakage risk on PDS update | Low-Medium | Medium | Low-Medium |
| KISS alignment | High | Low | Medium |

### Option Details

**Option A — Property trap (recommended).** Before calling `load()`, pre-create `document.porscheDesignSystem` and use `Object.defineProperty` to trap the `cdn` property. The setter accepts writes but always overrides `url` to `window.location.origin`. This way:
- `load()` reads the trapped `cdn.url` → builds core chunk URL pointing to localhost
- The second `load()` from the provider hits the same trap → no CDN reset
- All runtime asset URLs read the correct localhost value
- No `Element.prototype.appendChild` override needed

**Option B — Scoped appendChild + property trap.** Install appendChild monkeypatch, call `load()`, install property trap, restore `appendChild`. Two mechanisms for one goal — violates KISS.

**Option C — Keep current.** Global prototype pollution stays. Latent bug: second `load()` from provider resets `cdn.url` for non-JS assets. Works today because CSP isn't enforced in dev mode and assets happen to load before the reset.

## 4. Recommendation

**Option A: Property trap** — confidence: 0.80

Replace the entire `installPdsRuntimeScriptRewrite()` function and post-bootstrap `cdn` fixup with a single `Object.defineProperty` trap installed before `load()`. ~15 lines, zero prototype pollution, handles all edge cases.

Challenge: block — confidence in original (scoped appendChild): 0.23. Challenger correctly identified that the original "scope the appendChild patch" approach fails on: (1) double `load()` from provider, (2) core chunk caching vs runtime asset reads, (3) readiness boundary ambiguity. The property trap approach addresses all three.

Risk: Depends on PDS internal `document.porscheDesignSystem.cdn` structure. PDS itself uses this in `componentsReady()` and documents it in TypeScript types [S3], so it's a semi-stable internal contract.

## 5. Follow-Up Tasks

1. **Implementation task:** Replace appendChild monkeypatch with `Object.defineProperty` trap on `document.porscheDesignSystem.cdn` — at `research` status
2. **Cleanup task:** Remove dead `pdsPartialsPlugin()` from vite.config.ts — `getInitialStyles()` was removed in PDS v4 [S2] and the plugin's try/catch makes it a silent no-op — at `research` status
