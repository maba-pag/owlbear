---
id: 1592
title: 'P0-03: Tests — Tailwind v4 Vite plugin + Stylelint config'
status: review
priority: critical
created: 2026-05-16T03:34:43.226946+00:00
updated: 2026-05-16T06:22:08.865237+00:00
tags:
  - frontend
  - pds
  - phase-0
parent: 1590
depends_on: []
ac:
  - Test asserts that vite build output (`dist/assets/*.css`) contains compiled 
    CSS for PDS Tailwind utility classes `bg-canvas`, `text-contrast-high`, 
    `gap-fluid-md`, `rounded-sm` — fails RED because @tailwindcss/vite is not 
    yet installed so no utility compilation occurs
  - Test asserts that PDS color utilities compiled by Tailwind preserve 
    `light-dark()` function syntax in dist output (verified by finding compiled 
    PDS color utility output containing literal `light-dark(`) — fails RED 
    because without Tailwind no PDS utility CSS is emitted
  - 'Test asserts Stylelint with project `.stylelintrc.json` config does not flag
    `@theme`, `@utility`, or `@apply` as unknown at-rules when run on a CSS fixture
    containing them — fails RED because current config has bare `at-rule-no-unknown:
    true` without ignoreAtRules'
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1590.

Scope: Failing tests for Tailwind v4 Vite plugin integration and Stylelint at-rule recognition.
Out of scope: Token migration, layout, board scroll, implementation.

2026-05-16T04:08:04+00:00


## Research Findings

### AC-1 Discrepancy: `gap-md` is invalid
The brief's AC says `bg-canvas, text-contrast-high, gap-md, rounded-sm`. However, PDS Tailwind theme does NOT define `--spacing-md`. PDS uses `--spacing-fluid-{xs..2xl}` and `--spacing-static-{2xs..2xl}`. The correct class is `gap-fluid-md` or `gap-static-md`. Tests should use `gap-fluid-md`.

### Key Technical Details
- PDS theme file: `@porsche-design-system/components-react/tailwindcss/index.css` (789 lines)
- At-rules in PDS theme: `@theme` (1), `@utility` (47), `@layer` (1), `@supports` (1)
- `light-dark()` used in ALL color variables; lightningcss `Features.LightDark` exclusion already in vite.config.ts
- Stylelint fix: manual `ignoreAtRules` on `at-rule-no-unknown` (no new dependency needed)
- Tailwind at-rules to allow: `theme`, `utility`, `apply`, `source`, `reference`, `variant`, `custom-variant`, `plugin`

### Test Approaches
- AC-1: Verify `@tailwindcss/vite` plugin registered + build-output scan for compiled PDS utilities
- AC-2: Scan `dist/assets/*.css` for `light-dark(` after build
- AC-3: Run Stylelint on fixture CSS file with `@theme`/`@utility`/`@apply`, assert exit 0

Research doc: `.owlbear/research/1592-tailwind-v4-stylelint-tests.md`

[[2026-05-16T06:08:32+02:00]]
## Research
- Research doc: .owlbear/research/1592-tailwind-v4-stylelint-tests.md
- Sources: 8 studied, 5 high-relevance (≥0.85)
- Key finding: AC-1 `gap-md` is invalid — PDS uses `gap-fluid-md` / `gap-static-md`. Tests should use `gap-fluid-md`.
- Recommendation: Manual `ignoreAtRules` for Stylelint (confidence: 0.80), build-output scan for light-dark() and utility compilation (confidence: 0.82)
- No follow-up tasks needed — builder #1595 already exists as dependency

