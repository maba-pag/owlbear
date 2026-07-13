---
id: 1399
title: 'P3-09: Harden Cockpit delivery gate and dist packaging'
status: archived
priority: medium
created: 2026-05-06T01:09:48.720545+00:00
updated: 2026-05-11T20:16:25.000512+00:00
tags:
- cockpit
- audit-remediation
- phase-3
- scope:delivery
- type:build
- frontend
- ci
- packaging
- release
parent: 1363
depends_on:
- 1398
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---


## Purpose
Harden Cockpit delivery so frontend build, tests, visual checks, and dist packaging are verified before sync-to-main can fail late.

## Problem Evidence
- sync-to-main currently discovers Cockpit frontend build failures only during release sync.
- The consumer tree removes serve/cockpit/web after staging dist, so packaged assets must be verified explicitly.
- MegaLinter does not currently run npm build, Vitest, or Playwright for Cockpit.
- Existing documentation and release flow do not make frontend quality checks a first-class gate.

## Acceptance Criteria
- Cockpit frontend quality gate runs build, relevant tests, and appropriate lint or visual checks before release sync can surprise-fail.
- sync-to-main continues to build Cockpit dist and verifies serve/cockpit/dist/index.html plus packaged assets after the build.
- Release packaging preserves the intended consumer shape: prebuilt dist is present and source web package is not required for consumers.
- Frontend build or required frontend check failures stop the delivery gate clearly and early.
- Verification from #1398 passes without removing valid Cockpit packaging behavior.

## Scope
- In scope: CI or workflow hardening, release-sync packaging checks, frontend quality gate wiring, and delivery verification needed to satisfy #1398.
- Out of scope: consumer/developer docs from #1400, product UI changes, DR lifecycle implementation from #1385, product-boundary guardrails from #1390, and cache/SSE invalidation from #1346.

## Counterpart
Test task: #1398.

[[2026-05-11]]

## Refined Acceptance Criteria

1. `sync-to-main.yml` adds a Vitest step (`npm test` with `working-directory: serve/cockpit/web`) that runs after the build step but before both the prune step and the commit step, gated by `${{ inputs.sync_cockpit }}` (td:1)
2. `sync-to-main.yml` adds a Playwright E2E step (`npm run test:e2e` with `working-directory: serve/cockpit/web`) that runs before both the prune step and the commit step, gated by `${{ inputs.sync_cockpit }}` — a preceding `npx playwright install chromium` (or equivalent) is required in CI (td:1)
3. All cockpit quality-gate step conditions (`Setup Node.js`, `Build cockpit SPA`, `Assert SPA bundle exists`, `Stage built SPA bundle`, plus new test steps) reference `inputs.sync_cockpit` and do NOT reference `build_cockpit`; `Setup Node.js` must preserve its existing `inputs.sync_share` path for Excalidraw export (td:1)
4. Existing dist assertion (`serve/cockpit/dist/index.html`) and dist staging (`git add -f serve/cockpit/dist/`) behavior preserved (td:0)
5. Consumer tree pruning of `serve/cockpit/web` continues to function when `sync_cockpit` is enabled (td:0)
6. `test_cockpit_delivery_gate_1398.py` passes in full (td:1)

## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single concern: CI delivery gate hardening for Cockpit frontend |
| Interface clarity | PASS | Refined AC pins exact step names, conditions, working-directory, and ordering constraints |
| Dependency correctness | PASS | Depends on #1398 (archived/done); test file exists at `tests/test_cockpit_delivery_gate_1398.py` |
| Module layering | N/A | Workflow YAML, no Python module imports |
| TDD compliance | PASS | Test task #1398 done; test file validates workflow structure — builder runs GREEN phase |
| KISS/YAGNI | PASS | Minimal scope: add 2-3 steps to existing workflow, change 4 `if` conditions |
| Premise challenge | PASS | Late-discovery build failures in sync-to-main are a documented problem; this is the correct fix |
| Pattern consistency | PASS | Follows existing workflow patterns (npm ci, npx playwright install, working-directory gating) |
| Security surface | PASS | No new system boundaries; workflow runs in existing GitHub Actions context |
| Single domain | PASS | Delivery/CI domain only |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| Vitest step | Frontend tests fail | exit 1 | Yes — step fails, workflow stops | Sync blocked until tests pass |
| E2E step | Playwright tests fail | exit 1 | Yes — step fails, workflow stops | Sync blocked until E2E passes |
| Chromium install | Browser download fails | npx error | Yes — step fails before E2E | Sync blocked; retry usually fixes |
| Condition change | build_cockpit no longer bypasses build | N/A | Intentional | Build always runs when sync_cockpit=true |

