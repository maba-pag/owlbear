---
id: 1594
title: 'P0-02: PDS global-styles import + CSP font relaxation'
status: in-progress
priority: critical
created: 2026-05-16T03:35:01.700586+00:00
updated: 2026-05-16T12:58:17.879427+00:00
tags:
  - frontend
  - pds
  - phase-0
parent: 1590
depends_on:
  - 1591
ac:
  - --p-color-canvas, --p-spacing-static-md, --p-font-porsche-next resolve to 
    non-empty values in computed styles (regression guard)
  - CSP meta tag contains font-src 'self' https://cdn.ui.porsche.com (regression
    guard)
  - No console errors or warnings containing 'porsche' during shell load 
    (regression guard)
  - main.tsx contains no import referencing color-scheme.css
  - vite.config.ts contains no pdsColorSchemeCssPath const
  - vite.config.ts resolve.alias contains no color-scheme.css entry
  - Vitest and Playwright E2E suites in serve/cockpit/web/ pass with zero 
    failures
proof_bundle: existing
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1590.

Replace single `color-scheme.css` import in `main.tsx` with PDS `global-styles/index.css` bundle (variables, font-face, normalize, color-scheme). Add `font-src 'self' https://cdn.ui.porsche.com` to CSP meta tag in Vite HTML plugin (D6).

Scope: global-styles import and CSP font-src only.
Out of scope: Tailwind, Stylelint, board scroll.

## Research Findings

Core implementation already committed by #1591 builder (commit ad6e9f05):
- `tokens.css` imports `global-styles/index.css` (full PDS bundle)
- CSP `font-src 'self' https://cdn.ui.porsche.com` present in `vite.config.ts`
- All 8 E2E tests in `pds-foundation-1591.spec.ts` pass

Remaining builder work (cleanup):
1. Remove redundant `import '...color-scheme.css'` from `main.tsx` line 4 (subset of already-imported `index.css`)
2. Remove Vite alias + `pdsColorSchemeCssPath` const from `vite.config.ts`
3. **Update #1555 unit tests** that guard the old pattern:
   - `PdsColorSchemeBridge_1555.test.ts` (lines 115–132): asserts `color-scheme.css` import in `main.tsx` → update to assert `global-styles/index.css` import in `tokens.css`
   - `ViteConfigAlias_1555.test.ts` (lines 52–73): asserts Vite alias exists → remove or repurpose
4. Verify all E2E + vitest suites pass

AC property names corrected: `--p-spacing-md` → `--p-spacing-static-md`, `--p-font-family` → `--p-font-porsche-next`.
See `.owlbear/research/1594-pds-global-styles-import.md` for full analysis.

[[2026-05-16T14:37:46+02:00]]
## Research
- Research doc: .owlbear/research/1594-pds-global-styles-import.md
- Sources: 7 studied, 5 high-relevance (≥0.9)
- Recommendation: Builder scope is cleanup-only — remove redundant color-scheme.css import, Vite alias, and update #1555 unit tests. Core implementation already committed by #1591 builder. (confidence: 0.85)
- Follow-up tasks created: none (this task IS the implementation task)
- Decision requests: none
- AC corrected: --p-spacing-md → --p-spacing-static-md, --p-font-family → --p-font-porsche-next

## Challenge Results
- Challenger: reconsider (confidence in original: 0.63)
- Key challenges: #1555 test contracts guard old pattern (regression risk), scope drift on optional import-path migration, proof gap on untested import path
- Researcher response: accepted — added F4 finding for #1555 test updates, narrowed import-path change to advisory, kept alias cleanup as task-inherent. Revised confidence: 0.85

[[2026-05-16T14:53:52+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Cleanup-only: remove dead imports/const/alias from a superseded pattern |
| Interface clarity | PASS | AC4-6 name exact targets; AC1-3 name exact properties/directives; AC7 names suite scope |
| Dependency correctness | PASS | #1591 (archived/completed) committed the core implementation |
| Module layering | PASS | Changes confined to main.tsx and vite.config.ts in serve/cockpit/web/ |
| TDD compliance | PASS | Existing E2E proof covers behavioral regression; no new RED tests needed |
| KISS/YAGNI | PASS | Minimal cleanup scope — removal only, no new abstractions |
| Premise challenge | PASS | Dead code removal is warranted: color-scheme.css is a strict subset of global-styles/index.css already imported |
| Pattern consistency | PASS | Follows existing PDS integration pattern established by #1591 |
| Security surface | PASS | No new boundaries; CSP policy unchanged |
| Single domain | PASS | Frontend only |

### Challenge Results
- Challenger: reconsider (confidence: 0.68)
- Key findings: (1) task artifact mismatch — accepted, fixed via edit_task; (2) incomplete proof set — accepted, added dark-mode suite; (3) AC5 compound — accepted, split; (4) AC6 conflation — accepted, simplified; (5) hard-coded import path — accepted, outcome-focused wording; (6) test contract drift — non-blocking, builder discretion
- Architect response: Accepted 5 of 6 findings, revised AC from 3 lines to 7, changed proof_bundle from behavioral to existing

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: existing
- Existing proof scope: serve/cockpit/web/e2e/pds-foundation-1591.spec.ts, serve/cockpit/web/e2e/pds-scheme-dark-1555.spec.ts
- Test-writer: SKIP
- De-escalation rationale: Core implementation already landed via #1591. No new testable behavior is being introduced — only dead code removal. Existing E2E suites (8 foundation tests + dark-mode bridge) provide full behavioral regression coverage.

### Builder Guidance
- Remove color-scheme.css import from main.tsx (line 4)
- Remove pdsColorSchemeCssPath const (vite.config.ts lines 8-11) and resolve.alias entry (lines 67-70)
- Update or remove PdsColorSchemeBridge_1555.test.ts and ViteConfigAlias_1555.test.ts — these guard the old pattern that is being removed. Builder has discretion on update shape (may repurpose to verify new import path, or remove if #1555 contract is fully superseded)
- Note: ViteConfigAlias_1555.test.ts has a known issue where vite.config.ts fileURLToPath evaluates at module level causing import failures in jsdom context — removing the alias may resolve this naturally

### Verdict: APPROVE (REFINE + advance)
### Action Taken: Refined AC (3→7 lines), changed proof_bundle from behavioral to existing, advanced to todo

[[2026-05-16T14:58:17+02:00]]
## Test-Writer Notes
- Proof bundle: existing — no new test writing required.
- Existing proof scope: serve/cockpit/web/e2e/pds-foundation-1591.spec.ts, serve/cockpit/web/e2e/pds-scheme-dark-1555.spec.ts
- Passing through to builder.
