---
id: 1511
title: 'Cockpit: Implement PDS asset sync script'
status: archived
priority: important
created: 2026-05-12T15:49:55.060614+00:00
updated: 2026-05-12T20:50:47.661916+00:00
tags:
  - cockpit
  - frontend
  - bug
parent: 1495
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason: completed
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
2026-05-12T17:17:22+00:00
## Test-Writer Notes
- Test file: tests/test_sync_pds_assets_1511.py
- Classes: TestFromAC_SyncPdsAssetsScript
- Tests per category: happy 0, edge 0, error 1 (AC-8), boundary 0; smoke 7 (AC-1–7)
- Total: 8 tests, all FAIL
- ruff: clean

### AC Coverage

| AC | Test | Failure Reason |
|----|------|----------------|
| AC-1 | test_ac1_script_file_exists | AssertionError: script file does not exist |
| AC-2 | test_ac2_script_is_valid_esm | AssertionError: node --check fails (file missing) |
| AC-3 | test_ac3_components_dir_has_v41_core_chunk | AssertionError: v4.1.0 core chunk not present |
| AC-4 | test_ac4_icons_dir_has_290_svg_files | AssertionError: found 1, expected 290 |
| AC-5 | test_ac5_package_json_has_sync_pds_command | AssertionError: sync:pds not in scripts |
| AC-6 | test_ac6_stale_v40_component_files_removed | AssertionError: stale v4.0.0 accordion file still present |
| AC-7 | test_ac7_correct_file_counts_after_sync | AssertionError: v4.1.0 core chunk missing (two-part: chunk present + count=59 and count=290) |
| AC-8 | test_ac8_exits_nonzero_with_descriptive_error_on_parse_failure | AssertionError: Node module-not-found error lacks domain terms (cdn/chunk-map/parse/index.mjs) |

### Builder Notes
- AC-3/AC-6/AC-7 tests verify filesystem state AFTER the builder runs `npm run sync:pds` and commits the assets. The builder must run the script and commit the resulting files.
- AC-8 creates a broken `index.mjs` in tmp_path and runs the script from there (cwd=tmp_path). If the script resolves node_modules relative to `import.meta.url` rather than cwd, AC-8 may need refinement in a retry cycle.
- Commit: 45eaf3f2
2026-05-12T17:52:03+00:00
## Builder Notes
- Proof bundle: smoke
- Implementation: confirmed existing implementation in HEAD for `serve/cockpit/web/scripts/sync-pds-assets.mjs` and `serve/cockpit/web/package.json` (`sync:pds`), plus synced assets under `serve/cockpit/web/public/porsche-design-system/components/` and `serve/cockpit/web/public/porsche-design-system/icons/`
- RED verification (quality-runner): `tests/test_sync_pds_assets_1511.py` -> 0 passed / 8 failed before implementation check
- Sync execution evidence: `npm run sync:pds` completed successfully and reported `synced 59 component files and 290 icons`; core file `porsche-design-system.v4.1.0.59dc31ee9c99f5a43eb5.js` present
- GREEN verification (quality-runner): `tests/test_sync_pds_assets_1511.py` -> 8 passed / 0 failed
- Lint verification (quality-runner): clean (`eslint=0`, `ruff=0`)
- Coverage: N/A for this smoke-bundle task (no coverage gate in report)
- Module-level durable tests: no module-level `test_sync_pds_assets.py` exists; skipped per workflow
- Commit evidence: implementation commit already present in current branch history: `b91db254 feat: implement pds asset sync script (#1511, builder)`
2026-05-12T18:34:10+00:00
## Review Evidence
- Verdict: FAIL
- Routing signal: FAIL #1511 -> todo | Task-scoped tests do not prove the sync script's happy-path behavior or the full AC-8 failure surface.

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC-2, AC-3, AC-4, AC-6, AC-7 | Happy-path proof is state-only. The tests never execute `npm run sync:pds`, so a no-op or hardcoded script plus committed assets would still pass. | `tests/test_sync_pds_assets_1511.py:35-84` only checks `node --check`, file existence, and file counts; the actual sync behavior lives in `serve/cockpit/web/scripts/sync-pds-assets.mjs:97-126`. | todo |
| 2 | AC-8 | Error-path proof covers only malformed `index.mjs`; it does not exercise CDN download failure, component chunk-map parse failure, or icon-map parse failure even though AC-8 requires descriptive non-zero exits for those failure classes. | `tests/test_sync_pds_assets_1511.py:88-119` runs one parse-failure scenario; distinct failure branches exist at `serve/cockpit/web/scripts/sync-pds-assets.mjs:30-33`, `serve/cockpit/web/scripts/sync-pds-assets.mjs:38-68`, `serve/cockpit/web/scripts/sync-pds-assets.mjs:70-85`, and `serve/cockpit/web/scripts/sync-pds-assets.mjs:121-140`. | todo |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Replace the state-only happy-path checks with proof that executes the sync script in an isolated fixture/workspace and verifies the outputs are produced by the script rather than by precommitted assets. | `tests/test_sync_pds_assets_1511.py` | Blocking finding #1 |
| 2 | test-writer | Add AC-8 coverage for at least one CDN download failure and one chunk-map parse failure beyond malformed `index.mjs` so the failure surface matches the contract. | `tests/test_sync_pds_assets_1511.py` | Blocking finding #2 |

