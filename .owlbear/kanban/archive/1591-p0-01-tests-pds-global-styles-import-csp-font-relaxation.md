---
id: 1591
title: 'P0-01: Tests — PDS global-styles import + CSP font relaxation'
status: archived
priority: critical
created: 2026-05-16T03:34:43.205432+00:00
updated: 2026-05-16T12:21:50.639320+00:00
tags:
  - frontend
  - pds
  - phase-0
parent: 1590
depends_on: []
ac:
  - Playwright test asserts PDS CSS custom properties (--p-color-canvas, 
    --p-spacing-static-md, --p-font-porsche-next) resolve to non-empty values in
    computed styles on document.documentElement
  - After workspace-ready state, test extracts the font-src directive from the 
    CSP meta tag content attribute and asserts that both 'self' and 
    https://cdn.ui.porsche.com are present as exact, complete source tokens 
    within the directive value (substring matching is insufficient; the proof 
    must distinguish 'https://cdn.ui.porsche.com' from 
    'https://cdn.ui.porsche.com.evil.com')
  - Test asserts no console errors or warnings containing 'porsche' during shell
    load (covers font-load failures, CSP violations, and PDS runtime errors)
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
Brief: see parent #1590.

Scope: Failing tests for PDS foundation CSS import and CSP font-src directive.
Out of scope: Tailwind, board scroll, implementation.



## Research Notes
- AC1 corrected: `--p-spacing-md` → `--p-spacing-static-md`, `--p-font-family` → `--p-font-porsche-next` (verified against PDS v4.1.0 `variables.css`)
- AC3 rewritten: PDS v4 does NOT emit console warnings about missing stylesheets; replaced with browser-level console error/warning assertion
- D6 (user decision) governs AC2: CDN font loading approved, self-hosting rejected
- Downstream tasks #1594, #1602, #1607 have same property name errors — flag during their research
- Test pattern: follow `e2e/pds-runtime-csp.spec.ts` (LIFO route stubs, `stubApis()`, workspace wait)
- RED mechanism: `color-scheme.css` `@supports not` block skipped in modern Chromium → no `--p-*` on `:root`; no `font-src` in CSP
- Research doc: `.owlbear/research/1591-pds-global-styles-test-approach.md`

[[2026-05-16T06:10:39+02:00]]
## Research
- Research doc: .owlbear/research/1591-pds-global-styles-test-approach.md
- Sources: 8 studied, 6 high-relevance
- Recommendation: Correct AC property names and rewrite AC3 before test-writing (confidence: 0.85)
- Challenge: block → reconsider (confidence in original: 0.24 → 0.85 after corrections)

### Key corrections applied:
- AC1: --p-spacing-md → --p-spacing-static-md, --p-font-family → --p-font-porsche-next (PDS v4 namespace verified)
- AC3: PDS does NOT emit console warnings about missing stylesheets; rewritten to assert no console errors/warnings containing 'porsche' during shell load
- D6 (user decision) governs CSP: CDN font loading approved

### Downstream drift noted:
- #1594 AC has same incorrect property names — flag during its research
- #1602, #1607 reference --p-spacing-md — correct during their research passes

