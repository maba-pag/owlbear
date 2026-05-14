---
id: 1543
title: 'P1-02: impl — token architecture: agnostic rename + expansion + dark overrides'
status: archived
priority: critical
created: 2026-05-13T18:42:22.266810+00:00
updated: 2026-05-14T02:07:04.973359+00:00
tags:
  - phase-1
  - scope:cockpit
  - css
  - frontend
parent: 1534
depends_on:
  - 1535
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
Brief: see parent #1534 (`.owlbear/briefs/draft-board-visual-design/brief.md`)

## Scope
- **In:** Restructure `tokens.css` to agnostic names, add dark overrides selector, add shadow/radius/spacing token sets, add `@media (prefers-color-scheme: dark)` fallback
- **Out:** Theme bootstrap script, useTheme hook, component CSS consumption of tokens

## Acceptance Criteria

- AC-1: `tokens.css` uses agnostic `--pds-*` names; light values in `:root`, dark overrides in `[data-theme="dark"]`
- AC-2: `@media (prefers-color-scheme: dark) { :root:not([data-theme]) { ... } }` fallback applies the same 19 dark color overrides when no `data-theme` attribute is set on `<html>`
- AC-3: Shadow (`--pds-shadow-{sm,md,lg}`), border-radius (`--pds-radius-{sm..xl}`), and spacing (`--pds-spacing-{xs..2xl}`) token sets defined in `:root` as theme-independent values

Proof bundle: behavioral

## Builder Guidance

**Test defect in RED suite:** `TokenArchitecture_1535.test.ts` line 126 asserts `darkValue !== rootValue` for all 19 tokens, but PDS v4 defines `--pds-state-focus` and `--pds-background-shading` identically in both themes. The correct implementation will fail 2 assertions. Fix the test to exempt these 2 tokens from the difference check (or use `toHaveLength(>0)` for them) before or alongside the implementation commit.

## Research
- Research doc: .owlbear/research/1543-token-architecture-impl.md
- Sources: 9 studied, 6 high-relevance
- Recommendation: Proceed with single-file CSS restructure using PDS v4 authoritative values (confidence: 0.82)
- Follow-up tasks created: none needed (existing decomposition covers all downstream work)
- Decision requests: none

