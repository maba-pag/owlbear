---
id: 1398
title: 'P3-08: Test Cockpit delivery gate and dist packaging checks'
status: review
priority: needed
created: 2026-05-06T01:09:47.053865+00:00
updated: 2026-05-11T18:12:48.245111+00:00
tags:
- cockpit
- audit-remediation
- phase-3
- scope:delivery
- type:test
- frontend
- ci
- packaging
- release
parent: 1363
depends_on:
- 1367
- 1385
- 1389
- 1390
- 1396
- 1397
blocked: false
block_reason:
claimed_at: 2026-05-11T18:12:48.245111+00:00
archival_reason:
archival_refs: []
---


## Purpose
Write tests or workflow assertions proving Cockpit delivery gates catch frontend build, test, visual, and packaging failures before release sync.

## Problem Evidence
- sync-to-main is currently the first hard frontend build gate and removes serve/cockpit/web from the consumer tree after staging dist.
- npm run build currently fails, so sync cannot produce a fresh working dist.
- MegaLinter does not run npm build, Vitest, or Playwright.
- Release packaging must preserve serve/cockpit/dist after source removal.

## Acceptance Criteria
- Tests or CI assertions prove the Cockpit frontend quality gate runs build, relevant tests, and appropriate lint or visual checks before release sync can surprise-fail.
- Tests or workflow assertions prove sync-to-main verifies serve/cockpit/dist/index.html and packaged assets after building.
- Failure of the frontend build or required frontend checks prevents release sync from being treated as successful.
- Packaging verification covers the consumer-tree shape where serve/cockpit/web is absent but serve/cockpit/dist is present and usable.
- The proof fails against the audited delivery setup where frontend build, Vitest, and Playwright are not part of the release gate and is suitable for #1399 to satisfy.

## Scope
- In scope: delivery-gate tests, workflow assertions, packaging checks, and failure-mode proof for Cockpit dist generation and sync readiness.
- Out of scope: fixing the frontend build itself unless required by #1399, writing consumer/developer docs from #1400, changing Cockpit product behavior, and cache/SSE invalidation from #1346.

## Counterpart
Implementation task: #1399.

[[2026-05-11]]

## Acceptance Criteria (Refined — Supersedes Original)
- [ ] Workflow assertions prove sync-to-main runs `npm run build`, Vitest (`npm test`), and a Cockpit-specific Playwright E2E step (`npm run test:e2e`) for the frontend before the consumer branch is committed. Assertions must distinguish the Cockpit E2E step from the unrelated Excalidraw Playwright export already in the workflow. (td:2)
- [ ] Workflow assertions prove sync-to-main verifies `serve/cockpit/dist/index.html` exists after building. (td:1)
- [ ] Workflow assertions prove that the frontend build gate cannot be bypassed when cockpit sync is enabled — the `build_cockpit` input must not allow skipping build and quality checks while still syncing cockpit source. (td:2)
- [ ] Tests verify the consumer-tree shape: `serve/cockpit/dist/` contains `index.html` and built assets; `serve/cockpit/web/` is absent from the consumer tree. (td:2)
- [ ] Assertions for Vitest, Cockpit Playwright E2E, and the build-gate bypass guard fail against the current sync-to-main workflow definition and are satisfiable by #1399. (td:1)

