---
id: 1496
title: 'Cockpit: Replace PDS appendChild monkeypatch with property trap on document.porscheDesignSystem.cdn'
status: archived
priority: medium
created: 2026-05-12T02:37:00.298093+00:00
updated: 2026-05-12T21:32:45.953826+00:00
tags:
  - cockpit
  - frontend
parent: 1495
depends_on:
  - 1511
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---

Replace the global `Element.prototype.appendChild` monkeypatch in main.tsx with an `Object.defineProperty` trap on `document.porscheDesignSystem.cdn` that always returns `window.location.origin` as the URL. This eliminates prototype pollution, handles the double `load()` call from PorscheDesignSystemProvider, and correctly redirects all PDS asset URLs (JS chunks and non-JS assets like icons/flags) to localhost. See `.owlbear/research/1495-pds-v4-local-hosting.md` for full analysis.

## Acceptance Criteria

1. `installPdsRuntimeScriptRewrite()` function, its call site, and the `PDS_CDN_SCRIPT` regex are removed from main.tsx
2. Before `load()` is called, an `Object.defineProperty` trap on `document.porscheDesignSystem.cdn` ensures that reading `cdn.url` returns `window.location.origin` regardless of PDS `load()` assignments
3. The post-bootstrap `document.porscheDesignSystem` reassignment block (current main.tsx lines 38-41) is removed — the property trap replaces this fixup
4. E2E tests in `pds-runtime-csp.spec.ts` pass without modification

Proof bundle: behavioral

## Research
- Research doc: .owlbear/research/1496-pds-property-trap.md
- Sources: 8 studied, 5 high-relevance
- Recommendation: Proceed with Object.defineProperty trap on document.porscheDesignSystem.cdn (confidence: 0.82)
- Follow-up tasks created: #1510 (sync PDS local assets with npm version, at research)
- Decision requests: none