### Key Findings
1. Single-file edit: tokens.css grows from ~37 to ~90 lines (19 agnostic color tokens + 13 non-color tokens + dark overrides + media fallback)
2. **Critical test defect**: `--pds-state-focus` and `--pds-background-shading` have identical light/dark values in PDS v4. The RED test (#1535) asserts all dark values differ from light — will fail with correct PDS values. Builder must coordinate test fix.
3. `@media (prefers-color-scheme: dark)` with `:root:not([data-theme])` selector is the ONLY dark-mode path until #1545 integrates theme bootstrap
4. Full downstream breakage inventory: Shell.css, Card.css, Card.tsx, styles.ts, ErrorBoundary.tsx, test assertions — all handled by tasks #1546–#1550, #1552

## Challenge Results
- Challenger: reconsider (confidence in original: 0.55)
- Researcher response: revised to proceed at 0.82
- Key challenges accepted: focus/shading token identity (test defect, not architecture defect), media fallback is primary dark path (reframed), incomplete breakage list (expanded)
- Rebutted: "reconsider" severity — test defect is fixable in-pipeline, doesn't invalidate approach
2026-05-13T23:54:33+00:00
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single-file CSS restructure only |
| Interface clarity | PASS | AC enumerates token families, selectors, and counts; AC-2 refined to include explicit `:root:not([data-theme])` selector |
| Dependency correctness | PASS | #1535 archived/completed; RED tests exist at `TokenArchitecture_1535.test.ts` |
| Module layering | PASS | CSS tokens file; no cross-layer imports |
| TDD compliance | PASS | RED suite exists with 4 failing tests covering all 3 ACs. Known test defect (2 over-strict assertions) documented in builder guidance |
| KISS/YAGNI | PASS | Minimal single-file edit, ~37→~90 lines, no abstractions |
| Premise challenge | PASS | Brief deliverable; foundational for theme system (#1545+) |
| Pattern consistency | PASS | Follows existing token file structure |
| Security surface | N/A | Static CSS, no system boundaries |
| Single domain | PASS | Frontend CSS tokens only |

### Challenge Results
- Challenger: reconsider (confidence 0.66)
- Key challenges: (1) test defect creates false-negative gate for 2 tokens, (2) AC-2 lacked explicit fallback selector, (3) consolidation-test gap (rebutted — #1554 exists)
- Architect response: ACCEPTED challenge (2) — refined AC-2 to name `:root:not([data-theme])` selector explicitly. ACCEPTED challenge (1) — added explicit Builder Guidance section with fix instructions. REBUTTED challenge (3) — consolidation task #1554 already exists under parent #1534.
- Post-refinement confidence: 0.85

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED (RED tests exist at `src/__tests__/TokenArchitecture_1535.test.ts`)

### Verdict: APPROVE
### Action Taken: Refined AC-2 (explicit fallback selector), added Builder Guidance for test defect coordination, advanced to todo.
2026-05-14T00:24:28+00:00
## Test-Writer Notes
- Test file: serve/cockpit/web/src/__tests__/TokenArchitecture_1543.test.ts
- Classes: TestFromAC_TokenArchitecture_1543
- Tests per category: happy 3, edge 1, error 2, boundary 1
- Total: 7 tests, all FAIL (AssertionError — tokens.css has no media query, no dark selector yet)
- ESLint: clean

### AC Coverage
| AC | Tests |
|----|-------|
| AC-2 refined: `@media` uses `:root:not([data-theme])` selector (not bare `:root`) | happy, boundary, error tests 1–3, 6 |
| AC-2 refined: media fallback values match `[data-theme="dark"]` values for 17 differing tokens | happy test 4 |
| AC-2 edge: PDS-identical tokens (`--pds-state-focus`, `--pds-background-shading`) present in media fallback | edge test 5 |
| AC-3 boundary: non-color tokens (shadow/radius/spacing) absent from `[data-theme="dark"]` | boundary test 7 |

### Note for Builder
- Existing `TokenArchitecture_1535.test.ts` (4 tests, all FAIL) covers AC-1 agnostic names, basic AC-2/AC-3.
- This file covers the AC-2 **refinement** (explicit `:root:not([data-theme])` selector, exact value matching) and AC-3 theme-independence boundary.
- Builder Guidance in task body: fix the 2 over-strict assertions in `TokenArchitecture_1535.test.ts` line 126 (`--pds-state-focus` and `--pds-background-shading` have identical light/dark values in PDS v4).
2026-05-14T01:16:18+00:00
## Builder Notes
- Files changed:
  - `serve/cockpit/web/src/tokens.css`
  - `serve/cockpit/web/src/__tests__/TokenArchitecture_1535.test.ts`
- Implementation summary:
  - Replaced legacy `--pds-theme-light-*` color tokens with agnostic `--pds-*` color tokens in `:root`.
  - Added theme-independent shadow/radius/spacing token sets (13 tokens) in `:root`.
  - Added `[data-theme="dark"]` with 19 dark color overrides using PDS v4 values.
  - Added `@media (prefers-color-scheme: dark) { :root:not([data-theme]) { ... } }` fallback mirroring the same 19 dark overrides.
  - Applied builder-guidance test-defect fix in `TokenArchitecture_1535.test.ts`: exempted `--pds-state-focus` and `--pds-background-shading` from strict dark-vs-root inequality assertion.
- Test results (quality-runner, scoped):
  - `serve/cockpit/web/src/__tests__/TokenArchitecture_1535.test.ts`
  - `serve/cockpit/web/src/__tests__/TokenArchitecture_1543.test.ts`
  - Result: 11 passed, 0 failed, 0 skipped.
- Lint status (quality-runner scoped):
  - ESLint clean
  - Stylelint clean
- Coverage:
  - N/A for CSS token file in current Vitest instrumentation (runner reported no module coverage entries for `src/tokens.css`).
- Evidence summary:
  - RED verified before implementation: both token architecture test files failing.
  - GREEN verified after implementation: both files passing with lint clean.
- Commit:
  - `cc56c75d` — feat: implement token architecture dark overrides (#1543, builder)
2026-05-14T01:30:20+00:00
## Review Evidence
- Verdict: FAIL
- FAIL #1543 -> todo | AC-2 proof is incomplete: the media-fallback suite never asserts that the two PDS-identical tokens equal the `[data-theme="dark"]` values.
- AC evidence map:
| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC-1 | `.owlbear/kanban/tasks/1543-p1-02-impl-token-architecture-agnostic-rename-expansion-dark-overrides.md:30`; `serve/cockpit/web/src/tokens.css:55` shows the dark selector and `serve/cockpit/web/src/tokens.css:82` shows the fallback selector. | `serve/cockpit/web/src/__tests__/TokenArchitecture_1535.test.ts:100` proves exact agnostic token set in `:root`; `serve/cockpit/web/src/__tests__/TokenArchitecture_1535.test.ts:119` proves all 19 dark-selector tokens are present and non-empty. | PASS |
| AC-2 | `.owlbear/kanban/tasks/1543-p1-02-impl-token-architecture-agnostic-rename-expansion-dark-overrides.md:31`; `serve/cockpit/web/src/tokens.css:60`, `serve/cockpit/web/src/tokens.css:77`, `serve/cockpit/web/src/tokens.css:87`, and `serve/cockpit/web/src/tokens.css:104` show the two PDS-identical tokens currently match across dark selector and media fallback. | `serve/cockpit/web/src/__tests__/TokenArchitecture_1543.test.ts:100` and `serve/cockpit/web/src/__tests__/TokenArchitecture_1543.test.ts:109` prove selector shape and 19-token presence; `serve/cockpit/web/src/__tests__/TokenArchitecture_1543.test.ts:133` and `serve/cockpit/web/src/__tests__/TokenArchitecture_1543.test.ts:141` compare only the 17 differing tokens; `serve/cockpit/web/src/__tests__/TokenArchitecture_1543.test.ts:145` and `serve/cockpit/web/src/__tests__/TokenArchitecture_1543.test.ts:154` check the two PDS-identical tokens only for presence/non-empty. | FAIL |
| AC-3 | `.owlbear/kanban/tasks/1543-p1-02-impl-token-architecture-agnostic-rename-expansion-dark-overrides.md:32`; `serve/cockpit/web/src/tokens.css:36`, `serve/cockpit/web/src/tokens.css:44`, and `serve/cockpit/web/src/tokens.css:52` show root-only non-color tokens. | `serve/cockpit/web/src/__tests__/TokenArchitecture_1535.test.ts:153` proves the 13 root non-color tokens exist; `serve/cockpit/web/src/__tests__/TokenArchitecture_1543.test.ts:167` proves they are absent from `[data-theme="dark"]`. | PASS |
- Blocking findings:
| # | AC Line | Finding | Evidence | Route |
|---|---|---|---|---|
| 1 | AC-2 | The suite does not falsify the requirement that the media fallback applies the same dark override values for `--pds-state-focus` and `--pds-background-shading`. A regression changing either fallback value would still pass because equality is asserted only for the 17 differing tokens. | `serve/cockpit/web/src/__tests__/TokenArchitecture_1543.test.ts:133`, `serve/cockpit/web/src/__tests__/TokenArchitecture_1543.test.ts:141`, `serve/cockpit/web/src/__tests__/TokenArchitecture_1543.test.ts:145`, `serve/cockpit/web/src/__tests__/TokenArchitecture_1543.test.ts:154` | todo |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Add falsifiable AC-2 assertions that `--pds-state-focus` and `--pds-background-shading` in the media fallback equal the `[data-theme="dark"]` values, not just that they are present and non-empty. | `serve/cockpit/web/src/__tests__/TokenArchitecture_1543.test.ts` | Blocking finding #1 |

## Observations
- Direct source inspection shows the checked-in implementation currently satisfies the contract: `[data-theme="dark"]` is defined at `serve/cockpit/web/src/tokens.css:55`, the explicit fallback selector is present at `serve/cockpit/web/src/tokens.css:82`, and the two PDS-identical tokens already match at `serve/cockpit/web/src/tokens.css:60`, `serve/cockpit/web/src/tokens.css:77`, `serve/cockpit/web/src/tokens.css:87`, and `serve/cockpit/web/src/tokens.css:104`.
- Challenger cross-check returned `reconsider` because the proof gap is narrow, but I am keeping FAIL because AC-2 explicitly requires the same 19 dark overrides and the current suite leaves 2 of those 19 values unfalsified.
2026-05-14T01:35:14+00:00
## Test-Writer Notes
- Retry: added 1 test for reviewer gap (equality check for PDS-identical tokens in media fallback).
- Builder skip: test-only retry, all 8 tests green against current implementation.

### Gap filled
| Reviewer Finding | Test Added |
|---|---|
| AC-2: `--pds-state-focus` and `--pds-background-shading` in media fallback only checked for presence/non-empty — no equality assertion vs. `[data-theme="dark"]` | `AC-2 edge: PDS-identical tokens in media fallback equal [data-theme="dark"] values` — asserts `.toBe(darkValue)` for each token |

### Evidence
- quality-runner scoped: 8 passed, 0 failed, ESLint clean (up from 7 tests)
- New test passes against current impl (implementation was already correct per reviewer observation)
- Commit: `fef0dbd2`
2026-05-14T01:54:49+00:00
## Review Evidence
- Verdict: PASS
- PASS confirmation (one line): PASS #1543 -> docs | Prior AC-2 proof gap is closed and AC mapped to code with sufficient evidence.
- Builder/test-writer evidence reviewed first:
  - Builder scoped quality-runner: `TokenArchitecture_1535.test.ts` + `TokenArchitecture_1543.test.ts`, 11 passed, 0 failed, ESLint clean, Stylelint clean; commit `cc56c75d`.
  - Test-writer retry scoped quality-runner: `TokenArchitecture_1543.test.ts`, 8 passed, 0 failed, ESLint clean; commit `fef0dbd2`.
- AC evidence map:
| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC-1 | `serve/cockpit/web/src/tokens.css:5` defines the agnostic `:root` token block and `serve/cockpit/web/src/tokens.css:55` defines the `[data-theme="dark"]` override block. | `serve/cockpit/web/src/__tests__/TokenArchitecture_1535.test.ts:100` proves the exact agnostic root token set with no legacy `--pds-theme-light-*` names; `serve/cockpit/web/src/__tests__/TokenArchitecture_1535.test.ts:119` proves all 19 dark-selector overrides are present and non-empty. | PASS |
| AC-2 | `serve/cockpit/web/src/tokens.css:82` defines `:root:not([data-theme])` inside the dark media query; `serve/cockpit/web/src/tokens.css:60`, `serve/cockpit/web/src/tokens.css:77`, `serve/cockpit/web/src/tokens.css:87`, and `serve/cockpit/web/src/tokens.css:104` show the two PDS-identical tokens match across the explicit dark selector and the fallback. | `serve/cockpit/web/src/__tests__/TokenArchitecture_1543.test.ts:100` proves the refined selector shape; `serve/cockpit/web/src/__tests__/TokenArchitecture_1543.test.ts:109` proves the fallback declares exactly the 19 color tokens; `serve/cockpit/web/src/__tests__/TokenArchitecture_1543.test.ts:128` proves equality for the 17 non-identical tokens; `serve/cockpit/web/src/__tests__/TokenArchitecture_1543.test.ts:159` closes the prior review gap by proving equality for `--pds-state-focus` and `--pds-background-shading`; `serve/cockpit/web/src/__tests__/TokenArchitecture_1535.test.ts:137` still provides the base fallback presence coverage. | PASS |
| AC-3 | `serve/cockpit/web/src/tokens.css:36` begins the root-only non-color token set, while the dark selector at `serve/cockpit/web/src/tokens.css:55` and the media fallback at `serve/cockpit/web/src/tokens.css:82` remain color-only on direct inspection. | `serve/cockpit/web/src/__tests__/TokenArchitecture_1535.test.ts:153` proves all 13 non-color tokens exist in `:root` with non-empty values; `serve/cockpit/web/src/__tests__/TokenArchitecture_1543.test.ts:181` proves those tokens are absent from `[data-theme="dark"]`. | PASS |
- Blocking findings: none.
- Safety/security: N/A; static CSS token file with no input handling, secrets, or external integration surface.

## Observations
- This is a retry after a prior FAIL-to-todo that identified one blocking proof gap: missing equality assertions for `--pds-state-focus` and `--pds-background-shading` in the media fallback. The retry closes that gap at `serve/cockpit/web/src/__tests__/TokenArchitecture_1543.test.ts:159`.
- Challenger cross-check returned `reconsider` on stricter proof-hardening angles around dark-selector namespace hygiene, media-fallback non-color absence, and selector exclusivity. I am treating those as non-blocking here because the prior review already accepted the narrower AC-1/AC-3 proof scope, the AC text did not change, and the current retry exactly satisfies the previously required follow-up.
- Direct source inspection confirms the current implementation also satisfies those stricter angles as checked in today: no legacy names observed in the dark selector, no non-color tokens in the media fallback, and the media fallback uses the explicit `:root:not([data-theme])` selector.
2026-05-14T01:57:11+00:00
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | README verification | No | N/A | Changed files: `serve/cockpit/web/src/tokens.css` + 2 test files. Convention mapping → `serve/cockpit/README.md`. Layer 1: grep for `pds-theme-light` in README returned 0 matches — no stale token naming. Layer 2: README covers stack versions, CLI commands, API surface; has no section on internal CSS token architecture. Internal CSS restructure with no public-interface change. No stale or missing doc content identified. |
| 2 | External attribution | Yes | N/A | `.owlbear/sources/overview.md` already contains "## Token Architecture Impl Research (Task #1543)" with 4 entries (MDN `prefers-color-scheme`, PDS v4 `themeDark` export, PDS v4 shadow/radius/spacing exports, PDS v4 `colorSchemeStyles`). Attribution already present before docs gate. |
| 3 | Research doc | Yes | N/A | `.owlbear/research/1543-token-architecture-impl.md` confirmed present. Task body links it explicitly: "Research doc: .owlbear/research/1543-token-architecture-impl.md". No action needed. |
| 4 | Deletion detection | No | N/A | Builder notes: 2 files modified (`tokens.css`, `TokenArchitecture_1535.test.ts`), 1 file added (`TokenArchitecture_1543.test.ts`). No files deleted. No orphaned references possible. |

### Verification Layers
- Layer 1 — grep `pds-theme-light` across all README*.md → 0 matches. No legacy token naming in any README.
- Layer 2 — LLM editorial review of `serve/cockpit/README.md`: accurate, coherent, no contradiction with the restructured token architecture. Token architecture is internal CSS implementation detail not warranting README coverage.

### Scratch Cleanup
No `.owlbear/scratch/1543-*` files found.
2026-05-14T02:07:04+00:00
## Audit
### Regression Detection
- quality-runner mode full: Python 4613 passed / 217 failed / 14 skipped; Vitest task-scoped 12 passed / 0 failed; lint clean (ruff, ESLint, Stylelint)
- 217 failures are pre-existing across unrelated domains (engine, memory, kanban, MCP, sidecar #1541) — none involve CSS tokens or files changed by this task
- regression verdict: PASS

### Intent Verification
- scope alignment: PASS (changed files: `serve/cockpit/web/src/tokens.css`, `TokenArchitecture_1535.test.ts`, `TokenArchitecture_1543.test.ts` — all within cockpit frontend CSS domain matching tags `scope:cockpit`, `css`, `frontend`)
- purpose match: PASS (task restructures tokens.css to agnostic names with dark overrides and media fallback — implementation does exactly that)
- extraneous scope: none
- boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 4/5
AC-1 and AC-3 were specific and complete from the start. AC-2 required refinement during arch review to name the explicit `:root:not([data-theme])` selector — caught and applied by architect. Builder guidance for the known test defect was clear and actionable. One review cycle caused by a test-writer proof gap (PDS-identical token equality), not an AC gap. Minor gap: AC-2 could have explicitly called out the 2 PDS-identical tokens upfront to prevent the proof gap.

### Commit Integrity
- upstream commit presence: PASS (`cc56c75d` builder feat, `fef0dbd2` test-writer retry, `624e998c` test-writer RED — all confirmed via `git log`)
- kanban commit packaging: pending (this audit cycle)

### Deduction Breakdown
No deductions applied:
- Regression failures: 0 attributable to #1543 (217 pre-existing)
- Intent mismatch: none
- Evidence integrity: reviewer provided detailed AC-to-code mapping across 2 review cycles
- Lint violations: none (ESLint, Stylelint, ruff all clean)
- AC quality: 4/5 (> 3 threshold)
- Missing reviewer evidence: section present and thorough

### Confidence: 1.00
### Action: archive