[[2026-05-11]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Tests delivery gate + packaging — single concern (cockpit release readiness) |
| Interface clarity | PASS | Refined AC names exact tools (`npm run build`, `npm test`, `npm run test:e2e`), exact filesystem paths, and specific workflow inputs |
| Dependency correctness | PASS | All 6 dependencies (1367, 1385, 1389, 1390, 1396, 1397) archived/done |
| Module layering | N/A | Test task — no production module changes |
| TDD compliance | PASS | This IS the RED test task; tagged `type:test`; counterpart #1399 depends on it |
| KISS/YAGNI | PASS | Scoped to workflow assertions and packaging shape — no over-specification |
| Premise challenge | PASS | Existing `test_cockpit_pds_build_compat.py` covers build exit code and PDS types but NOT workflow structure, packaging shape, or bypass guards. New tests are warranted |
| Pattern consistency | PASS | Follows TDD pair pattern (#1398 test / #1399 impl); test approach (YAML parsing + subprocess) matches existing cockpit test patterns |
| Security surface | N/A | No new system boundaries |
| Single domain | PASS | Cockpit delivery domain; CI workflow is ancillary |

### Codebase Evidence
- `sync-to-main.yml`: Build step (L352), bundle assertion (L357), prune step (L392) — all conditional on `sync_cockpit && build_cockpit`
- `build_cockpit` input (L35) defaults true but can be set false independently of `sync_cockpit` — bypass gap
- Excalidraw export step (L376) already installs Playwright chromium — false-green risk for naive workflow assertions
- MegaLinter already runs ESLint (`TYPESCRIPT_ES`) and Stylelint (`CSS_STYLELINT`) scoped to `serve/cockpit/web/` — lint excluded from delivery gate scope
- `test_cockpit_pds_build_compat.py` runs `npm run build` and `npm test` via subprocess — existing pattern for builder to follow
- Vite config (`serve/cockpit/web/vite.config.ts:49`) outputs to `../dist` with `emptyOutDir: true`
- Backend `main.py:117` checks `dist/` existence at startup — runtime contract for packaging

### AC Refinement Summary
Original AC used vague "relevant tests" and "appropriate lint or visual checks." Refined to:
1. Named exact tools: `npm run build`, Vitest, Cockpit-specific Playwright E2E
2. Added Excalidraw Playwright disambiguation requirement (challenger finding)
3. Added `build_cockpit` bypass guard AC line (challenger finding — the input can disable the build gate while still syncing cockpit source)
4. Specified consumer-tree shape with concrete assertions
5. Sharpened RED-phase contract to list specific assertions that must fail

### Challenge Results
- Challenger: reconsider (confidence 0.29)
- Key findings addressed: (1) Artifact drift — refined AC now written to task; (2) `build_cockpit` bypass — new AC3 added; (3) False-green Playwright — AC1 requires disambiguation from Excalidraw export; (4) Packaging scope — kept reasonable (build success covers PDS runtime completeness)
- Architect response: accepted findings 1-3, rebutted finding 4 (PDS runtime integrity is a build-correctness concern, not a tree-shape concern — covered by AC1 build gate)

### Test Depth
- Max depth: 2
- Test-writer: PROCEED (but `type:test` tag = pass-through; builder writes the tests)

### Verdict: APPROVE
### Action Taken: Refined AC with 5 tightened lines (td:2/1/2/2/1). Added bypass-guard and Playwright-disambiguation requirements per challenger findings. Task approved to `todo`.
[[2026-05-11]]
## Test-Writer Notes
- Non-implementation task (tagged `type:test`) — no test-writer tests applicable.
- This task's deliverable IS the test file; the builder (#1399) writes workflow assertions and packaging tests per the refined AC.
- Passing through to builder.
[[2026-05-11]]
## Builder Notes
- Implementation: added `tests/test_cockpit_delivery_gate_1398.py` with `TestFromAC_*` workflow/package assertions for sync-to-main cockpit delivery gates.
- Tests: `5` assertions total; `2` pass (packaging shape checks), `3` fail as intended for RED proof.
- Coverage: not collected (task intentionally remains RED to drive #1399 implementation).
- ruff: clean on task file.
- Evidence summary:
  - FAIL `test_sync_workflow_runs_cockpit_vitest_before_commit`: no `npm test` cockpit gate step in workflow.
  - FAIL `test_sync_workflow_runs_cockpit_playwright_e2e_distinct_from_excalidraw`: no cockpit `npm run test:e2e` step (Excalidraw Playwright step exists but is unrelated).
  - FAIL `test_sync_workflow_disallows_build_gate_bypass_when_sync_cockpit_true`: cockpit gate steps are conditioned on `inputs.sync_cockpit && inputs.build_cockpit`, allowing bypass.
  - PASS packaging checks: workflow asserts `serve/cockpit/dist/index.html`, stages `serve/cockpit/dist/`, and prunes `serve/cockpit/web` for consumer shape.
- Fixes applied: lint cleanup (RET504, Q000) after initial run; final scoped quality-runner result = pytest exit 1 with expected 3 failures, ruff exit 0.