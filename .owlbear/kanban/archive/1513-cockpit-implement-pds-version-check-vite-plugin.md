---
id: 1513
title: 'Cockpit: Implement PDS version check Vite plugin'
status: archived
priority: nice-to-have
created: 2026-05-12T17:32:51.825110+00:00
updated: 2026-05-12T22:25:16.743629+00:00
tags:
  - cockpit
  - frontend
  - cleanup
parent: 1495
depends_on:
  - 1511
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---


## Context

Research: see `.owlbear/research/1512-pds-version-check.md` (task #1512).

Add an inline `pdsVersionCheckPlugin()` Vite plugin to `serve/cockpit/web/vite.config.ts` that guards against version drift between the locally synced PDS assets and the installed npm package.

## Revised Acceptance Criteria

> **Supersedes** the original AC section. Builder must use these criteria.

- [ ] AC-1: `pdsVersionCheckPlugin()` added to `serve/cockpit/web/vite.config.ts` plugins array with plugin name `'pds-version-check'`
- [ ] AC-2: Plugin object has `configResolved` hook (stores resolved root) and `buildStart` hook (executes the check); no `apply` property set (fires in both dev and build modes)
- [ ] AC-3: `buildStart` reads `version` field from `{root}/node_modules/@porsche-design-system/components-js/package.json`
- [ ] AC-4: `buildStart` scans `{root}/public/porsche-design-system/components/` for filename matching `/^porsche-design-system\.v(\d+\.\d+\.\d+)\./` and extracts semver from first match
- [ ] AC-5: When extracted asset version ≠ npm version, `console.warn` outputs message containing both version strings and `npm run sync:pds`
- [ ] AC-6: When no core chunk filename matches the pattern, `console.warn` outputs message indicating missing assets and `npm run sync:pds`
- [ ] AC-7: When any step throws, `console.warn` outputs `PDS version check skipped: {error.message}` — no re-throw

Proof bundle: smoke
Test-writer: PROCEED

**Builder note:** Follow the existing `cspPlugin()` inline pattern in `vite.config.ts`. Unlike `cspPlugin`, this plugin does filesystem I/O in `buildStart` — the test-writer may need to establish a new test pattern for lifecycle-hook behavior (existing tests in `src/__tests__/vite_config.test.ts` only cover structural plugin inspection). See research doc for implementation sketch.
2026-05-12T18:50:23+00:00
## Architecture Review

### Verdict: APPROVE (after REFINE)

AC refined from 8 unnumbered lines to 7 numbered lines (AC-1 through AC-7). Key improvements: added B2 input→output pairs to structural lines, specified exact regex pattern, specified warning message content requirements (both version strings + `npm run sync:pds` remediation), split mismatch vs missing into distinct AC lines, added plugin name requirement for testability.

### AC Assessment

| AC | Assessment | Action |
|----|-----------|--------|
| AC-1 | B1 pass — names function, file, plugin name | Refined: added plugin name `'pds-version-check'` |
| AC-2 | B1/B2 pass — hooks named, no-apply constraint testable | Refined: explicit "no `apply` property" |
| AC-3 | B1/B2 pass — specific file path, specific field | Refined: added `{root}/` path prefix |
| AC-4 | B1/B2 pass — directory, regex, extraction | Refined: added exact regex |
| AC-5 | B2 pass — input: version mismatch, output: warn with both versions | Refined: split from original combined AC |
| AC-6 | B2 pass — input: no match, output: warn with missing message | Refined: split from original combined AC |
| AC-7 | B2 pass — input: thrown error, output: specific warn format | Kept from original |

### Architecture Notes

| Criterion | Assessment |
|-----------|-----------|
| Single responsibility | PASS — one concern: build-time version drift detection |
| Interface clarity | PASS — inputs (package.json, directory listing), outputs (console.warn), side effects (none) |
| Dependency correctness | PASS — depends_on [#1511] correctly models asset producer dependency |
| Module layering | N/A — inline Vite plugin, no module imports |
| KISS/YAGNI | PASS — ~25 lines, zero new files, follows existing inline plugin pattern |
| Premise challenge | PASS — useful build guard; PDS version drift already caused runtime 404s and CSP violations |
| Pattern consistency | PASS — inline Vite plugin like `cspPlugin()` in same file |
| Security surface | PASS — local filesystem reads only, no network, no user input |
| Single domain | PASS — frontend/cockpit only |

### Dependency Analysis

- #1511 (PDS asset sync script) — `todo` status. Currently cycling through test improvement after reviewer rejection. Architecture approval of #1513 is independent of #1511's completion; pipeline will sequence execution via `depends_on`.

### Proof-Bundle Validation

- Planner assignment: smoke
- Final bundle: smoke (confirmed — non-blocking warning plugin, ~25 LOC)
- Test-writer: PROCEED
- Note: test-writer will need to establish lifecycle-hook test pattern (no existing precedent in `vite_config.test.ts`)

### Challenge Results

- Challenger: reconsider (0.64)
- Findings: (1) ac-quality — accepted, AC refined for B2 compliance; (2) precedent-and-proof — accepted as observation, testing pattern gap noted in builder guidance; (3) stale-inherited-evidence — noted, stale body text cleaned up in body rewrite; (4) consolidation-gap — rebutted: siblings operate at different layers (runtime vs build-time), existing `pds-runtime-csp.spec.ts` e2e consolidates runtime chain, #1513 tests inherently validate #1511→#1513 contract
- Architect override: proceed with approval after AC refinement addresses finding (1)
- Post-refinement confidence: 0.82
2026-05-12T21:11:45+00:00
## Test-Writer Notes
- Test file: serve/cockpit/web/src/__tests__/vite_config_pds_1513.test.ts
- Classes: TestFromAC_PdsVersionCheck
- Tests per category: smoke 7 (one per AC line; proof bundle = smoke)
- Total: 7 tests, all FAIL — AssertionError: expected undefined to be defined
- ESLint: clean
- AC coverage: AC-1 through AC-7 each mapped 1:1
- Pattern established: lifecycle-hook simulation (configResolved → buildStart) with vi.mock('node:fs')
2026-05-12T21:22:58+00:00
## Builder Notes
- Files changed: serve/cockpit/web/vite.config.ts
- Implemented inline `pdsVersionCheckPlugin()` and registered it in Vite plugins array.
- Hook behavior implemented per AC: `configResolved` captures root; `buildStart` performs version check in both dev/build (no `apply` gate).
- Build-start logic: reads npm version from `node_modules/@porsche-design-system/components-js/package.json`, scans `public/porsche-design-system/components` for first filename matching `/^porsche-design-system\.v(\d+\.\d+\.\d+)\./`, compares versions, warns on mismatch or missing core asset, catches all errors and warns with `PDS version check skipped: {error.message}`.

- RED verification (quality-runner):
  - `serve/cockpit/web/src/__tests__/vite_config_pds_1513.test.ts`: 0 passed / 7 failed (all TestFromAC cases failing pre-implementation)
  - lint: clean

- Module baseline before implementation (quality-runner):
  - `serve/cockpit/web/src/__tests__/vite_config.test.ts`: 6 passed / 0 failed
  - lint: clean

- GREEN verification (quality-runner, final):
  - Tests: 13 passed / 0 failed / 0 skipped
  - Covered files: `vite_config_pds_1513.test.ts` + `vite_config.test.ts`
  - Lint: clean (no violations)

- Fixes applied during GREEN:
  - Adjusted `node:fs` import style in `vite.config.ts` to align with existing Vitest module-mock shape; no AC behavior changes.

- Commit:
  - `b17e1d71` — feat: add PDS version check Vite plugin (#1513, builder)
2026-05-12T21:37:22+00:00
## Review Evidence
- Verdict: FAIL
- Builder evidence reviewed first: scoped smoke proof in builder notes, direct inspection of `serve/cockpit/web/vite.config.ts`, and direct inspection of `serve/cockpit/web/src/__tests__/vite_config_pds_1513.test.ts`.
- Blocking findings:

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC-4 | Test proof does not verify the regex extraction and first-match requirement. The dedicated AC-4 test asserts only that `readdirSync` was called with the assets directory, while the only version-extraction proof is the single-file mismatch case. A regression from first-match selection to a later match would still pass the current suite. | `serve/cockpit/web/vite.config.ts:40,47-48`; `serve/cockpit/web/src/__tests__/vite_config_pds_1513.test.ts:86,95,101,111-113` | todo |
| 2 | AC-6 | Test proof does not verify that the warning indicates missing assets. The implementation warns `no matching core asset found`, but the AC-6 test asserts only the presence of `npm run sync:pds`, so a generic sync warning would still pass. | `serve/cockpit/web/vite.config.ts:43`; `serve/cockpit/web/src/__tests__/vite_config_pds_1513.test.ts:117,127` | todo |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Add a lifecycle-hook test that feeds multiple matching asset filenames and proves the plugin uses the first regex match to derive the warned asset version. | `serve/cockpit/web/src/__tests__/vite_config_pds_1513.test.ts` | Finding 1; AC-4; `serve/cockpit/web/vite.config.ts:40,47-48` |
| 2 | test-writer | Strengthen the missing-assets test to assert that the warning explicitly indicates missing or unmatched core assets in addition to `npm run sync:pds`. | `serve/cockpit/web/src/__tests__/vite_config_pds_1513.test.ts` | Finding 2; AC-6; `serve/cockpit/web/vite.config.ts:43` |

## Observations
- Direct code inspection shows the implementation itself aligns with the AC on this pass: plugin registration at `serve/cockpit/web/vite.config.ts:64`, hooks at `serve/cockpit/web/vite.config.ts:29,32`, package read at `serve/cockpit/web/vite.config.ts:34-35`, regex extraction at `serve/cockpit/web/vite.config.ts:40,47-48`, mismatch warning at `serve/cockpit/web/vite.config.ts:52`, missing-assets warning at `serve/cockpit/web/vite.config.ts:43`, and skip warning at `serve/cockpit/web/vite.config.ts:57`.
- Builder evidence is internally consistent for a smoke bundle: RED failure recorded, GREEN summary reports 13 passed / 0 failed / 0 skipped with lint clean.
- Builder commit provenance confirmed in `.git/logs/refs/heads/dev:2643` for `b17e1d71`.
2026-05-12T21:40:53+00:00
## Test-Writer Notes
- Retry: added 2 gap-fill tests addressing reviewer findings 1 and 2
- Test file: serve/cockpit/web/src/__tests__/vite_config_pds_1513.test.ts
- Classes: TestFromAC_PdsVersionCheck
- New tests:
  - AC-4(first-match): feeds two matching filenames, asserts first match's version (3.19.0) appears in mismatch warning — proves `files.find()` first-match semantics
  - AC-6(missing-indicator): asserts warning matches `/no matching|missing|not found/` in addition to `npm run sync:pds` — proves missing-asset indicator not just remediation command
- Quality-runner (scoped): 9 passed / 0 failed / 0 skipped (7 original + 2 new)
- ESLint: clean
- Builder skip: test-only retry — both new tests green against current implementation (Step 1b.1)
- Commit: 0d5c3d7b
2026-05-12T21:47:06+00:00
## Review Evidence
- Verdict: FAIL
- Builder evidence reviewed first: prior builder quality-runner GREEN summary (13 passed / 0 failed / 0 skipped, lint clean), the test-writer retry note (9 passed / 0 failed / 0 skipped, lint clean), and direct inspection of `serve/cockpit/web/vite.config.ts` plus `serve/cockpit/web/src/__tests__/vite_config_pds_1513.test.ts`.
- Blocking findings:

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC-4 | The retry closes first-match selection, but proof still does not falsify a broken implementation that warns with the raw filename instead of the extracted semver. Both mismatch assertions are substring-only, so a regression from `match?.[1]` to `coreChunk` would still pass while violating AC-4's `extracts semver` requirement. | `serve/cockpit/web/vite.config.ts:47-48,52`; `serve/cockpit/web/src/__tests__/vite_config_pds_1513.test.ts:111-113,147,162-164` | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Refine the AC-4 proof contract so the retry suite must distinguish extracted semver from raw filename output, then return the task to test-writer for a falsifiable assertion update. | `serve/cockpit/web/src/__tests__/vite_config_pds_1513.test.ts`, `serve/cockpit/web/vite.config.ts` | Finding 1; AC-4; `serve/cockpit/web/vite.config.ts:47-48,52`; `serve/cockpit/web/src/__tests__/vite_config_pds_1513.test.ts:111-113,147,162-164` |

## Observations
- The previous review's AC-6 gap is closed: `AC-6(missing-indicator)` now asserts missing/unmatched wording plus remediation at `serve/cockpit/web/src/__tests__/vite_config_pds_1513.test.ts:168,179-180`.
- The retry also improves AC-4 by proving first-match selection at `serve/cockpit/web/src/__tests__/vite_config_pds_1513.test.ts:147,162-164`, but it still leaves semver-only extraction unfalsified.
- Direct code inspection still shows the implementation itself aligned with the revised AC at `serve/cockpit/web/vite.config.ts:28-57`; the blocker is proof quality on cycle 2, so reviewer routing goes to backlog.
2026-05-12T21:49:47+00:00

## Architecture Review (cycle 3 — proof-contract refinement)

### Reviewer Finding

Reviewer correctly identified that AC-5 mismatch assertions using `.toContain('3.19.0')` do not falsify a regression from `match?.[1]` (bare semver) to `coreChunk` (raw filename), because `3.19.0` is a substring of `porsche-design-system.v3.19.0.xyz123.js`.

### AC-5 Refinement

**Previous AC-5:** When extracted asset version ≠ npm version, `console.warn` outputs message containing both version strings and `npm run sync:pds`

**Revised AC-5:** When extracted asset version ≠ npm version, `console.warn` outputs message with labeled versions in format `assets={bare-semver}` and `npm={bare-semver}` (not raw filenames) and `npm run sync:pds` — tests must assert on `assets=X.Y.Z` label+value pair to falsify raw-filename regression

### Rationale

The implementation already uses `assets=${assetVersion}, npm=${npmVersion}` format at `vite.config.ts:51-52`. Asserting `expect(warnMsg).toContain('assets=3.19.0')` will FAIL if a regression changes to `assets=porsche-design-system.v3.19.0.xyz123.js`, closing the proof gap.

### Test-Writer Guidance

Update the AC-5 and AC-4(first-match) tests to assert `assets=` prefixed version strings instead of bare version substrings. Specifically:
- AC-5 test: `expect(warnMsg).toContain('assets=3.21.0')` and `expect(warnMsg).toContain('npm=3.22.0')`
- AC-4(first-match) test: `expect(warnMsg).toContain('assets=3.19.0')` and `expect(warnMsg).toContain('npm=3.21.0')`

### Verdict: REFINE → APPROVE

Proof bundle: smoke (unchanged)
Test-writer: PROCEED

2026-05-12T21:49:51+00:00
AC-5 proof contract refined: mismatch warning must use labeled `assets={bare-semver}` format so tests assert on label+value pairs (e.g. `assets=3.19.0`) rather than bare version substrings — falsifies raw-filename regression. Test-writer guidance included for AC-5 and AC-4(first-match) assertion updates.
2026-05-12T21:57:26+00:00
## Test-Writer Notes
- Retry (cycle 3): updated AC-5 and AC-4(first-match) assertions per architect's proof-contract refinement
- Test file: serve/cockpit/web/src/__tests__/vite_config_pds_1513.test.ts
- Changes:
  - AC-5 test: `toContain('3.21.0')` → `toContain('assets=3.21.0')`, `toContain('3.22.0')` → `toContain('npm=3.22.0')` — falsifies raw-filename regression
  - AC-4(first-match) test: `toContain('3.19.0')` → `toContain('assets=3.19.0')`, `toContain('3.21.0')` → `toContain('npm=3.21.0')`
- Quality-runner (scoped): 9 passed / 0 failed / 0 skipped, lint clean
- Builder skip: test-only retry — all tests green against current implementation (Step 1b.1)
- Commit: 72458fc8
2026-05-12T22:01:03+00:00
## Review Evidence
- Verdict: FAIL
- Builder evidence reviewed first: prior builder GREEN summary (13 passed / 0 failed / 0 skipped, lint clean), the latest test-writer retry note (9 passed / 0 failed / 0 skipped, lint clean), direct inspection of `serve/cockpit/web/vite.config.ts` and `serve/cockpit/web/src/__tests__/vite_config_pds_1513.test.ts`, plus IDE diagnostics on the scoped files (`get_errors`: none).
- Blocking findings:

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC-2, AC-3, AC-4 | Rooted-path proof is still too weak. The retry invokes `configResolved`, but the AC-3 and AC-4 assertions check only path suffixes, not `{root}`-prefixed paths, so a regression where `configResolved` ignores `root` and `buildStart` uses relative paths would still pass. This leaves AC-2's “stores resolved root” behavior and the `{root}/node_modules/...` / `{root}/public/...` contracts unfalsified. | `serve/cockpit/web/vite.config.ts:29,34,38`; `serve/cockpit/web/src/__tests__/vite_config_pds_1513.test.ts:74,80,90,96` | backlog |
| 2 | AC-4 | Regex-match scan proof still misses the mixed-list boundary. The retry proves first-match behavior only when both listed files already match the regex, and the no-match tests cover only all-miss input. There is still no test with a leading non-match followed by a valid core chunk, so a regression to first-entry logic (`files[0]`) could still pass while violating the “first regex match” contract. | `serve/cockpit/web/vite.config.ts:40`; `serve/cockpit/web/src/__tests__/vite_config_pds_1513.test.ts:120,152,171` | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Refine the proof contract for AC-2/AC-3/AC-4 so the retry suite must assert `FAKE_ROOT`-prefixed package and asset paths, not just suffix matches, then return the task to test-writer for falsifiable path assertions. | `serve/cockpit/web/src/__tests__/vite_config_pds_1513.test.ts`, `serve/cockpit/web/vite.config.ts` | Finding 1; `serve/cockpit/web/vite.config.ts:29,34,38`; `serve/cockpit/web/src/__tests__/vite_config_pds_1513.test.ts:74,80,90,96` |
| 2 | architect | Refine the AC-4 proof contract to require a mixed directory fixture with a leading non-match followed by a matching core chunk, then return the task to test-writer for a test that falsifies first-entry selection. | `serve/cockpit/web/src/__tests__/vite_config_pds_1513.test.ts`, `serve/cockpit/web/vite.config.ts` | Finding 2; `serve/cockpit/web/vite.config.ts:40`; `serve/cockpit/web/src/__tests__/vite_config_pds_1513.test.ts:120,152,171` |

## Observations
- Direct code inspection still shows the implementation itself aligned with the current AC on this pass: root capture at `serve/cockpit/web/vite.config.ts:29-30`, package read at `serve/cockpit/web/vite.config.ts:34-35`, asset scan and regex extraction at `serve/cockpit/web/vite.config.ts:38-48`, mismatch warning at `serve/cockpit/web/vite.config.ts:50-52`, missing-assets warning at `serve/cockpit/web/vite.config.ts:43`, and skip warning at `serve/cockpit/web/vite.config.ts:57`.
- The earlier raw-filename proof gap is closed: the current mismatch assertions require labeled semver output (`assets=...`, `npm=...`) at `serve/cockpit/web/src/__tests__/vite_config_pds_1513.test.ts:111-113,162-164`.
- Commit provenance for the relevant cycle is present in `.git/logs/refs/heads/dev:2643,2646,2649` for builder commit `b17e1d71` and test-writer retry commits `0d5c3d7b` and `72458fc8`.
- I did not dispatch `quality-runner` on this cycle because the blocking issue is proof quality in the current assertions, not contradictory execution evidence.
2026-05-12T22:03:10+00:00
## Architecture Review (cycle 4 — proof-contract refinement)

### Reviewer Findings

1. **AC-3/AC-4 root-path proof gap:** Tests assert `expect.stringContaining('...suffix')` for `readFileSync` and `readdirSync` calls. A regression where `configResolved` root is ignored and `buildStart` uses relative paths would still pass. Tests must assert exact `FAKE_ROOT`-prefixed paths.

2. **AC-4 mixed-list boundary gap:** The first-match test feeds two matching filenames only. A regression from `files.find(regex)` to `files[0]` would still pass. Need a leading non-match filename to falsify first-entry selection.

### Proof-Contract Refinements

**AC-3 test refinement:** Replace `expect.stringContaining('@porsche-design-system/components-js/package.json')` with exact path assertion: `expect(readFileSync).toHaveBeenCalledWith('/fake/project/node_modules/@porsche-design-system/components-js/package.json', 'utf-8')` — falsifies root-ignored regression.

**AC-4 test refinement:** Replace `expect.stringContaining('public/porsche-design-system/components')` with exact path assertion: `expect(readdirSync).toHaveBeenCalledWith('/fake/project/public/porsche-design-system/components')` — falsifies root-ignored regression.

**AC-4(first-match) test refinement:** Prepend a non-matching filename to the directory fixture:
```typescript
vi.mocked(readdirSync).mockReturnValue([
  'style.css',  // non-match — must be skipped
  'porsche-design-system.v3.19.0.xyz123.js',
  'porsche-design-system.v3.21.0.abc456.js',
] as never)
```
This falsifies a `files[0]` regression since `files[0]` is `'style.css'` (no regex match).

### Test-Writer Guidance

Three changes needed in `serve/cockpit/web/src/__tests__/vite_config_pds_1513.test.ts`:

1. **AC-3 test (line ~80):** Change `expect.stringContaining(...)` to exact path `'/fake/project/node_modules/@porsche-design-system/components-js/package.json'`
2. **AC-4 test (line ~96):** Change `expect.stringContaining(...)` to exact path `'/fake/project/public/porsche-design-system/components'`
3. **AC-4(first-match) test (line ~152):** Prepend `'style.css'` to the `readdirSync` mock array

### Verdict: REFINE → APPROVE

Proof bundle: smoke (unchanged)
Test-writer: PROCEED
2026-05-12T22:03:16+00:00
Cycle 4 proof-contract refinement: (1) AC-3/AC-4 tests must assert exact FAKE_ROOT-prefixed paths instead of stringContaining suffixes — falsifies root-ignored regression; (2) AC-4(first-match) test must prepend a non-matching filename to directory fixture — falsifies files[0] regression. Three targeted assertion changes in test file. AC wording unchanged; proof bundle: smoke.
2026-05-12T22:05:08+00:00
## Test-Writer Notes
- Retry (cycle 4): applied architect's proof-contract refinements to 3 assertions
- Test file: serve/cockpit/web/src/__tests__/vite_config_pds_1513.test.ts
- Changes:
  - AC-3 test: `expect.stringContaining('@porsche-design-system/...')` → exact path `'/fake/project/node_modules/@porsche-design-system/components-js/package.json'` — falsifies root-ignored regression
  - AC-4 test: `expect.stringContaining('public/porsche-design-system/...')` → exact path `'/fake/project/public/porsche-design-system/components'` — falsifies root-ignored regression
  - AC-4(first-match) test: prepended `'style.css'` to readdirSync mock array — falsifies files[0] regression
- Quality-runner (scoped): 9 passed / 0 failed / 0 skipped, lint clean
- Builder skip: test-only retry — all 9 tests green against current implementation (Step 1b.1)
- Commit: f1d6fd6a
2026-05-12T22:14:56+00:00
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1513 -> docs | AC mapped to code and evidence sufficient.
- Builder evidence reviewed first: builder quality-runner GREEN summary (13 passed / 0 failed / 0 skipped, lint clean), latest test-writer retry summary (9 passed / 0 failed / 0 skipped, lint clean), scoped IDE diagnostics on `serve/cockpit/web/vite.config.ts` and `serve/cockpit/web/src/__tests__/vite_config_pds_1513.test.ts` (no errors), direct file inspection, and an adversarial code-reader cross-check with no blocking findings.
- AC evidence map:

| AC | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC-1 | `serve/cockpit/web/vite.config.ts:28,64` plugin name + registration in Vite plugins array | `serve/cockpit/web/src/__tests__/vite_config_pds_1513.test.ts:56-58` | PASS |
| AC-2 | `serve/cockpit/web/vite.config.ts:29-32` defines `configResolved` and `buildStart`; no `apply` property | `serve/cockpit/web/src/__tests__/vite_config_pds_1513.test.ts:62-66` plus rooted-path execution proof at `:70-97` | PASS |
| AC-3 | `serve/cockpit/web/vite.config.ts:34-36` reads `{root}/node_modules/@porsche-design-system/components-js/package.json` and pulls `version` | `serve/cockpit/web/src/__tests__/vite_config_pds_1513.test.ts:70-82` exact `FAKE_ROOT` path assertion | PASS |
| AC-4 | `serve/cockpit/web/vite.config.ts:38-48` scans `{root}/public/...`, finds first regex match, extracts capture-group semver | `serve/cockpit/web/src/__tests__/vite_config_pds_1513.test.ts:86-97` exact rooted scan path + `:147-165` mixed-list first-match and `assets=3.19.0` semver extraction proof | PASS |
| AC-5 | `serve/cockpit/web/vite.config.ts:50-53` mismatch warning includes labeled asset/npm versions and remediation | `serve/cockpit/web/src/__tests__/vite_config_pds_1513.test.ts:101-113` | PASS |
| AC-6 | `serve/cockpit/web/vite.config.ts:42-44` missing-assets warning includes missing indicator and remediation | `serve/cockpit/web/src/__tests__/vite_config_pds_1513.test.ts:117-127` plus `:169-181` explicit missing/unmatched wording proof | PASS |
| AC-7 | `serve/cockpit/web/vite.config.ts:32-57` wraps the full check in `try/catch` and warns without rethrow | `serve/cockpit/web/src/__tests__/vite_config_pds_1513.test.ts:131-143` | PASS |

- Safety/security check: local filesystem reads only (`node_modules` package.json and synced public assets), no user input, no network calls, no credential/PII surface, and no new dependency additions in the reviewed scope.
- Blocking findings: none.

## Observations
- The cycle-4 retry closes the previously rejected proof gaps: exact rooted paths (`serve/cockpit/web/src/__tests__/vite_config_pds_1513.test.ts:79-80,95-96`), mixed-list first-match selection with a leading non-match (`:151-159`), labeled semver extraction proof (`:163-164`), and explicit missing/unmatched warning wording (`:180`).
- I did not dispatch `quality-runner` again because the builder and test-writer evidence was internally consistent for a smoke bundle, scoped diagnostics were clean, and the remaining review work was proof-quality inspection rather than contradictory execution evidence.
- Non-blocking residual risk: the suite does not include a near-miss filename boundary for the exact AC-4 regex shape; acceptable for PASS because the implementation currently uses the exact anchored regex at `serve/cockpit/web/vite.config.ts:40,47` and the smoke suite already proves rooted scan, first-match behavior, semver extraction, mismatch warning, missing-assets warning, and skip/no-rethrow behavior.
- Commit provenance for the reviewed changes is present in `.git/logs/refs/heads/dev:2643,2649,2651` for builder commit `b17e1d71` and test-writer retry commits `72458fc8` and `f1d6fd6a`.
2026-05-12T22:16:39+00:00
## Docs Gate

**Verdict: PASS — no docs impact**

### Checklist

| Item | Result | Evidence |
|------|--------|----------|
| 1. README Verification | N/A — no update needed | `serve/cockpit/web/vite.config.ts` → `serve/cockpit/README.md`. New inline `pdsVersionCheckPlugin()` follows the same undocumented pattern as `cspPlugin()`. `sync:pds` workflow section unchanged and still accurate. No removed symbols, commands, or flags. |
| 2. External Attribution | Already recorded | Sources S1/S2/S5 (Vite Plugin API, buildStart issue, npm scripts) recorded in `.owlbear/sources/overview.md` lines 86–88 under task #1512 entry. |
| 3. Research Doc | Linked | Task body references `.owlbear/research/1512-pds-version-check.md` (task #1512). |
| 4. Deletion Detection | N/A | No files deleted. `vite_config_pds_1513.test.ts` added; no orphaned references. |

**Scratch cleanup:** No `1513-*` scratch files found.

**Files edited:** none.
2026-05-12T22:25:16+00:00
## Audit

### Regression Detection
- quality-runner mode full (Python): 4399 passed, 210 failed (all pre-existing in unrelated modules: test_cockpit_view, test_server, test_engine_accessor_migration, test_ideation_diagram; zero Python files touched by #1513)
- quality-runner mode full (Frontend/Vitest): 1573 passed, 0 failed, 11 skipped
- Lint: ruff clean, stylelint clean, htmlhint clean, build clean
- Regression verdict: PASS (no task-related regressions)

### Intent Verification
- Scope alignment: PASS (changed files: serve/cockpit/web/vite.config.ts + serve/cockpit/web/src/__tests__/vite_config_pds_1513.test.ts, both in cockpit frontend domain)
- Purpose match: PASS (build-time PDS version drift guard, inline Vite plugin following existing cspPlugin pattern)
- Extraneous scope: none
- Boundary check: function-level behavior verification deferred to reviewer (reviewer PASS with full AC map across 4 review cycles)

### Architect Quality: 4/5
AC-1 through AC-7 well-specified with exact hooks, paths, regex, and behavioral contracts. Builder succeeded first-pass on implementation. Proof-contract gaps (AC-5 raw-filename, AC-3/AC-4 root-path, AC-4 mixed-list boundary) required 3 refinement cycles with reviewer, but the behavioral specification itself was sound. Score deduction from 5: initial proof-contract gaps should have anticipated testability requirements upfront.

### Commit Integrity
- Upstream commit presence: PASS (builder b17e1d71, test-writer 4f7cf714/0d5c3d7b/72458fc8/f1d6fd6a; all reference #1513 with correct agent attribution)
- Kanban commit packaging: pending (this archival)

### Deduction Breakdown
No deductions applied:
- Intent mismatch: none
- Evidence integrity: no concerns (reviewer PASS with detailed AC map)
- Lint violations: none
- AC quality score 4 > 3: no deduction
- Reviewer evidence section: present and thorough
- Regression failures: none (pre-existing only)

### Confidence: 1.00
### Action: archive