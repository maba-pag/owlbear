---
id: 1535
title: 'P1-01: test — token architecture: agnostic rename + expansion + dark overrides'
status: archived
priority: medium
created: 2026-05-13T18:41:58.189617+00:00
updated: 2026-05-13T23:13:03.081498+00:00
tags:
  - phase-1
  - scope:cockpit
  - css
  - test
  - frontend
parent: 1534
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
Brief: see parent #1534 (`.owlbear/briefs/draft-board-visual-design/brief.md`)

## Scope
- **In:** Tests for token rename from `--pds-theme-light-*` to `--pds-*`, dark override selectors (including OS fallback), new non-color token sets
- **Out:** Implementation of tokens, theme bootstrap, component CSS

## Acceptance Criteria

- AC-1: Vitest verifies `:root` declares exactly these 19 agnostic `--pds-*` color tokens (no `--pds-theme-light-*` names remain): `--pds-primary`, `--pds-background-{base,surface,shading}`, `--pds-contrast-{low,medium,high}`, `--pds-notification-{success,success-soft,warning,warning-soft,error,error-soft,info,info-soft}`, `--pds-state-{hover,active,focus,disabled}`
- AC-2: Vitest verifies `[data-theme="dark"]` selector overrides all 19 color tokens with non-empty values that differ from their `:root` counterparts; also verifies `@media (prefers-color-scheme: dark)` fallback block declares the same 19 overrides
- AC-3: Vitest verifies non-color tokens exist in `:root` with non-empty values: `--pds-shadow-{sm,md,lg}` (3), `--pds-radius-{sm,md,lg,xl}` (4), `--pds-spacing-{xs,sm,md,lg,xl,2xl}` (6) — 13 total

Proof bundle: behavioral

## Test Approach

File-based CSS parsing (read `tokens.css` with `readFileSync`, parse `:root`, `[data-theme="dark"]`, and `@media (prefers-color-scheme: dark)` blocks via regex). Follows existing `PDSHexScan_1395.test.ts` pattern. Test file location: `src/__tests__/TokenArchitecture_1535.test.ts`.

## Research Notes

**Token count correction:** AC-1 enumerates all 19 `--pds-theme-light-*` vars from current `tokens.css`: primary (1) + background (3) + contrast (3) + notification (8) + state (4) = 19.

**AC-2 dark value verification:** Tests verify structural correctness (non-empty, differs from light) rather than exact PDS `themeDark` values. This avoids brittleness from deprecated nested `themeDark` export while catching copy-paste errors.

**AC-3 token counts:** 3 shadow + 4 radius + 6 spacing = 13 non-color tokens.

**Naming:** Tests protect the brief's `--pds-*` alias layer (not PDS v4 native `--p-*`). No naming collision.

Research doc: `.owlbear/research/1535-token-architecture-test-approach.md`

## Research
- Research doc: .owlbear/research/1535-token-architecture-test-approach.md
- Sources: 6 studied, 4 high-relevance (PDS v4 CSS vars, migration guide, tokens.css, PDSHexScan pattern)
- Recommendation: file-based CSS parsing with regex (confidence: 0.77)
- Follow-up tasks created: none needed — task already correctly scoped
- Decision requests: none

## Challenge Results
- Challenger: proceed (confidence in original: 0.77, revised from 0.85)
- Key challenges: 19-vs-17 token count discrepancy, dark value exactness, non-color subset ambiguity, regex vs CSSOM
- Researcher response: accepted — corrected count to 19, specified dark value verification against PDS themeDark export, clarified AC-3 subset (13 tokens). Rejected CSSOM approach as over-engineered.

## Key Findings
1. Actual tokens.css has 19 vars (not 17 as AC states) — tests should enumerate all 19
2. Brief's --pds-* alias layer does not collide with PDS v4 native --p-* prefix
3. PDS v4 themeDark JS export provides authoritative dark color values
4. Non-color tokens: 3 shadow + 4 radius + 6 spacing = 13 total
5. Test approach follows PDSHexScan_1395.test.ts file-based pattern
2026-05-13T19:32:14+00:00
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Test-only task; writes RED tests for token architecture |
| Interface clarity | PASS | AC enumerates exact token names, verification methods, file location |
| Dependency correctness | PASS | No deps required; this is the root foundation task |
| Module layering | PASS | Tests in `src/__tests__/`, no cross-layer imports |
| TDD compliance | PASS | This IS the RED phase; pairs with #1543 (impl) |
| KISS/YAGNI | PASS | File-based regex; no jsdom/PostCSS overhead |
| Premise challenge | PASS | Token rename is brief deliverable; tests drive implementation |
| Pattern consistency | PASS | Follows PDSHexScan readFileSync+regex scaffolding pattern |
| Security surface | N/A | No system boundaries; static file parsing only |
| Single domain | PASS | Frontend CSS tokens only |

