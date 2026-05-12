# PDS Asset Version Check: Build-Time Drift Guard

> **Owning task:** #1512 — Cockpit: Add PDS asset version check to build
> **Date:** 2026-05-12 **Status:** Complete

## 1. Context and Question

After PDS assets are synced locally via `npm run sync:pds` (#1511), version
drift can occur when someone bumps the PDS npm package without re-running the
sync script. The core chunk filename in `public/porsche-design-system/components/`
embeds the version (e.g., `porsche-design-system.v4.1.0.{hash}.js`). How should
the build detect and warn about this mismatch?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| S1 | Vite Plugin API docs | vite.dev/guide/api-plugin.html | 0.95 |
| S2 | Vite `buildStart` behavior | github.com/vitejs/vite/issues/19607 | 0.80 |
| S3 | Existing `vite.config.ts` | serve/cockpit/web/vite.config.ts | 1.00 |
| S4 | PDS research #1510 | .owlbear/research/1510-pds-asset-sync.md | 0.90 |
| S5 | npm scripts docs | docs.npmjs.com/cli/v11/using-npm/scripts/ | 0.75 |
| S6 | PDS core chunk filename | cdn.ui.porsche.com/...porsche-design-system.v4.1.0.{hash}.js | 1.00 |

## 3. Analysis

### Finding 1: `buildStart` Hook Covers Both Dev and Build

The Vite `buildStart` hook (inherited from Rollup) fires once on dev server
start and once at production build start [S1, S2]. This is exactly the two
entry points required by the AC (`npm run dev` and `npm run build`). No
additional script hooks or npm pre-commands needed.

### Finding 2: Inline Plugin Pattern Is Established

The codebase already uses inline Vite plugins — `cspPlugin()` in
`vite.config.ts` [S3]. Adding `pdsVersionCheckPlugin()` follows the same
pattern. No new files or dependencies required.

### Finding 3: Core Chunk Version Is Deterministically Extractable

The core chunk filename follows the pattern
`porsche-design-system.v{semver}.{hash}.js` [S4, S6]. A simple regex
`/^porsche-design-system\.v(\d+\.\d+\.\d+)\./` reliably extracts the version.
The npm package version comes from the standard `package.json` `version` field.

### Trade-Off Matrix

| Criterion | A: Vite plugin | B: Standalone script | C: npm pre-hook |
|-----------|---------------|---------------------|-----------------|
| Files touched | 1 (vite.config.ts) | 2 (new script + pkg) | 2 (new script + pkg) |
| Lines of code | ~25 | ~20 + 2 script edits | ~20 + 2 script edits |
| Auto for dev + build | Yes (buildStart) | Yes (pre-command) | Yes (pre-command) |
| Non-blocking | console.warn | exit 0 | exit 0 |
| CI / standalone use | Vite-only | Works anywhere | Works anywhere |
| Testable | Extract fn, or Vitest | Naturally testable | Naturally testable |
| KISS alignment | High | Medium | Medium |
| Consistent w/ codebase | cspPlugin pattern | New pattern | New pattern |
| Extra dependencies | None | None | None |
| Risk | Low | Low | Low |

### Implementation Sketch (Option A)

```
pdsVersionCheckPlugin():
  configResolved → capture config.root
  buildStart →
    1. Read node_modules/@porsche-design-system/components-js/package.json → version
    2. Scan public/porsche-design-system/components/ for core chunk filename
    3. Extract version from filename via regex
    4. If missing: warn "PDS assets missing — run npm run sync:pds"
    5. If mismatch: warn "PDS version drift: assets=X, npm=Y — run npm run sync:pds"
    6. try/catch entire block — silently skip on error (non-blocking)
```

## 4. Recommendation

**Option A: Vite plugin inline in vite.config.ts** — confidence: 0.85

Add `pdsVersionCheckPlugin()` to `vite.config.ts` using the `configResolved` +
`buildStart` hooks. ~25 lines, zero new files, follows the existing `cspPlugin()`
pattern, automatically covers both `dev` and `build` entry points.

Option B/C (standalone script) is viable but adds a new file and requires
modifying two npm scripts — more moving parts for the same result. The only
advantage (standalone CI use) is not needed since the Cockpit build always
uses Vite.

Challenge: reconsider — confidence in original: 0.58. Challenger raised six
moderate-severity concerns: precedent mismatch (cspPlugin is build-only),
buildStart dev-mode proof, version source ambiguity, regex fragility, silent
failure masking real drift, testability/parser-reuse with #1511.

Researcher response: accepted in part, revised.

- **Version source**: resolved — read `version` from installed
  `node_modules/@porsche-design-system/components-js/package.json` (not
  range from root package.json, not loader metadata).
- **Error handling**: revised — catch logs `console.warn('PDS version check
  skipped: {reason}')` instead of silent swallow. Non-blocking but visible.
- **buildStart in dev**: documented Vite behavior [S1]: "The following hooks
  are called once on server start: options, buildStart". Vite 8 source
  confirms client pluginContainer.buildStart is called. Sufficient for AC.
- **Regex stability**: only the core chunk has the version-embedded filename
  (`porsche-design-system.v{semver}.{hash}.js`); 58 component chunks use
  component names without version. Pattern stable across v4.0.0→v4.1.0 [S4].
- **cspPlugin analogy**: corrected — the shared pattern is "inline plugins
  in vite.config.ts", not the `apply` behavior. New plugin omits `apply`
  to run in both modes (unlike cspPlugin's build-only constraint).
- **Parser reuse with #1511**: minimal overlap. The sync script parses CDN
  chunk maps; the version check reads one package.json field and one filename.
  Different concerns, different data sources.

Revised confidence: 0.80.

Risk: Core chunk filename pattern must stay `porsche-design-system.v{semver}.
{hash}.js`. Stable across v4.0.0→v4.1.0 and mirrors CDN URL structure [S4, S6].
If pattern changes, check warns "PDS version check skipped" (visible, not silent).

## 5. Follow-Up Tasks

1. **Implement PDS version check Vite plugin** — add `pdsVersionCheckPlugin()`
   to `vite.config.ts` with `configResolved` + `buildStart` hooks; non-blocking
   `console.warn` on version mismatch or missing assets; version source is
   installed `node_modules/.../components-js/package.json`; error handling logs
   skip reason instead of silent catch