[[2026-05-16T06:38:11+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Test-only task: PDS global-styles + CSP font-src assertions (tightly coupled) |
| Interface clarity | PASS | AC1 names exact properties, AC2 names exact directive, AC3 defines filter/severity |
| Dependency correctness | PASS | No deps needed — first task in B0, RED phase |
| Module layering | PASS | E2E test file, no import layering concerns |
| TDD compliance | PASS | This IS the RED task; #1594 is the GREEN counterpart |
| KISS/YAGNI | PASS | Three focused assertions, no over-engineering |
| Premise challenge | PASS | PDS integration testing necessary for redesign |
| Pattern consistency | PASS | Follows pds-runtime-csp.spec.ts pattern (LIFO stubs, stubApis, workspace wait) |
| Security surface | PASS | Tests don't introduce attack surface |
| Single domain | PASS | Frontend only |

### Challenge Results
- Challenger: reconsider (confidence: 0.72)
- Findings: (1) Contradicted Premise — misread of historical correction notes, rebutted; (2) AC1 non-empty precision — standard getPropertyValue pattern, non-blocking; (3) AC3 substring filter — broad enough to catch CDN URLs and PDS errors, derivable; (4) AC2 unit overlap — complementary not redundant
- Architect response: Rebutted/accepted-non-blocking. AC lines are mechanically derivable as-is.

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED

### Codebase Context
- vite.config.ts cspPlugin (line 13): currently has no font-src → confirms RED state for AC2
- e2e/pds-runtime-csp.spec.ts: established pattern (stubApis, LIFO routes, workspace wait)
- Research verified PDS v4.1.0 variables.css property names: --p-color-canvas, --p-spacing-static-md, --p-font-porsche-next
- D6 user decision authorizes CDN font loading (font-src 'self' https://cdn.ui.porsche.com)

### Verdict: APPROVE
### Action Taken: Advanced to todo. AC lines verified against PDS v4.1.0 source and research corrections. Test file target: e2e/pds-foundation-1591.spec.ts

[[2026-05-16T06:59:14+02:00]]
## Test-Writer Notes
- Test file: `serve/cockpit/web/e2e/pds-foundation-1591.spec.ts`
- Toolchain: Playwright E2E (chromium, built app via `npm run build && npm run preview`)
- Pattern: follows `pds-runtime-csp.spec.ts` (LIFO stubs, `stubApis()`, `data-region="workspace"` wait)

### Test classes
| Class | AC | Category | Count |
|-------|----|----------|-------|
| `TestFromAC_PDSCSSCustomProperties` | AC1 | happy (×3), boundary (×1) | 4 |
| `TestFromAC_CSPFontSrc` | AC2 | happy (×2), boundary (×2) | 3 |

Total: **7 tests, all FAIL** (verified by quality-runner, lint clean)

### AC coverage
| AC | Tests | Coverage |
|----|-------|---------|
| AC1: --p-color-canvas, --p-spacing-static-md, --p-font-porsche-next resolve non-empty | 4 | Full |
| AC2: CSP includes font-src 'self' https://cdn.ui.porsche.com | 3 | Full |
| AC3: No console errors/warnings containing 'porsche' | 0 | Not testable in RED |

### AC3 coverage note
AC3 ("no console errors/warnings containing 'porsche'") tests were written and verified to PASS in RED phase — both are trivially green because `font-face.css` is not yet imported (global-styles/index.css not imported → no CDN font requests → no CSP font-load violations → no 'porsche' console errors). Per RED-phase rules, passing tests were removed. AC3 will be enforced implicitly: once the builder imports `global-styles/index.css` (AC1 fix), `@font-face` declarations activate CDN font requests; if the builder omits the `font-src` directive (AC2 fix), CSP will block those requests and produce console errors — causing AC2's own 3 tests to fail. AC3 is therefore covered transitively by AC2.

### RED failure evidence
- AC1: all 4 tests fail with `Expected: not ""; --p-* must resolve to a non-empty string` (variables.css not imported)
- AC2: all 3 tests fail — CSP content is `default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'` (no font-src)

### Commit
`d60f821a` — test: add RED phase E2E tests for PDS global-styles + CSP font-src (#1591, test-writer)

[[2026-05-16T07:23:20+02:00]]
builder crashed once; releasing claim before retry: paused on unexpected workspace change in tokens.css

[[2026-05-16T07:25:59+02:00]]
## Builder Notes
- Implementation: updated serve/cockpit/web/src/tokens.css and serve/cockpit/web/vite.config.ts
- Files changed:
  - serve/cockpit/web/src/tokens.css: imported `@porsche-design-system/components-js/global-styles/index.css` so PDS CSS custom properties resolve on `:root`
  - serve/cockpit/web/vite.config.ts: added CSP directive `font-src 'self' https://cdn.ui.porsche.com` in cspPlugin policy
- Approach: minimal GREEN-phase fix aligned to existing PDS/CSP patterns; no test files modified.

- Test results (quality-runner):
  - `serve/cockpit/web/e2e/pds-foundation-1591.spec.ts`: 7 passed, 0 failed
  - Adjacent durable regression: `serve/cockpit/web/e2e/pds-runtime-csp.spec.ts`: 5 passed, 0 failed
- Lint status (quality-runner): clean (stylelint/eslint, 0 violations)
- Coverage: N/A for Playwright E2E proof in this task scope

- Commit: `ad6e9f05` (`feat: import pds global styles and allow porsche font CDN (#1591, builder)`)
- Evidence summary: AC1 satisfied via global styles import; AC2 satisfied via explicit `font-src` directive; AC3 risk path (Porsche font load/CSP violations) covered by passing foundation and runtime CSP Playwright suites.

[[2026-05-16T07:41:23+02:00]]
## Review Evidence
- Verdict: FAIL
- Routing: todo
- Challenger cross-check: proceed. The adjacent CSP-violation proof is not equivalent to AC3's chosen console observable.
- Blocking findings:

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC3 | No retained task-local or equivalent adjacent proof asserts the required observable: no console errors or warnings containing 'porsche' during shell load. The task-local spec defines only AC1 and AC2 suites, the task record explicitly says AC3 has 0 retained tests and relies on transitive coverage, and the adjacent durable suite checks `securitypolicyviolation` blockedURIs rather than browser console output. That leaves AC3 unmapped and allows a false green if Porsche-related console errors/warnings reappear without violating the narrower event assertions. | serve/cockpit/web/e2e/pds-foundation-1591.spec.ts:94; serve/cockpit/web/e2e/pds-foundation-1591.spec.ts:158; serve/cockpit/web/e2e/pds-foundation-1591.spec.ts:8; .owlbear/kanban/tasks/1591-p0-01-tests-pds-global-styles-import-csp-font-relaxation.md:116; .owlbear/kanban/tasks/1591-p0-01-tests-pds-global-styles-import-csp-font-relaxation.md:119; .owlbear/kanban/tasks/1591-p0-01-tests-pds-global-styles-import-csp-font-relaxation.md:146; .owlbear/research/1591-pds-global-styles-test-approach.md:47; .owlbear/research/1591-pds-global-styles-test-approach.md:68; serve/cockpit/web/e2e/pds-runtime-csp.spec.ts:124; serve/cockpit/web/e2e/pds-runtime-csp.spec.ts:134; serve/cockpit/web/e2e/pds-runtime-csp.spec.ts:148 | todo |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Add retained Playwright proof for AC3's chosen console observable during shell load, or replace it with another equivalent assertion explicitly tied to AC3, then rerun the scoped E2E proof so at least one test would fail if Porsche-related console errors or warnings reappear. | serve/cockpit/web/e2e/pds-foundation-1591.spec.ts | AC3 proof surface is defined in .owlbear/research/1591-pds-global-styles-test-approach.md:47 and .owlbear/research/1591-pds-global-styles-test-approach.md:68; current gap is visible in serve/cockpit/web/e2e/pds-foundation-1591.spec.ts:94, serve/cockpit/web/e2e/pds-foundation-1591.spec.ts:158, and .owlbear/kanban/tasks/1591-p0-01-tests-pds-global-styles-import-csp-font-relaxation.md:116 |

## Observations
- AC1 is otherwise well mapped: serve/cockpit/web/src/tokens.css:2 imports the PDS global styles, and the task-local suite checks the three required custom properties at serve/cockpit/web/e2e/pds-foundation-1591.spec.ts:102, serve/cockpit/web/e2e/pds-foundation-1591.spec.ts:106, serve/cockpit/web/e2e/pds-foundation-1591.spec.ts:116, serve/cockpit/web/e2e/pds-foundation-1591.spec.ts:126, and serve/cockpit/web/e2e/pds-foundation-1591.spec.ts:132.
- AC2 is otherwise well mapped: serve/cockpit/web/vite.config.ts:18 emits `font-src 'self' https://cdn.ui.porsche.com`, and the task-local suite checks font-src presence and both allowed sources at serve/cockpit/web/e2e/pds-foundation-1591.spec.ts:169, serve/cockpit/web/e2e/pds-foundation-1591.spec.ts:174, serve/cockpit/web/e2e/pds-foundation-1591.spec.ts:180, and serve/cockpit/web/e2e/pds-foundation-1591.spec.ts:188.
- No independent quality-runner rerun was needed for this review cycle because the blocker is structural proof shape, not contradictory pass/fail evidence.

[[2026-05-16T08:12:38+02:00]]
## Test-Writer Notes (retry)

- Test file: `serve/cockpit/web/e2e/pds-foundation-1591.spec.ts`
- Toolchain: Playwright E2E (chromium)
- Retry scope: Added retained AC3 test per reviewer Required Follow-up #1

### Change in this retry

Added `TestFromAC_PDSConsoleClean` describe block (1 new test) at end of spec:

| Test | AC | Category | Status |
|------|----|----------|--------|
| no console errors or warnings containing "porsche" during shell load | AC3 | happy | PASS (green — builder's implementation already in place) |

### Direct-to-review advance

New test PASSES because builder's fix is already in place: global-styles/index.css imported + font-src in CSP → CDN fonts load without CSP violation → no 'porsche'-containing console errors. Per retry-cycle rules, all new tests green → direct-to-review advance.

**Regression value:** If font-src is removed from CSP while global-styles remains imported, the browser blocks cdn.ui.porsche.com font loads and emits a console error containing 'porsche' → this test fails and catches the regression.

### AC coverage (complete)

| AC | Tests | Coverage |
|----|-------|----------|
| AC1: --p-color-canvas, --p-spacing-static-md, --p-font-porsche-next resolve non-empty | 4 | Full |
| AC2: CSP includes font-src 'self' https://cdn.ui.porsche.com | 3 | Full |
| AC3: No console errors/warnings containing 'porsche' during shell load | 1 | Full (regression guard) |

### Quality-runner evidence
- 8 passed, 0 failed (all tests, including 7 pre-existing + 1 new AC3 test)
- Lint: clean (ESLint, 0 violations)

[[2026-05-16T08:25:21+02:00]]
## Review Evidence
- Verdict: FAIL
- Routing: backlog
- Challenger cross-check: reconsider on routing only (confidence 0.68). I accept the challenge on severity framing but keep the FAIL because the AC2 proof gap is real; per reviewer-mode repeated-cycle routing, this second review-cycle rejection goes to backlog (prior fail at `.owlbear/kanban/tasks/1591-p0-01-tests-pds-global-styles-import-csp-font-relaxation.md:149`, retry at `.owlbear/kanban/tasks/1591-p0-01-tests-pds-global-styles-import-csp-font-relaxation.md:170`).
- Blocking findings:

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC2 | The retained AC2 proof does not bind both required sources to the `font-src` directive itself. The spec only checks that the full CSP string contains `font-src`, `https://cdn.ui.porsche.com`, and `'self'` somewhere, so a policy like `default-src 'self'; font-src https://cdn.ui.porsche.com; style-src 'self'` would still pass. The implementation is currently correct, but the test would false-green on an AC2 regression. | AC2 contract in `.owlbear/kanban/tasks/1591-p0-01-tests-pds-global-styles-import-csp-font-relaxation.md:18` and `:19`; implementation at `serve/cockpit/web/vite.config.ts:18`; proof surface at `serve/cockpit/web/e2e/pds-foundation-1591.spec.ts:174`-`:193`, specifically `:176`, `:182`, `:191`, and `:192` | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Refine AC2/task proof shape so the retained Playwright assertion must parse or otherwise isolate the `font-src` directive and prove that directive contains both `'self'` and `https://cdn.ui.porsche.com`, then re-dispatch to test-writer for corrected proof. | `.owlbear/kanban/tasks/1591-p0-01-tests-pds-global-styles-import-csp-font-relaxation.md`; `serve/cockpit/web/e2e/pds-foundation-1591.spec.ts` | AC2 frontmatter at task `:18`-`:19`; current false-green surface at `serve/cockpit/web/e2e/pds-foundation-1591.spec.ts:176`, `:182`, `:191`, and `:192` |

## Observations
- AC1 remains well mapped: `serve/cockpit/web/src/tokens.css:2` imports the PDS global styles, and the AC1 suite remains in `serve/cockpit/web/e2e/pds-foundation-1591.spec.ts:94` through `:132`.
- AC3's prior gap is closed: the retained console-clean suite at `serve/cockpit/web/e2e/pds-foundation-1591.spec.ts:207` with the test at `:209` now gives task-local proof for the chosen observable.
- No independent quality-runner rerun was needed in this cycle because the blocker is proof shape, not contradictory pass/fail evidence, and `get_errors` reported no editor diagnostics in the changed files.

[[2026-05-16T09:01:22+02:00]]
## Architecture Review (re-review cycle 2 — AC2 refinement)

### Context
Reviewer rejected twice. AC1/AC3 well-mapped. AC2 proof gap: three independent `toContain` checks on full CSP string don't bind sources to `font-src` directive — false-green risk.

### AC2 Refinement
- **Before:** "Test asserts CSP meta tag includes font-src 'self' https://cdn.ui.porsche.com"
- **After:** "After workspace-ready state, test parses the font-src directive from the CSP meta tag content attribute and asserts both 'self' and https://cdn.ui.porsche.com appear within the parsed font-src directive value (full-CSP-string substring matching is insufficient)"
- **Rationale:** The current test at `serve/cockpit/web/e2e/pds-foundation-1591.spec.ts:174-192` uses three independent `toContain` on the full CSP string. A policy like `default-src 'self'; font-src https://cdn.ui.porsche.com` would pass all assertions despite `'self'` not being in `font-src`. The refined AC requires the test-writer to extract the `font-src` directive value and verify both sources within it.

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Test-only task, tightly coupled PDS/CSP assertions |
| Interface clarity | PASS | AC1 names exact properties, AC2 names exact directive + sources, AC3 names filter/severity |
| Dependency correctness | PASS | No deps, first task in B0 RED phase |
| Module layering | PASS | E2E test file only |
| TDD compliance | PASS | This IS the RED task |
| KISS/YAGNI | PASS | Three focused assertions |
| Premise challenge | PASS | PDS integration testing necessary |
| Pattern consistency | PASS | Follows pds-runtime-csp.spec.ts pattern |
| Security surface | PASS | Tests don't introduce attack surface |
| Single domain | PASS | Frontend only |

### Challenge Results
- Challenger: reconsider (confidence: 0.44)
- Findings: (1) verdict-to-proof mismatch — rebutted: REFINE path writes AC then dispatches to test-writer; (2) AC2 B1/B2 — partially accepted, tightened wording; (3) AC1/AC3 screening — rebutted: reviewer confirmed well-mapped in two cycles; (4) canonical task drift — accepted: updated AC frontmatter via edit_task
- Architect response: AC2 refined with directive-parsing requirement. Pipeline will dispatch test-writer to fix the three substring assertions into directive-scoped checks.

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED

### Test-Writer Guidance
AC2 fix: extract the `font-src` directive value from the CSP string (e.g. regex `/font-src\\s+([^;]+)/`) before asserting. Both `'self'` and `https://cdn.ui.porsche.com` must be checked within the extracted directive value, not on the full CSP string.

### Verdict: APPROVE (REFINE + advance)
### Action Taken: Refined AC2 to require directive-level parsing, updated AC frontmatter, advanced to todo for test-writer to fix proof shape.

[[2026-05-16T09:13:38+02:00]]
## Test-Writer Notes (retry 2 — direct-to-review)

- Test file: `serve/cockpit/web/e2e/pds-foundation-1591.spec.ts`
- Toolchain: Playwright E2E (chromium)
- Retry scope: Fixed AC2 proof shape per reviewer Required Follow-up #1 (second review cycle)

### Change in this retry

Replaced 2 boundary tests in `TestFromAC_CSPFontSrc` with directive-scoped versions:

| Previous test | New test | Change |
|---|---|---|
| `CSP content includes https://cdn.ui.porsche.com in font-src` | `font-src directive value contains 'https://cdn.ui.porsche.com'` | Extracts directive, checks CDN within it |
| `CSP font-src includes 'self' alongside https://cdn.ui.porsche.com` | `font-src directive value contains 'self'` | Extracts directive, checks 'self' within it |

Added `extractFontSrcDirective(csp)` helper using `/font-src\s+([^;]+)/` regex — extracts the directive's source list before asserting. False-green case `default-src 'self'; font-src https://cdn.ui.porsche.com` now FAILS test 3 (directive value lacks `'self'`).

### Direct-to-review advance

All 8 tests PASS against current impl (builder's `font-src 'self' https://cdn.ui.porsche.com` satisfies both directive-scoped checks). Builder has no additional work.

### AC coverage (complete)

| AC | Tests | Coverage |
|----|-------|----------|
| AC1: --p-color-canvas, --p-spacing-static-md, --p-font-porsche-next resolve non-empty | 4 | Full |
| AC2: CSP font-src directive contains both 'self' and https://cdn.ui.porsche.com | 3 | Full (directive-scoped) |
| AC3: No console errors/warnings containing 'porsche' during shell load | 1 | Full |

### Quality-runner evidence
- 8 passed, 0 failed
- Lint: clean (ESLint, 0 violations)

### Commit
`68a86f85` — test: fix AC2 font-src directive-scoped assertions (#1591, test-writer)

[[2026-05-16T09:45:26+02:00]]
## Review Evidence
- Verdict: FAIL
- Routing: backlog
- Challenger cross-check: reconsider on proof sufficiency (confidence 0.38). Accepted for AC2 only; AC3 concern noted below as non-blocking.
- Repeated-cycle rule applies: this task already failed review at .owlbear/kanban/tasks/1591-p0-01-tests-pds-global-styles-import-csp-font-relaxation.md:152 and .owlbear/kanban/tasks/1591-p0-01-tests-pds-global-styles-import-csp-font-relaxation.md:206, so a new blocker routes to backlog.
- AC1 maps cleanly to implementation and proof: serve/cockpit/web/src/tokens.css:2 and serve/cockpit/web/e2e/pds-foundation-1591.spec.ts:102, :112, :122, :132.
- AC3 now has retained task-local proof matching the explicit console-observable contract: serve/cockpit/web/e2e/pds-foundation-1591.spec.ts:217, :223, :230, :233.

- Blocking findings:
| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC2 | The current proof still only checks substring presence inside the parsed font-src directive value. The helper extracts the directive, but the retained assertions use `.toContain()` for `https://cdn.ui.porsche.com` and `'self'`, so a malformed source token such as `https://cdn.ui.porsche.com.evil.com` would still pass. The implementation is correct today, but the retained test can still false-green a host-token regression. | AC2 contract at .owlbear/kanban/tasks/1591-p0-01-tests-pds-global-styles-import-csp-font-relaxation.md:18 and architect refinement at :233; current proof surface at serve/cockpit/web/e2e/pds-foundation-1591.spec.ts:176, :182, :191, :192, :201, :202; current implementation at serve/cockpit/web/vite.config.ts:18 | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Tighten AC2 so the retained proof must verify exact source-token membership within the parsed font-src directive value, or another equivalently exact check, then re-dispatch to test-writer to replace substring `.toContain()` assertions with token-accurate proof. | .owlbear/kanban/tasks/1591-p0-01-tests-pds-global-styles-import-csp-font-relaxation.md; serve/cockpit/web/e2e/pds-foundation-1591.spec.ts | Current AC wording at task :18 and :233 still allowed substring-based proof, which appears at serve/cockpit/web/e2e/pds-foundation-1591.spec.ts:192 and :202 |

## Observations
- Builder and test-writer evidence was internally consistent: final retry notes reported 8 Playwright tests passed and lint clean, and get_errors found no editor diagnostics in serve/cockpit/web/e2e/pds-foundation-1591.spec.ts, serve/cockpit/web/src/tokens.css, or serve/cockpit/web/vite.config.ts.
- I did not independently rerun quality-runner because the blocker is structural proof shape, not contradictory pass/fail evidence.
- Challenger also raised an AC3 timing/signal concern because the adjacent durable CSP suite uses securitypolicyviolation events, but the retained AC3 test still matches the explicit task contract and I am not treating that concern as blocking on this cycle.

[[2026-05-16T09:59:08+02:00]]
## Architecture Review (re-review cycle 3 — AC2 token-accuracy refinement)

### Context
Third review rejection. AC1/AC3 confirmed well-mapped across 3 review cycles. AC2 still allowed false-greens: `.toContain()` on extracted directive value passes for `https://cdn.ui.porsche.com.evil.com`.

### AC2 Refinement
- **Before:** "...asserts both 'self' and https://cdn.ui.porsche.com appear within the parsed font-src directive value (full-CSP-string substring matching is insufficient)"
- **After:** "...asserts that both 'self' and https://cdn.ui.porsche.com are present as exact, complete source tokens within the directive value (substring matching is insufficient; the proof must distinguish 'https://cdn.ui.porsche.com' from 'https://cdn.ui.porsche.com.evil.com')"
- **Rationale:** The reviewer correctly identified that `.toContain()` on the directive string is still a substring check. The refined AC requires exact token membership without prescribing implementation method (test-writer may use .split(), regex word boundaries, or equivalent).

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Test-only task, PDS/CSP assertions |
| Interface clarity | PASS | AC2 now specifies exact token requirement with concrete false-green example |
| Dependency correctness | PASS | No deps, first task in B0 |
| Module layering | PASS | E2E test file only |
| TDD compliance | PASS | This IS the RED task |
| KISS/YAGNI | PASS | Three focused assertions |
| Premise challenge | PASS | PDS integration testing necessary |
| Pattern consistency | PASS | Follows pds-runtime-csp.spec.ts pattern |
| Security surface | PASS | Tests don't introduce attack surface |
| Single domain | PASS | Frontend only |

### Challenge Results
- Challenger: proceed (confidence: 0.81)
- Findings: (1) semantic ambiguity — accepted: removed method prescription; (2) method over-specification — accepted: AC now requires outcome (exact tokens) not method (split); (3) AC1/AC3 minor — non-blocking, reviewer-confirmed across 3 cycles
- Architect response: Accepted findings 1-2, narrowed AC2 to outcome-only requirement. AC1/AC3 stable.

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED

### Test-Writer Guidance
AC2 fix: replace current `.toContain()` assertions on the extracted directive string with exact token membership checks. The false-green to eliminate: `https://cdn.ui.porsche.com.evil.com` must NOT pass. Acceptable approaches: split directive by whitespace and use `toContain` on the array, use regex `\\b` boundaries, or `===` comparison after splitting. Do NOT use string `.toContain()` on the directive value.

### Verdict: APPROVE (REFINE + advance)
### Action Taken: Refined AC2 to require exact source-token membership (not substring), updated AC frontmatter, advanced to todo for test-writer to fix proof shape.

[[2026-05-16T10:14:04+02:00]]
## Test-Writer Notes (retry 3 — direct-to-review)

- Test file: `serve/cockpit/web/e2e/pds-foundation-1591.spec.ts`
- Toolchain: Playwright E2E (chromium)
- Retry scope: Fixed AC2 proof shape per reviewer Required Follow-up #1 (third review cycle)

### Change in this retry

Replaced the two `.toContain()` boundary assertions on the extracted directive string with exact token-membership checks using array split:

| Previous test | New test | Change |
|---|---|---|
| `font-src directive value contains 'https://cdn.ui.porsche.com'` | `font-src directive tokens include 'https://cdn.ui.porsche.com' as exact token` | Splits directive by `\s+`, uses `expect(tokens).toContain(...)` on the array |
| `font-src directive value contains 'self'` | `font-src directive tokens include 'self' as exact token` | Splits directive by `\s+`, uses `expect(tokens).toContain(...)` on the array |

False-green case eliminated: `font-src https://cdn.ui.porsche.com.evil.com` now FAILS the CDN-token test because `'https://cdn.ui.porsche.com'` is not in the token array.

### Direct-to-review advance

All 8 tests PASS against current impl — builder's `font-src 'self' https://cdn.ui.porsche.com` directive satisfies both exact-token checks. Builder has no additional work.

### AC coverage (complete)

| AC | Tests | Coverage |
|----|-------|----------|
| AC1: --p-color-canvas, --p-spacing-static-md, --p-font-porsche-next resolve non-empty | 4 | Full |
| AC2: CSP font-src directive contains both 'self' and https://cdn.ui.porsche.com as exact tokens | 3 | Full (exact-token, not substring) |
| AC3: No console errors/warnings containing 'porsche' during shell load | 1 | Full |

### Quality-runner evidence
- 8 passed, 0 failed
- Lint: clean (ESLint, 0 violations)

### Commit
`fe403e8b` — test: fix AC2 font-src exact-token assertions (#1591, test-writer)

[[2026-05-16T10:32:06+02:00]]
## Review Evidence
- Verdict: PASS
- PASS confirmation (one line): PASS #1591 -> docs | AC mapped to code and evidence sufficient.
- Challenger cross-check: proceed (confidence 0.82), no blocking findings.
- Builder/test-writer evidence is internally consistent: final retry notes report all 8 tests passing and lint clean in [.owlbear/kanban/tasks/1591-p0-01-tests-pds-global-styles-import-csp-font-relaxation.md](.owlbear/kanban/tasks/1591-p0-01-tests-pds-global-styles-import-csp-font-relaxation.md#L392), [.owlbear/kanban/tasks/1591-p0-01-tests-pds-global-styles-import-csp-font-relaxation.md](.owlbear/kanban/tasks/1591-p0-01-tests-pds-global-styles-import-csp-font-relaxation.md#L403), and [.owlbear/kanban/tasks/1591-p0-01-tests-pds-global-styles-import-csp-font-relaxation.md](.owlbear/kanban/tasks/1591-p0-01-tests-pds-global-styles-import-csp-font-relaxation.md#L404). `get_errors` found no diagnostics in the scoped files.

| AC | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC1 | [serve/cockpit/web/src/tokens.css](serve/cockpit/web/src/tokens.css#L2) imports the PDS global styles bundle so the required root custom properties are defined. | Retained Playwright proof reads and asserts the three named properties at [serve/cockpit/web/e2e/pds-foundation-1591.spec.ts](serve/cockpit/web/e2e/pds-foundation-1591.spec.ts#L102), [serve/cockpit/web/e2e/pds-foundation-1591.spec.ts](serve/cockpit/web/e2e/pds-foundation-1591.spec.ts#L106), [serve/cockpit/web/e2e/pds-foundation-1591.spec.ts](serve/cockpit/web/e2e/pds-foundation-1591.spec.ts#L112), [serve/cockpit/web/e2e/pds-foundation-1591.spec.ts](serve/cockpit/web/e2e/pds-foundation-1591.spec.ts#L116), [serve/cockpit/web/e2e/pds-foundation-1591.spec.ts](serve/cockpit/web/e2e/pds-foundation-1591.spec.ts#L122), [serve/cockpit/web/e2e/pds-foundation-1591.spec.ts](serve/cockpit/web/e2e/pds-foundation-1591.spec.ts#L126), and the combined boundary check at [serve/cockpit/web/e2e/pds-foundation-1591.spec.ts](serve/cockpit/web/e2e/pds-foundation-1591.spec.ts#L132). | PASS |
| AC2 | [serve/cockpit/web/vite.config.ts](serve/cockpit/web/vite.config.ts#L19) emits `font-src 'self' https://cdn.ui.porsche.com` in the CSP policy. | The spec extracts the `font-src` directive at [serve/cockpit/web/e2e/pds-foundation-1591.spec.ts](serve/cockpit/web/e2e/pds-foundation-1591.spec.ts#L176), proves the directive exists at [serve/cockpit/web/e2e/pds-foundation-1591.spec.ts](serve/cockpit/web/e2e/pds-foundation-1591.spec.ts#L182) and [serve/cockpit/web/e2e/pds-foundation-1591.spec.ts](serve/cockpit/web/e2e/pds-foundation-1591.spec.ts#L192), splits directive tokens at [serve/cockpit/web/e2e/pds-foundation-1591.spec.ts](serve/cockpit/web/e2e/pds-foundation-1591.spec.ts#L193) and [serve/cockpit/web/e2e/pds-foundation-1591.spec.ts](serve/cockpit/web/e2e/pds-foundation-1591.spec.ts#L206), and checks exact-token membership at [serve/cockpit/web/e2e/pds-foundation-1591.spec.ts](serve/cockpit/web/e2e/pds-foundation-1591.spec.ts#L197) and [serve/cockpit/web/e2e/pds-foundation-1591.spec.ts](serve/cockpit/web/e2e/pds-foundation-1591.spec.ts#L210). This closes the prior substring false-green. | PASS |
| AC3 | The reviewed change surface introduces the PDS global styles import and the explicit `font-src` allowance, removing the previously expected Porsche CDN/CSP failure path at [serve/cockpit/web/src/tokens.css](serve/cockpit/web/src/tokens.css#L2) and [serve/cockpit/web/vite.config.ts](serve/cockpit/web/vite.config.ts#L19). | The retained shell-load guard registers the console listener before navigation at [serve/cockpit/web/e2e/pds-foundation-1591.spec.ts](serve/cockpit/web/e2e/pds-foundation-1591.spec.ts#L225) and [serve/cockpit/web/e2e/pds-foundation-1591.spec.ts](serve/cockpit/web/e2e/pds-foundation-1591.spec.ts#L228), filters warning/error messages containing `porsche` at [serve/cockpit/web/e2e/pds-foundation-1591.spec.ts](serve/cockpit/web/e2e/pds-foundation-1591.spec.ts#L231), and asserts zero matches at [serve/cockpit/web/e2e/pds-foundation-1591.spec.ts](serve/cockpit/web/e2e/pds-foundation-1591.spec.ts#L242). | PASS |

- Blocking findings: none.

## Observations
- AC3 is satisfied as written, but it is intentionally narrow: the retained proof covers only console warnings/errors containing `porsche` during the shell-load window. Broader runtime-error or post-load monitoring would require a different AC.
- I confirmed the cited builder and test-writer commits exist in [.git/logs/HEAD](.git/logs/HEAD#L3313) and [.git/logs/HEAD](.git/logs/HEAD#L3331). This tool surface could not run a path-scoped `git status`, so contamination checking relied on task notes, live file inspection, commit-log presence, and zero editor diagnostics rather than a direct working-tree proof.

[[2026-05-16T10:39:13+02:00]]
## Docs Gate

### Checklist

| Item | Result | Evidence |
|------|--------|----------|
| 1. README Verification | No impact | Full read of `serve/cockpit/README.md`. No references to `tokens.css`, `font-src`, `global-styles`, or `pds-foundation` — no stale content, no contradictions. The CSP policy and PDS global-styles import are implementation details not documented at README level. No updates needed. |
| 2. External Attribution | N/A | PDS v4.1.0 is `@porsche-design-system/components-js` — already listed in the stack table. No new external sources. |
| 3. Research Doc | ✓ | `.owlbear/research/1591-pds-global-styles-test-approach.md` exists and is linked in task body. |
| 4. Deletion Detection | N/A | No files deleted in this task. |

### Scratch Cleanup
No `.owlbear/scratch/1591-*` files found. Nothing to clean.

### Files Modified
None — no docs impact verified.

[[2026-05-16T14:21:50+02:00]]
## Audit
### Regression Detection
- quality-runner mode full: Vitest 1895/0, Playwright 171 pass (39 fail — all from unrelated tasks #1573, #1395, #1593, #1564, #1563, #959), Pytest 4626 pass (239 fail — unrelated to frontend CSS/CSP), lint clean (ruff/eslint/stylelint)
- task-scoped pds-foundation-1591.spec.ts: 8/8 PASS
- adjacent pds-runtime-csp.spec.ts: PASS (not in failure list)
- regression verdict: PASS (no task-caused regressions; background failures pre-exist)

### Intent Verification
- scope alignment: PASS (tokens.css, vite.config.ts, pds-foundation-1591.spec.ts — all in serve/cockpit/web/, frontend domain)
- purpose match: PASS (PDS global-styles import + CSP font-src directive + E2E tests — matches stated task purpose)
- extraneous scope: none
- boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 3/5
AC1 and AC3 were well-specified after research corrections. AC2 required 3 refinement cycles (substring → directive-parsed → exact-token) before reaching sufficient precision. The initial AC should have specified exact source-token membership from the start — the reviewer caught this iteratively. The architect responded well to feedback each cycle but the initial gap caused significant pipeline overhead (3 extra review/arch/test-writer cycles).

### Commit Integrity
- upstream commit presence: PASS (d60f821a test-writer RED, ad6e9f05 builder GREEN, 68a86f85 test-writer retry, fe403e8b test-writer retry 3 — all confirmed in git log)
- kanban commit packaging: pending (this step)

### Deduction Breakdown
- AC quality score 3 → -.03
- No other deductions

### Confidence: 0.97
### Action: archive