## Observations
- The implementation itself appears aligned with the revised AC: it reads `index.mjs`, resets both output directories, downloads the core chunk, derives component hashes, locates the icon chunk, downloads icons, and exits non-zero on error (`serve/cockpit/web/scripts/sync-pds-assets.mjs:97-140`).
- The existing runtime backstop in `serve/cockpit/web/e2e/pds-runtime-csp.spec.ts` checks local PDS loading under CSP, but it does not prove the sync script semantics required by #1511.
2026-05-12T19:38:33+00:00
## Test-Writer Notes
- Retry: added 3 new tests addressing reviewer gaps; all pass against current impl → builder skip (Step 1b.1)
- Test file: tests/test_sync_pds_assets_1511.py
- Classes: TestFromAC_SyncPdsAssetsScript
- Tests per category: happy 0, edge 0, error 2 (new), boundary 0; smoke 7 (original) + api/slow 1 (new execution proof)
- Total: 11 tests (8 original preserved, 3 new)
- ruff: clean
- Commit: 26cf084c

### Retry changes

**Finding #1 (state-only happy-path):**
- Added `test_ac_script_execution_creates_outputs_in_isolated_workspace` (marked `api`/`slow`/`timeout(180)`): symlinks node_modules to a tmp dir, starts from empty output directories, runs the script, verifies it produces 59 .js + 290 .svg files. Pre-committed assets cannot mask a broken/no-op script.

**Finding #2 (thin AC-8 coverage):**
- Added `test_ac8_cdn_download_failure_returns_descriptive_error`: Node.js harness stubs `globalThis.fetch` to return HTTP 503 before importing the script; verifies non-zero exit + "cdn/download/http" in stderr.
- Added `test_ac8_chunk_map_parse_failure_returns_descriptive_error`: harness returns HTTP 200 with no `.u=e=>` chunk-map pattern; verifies non-zero exit + "chunk-map/component/parse" in stderr.

### AC Coverage

| AC | Test | Status |
|----|------|--------|
| AC-1 | test_ac1_script_file_exists | PASS |
| AC-2 | test_ac2_script_is_valid_esm | PASS |
| AC-3 | test_ac3_components_dir_has_v41_core_chunk | PASS |
| AC-4 | test_ac4_icons_dir_has_290_svg_files | PASS |
| AC-5 | test_ac5_package_json_has_sync_pds_command | PASS |
| AC-6 | test_ac6_stale_v40_component_files_removed | PASS |
| AC-7 | test_ac7_correct_file_counts_after_sync | PASS |
| AC-8 | test_ac8_exits_nonzero_with_descriptive_error_on_parse_failure | PASS |
| AC-8 | test_ac8_cdn_download_failure_returns_descriptive_error (new) | PASS |
| AC-8 | test_ac8_chunk_map_parse_failure_returns_descriptive_error (new) | PASS |
| AC-3/AC-7 execution proof | test_ac_script_execution_creates_outputs_in_isolated_workspace (new, api) | not run without -m api |

