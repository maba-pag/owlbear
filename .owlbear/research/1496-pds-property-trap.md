# PDS Property Trap: Implementation Validation

> **Owning task:** #1496 — Cockpit: Replace PDS appendChild monkeypatch with property trap on document.porscheDesignSystem.cdn
> **Date:** 2026-05-12 **Status:** Complete

## 1. Context and Question

Task #1495 researched PDS v4 local hosting and recommended Option A: an `Object.defineProperty` trap on `document.porscheDesignSystem.cdn`. This task validates the specific implementation approach, confirms technical feasibility, and identifies pre-existing issues discovered during analysis.

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| S1 | PDS npm `index.mjs` (shipped, minified) | node_modules/@porsche-design-system/components-js/esm/index.mjs | 1.00 |
| S2 | PDS React provider | node_modules/@porsche-design-system/components-react/esm/provider.mjs | 0.95 |
| S3 | PDS GitHub issue #2701 | github.com/.../issues/2701 — still "to be refined" (Aug 2023) | 0.90 |
| S4 | MDN Object.defineProperty | developer.mozilla.org/docs/Web/JavaScript/Reference/Global_Objects/Object/defineProperty | 0.80 |
| S5 | MDN Proxy/Reflect.set | developer.mozilla.org/docs/Web/JavaScript/Reference/Global_Objects/Reflect/set | 0.80 |
| S6 | Current monkeypatch | serve/cockpit/web/src/main.tsx lines 10-25 | 1.00 |
| S7 | E2E spec | serve/cockpit/web/e2e/pds-runtime-csp.spec.ts | 0.95 |
| S8 | Stored test failure | serve/cockpit/web/test-results/pds-runtime-csp-TestFromAC-*-chromium/error-context.md | 0.90 |

## 3. Analysis

### Finding 1: PDS `load()` assignment pattern confirmed

Decompiled from S1. `load()` does exactly:
```js
document[s] || (document[s] = {})            // create namespace if missing
document[s].cdn = { url: cdnUrl, prefixes: [] } // direct property assignment
// immediately reads document[s].cdn.url to build script URL
```

An `Object.defineProperty` setter on `cdn` intercepts the assignment; the getter returns `url: window.location.origin` [S4]. The script URL is then built from localhost.

### Finding 2: `componentsReady()` Proxy is compatible

PDS `componentsReady()` wraps the namespace in a Proxy with only a `set` trap [S1]:
```js
const handler = { set(t, n, s) { return "4.1.0" === n && s.isReady().then(e), Reflect.set(...arguments) } }
document.porscheDesignSystem = new Proxy(document.porscheDesignSystem || {}, handler)
```

No `get` trap → property reads hit the target directly → our getter survives. The `set` trap uses `Reflect.set(...)` → triggers our setter for `cdn` writes [S5]. Handler only checks for version key `"4.1.0"`, not `"cdn"`.

### Finding 3: Post-bootstrap fixup must be removed

Current main.tsx replaces `document.porscheDesignSystem` with a fresh plain object between `load()` calls (lines 38-41). This would destroy a trap installed on the original namespace. The fixup IS the code being removed — the trap replaces it, so the namespace object survives for the provider's second `load()`.

### Finding 4: Current monkeypatch is incomplete for non-JS assets

Stored test failure [S8] shows CDN CSP violations for `close.eec3c5d.svg` icon assets. The `appendChild` monkeypatch only intercepts `HTMLScriptElement` nodes — icons, flags, and other non-JS assets read `cdn.url` at runtime and bypass the patch entirely. The property trap fixes this: all asset URL reads go through `cdn.url`, which our getter controls.

### Finding 5: Pre-existing version mismatch (orthogonal)

npm package: PDS 4.1.0 [S1]. Local `public/porsche-design-system/components/`: core chunk v4.0.0. The `load()` function builds a URL containing `v4.1.0` but the local file is `v4.0.0`. This causes 404s for the core chunk. Additionally, `public/porsche-design-system/icons/` has only 1 file (`list.411dd00.svg`); `close.eec3c5d.svg` is missing. Both issues affect the current monkeypatch AND the property trap equally — they are deployment/asset-copy issues, not approach-design issues.

### Trade-Off: Trap vs Current

| Criterion | Property trap | Current monkeypatch |
|-----------|--------------|---------------------|
| Prototype pollution | None | Global, permanent |
| Handles double `load()` | Yes (setter trap) | No (latent timing bug) |
| Non-JS asset URLs | All redirected | Scripts only |
| Lines of code | ~15 | ~25 + fixup |
| PDS internal dependency | `cdn` property structure | `cdn` + `appendChild` + regex |
| Version mismatch impact | Same | Same |

## 4. Recommendation

**Proceed with property trap** — confidence: 0.82

Implementation: ~15 LOC in main.tsx. Pre-create `document.porscheDesignSystem` with trapped `cdn` getter/setter before `load()`. Remove `installPdsRuntimeScriptRewrite()` and post-bootstrap fixup. Keep `waitForRequiredPdsElements()` and `REQUIRED_PDS_ELEMENTS` unchanged.

Challenge: block (confidence in original: 0.30). Challenger raised 6 concerns. Researcher rebuttal:
- **Trap lifetime**: Accepted and addressed — post-bootstrap fixup is removed as part of this task, not preserved. Trap survives.
- **Version mismatch**: Accepted as real finding, classified as orthogonal pre-existing issue. Created follow-up #1498.
- **Contradictory test evidence**: Accepted — stored failures show icon CDN violations, which SUPPORT the trap approach (it fixes non-JS assets the monkeypatch misses).
- **AC proof gap**: Partially accepted — existing E2E tests cover behavioral outcomes; AC-1 and AC-2 need test-writer attention but don't block the approach.
- **componentsReady evidence relevance**: Rebutted — the Proxy wrapping does execute (from core chunk auto-initialization), and compatibility was verified via source decompilation.

## 5. Follow-Up Tasks

1. **#1496 itself** → advance to backlog (this is the implementation task)
2. **New: Sync PDS local assets with npm package version** — v4.0.0 assets in `public/` don't match v4.1.0 npm package; icons are incomplete