[[2026-05-16T06:32:00+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | All 3 ACs test the same build-tooling concern: Tailwind v4 + Stylelint config |
| Interface clarity | PASS (after refine) | Original AC-1 had invalid `gap-md`; all ACs lacked explicit RED mechanisms. Refined to include verification method and RED failure reason |
| Dependency correctness | PASS | No deps — these are foundation tests that block #1595 (impl) |
| Module layering | PASS | Frontend test domain only |
| TDD compliance | PASS | This IS the RED phase task; builder #1595 provides GREEN |
| KISS/YAGNI | PASS | 3 tests, one per concern, minimal scope |
| Premise challenge | PASS | Tailwind v4 integration required per Brief and parent #1590 |
| Pattern consistency | PASS | Follows established Vitest patterns (vite_config.test.ts, PDSHexScan, ViteConfigAlias) |
| Security surface | PASS | N/A — test code only |
| Single domain | PASS | Frontend only |

### Challenger Results
- Challenger: reconsider (0.46)
- Issues raised: (1) AC-1 false-green risk — naive build-success test passes without PDS utilities in output; (2) AC-2 ambiguity — light-dark() already preserved by existing config, not Tailwind-specific; (3) AC-3 command scope — npm run lint:css vs direct Stylelint invocation; (4) gap-md drift to #1595
- Architect response: accepted all findings — rewrote all 3 AC lines with explicit verification methods and RED failure mechanisms. Fixed gap-md→gap-fluid-md. #1595 AC drift noted for that task's own review.

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Test-writer: PROCEED (writes RED tests; builder passes through since impl is on #1595)

### Design Diverge
- Trigger: skipped — single clear approach (build-output scan + Stylelint fixture)

### AC Corrections Applied
- `gap-md` → `gap-fluid-md` (PDS uses `--spacing-fluid-*` not `--spacing-md`)
- All 3 ACs rewritten for explicit RED mechanisms and verification methods
- AC-2 scoped to Tailwind-compiled PDS utility output specifically (not pre-existing global-styles light-dark)
- AC-3 specifies fixture-based Stylelint invocation with project config

### Verdict: APPROVE
### Action Taken: Refined AC (3 lines rewritten for RED-falsifiability), corrected gap-md to gap-fluid-md, approved to todo.

[[2026-05-16T06:43:01+02:00]]
Architecture review complete. Refined all 3 AC lines to address challenger findings (RED-falsifiability, scope ambiguity, verification method). Fixed gap-md→gap-fluid-md per PDS theme reality. Approved to todo.

[[2026-05-16T07:02:21+02:00]]
## Test-Writer Notes
- Test file: serve/cockpit/web/src/__tests__/TailwindStylelint_1592.test.ts
- Classes: TestFromAC_TailwindBuildOutput, TestFromAC_StylelintAtRules
- Tests per category: happy 0, edge 0, error 0, boundary 0 (build-output scan + CLI invocation pattern)
- Total: 8 tests, all FAIL
- ruff: N/A (TypeScript); ESLint: clean; TypeScript: clean

### AC Coverage
| AC | Tests | RED reason |
|----|-------|-----------|
| AC-1 (utility classes in dist) | 4 — one per class (bg-canvas, text-contrast-high, gap-fluid-md, rounded-sm) | @tailwindcss/vite not installed → no compiled selectors in dist |
| AC-2 (light-dark() in compiled output) | 1 — scans for --color-* var with light-dark() value | PDS @theme not processed → no --color-* declarations in dist |
| AC-3 (Stylelint allows @theme/@utility/@apply) | 3 — @theme alone, @utility alone, combined fixture | at-rule-no-unknown: true without ignoreAtRules → Stylelint exits 2 |

### Notes
- @apply standalone test removed: Stylelint 17.11.1 allows @apply natively (not flagged by at-rule-no-unknown). Combined fixture covers @apply alongside @theme/@utility.
- AC-1/AC-2 scan the existing dist without running a build — the dist has CSS from color-scheme.css (Tailwind utilities absent until @tailwindcss/vite installed).
- AC-2 pattern `--color-[a-z][a-z0-9-]*\s*:\s*light-dark\(` is distinct from the @supports condition in color-scheme.css which uses light-dark only as a feature-detection value, not a property value.

[[2026-05-16T07:14:15+02:00]]
## Builder Notes
- Implementation: none (non-implementation pass-through task)
- Files changed: none
- RED verification: 8/8 `TestFromAC_*` tests in `serve/cockpit/web/src/__tests__/TailwindStylelint_1592.test.ts` are failing as intended
- Lint: clean (eslint clean for the scoped test file)
- Coverage: N/A for RED-phase test task
- Evidence summary: quality-runner scoped run confirms AC-1/AC-2 fail due to missing `@tailwindcss/vite` integration and AC-3 fails due to Stylelint unknown at-rules (`@theme`, `@utility`) under current config.
- Routing rationale: task scope/body marks implementation out of scope and delegated to dependent task #1595; this task is complete as the RED foundation for that GREEN implementation work.

[[2026-05-16T07:44:25+02:00]]
## Review Evidence
- Verdict: FAIL
- Routing: todo
- Summary: AC-1 and AC-2 require proof about Vite build output, but the current tests only read the preexisting dist directory and never invoke a fresh build. AC-3 is materially sound.
- Blocking findings:

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC-1 | The test does not generate fresh Vite build output before scanning dist, so it can pass or fail based on leftover artifacts instead of the current source and config. | .owlbear/kanban/tasks/1592-p0-03-tests-tailwind-v4-vite-plugin-stylelint-config.md:15; .owlbear/research/1592-tailwind-v4-stylelint-tests.md:81; serve/cockpit/web/src/__tests__/TailwindStylelint_1592.test.ts:36,51-52,69,74; serve/cockpit/web/package.json:11,16; .owlbear/kanban/tasks/1592-p0-03-tests-tailwind-v4-vite-plugin-stylelint-config.md:127 | todo |
| 2 | AC-2 | The test likewise reads preexisting dist and therefore does not prove that current Tailwind-compiled output preserves light-dark(). The current dist already contains unrelated PDS light-dark content, so build-causal proof is required. | .owlbear/kanban/tasks/1592-p0-03-tests-tailwind-v4-vite-plugin-stylelint-config.md:19; .owlbear/research/1592-tailwind-v4-stylelint-tests.md:59,82,99; serve/cockpit/web/src/__tests__/TailwindStylelint_1592.test.ts:36,51-52,121,128; serve/cockpit/web/package.json:11,16; serve/cockpit/dist/assets/index-B_t56Oai.css:1; .owlbear/kanban/tasks/1592-p0-03-tests-tailwind-v4-vite-plugin-stylelint-config.md:127 | todo |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Rework the AC-1 test to create fresh Vite build output before scanning dist CSS. | serve/cockpit/web/src/__tests__/TailwindStylelint_1592.test.ts | Review finding 1 |
| 2 | test-writer | Rework the AC-2 test to tie light-dark preservation to fresh Tailwind build output from current sources rather than inherited dist artifacts. | serve/cockpit/web/src/__tests__/TailwindStylelint_1592.test.ts | Review finding 2 |

## Observations
- AC-3 is materially sound: the test invokes Stylelint directly with the project config and asserts zero exit status on fixtures at serve/cockpit/web/src/__tests__/TailwindStylelint_1592.test.ts:144,151-153,162-197, while the current config still has bare at-rule-no-unknown at serve/cockpit/web/.stylelintrc.json:3.
- Challenger review returned proceed at 0.83 confidence on this narrow fail: AC-1 and AC-2 are blocking, AC-3 is acceptable.
- No editor diagnostics were reported for serve/cockpit/web/src/__tests__/TailwindStylelint_1592.test.ts.

[[2026-05-16T08:13:16+02:00]]
## Test-Writer Notes (retry)
- Test file: serve/cockpit/web/src/__tests__/TailwindStylelint_1592.test.ts
- Classes: TestFromAC_TailwindBuildOutput, TestFromAC_StylelintAtRules
- Total: 8 tests, all FAIL (quality-runner: passed 0 / failed 8)
- ESLint: clean | TypeScript (tsc --noEmit): clean

### Retry changes (reviewer findings 1 & 2)
Added `beforeAll(() => spawnSync('node', [VITE_BIN, 'build'], ...), 120_000)` inside `TestFromAC_TailwindBuildOutput`. The hook runs a fresh Vite build before any AC-1 or AC-2 assertions, eliminating the stale-artifact risk the reviewer identified. Build succeeds without `@tailwindcss/vite` but emits no Tailwind utility output → tests fail causally.

### AC Coverage
| AC | Tests | RED reason |
|----|-------|------------|
| AC-1 (utility selectors in fresh dist) | 4 — bg-canvas, text-contrast-high, gap-fluid-md, rounded-sm | Fresh `vite build` without @tailwindcss/vite → no PDS utility selectors emitted |
| AC-2 (light-dark() in fresh Tailwind output) | 1 — --color-* with light-dark() | Fresh build; PDS @theme never processed → no --color-* declarations |
| AC-3 (Stylelint allows @theme/@utility/@apply) | 3 — @theme alone, @utility alone, combined | at-rule-no-unknown: true without ignoreAtRules → exit 2 |

[[2026-05-16T08:22:08+02:00]]
## Builder Notes
- Implementation: none (test-only RED foundation task; implementation is out of scope and delegated to #1595)
- Files changed: none
- Proof bundle: behavioral
- Verification command path: quality-runner scoped on `serve/cockpit/web/src/__tests__/TailwindStylelint_1592.test.ts`
- Tests: 8 total, 0 passed, 8 failed (expected RED)
- Failed tests:
  - AC-1: `.bg-canvas` selector missing in fresh dist output
  - AC-1: `.text-contrast-high` selector missing in fresh dist output
  - AC-1: `.gap-fluid-md` selector missing in fresh dist output
  - AC-1: `.rounded-sm` selector missing in fresh dist output
  - AC-2: `--color-* : light-dark(` pattern missing in dist output
  - AC-3: Stylelint flags `@theme` as unknown (exit 2)
  - AC-3: Stylelint flags `@utility` as unknown (exit 2)
  - AC-3: combined fixture with `@theme/@utility/@apply` fails via unknown at-rules
- Lint: clean (scoped eslint for test file)
- Coverage: N/A for RED-only pass-through
- Evidence summary: retry test-writer hook now runs fresh `vite build` before AC-1/AC-2 assertions; failures are causal to missing `@tailwindcss/vite` integration and missing Stylelint `ignoreAtRules`, matching AC RED expectations.
- Routing rationale: non-implementation pass-through complete; this task now provides stable RED evidence for builder implementation task #1595.