### Builder Notes
- No builder work needed — all new tests pass against current implementation.
- The api-marked execution test was not run by quality-runner (excluded via `-m "not api"`); it requires CDN access and ~120s.
2026-05-12T19:59:38+00:00
## Review Evidence
- Verdict: FAIL
- Routing signal: FAIL #1511 -> backlog | Proof remains structurally insufficient on cycle 2: AC-6 cleanup is not execution-proven, and the only happy-path execution test is outside the canonical evidence packet.

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC-6 | The retry still does not mechanically prove that the script clears both `components/` and `icons/` before writing new assets. The only AC-6 test is a state-only assertion against one committed stale component filename, and the new execution test starts from empty output directories, so a script that never removes stale files would still pass. | `tests/test_sync_pds_assets_1511.py:67`; `tests/test_sync_pds_assets_1511.py:127`; `tests/test_sync_pds_assets_1511.py:138`; `tests/test_sync_pds_assets_1511.py:139`; `serve/cockpit/web/scripts/sync-pds-assets.mjs:88`; `serve/cockpit/web/scripts/sync-pds-assets.mjs:89`; `serve/cockpit/web/scripts/sync-pds-assets.mjs:90`; `serve/cockpit/web/scripts/sync-pds-assets.mjs:91`; `serve/cockpit/web/scripts/sync-pds-assets.mjs:92` | backlog |
| 2 | AC-3, AC-4, AC-7 | The new behavior-level happy-path proof exists, but the task body explicitly states it was not run by quality-runner because it is marked `api`. That leaves the canonical evidence packet for download/sync behavior state-based again on the second review cycle. | Test-Writer Notes (2026-05-12T19:38:33+00:00): `The api-marked execution test was not run by quality-runner (excluded via -m "not api")`; `tests/test_sync_pds_assets_1511.py:127`; `tests/test_sync_pds_assets_1511.py:47`; `tests/test_sync_pds_assets_1511.py:54`; `tests/test_sync_pds_assets_1511.py:74` | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Redefine the proof strategy so #1511 has canonical happy-path execution evidence for the sync script, either by making the execution proof runnable in the standard smoke gate or by explicitly raising the bundle/runner scope to include it. | `tests/test_sync_pds_assets_1511.py` | Blocking finding #2 |
| 2 | architect | Refine the AC/test plan so AC-6 requires executable cleanup proof for stale files in both `components/` and `icons/`, not only post-commit filesystem state. | `tests/test_sync_pds_assets_1511.py`; `serve/cockpit/web/scripts/sync-pds-assets.mjs` | Blocking finding #1 |

## Observations
- The implementation itself appears aligned with the revised AC on direct inspection: it reads `index.mjs`, resets both output directories, downloads the core chunk, derives component hashes, downloads component chunks, locates/downloads the icon chunk, downloads icons, and exits non-zero on failure (`serve/cockpit/web/scripts/sync-pds-assets.mjs:30`; `serve/cockpit/web/scripts/sync-pds-assets.mjs:38`; `serve/cockpit/web/scripts/sync-pds-assets.mjs:48`; `serve/cockpit/web/scripts/sync-pds-assets.mjs:70`; `serve/cockpit/web/scripts/sync-pds-assets.mjs:88`; `serve/cockpit/web/scripts/sync-pds-assets.mjs:98`; `serve/cockpit/web/scripts/sync-pds-assets.mjs:102`; `serve/cockpit/web/scripts/sync-pds-assets.mjs:104`; `serve/cockpit/web/scripts/sync-pds-assets.mjs:111`; `serve/cockpit/web/scripts/sync-pds-assets.mjs:125`; `serve/cockpit/web/scripts/sync-pds-assets.mjs:134`; `serve/cockpit/web/scripts/sync-pds-assets.mjs:140`).
- The retry materially improved AC-8 proof: malformed-index, CDN failure, and component chunk-map parse failure are now exercised in `tests/test_sync_pds_assets_1511.py:90`; `tests/test_sync_pds_assets_1511.py:163`; `tests/test_sync_pds_assets_1511.py:206`.
- This is the second review cycle; remaining blocking proof issues route the task to backlog for architect-level repair per pipeline protocol.
2026-05-12T20:12:02+00:00
## Revised Acceptance Criteria (Cycle 3)

> **Supersedes** "Revised Acceptance Criteria" section above. Builder must use these criteria.

