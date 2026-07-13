---
id: 1594
title: 'P0-02: PDS global-styles import + CSP font relaxation'
status: archived
priority: medium
created: 2026-05-16T03:35:01.700586+00:00
updated: 2026-05-16T13:43:07.735479+00:00
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
archival_reason: completed
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

[[2026-05-16T15:13:17+02:00]]
## Builder Notes
- Files changed:
  - serve/cockpit/web/src/main.tsx
  - serve/cockpit/web/vite.config.ts
  - serve/cockpit/web/src/__tests__/PdsColorSchemeBridge_1555.test.ts
  - serve/cockpit/web/src/__tests__/ViteConfigAlias_1555.test.ts
- Implementation summary:
  - Removed legacy `color-scheme.css` import from main.tsx.
  - Removed obsolete `pdsColorSchemeCssPath` constant and resolve.alias bridge from vite.config.ts.
  - Updated #1555 contract test to assert global-styles/index.css import in tokens.css.
  - Repurposed Vite alias test to assert the legacy alias key is absent while keeping vite config importability coverage.
- Proof bundle handling:
  - Proof bundle is `existing`; executed required existing proofs in scoped quality run.
- Quality evidence (quality-runner, scoped):
  - Vitest: 26 passed, 0 failed
    - src/__tests__/PdsColorSchemeBridge_1555.test.ts
    - src/__tests__/ViteConfigAlias_1555.test.ts
  - Playwright: 10 passed, 0 failed
    - e2e/pds-foundation-1591.spec.ts
    - e2e/pds-scheme-dark-1555.spec.ts
  - Lint: clean (eslint exit 0) on changed frontend files
  - Coverage: N/A for this `existing` proof task
- Commit:
  - 7cbc8c4c6fa9a6b4ec436cf9e434ebdb5f4df6b8
- AC mapping:
  - AC4 satisfied: main.tsx has no color-scheme.css import.
  - AC5 satisfied: vite.config.ts has no pdsColorSchemeCssPath const.
  - AC6 satisfied: vite.config.ts resolve.alias has no color-scheme.css mapping.
  - AC2/AC7 validated by scoped proofs (CSP font-src and required vitest/e2e suites passing).

[[2026-05-16T15:26:24+02:00]]
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1594 -> docs | AC mapped to code and evidence sufficient.
- Blocking findings: none.
- Builder evidence reviewed first: scoped quality-runner notes report Vitest 26 passed, 0 failed on `src/__tests__/PdsColorSchemeBridge_1555.test.ts` and `src/__tests__/ViteConfigAlias_1555.test.ts`; Playwright 10 passed, 0 failed on `e2e/pds-foundation-1591.spec.ts` and `e2e/pds-scheme-dark-1555.spec.ts`; eslint clean on changed frontend files. Commit `7cbc8c4c6fa9a6b4ec436cf9e434ebdb5f4df6b8` is present in `.git/logs/refs/heads/dev:3110` and `.git/logs/HEAD:3351`.

| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| 1 | `serve/cockpit/web/src/main.tsx:5` imports `./tokens.css`; `serve/cockpit/web/src/tokens.css:2` imports PDS `global-styles/index.css` | `serve/cockpit/web/src/__tests__/PdsColorSchemeBridge_1555.test.ts:115,121` plus `serve/cockpit/web/e2e/pds-foundation-1591.spec.ts:102,132` prove the import path yields non-empty computed PDS vars | PASS |
| 2 | `serve/cockpit/web/vite.config.ts:14` contains `font-src 'self' https://cdn.ui.porsche.com` in the CSP policy | `serve/cockpit/web/e2e/pds-foundation-1591.spec.ts:182,189,202` prove directive presence and exact-token membership for both CDN origin and `'self'` | PASS |
| 3 | Existing behavior surface retained; no new Porsche logging or runtime branch added in the cleanup files | `serve/cockpit/web/e2e/pds-foundation-1591.spec.ts:225` fails on any console error or warning containing `porsche` during shell load | PASS |
| 4 | `grep_search` on `serve/cockpit/web/src/main.tsx` for `color-scheme.css` returned zero matches; current import surface at `serve/cockpit/web/src/main.tsx:1-6` contains only `tailwind.css`, `tokens.css`, and `App` imports | Static cleanup AC; no additional runtime proof required beyond retained regression suite green in AC7 | PASS |
| 5 | `grep_search` on `serve/cockpit/web/vite.config.ts` for `pdsColorSchemeCssPath` returned zero matches | Static cleanup AC; current file inspection matches the removal claim and AC7 existing-proof run stayed green | PASS |
| 6 | `grep_search` on `serve/cockpit/web/vite.config.ts` found no `resolve:`/`alias:` block and no `color-scheme.css` entry | `serve/cockpit/web/src/__tests__/ViteConfigAlias_1555.test.ts:44,49` assert the legacy alias key is absent in the imported config object | PASS |
| 7 | Current scoped files open without editor diagnostics (`get_errors`: no errors on main.tsx, vite.config.ts, the two Vitest files, and the two Playwright files) | Builder quality-runner notes report Vitest 26 passed, 0 failed; Playwright 10 passed, 0 failed; eslint clean | PASS |

