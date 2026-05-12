# PDS Asset Sync: Local Hosting of CDN Assets

> **Owning task:** #1510 — Cockpit: Sync PDS local assets in public/ with npm package version
> **Date:** 2026-05-12 **Status:** Complete

## 1. Context and Question

The PDS npm package (v4.1.0) and `public/porsche-design-system/` are out of sync:
components/ has v4.0.0 core chunk (wrong version, causes 404s), icons/ has 1 of
290 SVGs (missing icons fall back to CDN, causing CSP violations). What files
must be in `public/`, how do we keep them in sync with the npm package version,
and what's the right automation approach?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| S1 | PDS npm `index.mjs` (v4.1.0) | node_modules/@porsche-design-system/components-js/esm/index.mjs | 1.00 |
| S2 | PDS CDN core chunk (v4.1.0) | cdn.ui.porsche.com/.../porsche-design-system.v4.1.0.59dc31ee9c99f5a43eb5.js | 1.00 |
| S3 | PDS icon component chunk | cdn.ui.porsche.com/.../porsche-design-system.icon.a77dc30fd842f982a230.js | 1.00 |
| S4 | PDS vue-offline sample repo | github.com/porsche-design-system/sample-integration-vue-offline | 0.90 |
| S5 | PDS GitHub issue #2701 | github.com/.../issues/2701 — custom CDN URLs not yet supported | 0.85 |
| S6 | PDS TypeScript types | components-js/esm/index.d.ts — `document.porscheDesignSystem.cdn` contract | 0.80 |

## 3. Analysis

### Finding 1: CDN Assets Are Not Shipped in the npm Package

The `@porsche-design-system/components-js` npm package contains only the loader
(`index.mjs`), partials, styles, and type definitions. All runtime assets — the
core chunk, 58 component chunks, and 290 icon SVGs — are hosted exclusively on
`cdn.ui.porsche.com` [S1, S2]. No `postinstall` or bin script copies them.

### Finding 2: Asset Inventory for v4.1.0

| Category | Count | URL pattern | Source of truth |
|----------|-------|-------------|-----------------|
| Core chunk | 1 | `.../components/porsche-design-system.v4.1.0.{hash}.js` | `index.mjs` [S1] |
| Component chunks | 58 | `.../components/porsche-design-system.{name}.{hash}.js` | Webpack map in core chunk [S2] |
| Icon SVGs | 290 | `.../icons/{name}.{hash}.svg` | Icon name→filename map in icon chunk [S3] |
| **Total** | **349** | | |

Current `public/`: 59 component files (v4.0.0 hashes — all wrong), 1 icon SVG.

### Finding 3: Chunk Mapping Is Deterministically Extractable

The core chunk contains a webpack chunk resolver: `i.u=e=>"porsche-design-system."
+e+"."+{accordion:"391c1d7d...", ...}[e]+".js"` [S2]. The icon chunk contains a
full icon name→filename object: `{360:"360.0600731.svg", ...}` [S3]. Both can be
parsed programmatically from the downloaded core and icon chunks.

### Finding 4: PDS v4 Still Has No Native Offline Support

PDS v3 offline sample [S4] ships a patched npm package with `getCdnBaseUrl()` →
`'./assets'`. The README states v4 will make this obsolete, but v4.1.0 still
hardcodes CDN URLs [S1]. Issue #2701 remains open [S5].

### Trade-Off Matrix

| Criterion | A: Sync script + git | B: Vite plugin | C: postinstall | D: Manual |
|-----------|---------------------|----------------|----------------|-----------|
| Offline after setup | Yes | No | No | Yes |
| Auto-sync on bump | No (manual run) | Yes | Yes | No |
| Internet required | Once per bump | Every dev/build | Every install | Once |
| Complexity (LOC) | ~80 | ~120 | ~80 | 0 |
| Error-prone | Low | Low | Medium (CDN down) | High |
| Git size impact | ~1 MB | 0 (not committed) | 0 | ~1 MB |
| KISS alignment | High | Medium | Medium | Low |
| Version drift risk | Low (clear error) | None | None | High |

## 4. Recommendation

**Option A: Node.js sync script + committed assets** — confidence: 0.82

Create `scripts/sync-pds-assets.mjs` that: (1) reads the PDS version and core
chunk URL from `node_modules/@porsche-design-system/components-js/esm/index.mjs`,
(2) downloads the core chunk from CDN, (3) extracts the component chunk mapping,
(4) downloads all 58 component chunks, (5) downloads the icon chunk, (6) extracts
the icon filename mapping, (7) downloads all 290 icon SVGs, (8) writes everything
to `public/porsche-design-system/`. Run via `npm run sync:pds`. Commit results.

This aligns with OwlBear's offline-first, laptop-resident architecture. The ~1 MB
git footprint is acceptable — existing v4.0.0 assets are already 783 KB.

Challenge: FALLBACK — challenger subagent unavailable (service disruption).

Risk: Script depends on PDS CDN availability and internal webpack chunk map format.
Both are stable (CDN is production infrastructure; chunk map format hasn't changed
across v4.0.0→v4.1.0). Script failure is non-destructive (old files stay).

## 5. Follow-Up Tasks

1. **Implement PDS asset sync script** — create `scripts/sync-pds-assets.mjs`,
   add `npm run sync:pds` command, run it to populate v4.1.0 assets, commit
2. **Add build-time version check** — optional: warn during `npm run build` if
   core chunk version in `public/` doesn't match npm package version