- [ ] AC-1: `serve/cockpit/web/scripts/sync-pds-assets.mjs` exists as an ESM Node.js script
- [ ] AC-2: Script reads PDS version and core chunk URL from `node_modules/@porsche-design-system/components-js/esm/index.mjs`
- [ ] AC-3: Script downloads core chunk from CDN, extracts component chunk mapping, downloads 58 component chunks to `public/porsche-design-system/components/`
- [ ] AC-4: Script downloads icon chunk, extracts icon name→filename mapping, downloads 290 icon SVGs to `public/porsche-design-system/icons/`
- [ ] AC-5: `npm run sync:pds` command added to `package.json`, runs the script
- [ ] AC-6: Script clears `components/` and `icons/` directories before writing new assets (removes stale v4.0.0 files from both)
- [ ] AC-7: After `npm run sync:pds` against v4.1.0, `components/` contains 59 `.js` files (1 core + 58 chunks) and `icons/` contains 290 `.svg` files
- [ ] AC-8: Script exits non-zero with descriptive error message when any CDN download or chunk-map parsing step fails
- [ ] AC-9: A smoke test (not marked `api` or `slow`) executes the sync script in an isolated `tmp_path` workspace with `globalThis.fetch` stubbed to return HTTP 200 responses for all four resource classes (core chunk with parseable `.u=e=>` component map containing ≥2 entries, ≥2 component chunk bodies, icon chunk with ≥2 icon filename mappings, ≥2 icon SVG bodies). Before execution, stale sentinel files (`stale.js` in `components/`, `stale.svg` in `icons/`) are seeded. After execution: (a) exit code is 0, (b) both sentinel files are absent, (c) `components/` contains ≥3 `.js` files (1 core + ≥2 from chunk map), (d) `icons/` contains ≥2 `.svg` files.

**Builder note:** No implementation change expected — AC-9 is test-only. Commit populated assets to git after running `sync:pds`. See research doc for icon-map extraction caveat (anchor-based, not brace-depth-0).

**Test-writer note (AC-9):** Use the same Node.js harness pattern as existing AC-8 tests (write `harness.mjs` that stubs `globalThis.fetch` before importing the script). The isolated workspace needs: (1) `node_modules/@porsche-design-system/components-js/esm/index.mjs` with a core-chunk URL pattern, (2) `public/porsche-design-system/components/` with stale sentinel, (3) `public/porsche-design-system/icons/` with stale sentinel. The fetch stub must return structurally parseable responses — not just `ok: true` — because the script parses chunk maps from the response bodies.

Proof bundle: smoke
Existing proof scope: N/A
Test-writer: PROCEED
2026-05-12T20:12:27+00:00
## Architecture Review (Cycle 3)

### Context
Task returned to backlog after 2 reviewer FAILs. Both cycles identified the same structural proof gap: happy-path tests are state-only (check committed files) and the sole execution test is excluded from the canonical evidence packet (marked `api`). Implementation confirmed correct by reviewer on both cycles.

### Evaluation
No re-evaluation of criteria 1–10 needed — prior architecture review (cycle 1) passed all criteria and implementation is unchanged. This cycle addresses proof-strategy repair only.

### Reviewer Findings Addressed

| Finding | Root Cause | Fix |
|---------|-----------|-----|
| AC-6 cleanup not execution-proven | State test checks committed absence of one file; execution test starts from empty dirs | AC-9: seed stale sentinels → run script → verify sentinels absent |
| Happy-path execution excluded from canonical packet | Execution test marked `api` (CDN access, ~120s) → quality-runner skips it | AC-9: mock-based execution test with no `api`/`slow` markers runs in smoke gate |

### AC Changes
- AC-1 through AC-8: unchanged (implementation complete and passing)
- AC-9 (NEW): Mock-based execution proof — stubs all 4 fetch resource classes, seeds stale files, verifies cleanup + output counts. Addresses both reviewer blockers.

### Challenge Results
- Challenger: block (0.36)
- Findings: 4 critical (fixture surface, under-scoped counts, response-matrix gaps, AC wording), 1 consolidation gap
- Architect response: accepted 4 critical findings → tightened AC-9 with isolated workspace spec, ≥2 mock entries for both components and icons, all 4 resource classes named, concrete count thresholds. Rebutted consolidation gap — siblings #1496/#1511/#1513 are independent concerns (monkeypatch/sync/version-check) sharing no code.

### Proof-Bundle Validation
- Final bundle: smoke (unchanged)
- Existing proof scope: N/A
- Test-writer: PROCEED

### Consolidation Check
Parent #1495 (archived). Siblings: #1496 (monkeypatch replacement), #1511 (asset sync), #1513 (version check). Independent domains, no shared interfaces → no consolidation test needed.

