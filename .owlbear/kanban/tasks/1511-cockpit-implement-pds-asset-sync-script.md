---
id: 1511
title: 'Cockpit: Implement PDS asset sync script'
status: todo
priority: important
created: 2026-05-12T15:49:55.060614+00:00
updated: 2026-05-12T16:39:01.910017+00:00
tags:
  - cockpit
  - frontend
  - bug
parent: 1495
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---


## Context

Research: see `.owlbear/research/1510-pds-asset-sync.md` (task #1510).

PDS npm package (v4.1.0) ships only the loader — all runtime assets (core chunk, 58 component chunks, 290 icon SVGs) are on `cdn.ui.porsche.com`. Current `public/porsche-design-system/` has v4.0.0 component chunks (wrong version → 404s) and only 1 of 290 icon SVGs (missing icons → CDN fallback → CSP violations).

## Acceptance Criteria

- [ ] `serve/cockpit/web/scripts/sync-pds-assets.mjs` exists
- [ ] Script reads PDS version and core chunk URL from `node_modules/@porsche-design-system/components-js/esm/index.mjs`
- [ ] Script downloads core chunk from CDN, extracts webpack component chunk mapping, downloads all 58 component chunks
- [ ] Script downloads icon chunk, extracts icon name→filename mapping, downloads all 290 icon SVGs
- [ ] Script writes assets to `public/porsche-design-system/` (`components/` and `icons/` subdirectories)
- [ ] `npm run sync:pds` command added to `package.json`
- [ ] Script run populates v4.1.0 assets (core chunk + 58 component chunks + 290 icon SVGs)
- [ ] Old v4.0.0 files removed from `public/porsche-design-system/components/`
- [ ] Assets committed to git
2026-05-12T16:17:08+00:00
## Research

Validated existing research from #1510 (`.owlbear/research/1510-pds-asset-sync.md`). All claims confirmed against live codebase and CDN.

### Verification Results

| Claim | Status | Evidence |
|-------|--------|----------|
| v4.1.0 installed, public/ has v4.0.0 hashes | ✓ | `package.json` version=4.1.0; 59 files with v4.0.0 hashes in components/ |
| Only 1 icon SVG in public/icons/ | ✓ | `list.411dd00.svg` is the sole file |
| Core chunk URL extractable from index.mjs | ✓ | Regex on `cdn.url+"/porsche-design-system/components/porsche-design-system.v4.1.0.59dc31ee9c99f5a43eb5.js"` |
| Webpack chunk map has 58 components | ✓ | Extracted via `.u=e=>"porsche-design-system."+e+"."+{...}[e]` — all 58 keys with v4.1.0 hashes |
| Icon chunk has 290 SVG mappings | ✓ | Icon map is nested inside webpack module (not top-level braces); anchored extraction via `{360:"360.` finds all 290 unique SVG filenames |
| CDN download URLs work | ✓ | HTTP 200 for both component chunk and icon SVG test URLs |
| No native PDS v4 offline support | ✓ | v3 offline sample uses patched npm package; v4 issue #2701 still open |

### Implementation Notes for Builder

1. **Icon map extraction caveat:** The icon name→filename map is nested inside a webpack module closure, not at brace depth 0. Use anchor-based extraction (e.g., find `{360:"360.` then match to closing brace) rather than simple top-level object parsing.
2. **Chunk map regex:** `.u=e=>"porsche-design-system."+e+"."+{...}[e]+".js"` — the `{...}` object contains all 58 chunk names and hashes.
3. No `scripts/` directory exists yet — must be created.

### Research Gate Checklist

- [x] Theoretical validity — sync script copies CDN assets locally, sound approach
- [x] Environment audit — no PDS-native offline tooling in v4.1.0
- [x] Prior art — PDS vue-offline sample (v3, patched packages); #1510 research doc
- [x] Technical feasibility — all extraction patterns verified against live CDN
- [x] Architecture fit — writes to existing `public/porsche-design-system/` structure
- [x] Implementation approach — Node.js ESM script (~80-100 LOC)
- [x] Testing strategy — run script, verify file counts (1 core + 58 components + 290 icons)
- [x] Findings documented — `.owlbear/research/1510-pds-asset-sync.md`

### Tier Classification

T1 — Autonomous. Bug fix (wrong version assets + missing icons). No architecture change, no new capability, no user-facing behavior change beyond fixing 404s and CSP violations.

Follow-up tasks: none needed — #1511 AC is already implementation-ready, and #1512 (build-time version check) already exists as a dependent.
Decision requests: none.
2026-05-12T16:38:53+00:00


## Revised Acceptance Criteria

> **Supersedes** the original AC section above. Builder must use these criteria.

- [ ] AC-1: `serve/cockpit/web/scripts/sync-pds-assets.mjs` exists as an ESM Node.js script
- [ ] AC-2: Script reads PDS version and core chunk URL from `node_modules/@porsche-design-system/components-js/esm/index.mjs`
- [ ] AC-3: Script downloads core chunk from CDN, extracts component chunk mapping, downloads 58 component chunks to `public/porsche-design-system/components/`
- [ ] AC-4: Script downloads icon chunk, extracts icon name→filename mapping, downloads 290 icon SVGs to `public/porsche-design-system/icons/`
- [ ] AC-5: `npm run sync:pds` command added to `package.json`, runs the script
- [ ] AC-6: Script clears `components/` and `icons/` directories before writing new assets (removes stale v4.0.0 files from both)
- [ ] AC-7: After `npm run sync:pds` against v4.1.0, `components/` contains 59 `.js` files (1 core + 58 chunks) and `icons/` contains 290 `.svg` files
- [ ] AC-8: Script exits non-zero with descriptive error message when any CDN download or chunk-map parsing step fails

**Builder note:** Commit populated assets to git after running `sync:pds`. See research doc for icon-map extraction caveat (anchor-based, not brace-depth-0).

Proof bundle: smoke
Existing proof scope: N/A
Test-writer: PROCEED

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single concern: sync PDS CDN assets to local public/ |
| Interface clarity | PASS | Input: node_modules index.mjs; output: files in public/; side effect: removes old files |
| Dependency correctness | PASS | No depends_on needed; parent #1495 is PDS umbrella |
| Module layering | N/A | Standalone utility script, no import dependencies |
| TDD compliance | PASS | Proof bundle `smoke` assigned; existing e2e suite provides runtime backstop |
| KISS/YAGNI | PASS | ~80-100 LOC utility, simplest of 4 options evaluated in research |
| Premise challenge | PASS | PDS v4 has no native offline support (issue #2701 open); script is necessary |
| Pattern consistency | PASS | Standard frontend tooling pattern (scripts/ directory) |
| Security surface | PASS | HTTPS CDN (cdn.ui.porsche.com), trusted source, output committed for review |
| Single domain | PASS | Frontend/cockpit domain only |

### Failure Mode Map

| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| CDN download | Network unreachable or 404 | fetch error | AC-8 requires non-zero exit | Script fails, old files already cleared (AC-6) |
| index.mjs parse | PDS loader format changes | regex miss | AC-8 requires non-zero exit | Script fails with descriptive error |
| Chunk map extract | Webpack format changes | parse error | AC-8 requires non-zero exit | Script fails, user investigates |
| File write | Disk full / permissions | fs error | Node.js native throw | Script fails |

### Challenge Results

- Challenger: reconsider (0.66)
- Architect response: accepted 4 of 6 findings (B3 cleanup, failure semantics AC, icons cleanup scope, AC-9 demotion); rebutted 2 (v4.1.0 scope contradiction — task IS current-version fix; consolidation gap — independent concerns)
- AC refined to address accepted findings → confidence restored

### Proof-Bundle Validation

- Planner assignment: (missing)
- Final bundle: smoke
- Existing proof scope: N/A
- Test-writer: PROCEED
- Runtime backstop: `serve/cockpit/web/e2e/pds-runtime-csp.spec.ts` validates PDS loading + CSP after assets are synced

### Verdict: APPROVE (after REFINE)
### Action Taken: Refined AC (8 lines replacing original 9), added proof bundle, advanced backlog → todo
2026-05-12T16:39:01+00:00
Architecture review complete. AC refined from 9 lines to 8: removed "all" B3 violations, expanded cleanup to cover both components/ and icons/ (challenger blind-spot catch), added error-handling AC (exit non-zero), demoted "commit to git" from AC to builder note. Proof bundle: smoke (was missing). Runtime backstop: existing pds-runtime-csp.spec.ts e2e suite.