### Challenge Results
- Challenger: reconsider (confidence 0.64)
- Key challenges: (1) AC-1 lacked exhaustive enumeration, (2) AC-2 missing OS-dark fallback, (3) themeDark deprecated mapping ambiguity, (4) AC-3 existence-only insufficient, (5) task body stale
- Architect response: ACCEPTED all challenges — refined AC to address each:
  - AC-1: exhaustive 19-token name list added
  - AC-2: `@media (prefers-color-scheme: dark)` fallback added + "non-empty, differs from :root" replaces fragile themeDark comparison
  - AC-3: "with non-empty values" added
  - Body: updated with authoritative refined text
- Post-refinement confidence: 0.85

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: pass-through (tag: `test`)

### Verdict: APPROVE
### Action Taken: Refined AC (17→19 count, exhaustive enumeration, OS-dark fallback, non-empty value checks, removed themeDark dependency), advanced to todo.
2026-05-13T20:01:03+00:00
## Test-Writer Notes
- Non-implementation task (tagged `test`) — no Python pytest tests applicable.
- Proof bundle: behavioral — but deliverable is frontend Vitest TypeScript tests, not pytest.
- Architect explicitly routed: "Test-writer: pass-through (tag: `test`)".
- Passing through to builder to write `src/__tests__/TokenArchitecture_1535.test.ts` per AC and Test Approach section.
2026-05-13T20:18:13+00:00
## Builder Notes
- Files changed:
  - serve/cockpit/web/src/__tests__/TokenArchitecture_1535.test.ts (new)
- Implementation summary:
  - Added `TestFromAC_TokenArchitecture_1535` Vitest coverage for AC-1/2/3 using file-based CSS parsing of `src/tokens.css`.
  - AC-1: asserts exact 19 agnostic `--pds-*` color tokens in `:root` and no legacy `--pds-theme-light-*` names.
  - AC-2: asserts `[data-theme="dark"]` overrides all 19 tokens with non-empty values different from `:root`; asserts dark OS fallback `@media (prefers-color-scheme: dark)` declares same 19 tokens with non-empty values.
  - AC-3: asserts 13 non-color tokens (`shadow/radius/spacing`) exist in `:root` with non-empty values.
- Quality-runner evidence (scoped):
  - Tests: 0 passed, 4 failed (expected RED for current implementation)
  - Failed tests:
    - AC-1 token rename set mismatch (`[]` vs expected 19)
    - AC-2 missing `[data-theme="dark"]` block
    - AC-2 missing `@media (prefers-color-scheme: dark)` block
    - AC-3 non-color token set mismatch (`[]` vs expected 13)
  - Lint: clean (`violations: none`)
  - Coverage: N/A for this RED gate
- Commit:
  - db8d89c8
  - `test: add token architecture RED checks (#1535, builder)`
- Routing rationale:
  - Task body marks this as a frontend test deliverable pass-through from test-writer notes; RED evidence captured and committed for downstream implementation task.
2026-05-13T20:58:27+00:00
## Review Evidence
- Verdict: FAIL
- FAIL route: FAIL #1535 -> todo | AC-1 exact-set proof is lax; extra agnostic color tokens would not fail.
- Builder evidence reviewed first: scoped quality-runner output is internally consistent for an expected RED task, lint is clean, commit `db8d89c8` is present in git logs, and direct file inspection matches the reported failures against the current `src/tokens.css`.
- Challenger cross-check: reconsider (confidence 0.72); retained AC-1 as the blocking finding and dropped stricter AC-2 / AC-3 interpretations as contract expansion.
- Blocking findings:
| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC-1 | The test only compares the intersection of `:root` declarations and the 19 expected names, so it proves presence but not exactness. Extra agnostic `--pds-*` color tokens would still pass even though AC-1 requires exactly these 19 tokens. | `serve/cockpit/web/src/__tests__/TokenArchitecture_1535.test.ts:100`, `serve/cockpit/web/src/__tests__/TokenArchitecture_1535.test.ts:104` | todo |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Strengthen the AC-1 assertion so it fails when `:root` contains any extra agnostic color tokens beyond the enumerated 19. | serve/cockpit/web/src/__tests__/TokenArchitecture_1535.test.ts | AC-1 proof gap at `:100` / `:104` |