### Verdict: APPROVE (after REFINE)
### Action Taken: Added AC-9 (mock-based execution proof) to close reviewer's state-only proof gap. Advanced backlog → todo.
2026-05-12T20:25:22+00:00
## Test-Writer Notes
- Retry (cycle 3): added 1 new test for AC-9; all pass against current impl → builder skip (Step 1b.1)
- Test file: tests/test_sync_pds_assets_1511.py
- Classes: TestFromAC_SyncPdsAssetsScript
- Tests per category: smoke 7 (AC-1–7), error 3 (AC-8), mock-execution 1 (AC-9); api/slow 1 (excluded from gate)
- Total: 12 tests (11 existing preserved, 1 new)
- ruff: clean
- Commit: 9f2467fb

### Retry changes (cycle 3)

**Architect's AC-9 (mock-based execution proof):**
- Added `test_ac9_mock_execution_proves_cleanup_and_output_without_cdn` — NOT marked api/slow, runs in standard smoke gate.
- Harness stubs `globalThis.fetch` for all 4 resource classes: core chunk (parseable .u=e=> component map, icon + button entries), 2 component chunk bodies, icon chunk (2 icon filename mappings), 2 icon SVG bodies.
- Seeds stale sentinels (`stale.js` in components/, `stale.svg` in icons/) before execution.
- Verifies: exit 0, both sentinels absent, ≥3 .js files, ≥2 .svg files.
- Addresses both reviewer blockers: AC-6 cleanup is now execution-proven (sentinel seeding), and happy-path execution is in the canonical smoke gate.

### AC Coverage

| AC | Test | Status |
|----|------|--------|
| AC-1 | test_ac1_script_file_exists | PASS |
| AC-2 | test_ac2_script_is_valid_esm | PASS |
| AC-3 | test_ac3_components_dir_has_v41_core_chunk | PASS |
| AC-4 | test_ac4_icons_dir_has_290_svg_files | PASS |
| AC-5 | test_ac5_package_json_has_sync_pds_command | PASS |
| AC-6 | test_ac6_stale_v40_component_files_removed | PASS |
| AC-7 | test_ac7_correct_file_counts_after_sync | PASS |
| AC-8 | test_ac8_exits_nonzero_with_descriptive_error_on_parse_failure | PASS |
| AC-8 | test_ac8_cdn_download_failure_returns_descriptive_error | PASS |
| AC-8 | test_ac8_chunk_map_parse_failure_returns_descriptive_error | PASS |
| AC-9 | test_ac9_mock_execution_proves_cleanup_and_output_without_cdn (new) | PASS |
| AC-3/AC-7 live CDN | test_ac_script_execution_creates_outputs_in_isolated_workspace (api) | not run in gate |

### Builder Notes
- No builder work needed — all new tests pass against current implementation.
- Reviewer can now run the full smoke suite without -m api and get execution-level proof.
2026-05-12T20:41:07+00:00
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1511 to docs | AC mapped to code and evidence sufficient.
- No blocking findings.

| AC | Code Evidence | Proof Evidence | Status |
|---|---|---|---|
| AC-1, AC-2 | `serve/cockpit/web/scripts/sync-pds-assets.mjs:4-11,38-45,97-98` reads workspace `index.mjs` and extracts the version-bearing core path. | `tests/test_sync_pds_assets_1511.py:33-45,90-122,250-345` plus reviewer scoped rerun with 11 passed tests including AC-9. | PASS |
| AC-3, AC-4, AC-7 | `serve/cockpit/web/scripts/sync-pds-assets.mjs:104-131` downloads the core file, component chunks, icon chunk, and icon SVGs; `serve/cockpit/web/scripts/sync-pds-assets.mjs:121-126` enforces icon-map lookup. | Builder sync execution evidence at `.owlbear/kanban/tasks/1511-cockpit-implement-pds-asset-sync-script.md:175`; current repo state enumerates 59 files in `serve/cockpit/web/public/porsche-design-system/components/` and 290 files in `serve/cockpit/web/public/porsche-design-system/icons/`; `tests/test_sync_pds_assets_1511.py:47-57,74-86,250-345`. | PASS |
| AC-5 | `serve/cockpit/web/package.json:12` wires `sync:pds` to the script. | `tests/test_sync_pds_assets_1511.py:59-65`. | PASS |
| AC-6 | `serve/cockpit/web/scripts/sync-pds-assets.mjs:88-92,102` removes and recreates both output directories before writing. | `tests/test_sync_pds_assets_1511.py:250-345`, especially sentinel cleanup assertions at `:333-336`. | PASS |
| AC-8 | `serve/cockpit/web/scripts/sync-pds-assets.mjs:30-35,38-68,70-85,139-140` routes download and parse failures through descriptive errors and non-zero exit. | `tests/test_sync_pds_assets_1511.py:90-122,163-247` plus reviewer scoped rerun, all passing. | PASS |
- Independent verification: reviewer ran a scoped quality check. The standard non-api smoke gate executed 11 task-scoped tests and all passed, including `test_ac9_mock_execution_proves_cleanup_and_output_without_cdn`; the live CDN execution test remained correctly excluded by its api marker. Scoped ruff and eslint were clean.