### Architecture Notes
- **Step ordering:** Build → Vitest → Chromium install → E2E → Assert dist → Stage dist → Prune web. Tests and assertions must come before prune removes `serve/cockpit/web`.
- **Setup Node.js condition:** Change from `${{ (inputs.sync_cockpit && inputs.build_cockpit) || inputs.sync_share }}` to `${{ inputs.sync_cockpit || inputs.sync_share }}` to satisfy AC3 while preserving Excalidraw export path.
- **`build_cockpit` input:** Consider removing from workflow dispatch inputs since it becomes dead after condition changes. Not AC-required but recommended cleanup.
- **Playwright webServer rebuild:** `playwright.config.ts` has `webServer.command: 'npm run build && npm run preview'`. This re-builds the app during E2E — redundant with the Build step but harmless for a deterministic build. If builder wants staged dist to match tested dist exactly, order Stage after E2E.
- **Workflow timeout:** 10-minute limit should accommodate additional steps. If not, increase to 15 minutes.

### Design Diverge
- Trigger: skipped — single clear approach (add steps to existing workflow), no competing alternatives.

### Challenge Results
- Challenger: block (confidence 0.43)
- Architect response: Rebutted. Two valid concerns addressed in AC refinement: (1) ordering before prune added to AC1/AC2; (3) sync_share preservation added to AC3. Remaining concerns (artifact determinism, timeout budget, benchmark flakiness) are operational/implementation-level, not architectural defects. Test file from #1398 is the locked specification; builder implements to satisfy it plus the architectural ordering constraint.