## Challenge Results
- Challenger: block (confidence in original: 0.30)
- Key challenges: trap lifetime after post-bootstrap fixup, version mismatch 4.0.0 vs 4.1.0, contradictory test evidence
- Researcher response: revised — accepted version mismatch as orthogonal pre-existing issue (#1510), rebutted trap lifetime concern (post-bootstrap fixup IS the code being removed), accepted test evidence as supporting trap approach (icon CDN violations prove appendChild monkeypatch is incomplete)
- Final confidence after rebuttal: 0.82

## Key Findings
1. PDS load() uses direct assignment: document[s].cdn = { url, prefixes } — interceptable by defineProperty setter
2. componentsReady() Proxy has only a set trap using Reflect.set — our getter/setter survives
3. Current appendChild monkeypatch is incomplete: only intercepts HTMLScriptElement, not icon/flag asset URLs
4. Pre-existing version mismatch: npm 4.1.0 vs public/ v4.0.0 core chunk + missing icon files — separate follow-up #1510
5. Post-bootstrap fixup (lines 38-41) must be removed as part of implementation — it replaces the trapped namespace
2026-05-12T09:39:24+00:00
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: replace monkeypatch with property trap in main.tsx |
| Interface clarity | PASS | AC specifies concrete function/regex removal, trap mechanism, and regression gate |
| Dependency correctness | PASS | No dependencies. Pre-existing asset mismatch tracked separately as #1510 |
| Module layering | PASS | Frontend-only change, no cross-layer concerns |
| TDD compliance | PASS | Behavioral bundle → test-writer writes RED phase tests |
| KISS/YAGNI | PASS | ~15 LOC replacement, simpler than current ~25 LOC + fixup |
| Premise challenge | PASS | PDS v4 has no native self-hosting config (confirmed by research + GitHub issue #2701) |
| Pattern consistency | PASS | Boot-time side effects in main.tsx follow existing pattern |
| Security surface | PASS | Removes prototype pollution (code hygiene improvement), no new attack surface |
| Single domain | PASS | Cockpit frontend only |

### Failure Mode Map

| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|-------------|-----------|----------|-------------|
| defineProperty trap | PDS changes cdn property structure in future version | N/A (runtime) | No — pinned at 4.1.0 | PDS assets load from CDN instead of localhost |
| Proxy wrapping by componentsReady() | Future PDS adds get trap that shadows our getter | N/A (runtime) | No — verified compatible with current 4.1.0 | Same as above |

### AC Refinement

Rewrote original AC to fix B3 violation ("correctly" banned word in AC-4) and add specificity:
- AC-1: Names concrete function (`installPdsRuntimeScriptRewrite`), call site, and regex (`PDS_CDN_SCRIPT`)
- AC-2: Specifies trap mechanism, timing (before `load()`), and observable invariant
- AC-3: Identifies post-bootstrap fixup block by line reference
- AC-4: Regression gate on existing E2E suite

### Design Diverge
- Skipped — single valid approach (property trap). Research already evaluated 3 options (property trap, scoped patch + trap, keep current) and selected Option A with challenger validation.

### Challenge Results
- Challenger: reconsider (confidence: 0.66)
- Key findings: AC-1/AC-3 are structural checks not input→output pairs; E2E doesn't directly test trap mechanism; version mismatch understated
- Architect response: rebutted — structural removal AC is standard for refactoring tasks; behavioral proof bundle triggers TDD RED phase where test-writer writes trap-specific unit tests; version mismatch is pre-existing/orthogonal (#1510); consolidation test not needed (different files/concerns between #1496 and #1497)
- Override justification: all moderate-severity findings are addressed by the existing proof bundle workflow. No blocking architectural defects.

### Proof-Bundle Validation
- Planner assignment: (none)
- Final bundle: behavioral
- Test-writer: PROCEED
- Guidance for test-writer: Write a jsdom unit test that (1) installs the property trap, (2) simulates PDS load() cdn assignment, (3) asserts cdn.url returns window.location.origin. E2E in pds-runtime-csp.spec.ts covers regression.

### Verdict: APPROVE
### Action Taken: Refined AC (B3 fix, specificity improvements), assigned proof bundle behavioral, advanced backlog → todo.
2026-05-12T10:40:17+00:00
## Test-Writer Notes

- **Test file:** `serve/cockpit/web/src/__tests__/main_pds_trap_1496.test.ts`
- **Framework:** Vitest + jsdom (frontend, TypeScript)
- **Total tests:** 12 — 9 FAIL (RED), 3 PASS (regression guards)
- **Lint:** ESLint clean

### Test classes

| Class | Category | Tests | Status |
|-------|----------|-------|--------|
| `TestFromAC_PdsTrapStructural` | structural source-read | 6 | ALL FAIL ✓ |
| `TestFromAC_PdsTrapBehavior` | behavioral import | 3 | ALL FAIL ✓ |
| `TestFromAC_E2eRegressionGuard` | regression guard | 3 | ALL PASS (correct) |

### AC coverage

| AC | Tests | Approach |
|----|-------|----------|
| AC-1: `installPdsRuntimeScriptRewrite`, call site, `PDS_CDN_SCRIPT` removed | 3 source-read | Assert strings absent from main.tsx → FAIL (currently present) |
| AC-2: `Object.defineProperty` trap on `cdn` before `load()` | 2 structural + 3 behavioral | Source: assert defineProperty present and before load() call; Behavioral: import main.tsx with mocked PDS/React, check descriptor + cdn.url during load() + trap-before-load order |
| AC-3: Post-bootstrap reassignment block removed | 1 source-read | Assert spread-reassignment pattern absent → FAIL (currently present) |
| AC-4: E2E spec unmodified | 3 regression guards | Read spec file, assert key describe/test names present → PASS (regression gate) |

### Behavioral test approach (AC-2)
- `vi.mock('@porsche-design-system/components-js', ...)` + `vi.mock('react-dom/client', ...)` + `vi.mock('../App', ...)`
- `beforeEach`: `vi.resetModules()`, delete namespace, spy on `customElements.whenDefined`
- Dynamic `import('../main')` + 50ms settle for async bootstrap
- Mocked `load()` simulates PDS direct cdn assignment; reads back immediately to capture cdn.url during assignment (bypasses post-bootstrap fixup)

### Fail verification
- quality-runner confirmed: 9 FAIL, 3 PASS, lint clean
2026-05-12T11:17:09+00:00
## Builder Notes

### Files Changed
- serve/cockpit/web/src/main.tsx

### Implementation Summary
- Removed legacy PDS runtime script rewrite implementation:
  - removed `PDS_CDN_SCRIPT`
  - removed `installPdsRuntimeScriptRewrite()`
  - removed global `Element.prototype.appendChild` monkeypatch and call site
- Added `installPdsCdnTrap()` using `Object.defineProperty` on `document.porscheDesignSystem.cdn`.
- Installed trap before `load()` inside `bootstrap()`.
- Removed post-bootstrap `document.porscheDesignSystem` reassignment fixup block (trap now enforces `cdn.url` invariant at assignment/read time).

### Test Results (quality-runner)
- Scoped RED verification before implementation:
  - file: `serve/cockpit/web/src/__tests__/main_pds_trap_1496.test.ts`
  - result: 9 failed, 3 passed (expected RED)
  - lint: clean
- Scoped GREEN verification after implementation:
  - file: `serve/cockpit/web/src/__tests__/main_pds_trap_1496.test.ts`
  - result: 12 passed, 0 failed
  - coverage: `main.tsx` 100%
  - lint: clean

### Durable Module Test Visibility
- No module-level durable test file for `main` found beyond task-scoped test artifact; skipped per workflow rule.

### Lint Status
- ESLint clean for:
  - serve/cockpit/web/src/main.tsx
  - serve/cockpit/web/src/__tests__/main_pds_trap_1496.test.ts

### Commit
- `a615918d` — feat: replace PDS monkeypatch with cdn property trap (#1496, builder)

### Evidence Summary
- AC-1 satisfied: monkeypatch function/call site/regex removed.
- AC-2 satisfied: trap installed before `load()` and enforces `cdn.url === window.location.origin` through getter.
- AC-3 satisfied: post-bootstrap reassignment block removed.
- AC-4 guard preserved: no edits to e2e spec; regression guard tests passed in scoped suite.

### Fixes Applied
- Replaced prototype-polluting runtime rewrite with namespace-local property trap.
- Ensured assignment-time and read-time normalization of PDS CDN URL to localhost origin.
2026-05-12T11:51:30+00:00
## Review Evidence
- Verdict: FAIL
- AC-1: PASS — serve/cockpit/web/src/main.tsx file inspection shows the legacy installPdsRuntimeScriptRewrite / PDS_CDN_SCRIPT / appendChild monkeypatch path is gone, while the new runtime path is centered on installPdsCdnTrap() at serve/cockpit/web/src/main.tsx:9-28.
- AC-2: PASS — the trap is defined with Object.defineProperty at serve/cockpit/web/src/main.tsx:14 and installed before load() at serve/cockpit/web/src/main.tsx:36-37. Task-scoped tests specifically assert cdn.url during assignment at serve/cockpit/web/src/__tests__/main_pds_trap_1496.test.ts:161 and trap-before-load ordering at serve/cockpit/web/src/__tests__/main_pds_trap_1496.test.ts:190.
- AC-3: PASS — serve/cockpit/web/src/main.tsx:35-45 now bootstraps directly from trap install -> load() -> waitForRequiredPdsElements() -> render(), with no post-bootstrap document.porscheDesignSystem reassignment block remaining on file inspection.
- AC-4: FAIL — the task-scoped tests at serve/cockpit/web/src/__tests__/main_pds_trap_1496.test.ts:220-235 only verify that serve/cockpit/web/e2e/pds-runtime-csp.spec.ts still contains key strings / was not modified. They do not execute the real Playwright assertions in serve/cockpit/web/e2e/pds-runtime-csp.spec.ts:87, :95, :118, and :134. Builder notes contain no actual run of serve/cockpit/web/e2e/pds-runtime-csp.spec.ts. Independent review verification also could not execute the suite because Playwright first runs npm run build && npm run preview (serve/cockpit/web/playwright.config.ts:17-18) and the build failed before tests started with: serve/cockpit/web/src/components/DetailTab.tsx:107 — "Argument of type 'TaskEditPayload' is not assignable to parameter of type 'Record<string, unknown>'. Index signature for type 'string' is missing in type 'TaskEditPayload'."

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC-4 | Executable proof is insufficient. The task substitutes source-read regression guards for the named Playwright gate, and review could not independently execute the real E2E suite. | serve/cockpit/web/src/__tests__/main_pds_trap_1496.test.ts:220-235; serve/cockpit/web/e2e/pds-runtime-csp.spec.ts:87,95,118,134; serve/cockpit/web/playwright.config.ts:17-18; quality-runner instrument failure citing serve/cockpit/web/src/components/DetailTab.tsx:107 | in-progress |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Provide real AC-4 evidence by running the named Playwright spec serve/cockpit/web/e2e/pds-runtime-csp.spec.ts and attach the result in task notes; do not treat the source-read regression guards as proof of E2E pass. If the shared frontend build failure still blocks that run, document the blocker explicitly and resolve or coordinate it before returning to review. | serve/cockpit/web/e2e/pds-runtime-csp.spec.ts; serve/cockpit/web/playwright.config.ts; serve/cockpit/web/src/__tests__/main_pds_trap_1496.test.ts | Blocking finding #1; Playwright build gate at serve/cockpit/web/playwright.config.ts:17-18; quality-runner build failure in serve/cockpit/web/src/components/DetailTab.tsx:107 |

## Observations
- The implementation in serve/cockpit/web/src/main.tsx:9-37 appears to satisfy AC-1 through AC-3: the trap is defined with Object.defineProperty, installed before load(), and the legacy monkeypatch/fixup code is absent on file inspection.
- The AC-2 unit tests are appropriately specific for the trap behavior. The review miss is specifically AC-4 proof, not the main runtime rewrite itself.
- I could not perform the path-scoped git status contamination check from reviewer Step 1 because git/terminal tools are not available in this tool surface.
2026-05-12T12:30:03+00:00
## Builder Notes

### Files Changed
- None

### Verification Run (AC-4 executable proof)
- quality-runner (first attempt): environment routing error (`Playwright not found in $PATH`)
- quality-runner retry with frontend hint (`cd serve/cockpit/web`): executed real Playwright spec and reported 5/5 FAIL
  - `serve/cockpit/web/e2e/pds-runtime-csp.spec.ts`
  - all failures timeout in `beforeEach` waiting for `[data-region="workspace"]`

### Independent Runtime Diagnosis
- Direct browser runtime capture against preview build shows root blocker is missing local PDS asset:
  - 404: `/porsche-design-system/components/porsche-design-system.v4.1.0.59dc31ee9c99f5a43eb5.js`
  - request failure: `net::ERR_ABORTED`
  - workspace never renders within 10s
- This matches known pre-existing version-sync gap tracked by task #1510.

### Dependency Coordination
- Added dependency: #1496 now depends on #1510.

### Lint/Test Snapshot
- E2E spec execution: 0 passed, 5 failed (runtime blocker)
- ESLint on spec: clean
- No source edits performed in this retry.

### Evidence Summary
- AC-4 is now proven with executable evidence (named Playwright spec was run), but currently failing due a pre-existing PDS asset sync blocker rather than additional #1496 code changes.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | After #1510 lands, rerun `serve/cockpit/web/e2e/pds-runtime-csp.spec.ts` and re-submit AC-4 proof for #1496. | serve/cockpit/web/e2e/pds-runtime-csp.spec.ts | Playwright failures at `waitFor([data-region="workspace"])` and runtime 404 on `/porsche-design-system/components/porsche-design-system.v4.1.0.59dc31ee9c99f5a43eb5.js` |
| 2 | architect | Confirm AC routing/dependency sequencing keeps #1496 behind #1510 for executable E2E pass criteria. | .owlbear/kanban/tasks/1496.md | Structural gate is unreachable until local PDS asset sync is fixed (#1510). |
2026-05-12T12:59:25+00:00
## Builder Notes

### Files Changed
- None

### Verification Run (AC-4 executable proof)
- quality-runner scoped run executed the real Playwright spec:
  - `serve/cockpit/web/e2e/pds-runtime-csp.spec.ts`
- Result: 0 passed, 5 failed (all target tests timed out at 30s)
  - `p-button custom element is defined after workspace renders`
  - `p-icon, p-tabs, and p-tabs-item are defined after workspace renders`
  - `no securitypolicyviolation fires with blockedURI from cdn.ui.porsche.com`
  - `no securitypolicyviolation fires with blockedURI from cdn.ui.porsche.cn`
  - `p-button element has non-empty shadowRoot after page stabilizes`
- quality-runner also reported broader suite instability/timeouts in same environment run, consistent with workspace not stabilizing under current local PDS asset state.

### Lint/Test Snapshot
- Playwright: failed (exit code 1)
- Lint for target spec: no violations reported
- No source edits performed in this retry.

### Evidence Summary
- AC-1 through AC-3 remain implemented from prior builder pass.
- AC-4 remains unmet in executable form because the named Playwright regression spec does not pass in current workspace state.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Resolve routing/sequencing so #1496 is only re-entered when asset-sync prerequisite is completed and the executable E2E gate is reachable. | serve/cockpit/web/e2e/pds-runtime-csp.spec.ts | Current scoped run: 0/5 passing with 30s timeouts across all AC-4 checks. |
| 2 | builder | Re-run scoped AC-4 proof (`serve/cockpit/web/e2e/pds-runtime-csp.spec.ts`) after prerequisite fix lands, then resubmit to review only on real Playwright pass. | serve/cockpit/web/e2e/pds-runtime-csp.spec.ts | Latest quality-runner evidence confirms executable gate still red. |
2026-05-12T13:34:27+00:00
## Builder Notes
- Files changed: none
- Verification: quality-runner scoped run on `serve/cockpit/web/e2e/pds-runtime-csp.spec.ts`
- Playwright: 0 passed, 5 failed
- Lint: clean
- Coverage: not applicable for Playwright run
- Result: AC-4 executable proof remains failing in current workspace state (all five tests timeout waiting for `[data-region="workspace"]`).

### Evidence Summary
- Executed required AC-4 gate (real Playwright spec): `serve/cockpit/web/e2e/pds-runtime-csp.spec.ts`
- Failures:
  1. `p-button custom element is defined after workspace renders`
  2. `p-icon, p-tabs, and p-tabs-item are defined after workspace renders`
  3. `no securitypolicyviolation fires with blockedURI from cdn.ui.porsche.com`
  4. `no securitypolicyviolation fires with blockedURI from cdn.ui.porsche.cn`
  5. `p-button element has non-empty shadowRoot after page stabilizes`
- All failures timeout at 30s in `beforeEach`/test path while waiting for workspace visibility.
- Dependency check: task #1510 (`Sync PDS local assets in public/ with npm package version`) is still in `research`, so the known prerequisite for stable runtime rendering is not yet delivered.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | researcher | Complete and advance dependency task #1510 so local PDS assets align with npm version and runtime boot can stabilize. | serve/cockpit/web/public/porsche-design-system/** | #1510 currently in `research`; AC-4 Playwright gate still 0/5 passing.
| 2 | builder | Re-run scoped AC-4 proof after #1510 is complete; only return DONE when the real Playwright spec passes. | serve/cockpit/web/e2e/pds-runtime-csp.spec.ts | Current quality-runner run: 0 passed, 5 failed (workspace visibility timeouts).
| 3 | architect | Confirm sequencing keeps #1496 behind #1510 until executable AC-4 evidence is attainable. | .owlbear/kanban/tasks/1496.md | Gate is structurally unreachable before dependency completion.

2026-05-12T14:20:51+00:00
## Builder Notes

### Files Changed
- None

### Verification Run (AC-4 executable proof)
- quality-runner scoped run on `serve/cockpit/web/e2e/pds-runtime-csp.spec.ts`
- Result: 0 passed, 5 failed
- All failures timeout at 30s in `beforeEach` waiting for `[data-region="workspace"]` visibility.

### Lint/Test Snapshot
- Playwright: failed (exit code 1)
- ESLint on target spec: clean (exit code 0)
- Coverage: not applicable for Playwright run

### Dependency State
- Existing prerequisite remains unresolved: task #1510 is still in `research`.
- #1496 already depends on #1510.

### Evidence Summary
- AC-1 through AC-3 were previously implemented and committed (`a615918d`).
- AC-4 remains red in executable form (real Playwright spec), so GREEN gate is structurally unreachable until prerequisite #1510 is delivered.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | researcher | Complete task #1510 so local PDS assets match npm package version and workspace can render in E2E runtime. | serve/cockpit/web/public/porsche-design-system/** | #1510 status is `research`; AC-4 proof run on `serve/cockpit/web/e2e/pds-runtime-csp.spec.ts` is 0/5 passing with workspace visibility timeouts. |
| 2 | builder | Re-run scoped AC-4 Playwright proof for #1496 immediately after #1510 is complete; advance only when `serve/cockpit/web/e2e/pds-runtime-csp.spec.ts` passes. | serve/cockpit/web/e2e/pds-runtime-csp.spec.ts | Current quality-runner result: 0 passed, 5 failed, eslint clean. |
| 3 | architect | Keep #1496 sequencing behind #1510 in dispatch planning to avoid repeated unreachable builder cycles. | .owlbear/kanban/tasks/1496.md | Structural gate (AC-4 executable pass) remains blocked by unresolved dependency.
2026-05-12T14:54:21+00:00
## Builder Notes

### Files Changed
- None

### Verification Run (AC-4 executable proof)
- quality-runner scoped run executed required Playwright gate:
  - `serve/cockpit/web/e2e/pds-runtime-csp.spec.ts`
- Result: 0 passed, 5 failed
- All failures timeout in `beforeEach` at 30s while waiting for `[data-region="workspace"]` to be visible.

### Failure Details
1. `TestFromAC_PDSCustomElementsRegistered` — `p-button custom element is defined after workspace renders`
2. `TestFromAC_PDSCustomElementsRegistered` — `p-icon, p-tabs, and p-tabs-item are defined after workspace renders`
3. `TestFromAC_NoCDNCSPViolations` — `no securitypolicyviolation fires with blockedURI from cdn.ui.porsche.com`
4. `TestFromAC_NoCDNCSPViolations` — `no securitypolicyviolation fires with blockedURI from cdn.ui.porsche.cn`
5. `TestFromAC_PDSShadowRootActivation` — `p-button element has non-empty shadowRoot after page stabilizes`

### Lint/Test Snapshot
- Playwright exit code: 1
- ESLint on target spec: clean (exit code 0)
- Coverage: not applicable for Playwright run

### Dependency State
- Existing prerequisite remains unresolved: task #1510 is still in `research`.
- #1496 already depends on #1510.

### Evidence Summary
- AC-1 through AC-3 remain implemented from prior builder commit (`a615918d`).
- AC-4 executable gate remains red in current workspace state; task cannot be advanced to review.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | researcher | Complete #1510 so local PDS assets align with npm package runtime expectations and workspace render unblocks. | `serve/cockpit/web/public/porsche-design-system/**` | AC-4 scoped Playwright run for #1496 is 0/5 passing with workspace visibility timeouts. |
| 2 | builder | Re-run scoped AC-4 Playwright proof after #1510 is complete and only return DONE once the named spec passes. | `serve/cockpit/web/e2e/pds-runtime-csp.spec.ts` | Latest quality-runner evidence: 0 passed, 5 failed; eslint clean. |
2026-05-12T15:16:26+00:00
## Builder Notes

### Files Changed
- None

### Verification Status
- No new implementation work was possible this cycle.
- Existing builder implementation for AC-1..AC-3 remains in place from commit `a615918d`.
- AC-4 requires executable Playwright pass for `serve/cockpit/web/e2e/pds-runtime-csp.spec.ts`.

### Blocking Condition
- Task #1496 already depends on #1510.
- Dependency #1510 is still in `research` (not implemented), which keeps AC-4 gate structurally unreachable in current workspace state.

### Evidence Summary
- Verified current board state directly: #1510 status is `research`.
- Prior #1496 retries already produced repeated AC-4 executable failures (workspace never stabilizes for the required spec) while dependency remained unresolved.
- No additional source changes were made in this cycle.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | researcher | Complete and advance #1510 so local PDS assets align with runtime package expectations. | serve/cockpit/web/public/porsche-design-system/** | #1510 currently `research`; #1496 AC-4 depends on that prerequisite. |
| 2 | builder | Re-run scoped executable AC-4 proof immediately after #1510 lands; only advance #1496 when `serve/cockpit/web/e2e/pds-runtime-csp.spec.ts` passes. | serve/cockpit/web/e2e/pds-runtime-csp.spec.ts | Current cycle confirms prerequisite is still unresolved, so gate remains unreachable. |
2026-05-12T16:12:35+00:00
## Builder Notes

### Files Changed
- None

### Verification Run (AC-4 executable proof)
- quality-runner scoped run on `serve/cockpit/web/e2e/pds-runtime-csp.spec.ts`
- Result: 0 passed, 5 failed
- All failures timeout at 30s in `beforeEach` waiting for `[data-region="workspace"]` visibility.

### Failure Details
1. `TestFromAC_PDSCustomElementsRegistered` — `p-button custom element is defined after workspace renders`
2. `TestFromAC_PDSCustomElementsRegistered` — `p-icon, p-tabs, and p-tabs-item are defined after workspace renders`
3. `TestFromAC_NoCDNCSPViolations` — `no securitypolicyviolation fires with blockedURI from cdn.ui.porsche.com`
4. `TestFromAC_NoCDNCSPViolations` — `no securitypolicyviolation fires with blockedURI from cdn.ui.porsche.cn`
5. `TestFromAC_PDSShadowRootActivation` — `p-button element has non-empty shadowRoot after page stabilizes`

### Environment Evidence (dependency still unresolved)
- Installed PDS packages in lockfile: `@porsche-design-system/components-js@4.1.0`, `@porsche-design-system/components-react@4.1.0`
- Local public core asset still at v4.0.0: `public/porsche-design-system/components/porsche-design-system.v4.0.0.9faf55bc815263bee13d.js`
- Required v4.1.0 runtime chunk missing: `public/porsche-design-system/components/porsche-design-system.v4.1.0.59dc31ee9c99f5a43eb5.js` (not found)
- Icon inventory still incomplete: `ICON_SVG_COUNT=1`

### Lint/Test Snapshot
- Playwright exit code: 1
- ESLint on target spec: clean (exit code 0)
- Coverage: not applicable for Playwright run

### Evidence Summary
- AC-1 through AC-3 remain implemented from prior commit `a615918d`.
- AC-4 executable gate remains unreachable in current workspace state because dependency #1510 (PDS asset sync) is not implemented yet.

### Required Follow-up
1. Complete dependency #1510 (asset sync implementation) so public PDS assets match runtime package versions.
2. Re-run scoped executable AC-4 proof for #1496 (`serve/cockpit/web/e2e/pds-runtime-csp.spec.ts`) immediately after #1510 lands; advance only on real Playwright pass.
2026-05-12T16:38:37+00:00
## Builder Notes

### Files Changed
- None

### Verification Run (AC-4 executable proof)
- quality-runner scoped run on `serve/cockpit/web/e2e/pds-runtime-csp.spec.ts`
- Result: 0 passed, 5 failed
- Lint: clean

### Failure Details
All five Playwright tests timed out in `beforeEach` waiting for `[data-region="workspace"]` to be visible:
1. `p-button custom element is defined after workspace renders`
2. `p-icon, p-tabs, and p-tabs-item are defined after workspace renders`
3. `no securitypolicyviolation fires with blockedURI from cdn.ui.porsche.com`
4. `no securitypolicyviolation fires with blockedURI from cdn.ui.porsche.cn`
5. `DOM structure in shadowed p-button matches design token shape`

### Dependency Alignment
- Updated #1496 dependency from #1510 to #1511.
- Reason: #1510 is research complete; #1511 is the implementation task that actually syncs local PDS assets required for workspace render stability.

### Evidence Summary
- AC-1 through AC-3 remain implemented from prior commit `a615918d`.
- AC-4 executable gate remains red in current workspace state and is structurally unreachable until #1511 lands.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Implement and land task #1511 (PDS asset sync script + synced assets) so local runtime assets match installed PDS package version. | serve/cockpit/web/scripts/sync-pds-assets.mjs; serve/cockpit/web/public/porsche-design-system/** | #1496 scoped Playwright run remains 0/5 with workspace visibility timeouts. |
| 2 | builder | Re-run scoped AC-4 executable proof for #1496 and advance only when `serve/cockpit/web/e2e/pds-runtime-csp.spec.ts` passes. | serve/cockpit/web/e2e/pds-runtime-csp.spec.ts | Current quality-runner evidence: 0 passed, 5 failed; lint clean. |
2026-05-12T17:07:44+00:00
## Builder Notes

### Files Changed
- None

### Verification Run (AC-4 executable proof)
- quality-runner scoped run on `serve/cockpit/web/e2e/pds-runtime-csp.spec.ts`
- Retry with environment hint (`frontend — cd serve/cockpit/web before all commands`) executed fully
- Result: 0 passed, 5 failed
- All five tests time out in `beforeEach` at 30s waiting for `[data-region="workspace"]` visibility

### Failure Details
1. `p-button custom element is defined after workspace renders`
2. `p-icon, p-tabs, and p-tabs-item are defined after workspace renders`
3. `no securitypolicyviolation fires with blockedURI from cdn.ui.porsche.com`
4. `no securitypolicyviolation fires with blockedURI from cdn.ui.porsche.cn`
5. `p-button element has non-empty shadowRoot after page stabilizes`

### Environment/Dependency Evidence
- `@porsche-design-system/components-js` version: `^4.1.0`
- `serve/cockpit/web/public/porsche-design-system/components/` contains 59 JS files, but versioned core still `porsche-design-system.v4.0.0.9faf55bc815263bee13d.js`
- required v4.1.0 core chunk `porsche-design-system.v4.1.0.59dc31ee9c99f5a43eb5.js` does not exist
- `serve/cockpit/web/public/porsche-design-system/icons/` contains only 1 SVG file
- #1496 already depends on #1511; #1511 is currently `todo`

### Lint/Test Snapshot
- Playwright: failed (exit 1)
- ESLint on target spec: clean (exit 0)
- Coverage: N/A for Playwright

### Evidence Summary
- AC-1..AC-3 remain implemented from prior commit `a615918d`.
- AC-4 executable proof remains structurally unreachable in current workspace state until #1511 lands.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Complete #1511 (sync PDS local assets + script) so runtime assets align with installed v4.1.0 package. | serve/cockpit/web/scripts/sync-pds-assets.mjs; serve/cockpit/web/public/porsche-design-system/** | Missing v4.1.0 core chunk and icon inventory (1/290) keep workspace from rendering in E2E runtime. |
| 2 | builder | Re-run scoped AC-4 executable proof for #1496 (`serve/cockpit/web/e2e/pds-runtime-csp.spec.ts`) immediately after #1511 is complete; advance only on real Playwright pass. | serve/cockpit/web/e2e/pds-runtime-csp.spec.ts | Current run is 0/5 passing with workspace visibility timeouts. |
2026-05-12T17:42:31+00:00
## Builder Notes

### Files Changed
- None

### Verification Run (AC-4 executable proof)
- quality-runner scoped run on `serve/cockpit/web/e2e/pds-runtime-csp.spec.ts`
- Result: failed (`playwright: 1`, `eslint: 0`)
- Reported failure: `TestFromAC_PDSCustomElementsRegistered › p-button custom element is defined after workspace renders`
- Error: 30s timeout in `beforeEach` while waiting for `[data-region="workspace"]` visibility

### Dependency Evidence Snapshot
- `@porsche-design-system/components-js`: `^4.1.0`
- `public/porsche-design-system/components/*.js`: `59` files
- Missing required v4.1.0 core chunk:
  - `serve/cockpit/web/public/porsche-design-system/components/porsche-design-system.v4.1.0.59dc31ee9c99f5a43eb5.js` = not present
- Present core file is still v4.0.0:
  - `serve/cockpit/web/public/porsche-design-system/components/porsche-design-system.v4.0.0.9faf55bc815263bee13d.js`
- `public/porsche-design-system/icons/*.svg`: `1` file

### Evidence Summary
- AC-1..AC-3 remain implemented from prior builder commit `a615918d`.
- AC-4 executable gate remains red and structurally blocked by unresolved asset-sync dependency.
- Task already depends on #1511, which is the implementation path to align local PDS assets with installed runtime version.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Complete #1511 (sync PDS local assets script + output) so local runtime assets include the v4.1.0 core chunk and full icon set. | serve/cockpit/web/scripts/sync-pds-assets.mjs; serve/cockpit/web/public/porsche-design-system/** | #1496 AC-4 Playwright run times out before workspace render; v4.1.0 core chunk missing and icons count remains 1. |
| 2 | builder | Re-run scoped executable AC-4 proof for #1496 and advance only when `serve/cockpit/web/e2e/pds-runtime-csp.spec.ts` passes. | serve/cockpit/web/e2e/pds-runtime-csp.spec.ts | Current quality-runner evidence: Playwright failed, ESLint clean. |
2026-05-12T18:31:11+00:00
## Builder Notes

### Files Changed
- serve/cockpit/web/src/components/DetailTab.tsx
- serve/cockpit/web/src/components/TaskFieldsEditor.tsx
- serve/cockpit/web/src/hooks/useConflictDraft.ts

### Why these changes were required
- AC-4 requires executable proof from `serve/cockpit/web/e2e/pds-runtime-csp.spec.ts`.
- The Playwright webServer startup path (`npm run build && npm run preview`) was blocked by frontend type contract drift around nullable task body fields, preventing reliable AC-4 execution.
- Applied the minimal type-alignment fix so build succeeds and the named Playwright gate can run to completion.

### Fixes Applied
1. `DetailTab` task model now matches API nullability for `body`:
   - `body: string | null`
2. `TaskFieldsEditor` now normalizes nullable `task.body` into local string edit state:
   - initialize/reset body via `task.body ?? ''`
   - dirty-check compares against `(task.body ?? '')`
3. `useConflictDraft` remote task model now matches nullable body shape:
   - `ConflictRemoteTask.body: string | null`

### Verification (quality-runner)
- Scoped AC-4 executable proof:
  - test path: `serve/cockpit/web/e2e/pds-runtime-csp.spec.ts`
  - result: **5 passed, 0 failed**
  - playwright exit code: **0**
- Scoped lint:
  - paths:
    - `serve/cockpit/web/src/components/DetailTab.tsx`
    - `serve/cockpit/web/src/components/TaskFieldsEditor.tsx`
    - `serve/cockpit/web/src/hooks/useConflictDraft.ts`
    - `serve/cockpit/web/e2e/pds-runtime-csp.spec.ts`
  - result: **clean** (`eslint: 0`)

### AC Evidence Summary
- AC-1/AC-2/AC-3: remain satisfied by prior implementation commit `a615918d` (`main.tsx` trap migration).
- AC-4: now satisfied with executable proof — named Playwright spec passes unmodified.

### Commit
- `821df8cf` — fix: align nullable task body types for e2e build gate (#1496, builder)
- Shortstat: 3 files changed, 5 insertions(+), 5 deletions(-)
2026-05-12T21:05:20+00:00
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1496 -> docs | AC mapped to code and evidence sufficient.
- AC evidence:

| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC-1 | [serve/cockpit/web/src/main.tsx](serve/cockpit/web/src/main.tsx#L9-L47) contains the trap-based bootstrap path only; legacy rewrite identifiers are absent on file inspection. | [serve/cockpit/web/src/__tests__/main_pds_trap_1496.test.ts](serve/cockpit/web/src/__tests__/main_pds_trap_1496.test.ts#L66-L78) passed in the scoped reviewer rerun. | PASS |
| AC-2 | [serve/cockpit/web/src/main.tsx](serve/cockpit/web/src/main.tsx#L14-L37) defines the `cdn` accessor and installs it before `load()`. | [serve/cockpit/web/src/__tests__/main_pds_trap_1496.test.ts](serve/cockpit/web/src/__tests__/main_pds_trap_1496.test.ts#L132), [serve/cockpit/web/src/__tests__/main_pds_trap_1496.test.ts](serve/cockpit/web/src/__tests__/main_pds_trap_1496.test.ts#L161), and [serve/cockpit/web/src/__tests__/main_pds_trap_1496.test.ts](serve/cockpit/web/src/__tests__/main_pds_trap_1496.test.ts#L190) passed in the scoped reviewer rerun. | PASS |
| AC-3 | [serve/cockpit/web/src/main.tsx](serve/cockpit/web/src/main.tsx#L34-L47) bootstraps directly from trap install to `load()` to element wait to render, with no post-bootstrap namespace reassignment block remaining. | [serve/cockpit/web/src/__tests__/main_pds_trap_1496.test.ts](serve/cockpit/web/src/__tests__/main_pds_trap_1496.test.ts#L100) passed in the scoped reviewer rerun. | PASS |
| AC-4 | [serve/cockpit/web/e2e/pds-runtime-csp.spec.ts](serve/cockpit/web/e2e/pds-runtime-csp.spec.ts#L95), [serve/cockpit/web/e2e/pds-runtime-csp.spec.ts](serve/cockpit/web/e2e/pds-runtime-csp.spec.ts#L101), [serve/cockpit/web/e2e/pds-runtime-csp.spec.ts](serve/cockpit/web/e2e/pds-runtime-csp.spec.ts#L134), [serve/cockpit/web/e2e/pds-runtime-csp.spec.ts](serve/cockpit/web/e2e/pds-runtime-csp.spec.ts#L148), and [serve/cockpit/web/e2e/pds-runtime-csp.spec.ts](serve/cockpit/web/e2e/pds-runtime-csp.spec.ts#L174) remain the real executable assertions; the task guard still checks the spec stays intact at [serve/cockpit/web/src/__tests__/main_pds_trap_1496.test.ts](serve/cockpit/web/src/__tests__/main_pds_trap_1496.test.ts#L221), [serve/cockpit/web/src/__tests__/main_pds_trap_1496.test.ts](serve/cockpit/web/src/__tests__/main_pds_trap_1496.test.ts#L228), and [serve/cockpit/web/src/__tests__/main_pds_trap_1496.test.ts](serve/cockpit/web/src/__tests__/main_pds_trap_1496.test.ts#L233). | Builder quality-runner evidence for the named Playwright gate is 5 passed, 0 failed, eslint clean on serve/cockpit/web/e2e/pds-runtime-csp.spec.ts. | PASS |

- Collateral-file proof: reviewer quality-runner rerun on [serve/cockpit/web/src/__tests__/main_pds_trap_1496.test.ts](serve/cockpit/web/src/__tests__/main_pds_trap_1496.test.ts), [serve/cockpit/web/src/__tests__/DetailTab.edit-payload.test.tsx](serve/cockpit/web/src/__tests__/DetailTab.edit-payload.test.tsx), [serve/cockpit/web/src/__tests__/DetailTab.conflict-resolution.test.tsx](serve/cockpit/web/src/__tests__/DetailTab.conflict-resolution.test.tsx), [serve/cockpit/web/src/__tests__/DetailTab.body-preview-toggle.1508.test.tsx](serve/cockpit/web/src/__tests__/DetailTab.body-preview-toggle.1508.test.tsx), and [serve/cockpit/web/src/__tests__/tasks_1501.test.ts](serve/cockpit/web/src/__tests__/tasks_1501.test.ts) reported 130 passed, 0 failed, lint clean. Coverage for the touched proof surface: [serve/cockpit/web/src/main.tsx](serve/cockpit/web/src/main.tsx) 100%, [serve/cockpit/web/src/components/DetailTab.tsx](serve/cockpit/web/src/components/DetailTab.tsx) 84.21%, [serve/cockpit/web/src/components/TaskFieldsEditor.tsx](serve/cockpit/web/src/components/TaskFieldsEditor.tsx) 92.25%, [serve/cockpit/web/src/hooks/useConflictDraft.ts](serve/cockpit/web/src/hooks/useConflictDraft.ts) 97.29%, [serve/cockpit/web/src/api/tasks.ts](serve/cockpit/web/src/api/tasks.ts) 100%.
- Nullable-body alignment is consistent with the existing read/edit contract: [serve/cockpit/web/src/api/tasks.ts](serve/cockpit/web/src/api/tasks.ts#L7-L15) and [serve/cockpit/web/src/api/tasks.ts](serve/cockpit/web/src/api/tasks.ts#L29-L37) already allow `body: string | null`; backend mutation semantics keep `body: null` as no-op in [serve/cockpit/src/owlbear_cockpit/routes/mutation.py](serve/cockpit/src/owlbear_cockpit/routes/mutation.py#L53) and [serve/cockpit/src/owlbear_cockpit/routes/mutation.py](serve/cockpit/src/owlbear_cockpit/routes/mutation.py#L187); the UI only normalizes null at the local edit/conflict boundary in [serve/cockpit/web/src/components/DetailTab.tsx](serve/cockpit/web/src/components/DetailTab.tsx#L15-L23), [serve/cockpit/web/src/components/TaskFieldsEditor.tsx](serve/cockpit/web/src/components/TaskFieldsEditor.tsx#L109-L140), and [serve/cockpit/web/src/hooks/useConflictDraft.ts](serve/cockpit/web/src/hooks/useConflictDraft.ts#L10-L16).

## Observations
- Challenger cross-check returned proceed; no blocking contradiction surfaced between the final Playwright proof and the current repo state.
- I could not perform the path-scoped dirty-tree contamination check from reviewer Step 1 because git/terminal tools are not available in this tool surface.
2026-05-12T21:13:43+00:00
## Docs Gate

### Checklist

**Item 1: README Verification**
- Convention mapping: `serve/cockpit/web/src/**` → `serve/cockpit/README.md`
- Changed files: `main.tsx` (PDS CDN property trap), `DetailTab.tsx`, `TaskFieldsEditor.tsx`, `useConflictDraft.ts` (nullable body alignment)
- Layer 1 grep: no documentation references to `installPdsRuntimeScriptRewrite`, `PDS_CDN_SCRIPT`, `installPdsCdnTrap`, or `appendChild` monkeypatch found in any `.md` file. No orphaned symbols.
- Layer 2 editorial: Full README read confirmed accurate. The PDS boot-time interception is an internal implementation detail not documented at README level. The nullable `body` type alignment is a UI-internal normalization consistent with the already-documented API contract ("tri-state field semantics: `body: null`/omitted = no change"). No README updates required.
- Verdict: **no docs impact** — implementation-level internal changes only.

**Item 2: External Attribution**
- Research doc lists 3 external sources: PDS GitHub issue #2701, MDN Object.defineProperty, MDN Reflect.set.
- All three present in `.owlbear/sources/overview.md` under "## PDS Property Trap Validation (Task #1496)" (lines 68-74). ✓

**Item 3: Research Doc**
- Research doc `.owlbear/research/1496-pds-property-trap.md` exists and is linked from task body. ✓

**Item 4: Deletion Detection**
- No source files were deleted. `main.tsx` was edited in place; collateral files were type-contract fixes, not removals. N/A — no deletion impact.

### Files Updated
- None (no docs impact)

### Scratch Cleanup
- Deleted: `serve/.owlbear/scratch/1496-coverage.txt`, `serve/.owlbear/scratch/1496-vitest-output.txt`, `serve/.owlbear/scratch/1496-eslint-output.txt`
2026-05-12T21:32:45+00:00
## Audit\n### Regression Detection\n- quality-runner mode full: 2127 passed, 88 failed, lint clean\n- All 88 failures are pre-existing background test debt (test_cockpit_view.py FileNotFoundError, test_engine_accessor_migration.py accessor patterns, test_server.py NoneType, test_ideation_diagram.py bridge elements) — all Python tests in kanban/server/ideation domains\n- #1496 changed only cockpit frontend TypeScript files; no mechanism for TS changes to cause Python test failures\n- Baseline comparison: prior full run (1511 audit) showed 201 failures in the same categories\n- regression verdict: PASS\n\n### Intent Verification\n- scope alignment: PASS (all changes in serve/cockpit/web/src/ — main.tsx, DetailTab.tsx, TaskFieldsEditor.tsx, useConflictDraft.ts)\n- purpose match: PASS (replaced Element.prototype.appendChild monkeypatch with Object.defineProperty trap on document.porscheDesignSystem.cdn; collateral nullable body type fix enabled E2E build gate)\n- extraneous scope: none — type alignment fix is minimal and directly required for AC-4 proof\n- boundary check: function-level behavior verification deferred to reviewer\n\n### Architect Quality: 4/5\n- AC-1..AC-3 specific: named concrete function, regex, mechanism, timing, line references\n- AC-4 clear regression gate on named E2E spec\n- Minor gap: AC didn't anticipate pre-existing environment blocker (#1510/#1511) that delayed AC-4 proof, but this is a pre-existing condition not an AC quality issue\n- Challenger engagement at both research and arch-review stages with documented rebuttals\n\n### Commit Integrity\n- upstream commit presence: PASS\n  - 347b1a4e docs: research (#1496, researcher)\n  - 85a42972 test: TDD RED tests (#1496, test-writer)\n  - a615918d feat: replace PDS monkeypatch with cdn property trap (#1496, builder)\n  - 821df8cf fix: align nullable task body types for e2e build gate (#1496, builder)\n- kanban commit packaging: pending (this step)\n\n### Deduction Breakdown\n- No deductions applied\n- Regression: no task-caused regressions (pre-existing background debt)\n- Intent: all changes in cockpit frontend domain, matching stated purpose\n- Lint: clean\n- AC quality: 4/5 (threshold for deduction is ≤3)\n- Reviewer evidence: detailed PASS verdict with AC mapping and collateral coverage\n\n### Confidence: 1.00\n### Action: archive