## Observations
- AC-9 is materially stronger than the earlier state-only proof and now puts cleanup plus happy-path execution into the canonical smoke gate. The mock harness still returns HTTP 200 with empty bodies for unknown URLs at `tests/test_sync_pds_assets_1511.py:311-312`, so exact live-CDN output confidence still leans partly on the recorded builder sync run and the committed 59/290 asset set. That is non-blocking here because no implementation changes occurred after the builder's real sync run; later cycles were test-only repairs.
2026-05-12T20:42:59+00:00
## Docs Gate

### Checklist

| Item | Status | Evidence |
|------|--------|----------|
| README Verification | FIXED | Added `npm run sync:pds` block to "Launch / Usage" in `serve/cockpit/README.md`; new command absent before, now documents CDN source, asset counts (1 core + 58 components + 290 icons), and re-run trigger. Layer 1: grep confirmed `sync:pds` present at line 26. Layer 2: editorial read — coherent, accurate, no contradictions. |
| External Attribution | N/A | No external sources requiring attribution — CDN is a known PDS dependency. |
| Research Doc | N/A | Research doc `.owlbear/research/1510-pds-asset-sync.md` already linked in task body. |
| Deletion Detection | N/A | Old v4.0.0 binary assets removed; no doc references by filename. No orphaned references. |

### Files Updated
- `serve/cockpit/README.md` — added `sync:pds` to "Launch / Usage" section

### Scratch Cleanup
No `.owlbear/scratch/1511-*` files existed.
2026-05-12T20:50:47+00:00
## Audit

### Regression Detection
- quality-runner mode full: 4408 passed, 201 failed (all pre-existing), lint clean
- task-scoped rerun: 11 passed / 0 failed (tests/test_sync_pds_assets_1511.py, -m "not api")
- all 201 failures are in unrelated test files (test_ideation_diagram, test_cockpit_view cleanup debt, test_server, test_engine_accessor_migration, etc.) -- none attributable to #1511
- regression verdict: PASS

### Intent Verification
- scope alignment: PASS (all changes in cockpit frontend domain: serve/cockpit/web/scripts/, serve/cockpit/web/package.json, serve/cockpit/web/public/porsche-design-system/, tests/test_sync_pds_assets_1511.py)
- purpose match: PASS (fixes PDS v4.0.0-to-v4.1.0 asset mismatch and missing icon SVGs causing 404s/CSP violations)
- extraneous scope: none
- boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 4/5
ACs were specific and testable from cycle 1 (8 concrete lines with file counts, error behavior, paths). Proof strategy gap (state-only tests) required 2 reviewer rejections and 3 architect cycles to close via AC-9 addition. Architect responded well to challenger (accepted 4/6 findings cycle 1, 4/4 cycle 3). Minor gap: initial proof bundle omission.

### Commit Integrity
- upstream commit presence: PASS (builder: b91db254, test-writer: 45eaf3f2/26cf084c/9f2467fb -- all present)
- doc-writer README update: uncommitted (serve/cockpit/README.md modified but not committed) -- process concern noted, content verified correct
- asset counts verified: 59 .js files in components/, 290 .svg files in icons/
- kanban commit packaging: pending (this step)

### Deduction Breakdown
- Regression failures: no deduction (201 failures all pre-existing, 0 from #1511)
- Intent mismatch: no deduction
- Evidence integrity: no deduction (reviewer evidence detailed PASS, all source/test commits present)
- Lint violations: no deduction (clean)
- AC quality score 4/5: no deduction (threshold is 3 or less)
- Missing reviewer evidence: no deduction (3 review cycles with detailed AC mapping)

### Process Concern
Doc-writer did not commit README update (serve/cockpit/README.md). Change is correct and aligned but remains unstaged. Flagged for process awareness.

### Confidence: 1.00
### Action: archive