## Observations
- AC-2 and AC-3 are acceptable against the task body as currently written; I did not treat stricter exclusivity or fallback-value-difference interpretations as blocking.
- `serve/cockpit/web/src/__tests__/TokenArchitecture_1535.test.ts` has no editor-reported TypeScript issues.
- Process note: this task-specific pass-through had builder authoring a frontend RED suite after test-writer pass-through. The task body is explicit, so I treated that as non-blocking local routing rather than a defect in #1535.
2026-05-13T21:29:37+00:00
## Test-Writer Notes
- Retry: Strengthened AC-1 assertion in `serve/cockpit/web/src/__tests__/TokenArchitecture_1535.test.ts`
- Gap filled: AC-1 now uses an exact-set check — extracts all `:root` tokens matching `--pds-*` that are not in `EXPECTED_NON_COLOR_TOKENS`, then asserts exact equality to the 19 expected color tokens. Extra agnostic color tokens will now cause the test to fail.
- Old logic: filtered `:root` declarations to tokens in `EXPECTED_COLOR_TOKENS` (presence/subset check only)
- New logic: filters to all `--pds-*` tokens not in non-color set → exact-set assertion
- Quality-runner evidence: 0 passed, 4 failed (all FAIL, AssertionError — expected RED)
  - AC-1: "expected [ ...(19) ] to deeply equal [ ... ]" — correct fail; legacy `--pds-theme-light-*` tokens detected as color tokens, mismatch against expected `--pds-*` names
  - AC-2/AC-3: unchanged, still fail as before
- Lint: clean (ESLint exit 0)
- Commit: c7ef94a1
- Prior 3 tests (AC-2 × 2, AC-3) preserved and still fail
2026-05-13T21:52:24+00:00
## Builder Notes
- Files changed: none in this builder pass.
- Task type confirmation: non-implementation frontend test task (`test` tag) per existing task notes.
- Verification run (quality-runner, scoped):
  - Test file: `serve/cockpit/web/src/__tests__/TokenArchitecture_1535.test.ts`
  - Tests: 0 passed, 4 failed (expected RED for this test-authoring task)
  - Failing checks:
    - AC-1 exact-set assertion fails against current legacy token architecture
    - AC-2 `[data-theme="dark"]` selector missing
    - AC-2 `@media (prefers-color-scheme: dark)` fallback missing
    - AC-3 non-color token set missing
  - Lint: clean (`eslint` exit 0)
  - Coverage: not applicable for RED proof gate
- Evidence summary:
  - Reviewer-requested AC-1 exactness gap is addressed in current test logic (exact-set extraction of `--pds-*` color tokens excluding explicit non-color set).
  - Task proof remains intentionally RED and now enforces stricter AC-1 behavior.
- Fixes applied in this pass: none required; verified and routed.
2026-05-13T22:26:56+00:00
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1535 -> docs | AC mapped to code and evidence sufficient.
- Builder evidence reviewed first: scoped quality-runner output is internally consistent for an expected RED test-authoring task (0 passed, 4 failed; lint clean; coverage N/A), and direct file inspection matches the reported failure surface against the current legacy token file.
- AC coverage map:

| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC-1 | Exact-set extraction of agnostic `--pds-*` tokens excluding the explicit non-color set, plus explicit rejection of legacy `--pds-theme-light-*` names | `serve/cockpit/web/src/__tests__/TokenArchitecture_1535.test.ts:95`, `serve/cockpit/web/src/__tests__/TokenArchitecture_1535.test.ts:105`, `serve/cockpit/web/src/__tests__/TokenArchitecture_1535.test.ts:108`, `serve/cockpit/web/src/__tests__/TokenArchitecture_1535.test.ts:110` | PASS |
| AC-2 | `[data-theme="dark"]` test proves per-token presence, non-empty values, and value difference from `:root`; fallback test proves the dark media block declares the same 19 token names with non-empty values | `serve/cockpit/web/src/__tests__/TokenArchitecture_1535.test.ts:114`, `serve/cockpit/web/src/__tests__/TokenArchitecture_1535.test.ts:124`, `serve/cockpit/web/src/__tests__/TokenArchitecture_1535.test.ts:126`, `serve/cockpit/web/src/__tests__/TokenArchitecture_1535.test.ts:130`, `serve/cockpit/web/src/__tests__/TokenArchitecture_1535.test.ts:135`, `serve/cockpit/web/src/__tests__/TokenArchitecture_1535.test.ts:141`, `serve/cockpit/web/src/__tests__/TokenArchitecture_1535.test.ts:142` | PASS |
| AC-3 | Exact expected non-color token set with non-empty per-token assertions | `serve/cockpit/web/src/__tests__/TokenArchitecture_1535.test.ts:146`, `serve/cockpit/web/src/__tests__/TokenArchitecture_1535.test.ts:152`, `serve/cockpit/web/src/__tests__/TokenArchitecture_1535.test.ts:159` | PASS |

- Proof sufficiency: the prior AC-1 exactness gap is fixed. The current assertions are falsifiable and would fail on missing or wrongly named agnostic tokens, surviving legacy names, missing dark-selector declarations, missing dark-media declarations, or missing/empty non-color tokens.
- Challenger cross-check: reconsider on a stricter fallback-vs-`:root` reading; retained PASS because the task body and prior task record make the `differs from :root` requirement explicit for `[data-theme="dark"]`, while the fallback clause is written and previously accepted as same-token-name plus non-empty proof.
- Safety & security: static CSS file parsing only; no input-handling or execution-surface concerns introduced.

## Observations
- Non-blocking: if the team wants the OS-dark fallback block to also be asserted against `:root` values or matched value-for-value with `[data-theme="dark"]`, tighten AC-2 first and then extend the test. The current task history does not make that stricter reading the operative contract.
- No editor-reported TypeScript issues in `serve/cockpit/web/src/__tests__/TokenArchitecture_1535.test.ts`.
2026-05-13T22:37:57+00:00
## Docs Gate

**Verdict: PASS — no docs impact**

### Checklist

| Item | Status | Evidence |
|------|--------|---------|
| README Verification | N/A — no update needed | Changed file `serve/cockpit/web/src/__tests__/TokenArchitecture_1535.test.ts` maps to `serve/cockpit/README.md`; Layer 1 grep shows no removed symbols/commands; Layer 2 editorial confirms README correctly describes Vitest stack and prior behavioral milestones — RED test file adds no public interface, no command, no passing behavior to document |
| External Attribution | ✓ already recorded | `sources/overview.md` has "Token Architecture Test Research (Task #1535)" with 5 PDS v4 sources |
| Research Doc | ✓ linked | `.owlbear/research/1535-token-architecture-test-approach.md` exists; linked in task body |
| Deletion Detection | N/A | No files deleted; one new test file added only |

**Files updated:** none  
**Scratch cleanup:** no `.owlbear/scratch/1535-*` files found
2026-05-13T23:13:03+00:00
## Audit
### Regression Detection
- quality-runner mode full: 6224 passed; failures are pre-existing baseline (corruption, symlink, sync-workflow, pds-build-compat, integration tests — same 214+ pattern as task 1536 baseline run). 4 TokenArchitecture_1535 failures are expected RED. ESLint violation in `computeSignal.test.ts` is unrelated to this task.
- regression verdict: PASS

### Intent Verification
- scope alignment: PASS (both commits touch only `serve/cockpit/web/src/__tests__/TokenArchitecture_1535.test.ts` — cockpit frontend test domain matches `scope:cockpit`, `css`, `test`, `frontend` tags)
- purpose match: PASS (RED Vitest tests for token architecture rename/expansion/dark overrides per AC-1/2/3)
- extraneous scope: none
- boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 4/5
AC was refined through two challenger rounds. Exhaustive 19-token enumeration, OS-dark fallback, non-empty value checks all specified. Minor gap: AC-1 didn't originally enforce exact-set semantics, requiring a reviewer-driven retry cycle to strengthen the assertion from subset to exact-set. Overall adequate.

### Commit Integrity
- upstream commit presence: PASS (`db8d89c8` builder, `c7ef94a1` test-writer retry — both scoped to single test file)
- kanban commit packaging: pending (this audit cycle)

### Deduction Breakdown
No deductions applied.

### Confidence: 1.00
### Action: archive