### Test Depth
- Max depth: 1
- Test-writer: PROCEED (but tests already exist from #1398 — test-writer verifies existing tests are sufficient)

### Verdict: APPROVE
### Action Taken: Rewrote AC from 5 vague lines to 6 precise, td-annotated lines. Added ordering constraints, sync_share preservation requirement, and chromium install mandate. Task advances to `todo`.

[[2026-05-11]]
Architecture review complete. Refined AC from 5 vague lines to 6 precise td-annotated lines. Key refinements: (1) ordering constraint — test steps must run before prune step, not just before commit; (2) sync_share preservation in Setup Node.js condition; (3) chromium install requirement for Playwright E2E. Challenger blocked at 0.43 confidence — rebutted with AC refinement addressing two valid concerns (ordering, cross-scope regression) and overruling four operational concerns. Task advances to todo.
[[2026-05-11]]
## Test-Writer Notes
- Test file: tests/test_cockpit_delivery_gate_1399.py
- Classes: TestFromAC_CockpitDeliveryGateOrdering
- Tests per category: happy 0, edge 0, error 0, boundary 3 (ordering constraints)
- Total: 3 tests, all FAIL
- ruff: clean

**AC coverage:**
| AC | Coverage | Notes |
|----|----------|-------|
| AC1 — Vitest step gated by sync_cockpit, after build, before prune/commit | test_vitest_step_runs_before_prune_step (NEW) + 1398 tests cover gating/commit | 1398 covers gating+commit ordering; 1399 adds prune ordering |
| AC2 — E2E step with chromium install, before prune/commit | test_playwright_chromium_install_precedes_cockpit_e2e + test_playwright_e2e_runs_before_prune_step (NEW) + 1398 covers commit ordering | 1398 covers commit ordering; 1399 adds chromium install and prune ordering |
| AC3 — Conditions reference sync_cockpit not build_cockpit; Setup Node.js preserves sync_share | test_cockpit_delivery_gate_1398.py::test_sync_workflow_disallows_build_gate_bypass_when_sync_cockpit_true | Fully covered by 1398 |
| AC4 — Dist assertion and staging preserved (td:0) | test_cockpit_delivery_gate_1398.py::test_sync_workflow_asserts_cockpit_dist_index_and_stages_dist_tree | Fully covered by 1398 |
| AC5 — Consumer tree pruning preserved (td:0) | test_cockpit_delivery_gate_1398.py::test_sync_workflow_prunes_cockpit_web_tree_for_consumer_shape | Fully covered by 1398 |
| AC6 — test_cockpit_delivery_gate_1398.py passes in full (td:1) | Meta-AC; no new test required — builder must make 1398 tests pass | Pass-through |
[[2026-05-11]]
## Builder Notes
- Files changed: .github/workflows/sync-to-main.yml
- Implementation:
  - Updated cockpit quality-gate `if` expressions from `inputs.sync_cockpit && inputs.build_cockpit` to `inputs.sync_cockpit` for `Build cockpit SPA`, `Assert SPA bundle exists`, and `Stage built SPA bundle`.
  - Updated `Setup Node.js` gate to `${{ inputs.sync_cockpit || inputs.sync_share }}` to preserve the `sync_share` Excalidraw path while removing `build_cockpit` dependency.
  - Added cockpit Vitest step: `npm test` in `serve/cockpit/web`, gated by `inputs.sync_cockpit`.
  - Added Chromium install step before E2E: `npx playwright install chromium --with-deps` in `serve/cockpit/web`, gated by `inputs.sync_cockpit`.
  - Added cockpit Playwright E2E step: `npm run test:e2e` in `serve/cockpit/web`, gated by `inputs.sync_cockpit`.
- Test results:
  - Scoped delivery-gate suite: 8 passed, 0 failed
  - Files: tests/test_cockpit_delivery_gate_1398.py, tests/test_cockpit_delivery_gate_1399.py
- Coverage: N/A (workflow YAML change; no Python module touched)
- Lint: ruff clean (scoped)
- Evidence summary:
  - RED verified pre-change: 2 passed, 6 failed across 1398/1399 tests (missing Vitest/E2E steps and `build_cockpit`-dependent conditions).
  - GREEN verified post-change via quality-runner: all targeted tests pass and lint is clean.
- Fixes applied:
  - Enforced early frontend delivery gates before prune/commit.
  - Preserved dist assertion/staging and consumer pruning behavior.
[[2026-05-11]]

- Commit: 048a80c712b7eb0893e8b5023685002bc13bd799 (`feat: harden cockpit delivery gate ordering (#1399, builder)`)
[[2026-05-11]]
## Review Evidence
### Test Results
- quality-runner pytest: 8 passed, 0 failed
- Command: uv run pytest tests/test_cockpit_delivery_gate_1398.py tests/test_cockpit_delivery_gate_1399.py -q --tb=short

### Lint: clean
- quality-runner ruff: clean
- Command: uv run ruff check tests/test_cockpit_delivery_gate_1398.py tests/test_cockpit_delivery_gate_1399.py

### Coverage: skipped
- Inapplicable for this task: builder changed workflow YAML (.github/workflows/sync-to-main.yml), not a Python source module.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1 — Vitest step runs after Build and before Prune/Commit, gated by sync_cockpit | tests/test_cockpit_delivery_gate_1398.py::test_sync_workflow_runs_cockpit_vitest_before_commit + tests/test_cockpit_delivery_gate_1399.py::test_vitest_step_runs_before_prune_step | No for the after-Build clause. Current assertions prove build < commit, vitest < commit, and vitest < prune, but they do not compare Vitest vs Build. Moving Vitest before Build would keep the suite green. | MISSING |
| AC2 — E2E step before Prune/Commit with preceding Chromium install | tests/test_cockpit_delivery_gate_1398.py::test_sync_workflow_runs_cockpit_playwright_e2e_distinct_from_excalidraw + tests/test_cockpit_delivery_gate_1399.py::test_playwright_chromium_install_precedes_cockpit_e2e + tests/test_cockpit_delivery_gate_1399.py::test_playwright_e2e_runs_before_prune_step | Yes. Removing cockpit E2E, moving it after prune/commit, or omitting any install command before E2E would fail. | COVERED |
| AC3 — Quality-gate conditions use sync_cockpit, not build_cockpit; Setup Node.js preserves sync_share | tests/test_cockpit_delivery_gate_1398.py::test_sync_workflow_disallows_build_gate_bypass_when_sync_cockpit_true | No for the sync_share-preservation clause. The test asserts sync_cockpit is present and build_cockpit is absent, but does not assert inputs.sync_share remains present on Setup Node.js. | MISSING |
| AC4 — Dist assertion and staging preserved | tests/test_cockpit_delivery_gate_1398.py::test_sync_workflow_asserts_cockpit_dist_index_and_stages_dist_tree | Yes. Removing dist assertion or staging would fail. | COVERED |
| AC5 — Consumer pruning preserved when sync_cockpit is enabled | tests/test_cockpit_delivery_gate_1398.py::test_sync_workflow_prunes_cockpit_web_tree_for_consumer_shape | Yes. Removing the prune command or sync_cockpit guard would fail. | COVERED |
| AC6 — test_cockpit_delivery_gate_1398.py passes in full | quality-runner scoped pytest run | Yes. The full file was included in the green run. | COVERED |

#### Security Review
- No issues found. The change adds workflow steps only: npm test, Playwright Chromium install, npm run test:e2e, and condition rewrites. No secrets, injection points, or new untrusted input surfaces observed.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| TestFromAC_CockpitDeliveryGateWorkflow / TestFromAC_CockpitPackagingShape / TestFromAC_CockpitDeliveryGateOrdering | Direct commit diff and scoped git status were not available in this tool surface. Builder notes list only .github/workflows/sync-to-main.yml as changed, current 1399 TestFromAC file still matches the test-writer note (3 tests), and commit 048a80c712b7eb0893e8b5023685002bc13bd799 is present in .git/logs. | No evidence of weakening, but immutability and dirty-tree checks remain lower-confidence than a direct git diff/status verification. |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | WEAK | AC1 proof is split across build < commit (tests/test_cockpit_delivery_gate_1398.py line 64), vitest < commit (tests/test_cockpit_delivery_gate_1398.py line 78), and vitest < prune (tests/test_cockpit_delivery_gate_1399.py line 54). None of those assertions prove Vitest runs after Build. AC3 proof at tests/test_cockpit_delivery_gate_1398.py lines 128 and 131 does not assert sync_share preservation. |
| Negative/error-path coverage | ADEQUATE | Structural workflow-ordering task; the important negative cases are order/gate regressions. Those are partly covered, but not fully for AC1/AC3. |
| Manual mutation reasoning | WEAK | Mutating the workflow so Run cockpit Vitest appears before Build cockpit SPA still satisfies the current tests. Mutating Setup Node.js to `${{ inputs.sync_cockpit }}` would also satisfy the current gating test even though it violates AC3. |
| Test independence | ADEQUATE | Tests parse the workflow fresh and do not share mutable state. |
| Descriptive test names | STRONG | Test names are specific and map cleanly to workflow behaviors. |

#### Data Safety
- No issues found.

#### Implementation-Aware Gaps
- No implementation defect found in the live workflow. The workflow currently satisfies the refined AC: Setup Node.js preserves sync_share (.github/workflows/sync-to-main.yml line 344), Build precedes Vitest (lines 351-359), Chromium install precedes E2E (lines 361-369), dist assertion/staging remain intact (lines 371-381), and prune still removes serve/cockpit/web when sync_cockpit is enabled (line 407).
- The failure is proof quality: two AC subclauses are implemented but not discriminated by the tests.

#### Builder Process Quality
| Metric | Value |
|-------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- build_cockpit still exists as a workflow_dispatch input, but the refined AC does not require its removal. This is cleanup-only, not a review blocker.
- Direct git diff/status evidence was unavailable in this tool surface, so commit ownership and dirty-tree cleanliness could not be verified at full confidence.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1 | Live workflow is correct: Build cockpit SPA at .github/workflows/sync-to-main.yml lines 351-354, Run cockpit Vitest at lines 356-359, Prune at line 397, Commit at line 439. Proof is incomplete: tests/test_cockpit_delivery_gate_1398.py line 64 only proves build before commit, line 78 only proves vitest before commit, and tests/test_cockpit_delivery_gate_1399.py line 54 only proves vitest before prune. | tests/test_cockpit_delivery_gate_1398.py::test_sync_workflow_runs_cockpit_vitest_before_commit; tests/test_cockpit_delivery_gate_1399.py::test_vitest_step_runs_before_prune_step | FAIL |
| AC2 | Live workflow lines 361-369 install Chromium then run cockpit E2E before prune/commit; mapped tests assert install-before-E2E and E2E-before-prune/commit. | tests/test_cockpit_delivery_gate_1398.py::test_sync_workflow_runs_cockpit_playwright_e2e_distinct_from_excalidraw; tests/test_cockpit_delivery_gate_1399.py::test_playwright_chromium_install_precedes_cockpit_e2e; tests/test_cockpit_delivery_gate_1399.py::test_playwright_e2e_runs_before_prune_step | PASS |
| AC3 | Live workflow is correct: Setup Node.js line 344 preserves sync_share and sync_cockpit; other quality-gate conditions at lines 352, 357, 362, 367, 372, 380 use sync_cockpit only. Proof is incomplete: tests/test_cockpit_delivery_gate_1398.py lines 128 and 131 check sync_cockpit presence and build_cockpit absence, but there is no inputs.sync_share assertion in the file. | tests/test_cockpit_delivery_gate_1398.py::test_sync_workflow_disallows_build_gate_bypass_when_sync_cockpit_true | FAIL |
| AC4 | Workflow keeps dist assertion and staging at .github/workflows/sync-to-main.yml lines 371-381. | tests/test_cockpit_delivery_gate_1398.py::test_sync_workflow_asserts_cockpit_dist_index_and_stages_dist_tree | PASS |
| AC5 | Workflow prune step still removes serve/cockpit/web under sync_cockpit at .github/workflows/sync-to-main.yml line 407. | tests/test_cockpit_delivery_gate_1398.py::test_sync_workflow_prunes_cockpit_web_tree_for_consumer_shape | PASS |
| AC6 | quality-runner scoped pytest included tests/test_cockpit_delivery_gate_1398.py and returned 8 passed, 0 failed. | quality-runner scoped pytest | PASS |

### Confidence: 0.77
### Verdict: FAIL
### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Add a discriminating assertion that the cockpit Vitest step index is after Build cockpit SPA and still before Prune/Commit. | tests/test_cockpit_delivery_gate_1398.py, tests/test_cockpit_delivery_gate_1399.py | AC1 coverage gap: build < commit at tests/test_cockpit_delivery_gate_1398.py line 64, vitest < commit at line 78, vitest < prune at tests/test_cockpit_delivery_gate_1399.py line 54; no build -> vitest assertion. |
| 2 | test-writer | Add an assertion that Setup Node.js preserves inputs.sync_share while also requiring inputs.sync_cockpit and excluding build_cockpit. | tests/test_cockpit_delivery_gate_1398.py | AC3 coverage gap: tests/test_cockpit_delivery_gate_1398.py lines 128 and 131 assert sync_cockpit presence and build_cockpit absence only; grep for inputs.sync_share in the file returns no matches. |
[[2026-05-11]]
## Test-Writer Notes
- Retry: 2 new tests added for reviewer-cited proof gaps. All pass against current implementation.
- Builder skip: test-only retry, all tests green.

### New tests added
| File | Test | Gap addressed |
|------|------|---------------|
| tests/test_cockpit_delivery_gate_1399.py | `test_vitest_step_runs_after_build_step` | AC1: discriminates Build→Vitest ordering (build_index < vitest_index) |
| tests/test_cockpit_delivery_gate_1398.py | `test_setup_node_condition_preserves_sync_share` | AC3: asserts Setup Node.js preserves inputs.sync_share while requiring sync_cockpit and excluding build_cockpit |

### Quality results
- pytest: 10 passed, 0 failed (test_cockpit_delivery_gate_1398.py + test_cockpit_delivery_gate_1399.py)
- ruff: clean
- Commit: 8731ce08 (`test: add retry coverage for AC1/AC3 proof gaps (#1399, test-writer)`)

### Step 1b.1 rationale
Reviewer's Required Follow-up contained only test-proof gaps (no implementation fixes needed). Both new tests pass against current code — the workflow already satisfies AC1 (Build before Vitest) and AC3 (sync_share preserved in Setup Node.js). Advancing directly to review.
[[2026-05-11]]
## Builder Notes
- Implementation: no additional code changes in this builder cycle.
- Reason: reviewer-raised gaps were test-proof gaps only; test-writer retry added discriminating coverage and verified against current workflow implementation.
- Files changed: none.
- Tests: 10 passed (scoped) on `tests/test_cockpit_delivery_gate_1398.py` and `tests/test_cockpit_delivery_gate_1399.py`.
- Coverage: N/A for this cycle (workflow YAML task; verification tests only).
- ruff: clean (scoped on the two delivery-gate test files).
- Evidence summary: quality-runner scoped run returned `failed: []`, `passed: 10`, `clean: true`; no implementation regression detected; AC proof set now includes AC1 build->vitest ordering and AC3 sync_share preservation checks from the test-writer retry.
[[2026-05-11]]
## Review Evidence
### Test Results
- quality-runner pytest: 10 passed, 0 failed
- Scoped evidence covers `tests/test_cockpit_delivery_gate_1398.py` and `tests/test_cockpit_delivery_gate_1399.py`

### Lint: clean
- quality-runner ruff: clean
- Scoped lint target: `tests/test_cockpit_delivery_gate_1398.py`, `tests/test_cockpit_delivery_gate_1399.py`

### Coverage: skipped
- Inapplicable for this task: the implementation change is workflow YAML (`.github/workflows/sync-to-main.yml`), not a Python module.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1 — Vitest step runs after Build and before Prune/Commit, gated by `sync_cockpit` | `tests/test_cockpit_delivery_gate_1398.py::test_sync_workflow_runs_cockpit_vitest_before_commit`; `tests/test_cockpit_delivery_gate_1399.py::test_vitest_step_runs_before_prune_step`; `tests/test_cockpit_delivery_gate_1399.py::test_vitest_step_runs_after_build_step`; `tests/test_cockpit_delivery_gate_1398.py::test_sync_workflow_disallows_build_gate_bypass_when_sync_cockpit_true` | Yes. Moving Vitest before Build fails `tests/test_cockpit_delivery_gate_1399.py:125`; moving it after Prune fails `tests/test_cockpit_delivery_gate_1399.py:54`; moving it after Commit fails `tests/test_cockpit_delivery_gate_1398.py:78`; removing the `sync_cockpit` gate or reintroducing `build_cockpit` fails `tests/test_cockpit_delivery_gate_1398.py:128-131`. | COVERED |
| AC2 — E2E step with preceding Chromium install runs before Prune/Commit | `tests/test_cockpit_delivery_gate_1398.py::test_sync_workflow_runs_cockpit_playwright_e2e_distinct_from_excalidraw`; `tests/test_cockpit_delivery_gate_1399.py::test_playwright_chromium_install_precedes_cockpit_e2e`; `tests/test_cockpit_delivery_gate_1399.py::test_playwright_e2e_runs_before_prune_step`; `tests/test_cockpit_delivery_gate_1398.py::test_sync_workflow_disallows_build_gate_bypass_when_sync_cockpit_true` | Yes. Removing or moving cockpit E2E after Commit fails `tests/test_cockpit_delivery_gate_1398.py:99`; moving it after Prune fails `tests/test_cockpit_delivery_gate_1399.py:104`; removing install-before-E2E fails `tests/test_cockpit_delivery_gate_1399.py:82`; removing the `sync_cockpit` gate or reintroducing `build_cockpit` fails `tests/test_cockpit_delivery_gate_1398.py:128-131`. | COVERED |
| AC3 — Quality-gate conditions use `sync_cockpit`, not `build_cockpit`; Setup Node.js preserves `sync_share` | `tests/test_cockpit_delivery_gate_1398.py::test_sync_workflow_disallows_build_gate_bypass_when_sync_cockpit_true`; `tests/test_cockpit_delivery_gate_1398.py::test_setup_node_condition_preserves_sync_share` | Yes. Removing `inputs.sync_share` from Setup Node.js fails `tests/test_cockpit_delivery_gate_1398.py:144`; removing `inputs.sync_cockpit` fails `tests/test_cockpit_delivery_gate_1398.py:148`; reintroducing `build_cockpit` fails `tests/test_cockpit_delivery_gate_1398.py:131` and `tests/test_cockpit_delivery_gate_1398.py:152`. | COVERED |
| AC4 — Dist assertion and staging preserved | `tests/test_cockpit_delivery_gate_1398.py::test_sync_workflow_asserts_cockpit_dist_index_and_stages_dist_tree` | Yes. Breaking build->assert ordering fails `tests/test_cockpit_delivery_gate_1398.py:168`; removing the dist stage fails `tests/test_cockpit_delivery_gate_1398.py:178`. | COVERED |
| AC5 — Consumer pruning preserved when `sync_cockpit` is enabled | `tests/test_cockpit_delivery_gate_1398.py::test_sync_workflow_prunes_cockpit_web_tree_for_consumer_shape` | Yes. Removing prune fails `tests/test_cockpit_delivery_gate_1398.py:189`; removing the `sync_cockpit` guard fails `tests/test_cockpit_delivery_gate_1398.py:192`. | COVERED |
| AC6 — `test_cockpit_delivery_gate_1398.py` passes in full | quality-runner scoped pytest run | Yes. The green run included the full `tests/test_cockpit_delivery_gate_1398.py` file and returned 10 passed, 0 failed. | COVERED |

#### Security Review
- No issues found. The change surface is workflow-step wiring and workflow-order assertions only. No secrets, injection points, path traversal, or unsafe deserialization patterns were introduced.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `TestFromAC_CockpitDeliveryGateWorkflow`, `TestFromAC_CockpitPackagingShape`, `TestFromAC_CockpitDeliveryGateOrdering` | The retry added two strengthening tests: `tests/test_cockpit_delivery_gate_1399.py:109` (`test_vitest_step_runs_after_build_step`) and `tests/test_cockpit_delivery_gate_1398.py:137` (`test_setup_node_condition_preserves_sync_share`). Task history records builder commit `048a80c712b7eb0893e8b5023685002bc13bd799` for workflow changes and test-writer commit `8731ce08` for proof-only retry; both commits are present in `.git/logs/HEAD:2738-2739` and `.git/logs/refs/heads/dev:2538-2539`. Direct `git show --name-only` / `git status --porcelain` were unavailable in this tool surface. | STRENGTHENED (with a small confidence deduction for indirect git verification) |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | Ordering is now pinned by explicit index comparisons: build before commit (`tests/test_cockpit_delivery_gate_1398.py:64`), Vitest before commit (`tests/test_cockpit_delivery_gate_1398.py:78`), Vitest before prune (`tests/test_cockpit_delivery_gate_1399.py:54`), Vitest after build (`tests/test_cockpit_delivery_gate_1399.py:125`), E2E before commit (`tests/test_cockpit_delivery_gate_1398.py:99`), E2E before prune (`tests/test_cockpit_delivery_gate_1399.py:104`), install before E2E (`tests/test_cockpit_delivery_gate_1399.py:82`), and Setup Node.js gate contents (`tests/test_cockpit_delivery_gate_1398.py:128-152`). |
| Negative/error-path coverage | ADEQUATE | This is a structural workflow-ordering task. The meaningful failure modes are mis-ordering and wrong gate expressions; the suite now asserts those directly for AC1-AC5. |
| Manual mutation reasoning | STRONG | Moving Vitest before Build, removing `sync_share` from Setup Node.js, moving E2E after Prune/Commit, removing dist staging, or removing the prune guard each trips a named assertion. |
| Test independence | STRONG | Each test parses the workflow independently and shares no mutable state. |
| Descriptive test names | STRONG | Test names map directly to the refined AC clauses and prior reviewer feedback. |

#### Data Safety
- No issues found.

#### Implementation-Aware Gaps
- No AC-scoped gaps found. The live workflow matches the now-discriminating proof set: Setup Node.js preserves `sync_share` at `.github/workflows/sync-to-main.yml:344`; Build/Vitest/E2E/dist steps are present and ordered at `.github/workflows/sync-to-main.yml:351`, `:356`, `:361`, `:366`, `:371`, `:379`; prune remains at `.github/workflows/sync-to-main.yml:397` with `sync_cockpit`-scoped removal at `:406-407`; Commit remains later at `:439`.

#### Builder Process Quality
| Metric | Value |
|-------|-------|
| Builder Notes sections | 2 |
| Approach variation | Yes |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- Direct `git show --name-only` and scoped `git status --porcelain` were not available in this tool surface. Commit presence was verified via reflog, but ownership reconstruction and dirty-tree cleanliness remain slightly lower-confidence than a terminal-backed git review.
- `build_cockpit` still exists as a workflow-dispatch input, but the refined AC does not require removing it. This is cleanup-only, not a blocker.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1 | Live workflow order is Build `:351` -> Vitest `:356` -> Prune `:397` -> Commit `:439` with `sync_cockpit` gate at `:357`; tests assert before-commit, before-prune, after-build, and gate contents. | `test_sync_workflow_runs_cockpit_vitest_before_commit`; `test_vitest_step_runs_before_prune_step`; `test_vitest_step_runs_after_build_step`; `test_sync_workflow_disallows_build_gate_bypass_when_sync_cockpit_true` | PASS |
| AC2 | Live workflow order is Install Chromium `:361` -> Run cockpit Playwright E2E `:366` -> Prune `:397` -> Commit `:439`; tests assert E2E-before-commit, install-before-E2E, E2E-before-prune, and `sync_cockpit` gating for the E2E step. | `test_sync_workflow_runs_cockpit_playwright_e2e_distinct_from_excalidraw`; `test_playwright_chromium_install_precedes_cockpit_e2e`; `test_playwright_e2e_runs_before_prune_step`; `test_sync_workflow_disallows_build_gate_bypass_when_sync_cockpit_true` | PASS |
| AC3 | Setup Node.js preserves `inputs.sync_share` and `inputs.sync_cockpit` at `.github/workflows/sync-to-main.yml:344`; other quality-gate steps use `inputs.sync_cockpit` at `:352`, `:357`, `:362`, `:367`, `:372`, `:380`; tests assert `sync_share` preserved and `build_cockpit` absent. | `test_sync_workflow_disallows_build_gate_bypass_when_sync_cockpit_true`; `test_setup_node_condition_preserves_sync_share` | PASS |
| AC4 | Dist assertion and staging remain at `.github/workflows/sync-to-main.yml:371-381`; test asserts build-before-assert and `git add -f serve/cockpit/dist/`. | `test_sync_workflow_asserts_cockpit_dist_index_and_stages_dist_tree` | PASS |
| AC5 | Prune still removes `serve/cockpit/web` under `sync_cockpit` at `.github/workflows/sync-to-main.yml:406-407`; test asserts both the removal command and the guard. | `test_sync_workflow_prunes_cockpit_web_tree_for_consumer_shape` | PASS |
| AC6 | quality-runner scoped pytest run returned 10 passed, 0 failed while including the full `tests/test_cockpit_delivery_gate_1398.py` file. | quality-runner scoped pytest | PASS |

### Confidence: 0.93
### Verdict: PASS
[[2026-05-11]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | Changed file is `.github/workflows/sync-to-main.yml` (CI config, not IN-scope). No IN-scope README references sync-to-main, sync_cockpit, build_cockpit, or the delivery gate workflow. Verified via grep across all root and package READMEs. |
| 2 | Module docstrings | No | N/A | No Python source modules modified; task is workflow YAML + test files only. |
| 3 | External attribution | No | N/A | Builder notes cite no external repos or patterns. |
| 4 | Research doc | No | N/A | No .owlbear/research/ file referenced in task body. |
| 5 | Diagram maintenance (describes match) | No | N/A | Doc-index checked; no diagram describes glob matches `.github/workflows/**` or `tests/**`. |
| 6 | Explicit diagram creation | No | N/A | No diagram creation request in task body. |
| 7 | Deletion detection | No | N/A | No files deleted; task added steps to existing workflow and added test coverage. |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| `.github/workflows/sync-to-main.yml` | OUT | N/A — CI workflow config, not a prose doc |
| `tests/test_cockpit_delivery_gate_1399.py` | OUT | N/A — test file |
| `tests/test_cockpit_delivery_gate_1398.py` | OUT | N/A — test file |

### Files Updated
- None

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no 1399-* scratch files existed)
[[2026-05-11]]
## Audit
### Regression Detection
- quality-runner mode full: 4430 passed, 202 failed, 5 collection errors
- Background failures confirmed pre-existing: ~200 failures present in prior full-suite runs (/tmp/qr-1489-pytest.txt: 203 failed; /tmp/qr-1455-pytest.txt: 206 failed) across unrelated modules (test_cockpit_view, test_ideation_diagram, test_cockpit_pds_build_compat, etc.)
- Task-scoped verification: 10 passed, 0 failed (test_cockpit_delivery_gate_1398.py + test_cockpit_delivery_gate_1399.py)
- Lint: 271 pre-existing E402 violations across workspace; scoped reviewer lint on task files was clean
- regression verdict: PASS (no regressions attributable to #1399)

### Intent Verification
- scope alignment: PASS (builder commit 048a80c7 touches only .github/workflows/sync-to-main.yml; test-writer commit 8731ce08 touches only the two delivery gate test files — all within cockpit delivery/CI domain)
- purpose match: PASS (added Vitest step, Chromium install, Playwright E2E step, and condition rewrites to sync-to-main workflow — directly addresses stated purpose of hardening delivery gate)
- extraneous scope: none
- boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 4/5
AC was refined from 5 vague lines to 6 precise td-annotated lines with ordering constraints, sync_share preservation, and chromium install mandate. Minor gap: AC1 "runs after Build" was implicit rather than explicit, requiring reviewer to catch the test proof gap. Overall solid — architect caught key concerns via challenger process and refined accordingly.

### Commit Integrity
- upstream commit presence: PASS (048a80c7 builder: 1 file, 19+/4-; 8731ce08 test-writer: 2 files, 42+/0-; both present in git log)
- working tree clean: PASS (git status --porcelain shows no uncommitted changes for task paths)
- kanban commit packaging: pending (this audit)

### Deduction Breakdown
No deductions applied:
- Regression failures: 0 (all failures pre-existing)
- Intent mismatch: 0 (clean scope)
- Evidence integrity: 0 (reviewer provided thorough two-pass review with explicit AC coverage)
- Lint violations: 0 (task files clean; workspace violations pre-existing)
- AC quality ≤ 3: 0 (scored 4/5)
- Missing reviewer evidence: 0 (detailed)

### Confidence: 1.00
### Action: archive