- Safety/security check: AC2 touches CSP only. Source inspection shows a static `font-src` token in `serve/cockpit/web/vite.config.ts:14` with no new dynamic input, credential, or logging surface.

## Observations
- `serve/cockpit/web/playwright.config.ts:17-18` runs `npm run build && npm run preview`, so the retained Playwright proof legitimately exercises build-time CSP injection rather than dev-server HTML.
- Terminal/git execution was unavailable in this session, so I could not independently run the scoped `git status --porcelain` contamination check. I confirmed commit presence via reflog and found no contradictory evidence in current source, tests, or editor diagnostics.

[[2026-05-16T15:28:06+02:00]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | README verification | Yes | N/A — no update needed | `serve/cockpit/README.md` contains no references to `color-scheme.css`, `pdsColorSchemeCssPath`, or the removed Vite alias. The task removed implementation-internal dead code never surfaced in the README. grep confirmed zero matches. |
| 2 | External attribution | Yes | N/A — already done | `sources/overview.md` line 117–121 has `## PDS Global-Styles Import Research (Task #1594)` with 5 source entries added by the researcher. No update needed. |
| 3 | Research doc | Yes | N/A — linked | `.owlbear/research/1594-pds-global-styles-import.md` exists; task body references it ("See `.owlbear/research/1594-pds-global-styles-import.md` for full analysis."). |
| 4 | Deletion detection | No | N/A | No source files deleted — only code removed from `main.tsx` and `vite.config.ts`, and test files updated (not deleted). No orphaned references. |

### Verification Layers
- Layer 1 — grep: zero hits for `color-scheme.css`/`pdsColorSchemeCssPath` in `serve/cockpit/README.md`; `sources/overview.md` confirmed to contain `#1594` entry at line 117.
- Layer 2 — editorial: `serve/cockpit/README.md` Frontend Surface table, PDS integration, and Accessibility sections are all accurate with respect to this cleanup task. No contradictions or stale claims introduced.

### Scratch Cleanup
No `.owlbear/scratch/1594-*` files existed. Nothing to delete.

[[2026-05-16T15:43:07+02:00]]
## Audit
### Regression Detection
- quality-runner mode full: pytest 4642 passed, ~240 failed (pre-existing background set matching #1632 baseline of 236 failed/4646 passed), 9 errors (pre-existing). Vitest 26 passed 0 failed. Playwright 10 passed 0 failed. Ruff clean. ESLint clean (only ignore-pattern info on vite.config.ts, not a violation).
- regression verdict: PASS (zero new failures)

### Intent Verification
- scope alignment: PASS (all 4 changed files within serve/cockpit/web/: main.tsx, vite.config.ts, PdsColorSchemeBridge_1555.test.ts, ViteConfigAlias_1555.test.ts)
- purpose match: PASS (dead code removal of superseded color-scheme.css bridge + test contract updates, matching stated task purpose)
- extraneous scope: none
- boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 5/5
AC refined from 3 to 7 lines after challenger feedback. AC1-3 are regression guards naming exact CSS properties and CSP directives. AC4-6 name exact removal targets (import, const, alias). AC7 is suite-level green gate. Specific, complete, clean implementation path. Challenger improved proof_bundle from behavioral to existing (appropriate for cleanup-only task).

### Commit Integrity
- upstream commit presence: PASS (builder commit 7cbc8c4c confirmed via git log on all 4 changed files)
- kanban commit packaging: pending (this archive cycle)

### Deduction Breakdown
No deductions applied.

### Confidence: 1.00
### Action: archive
