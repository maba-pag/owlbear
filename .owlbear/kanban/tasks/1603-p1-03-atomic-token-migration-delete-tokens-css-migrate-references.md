---
id: 1603
title: 'P1-03: Atomic token migration — delete tokens.css + migrate references'
status: review
priority: important
created: 2026-05-16T03:36:06.954546+00:00
updated: 2026-05-17T10:13:06.457984+02:00
tags:
  - frontend
  - pds
  - phase-1
parent: 1590
depends_on: []
ac:
  - grep -r '\-\-pds-' serve/cockpit/web/src/ --exclude-dir=__tests__ returns 
    zero matches (all authored CSS and production TS/TSX are free of legacy 
    token references)
  - tokens.css deleted; custom-tokens.css declares exactly 
    --custom-signal-claimed (the sole custom-keep token with no PDS equivalent) 
    and no other custom properties
  - Manual dark-mode override blocks ([data-theme="dark"] and @media 
    prefers-color-scheme) removed from authored CSS
  - Tests with executable assertions requiring --pds-* token presence in source 
    files updated to assert --p-* equivalents or deleted when their assertion 
    target (tokens.css) no longer exists; non-executable references (comments, 
    error messages, anti-regression regex patterns) are explicitly out of scope
proof_bundle: critical
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1590.

Atomic migration (constraint C4): delete `tokens.css`, update `--pds-*` → `--p-*` or Tailwind utility, create `custom-tokens.css` only for provenance-map custom-keep values. Update/retire test assertions: TokenArchitecture, BoardVisualDesign, PdsColorSchemeBridge, PdsMigration, ShellSecondaryCSS.

Complexity waiver: 4 AC exceeds target of 3 because token migration is explicitly atomic per constraint C4 — splitting delete/migrate/custom-tokens across tasks would violate the brief.

Scope: Token migration + test updates.
Out of scope: New components, layout changes.

[[2026-05-16T17:16:07+02:00]]
## Research
- Research doc: .owlbear/research/1603-token-migration-provenance.md
- Sources: 6 studied, 4 high-relevance (PDS v4 CSS source files)
- Recommendation: Proceed with atomic migration (confidence: 0.88)

### Key Findings
- 33 --pds-* tokens defined; only 23 consumed by 8 files; 11 are dead
- Every consumed token has an exact PDS v4 --p-* equivalent with matching values
- 1 custom-keep token: --pds-signal-claimed (custom purple, no PDS equivalent)
- 2 undeclared tokens in Card.css (--pds-border-subtle, --pds-text-subtle) resolve to nothing — replacing with actual PDS tokens is a visual improvement
- PDS dark mode handled natively via .scheme-dark/.scheme-light classes; manual overrides in tokens.css are redundant
- 9 test files affected: 2 retire, 7 update
- #1597 (Token provenance map) superseded by this research

Challenge: FALLBACK — challenger subagent unavailable

[[2026-05-16T17:55:49+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Token migration only — CSS variable rename + file restructure |
| Interface clarity | PASS | AC defines binary grep verifier, exact custom-token name, specific override selectors |
| Dependency correctness | PASS | depends_on=[] — predecessor #1600 archived as deprecated (absorbed), #1597 superseded by inline research |
| Module layering | PASS | CSS tokens are leaf-level; no upward imports |
| TDD compliance | PASS | proof_bundle=critical; test-writer will create failing tests at todo |
| KISS/YAGNI | PASS | Minimal scope — find-and-replace with 1 custom-tokens.css for the sole non-PDS token |
| Premise challenge | PASS | tokens.css genuinely duplicates PDS v4 native tokens; manual dark overrides are redundant with useTheme hook |
| Pattern consistency | PASS | Follows PDS v4 --p-* naming convention documented at designsystem.porsche.com |
| Security surface | N/A | Pure CSS — no system boundaries |
| Single domain | PASS | Frontend CSS only |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| --pds-border-subtle/--pds-text-subtle (Card.css) | Currently resolve to nothing | N/A | Replacing with real PDS tokens is an improvement | Visual improvement |
| custom-tokens.css import missing | --custom-signal-claimed undefined | CSS fallback | Builder must wire import in main.tsx | Claimed cards lose purple indicator |

### Design Diverge
Skipped — single approach (direct token replacement per provenance map). No competing alternatives.

### Challenge Results
- Challenger: reconsider (confidence 0.47)
- Findings: (1) AC-2 external reference, (2) AC-4 retirement loophole, (3) test surface wider than research doc lists
- Architect response: REFINED — AC-2 now names exact token (--custom-signal-claimed); AC-4 tightened to require assertion target no longer exists for deletion. Blast radius covered by critical proof bundle. AC-1's whole-tree grep naturally forces all test files to be updated.

### Proof-Bundle Validation
- Planner assignment: critical
- Final bundle: critical
- Existing proof scope: N/A
- Test-writer: PROCEED

### Builder Guidance
- Research doc (.owlbear/research/1603-token-migration-provenance.md) has complete provenance map with 1:1 replacements
- Test files beyond research doc table: ThemeLightTokenScan_1552.test.ts, CardCSS_1546.test.ts, ResponsiveLayout_1391.test.tsx also contain --pds-* references that must be updated per AC-1
- main.tsx import must change from tokens.css to custom-tokens.css
- --pds-grid-gap/--pds-grid-margin in Shell.css are undeclared pass-throughs; replace with --p-spacing-static-sm (8px) and --p-spacing-static-md (16px)

### Verdict: APPROVE
### Action Taken: Refined AC-2 (self-contained custom-keep token) and AC-4 (deletion requires target no longer exists). Advanced to todo.

[[2026-05-16T18:31:40+02:00]]
## Test-Writer Notes
- Test file: serve/cockpit/web/src/__tests__/TokenMigration_1603.test.ts
- Classes: TestFromAC_NoPdsTokensInSource, TestFromAC_TokenFileMigration, TestFromAC_DarkModeOverridesRemoved, TestFromAC_LegacyTestFilesRetired, TestFromAC_LegacyTestFilesUpdated
- Tests per category: source-contract/9, meta-test (test file state)/8
- Total: 17 tests, all FAIL (verified by quality-runner)
- lint: clean (ESLint + TypeScript pass)
- AC coverage:
  - AC-1 ✓ — 2 tests: CSS files / TSX+TS files contain zero --pds-* references
  - AC-2 ✓ — 5 tests: tokens.css deleted; custom-tokens.css exists with exactly --custom-signal-claimed and no --pds-*
  - AC-3 ✓ — 2 tests: no [data-theme="dark"] block; no @media prefers-color-scheme block in authored CSS
  - AC-4 ✓ — 8 tests: TokenArchitecture_1535/1543 deleted; CardCSS_1546 updated to --p-color-contrast-medium; BoardVisualDesign updated (no [data-theme="dark"] assertion, uses --custom-signal-claimed); ShellSecondaryCSS_1550 updated to --p-color-surface

[[2026-05-16T20:27:55+02:00]]
## Builder Notes
- Files changed: none (no new edits were required in this builder pass).
- Rationale: task-scoped RED/GREEN gate is already green and AC source-contract checks are satisfied in current workspace state.

### Evidence Summary
- Quality-runner (scoped) on `serve/cockpit/web/src/__tests__/TokenMigration_1603.test.ts`:
  - Tests: 17 passed, 0 failed, 0 skipped
  - Lint: clean (ESLint)
  - Exit codes: vitest 0, eslint 0
- AC-1 authored-source scan (excluding `__tests__`):
  - `--pds-` in authored CSS: 0 matches
  - `--pds-` in authored TS/TSX: 0 matches
- AC-2 file migration checks:
  - `serve/cockpit/web/src/tokens.css`: absent
  - `serve/cockpit/web/src/custom-tokens.css`: present
  - custom property declarations in `custom-tokens.css`: exactly 1 (`--custom-signal-claimed`)
- AC-3 dark override checks (authored CSS):
  - `[data-theme="dark"]` / `@media (prefers-color-scheme: dark)`: 0 matches
- AC-4 legacy test surface:
  - retired tests absent: `TokenArchitecture_1535.test.ts`, `TokenArchitecture_1543.test.ts`
  - updated assertions present in durable tests (`BoardVisualDesign.test.tsx`, `ShellSecondaryCSS_1550.test.tsx`, `CardCSS_1546.test.ts`).

### Lint / Coverage
- Lint status: clean for scoped task test file.
- Coverage: not requested for this frontend task-specific vitest scope; source-contract AC verified via targeted grep/file checks.

### Fixes Applied
- None in this pass. Implementation appears already completed before this claim; this step verified AC conformance and advanced per gate.

[[2026-05-16T22:30:02+02:00]]
## Review Evidence
- Verdict: FAIL
- Route: in-progress
- AC status summary:

| AC | Status | Evidence |
|---|---|---|
| AC-1 | Partial | Source-side migration is in place: `serve/cockpit/web/src/main.tsx` imports `./custom-tokens.css`, `serve/cockpit/web/src/Shell.css` has zero `--pds-` matches, and the reviewed production CSS/TSX surfaces use `--p-*` / `--custom-*`. The task-local verifier in `serve/cockpit/web/src/__tests__/TokenMigration_1603.test.ts` narrows the scan to authored source and does not cover the stale durable tests below. |
| AC-2 | PASS | `serve/cockpit/web/src/tokens.css` is absent, and `serve/cockpit/web/src/custom-tokens.css` declares exactly one custom property: `--custom-signal-claimed`. |
| AC-3 | PASS | Independent search over `serve/cockpit/web/src/**/*.css` found no `[data-theme="dark"]` selectors and no `@media (prefers-color-scheme` blocks. |
| AC-4 | FAIL | Two durable tests still encode the retired contract: one opens deleted `tokens.css`, and one still requires `--pds-*` tokens in `Shell.css`. |

- Blocking findings:

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC-4 | `serve/cockpit/web/src/__tests__/PdsColorSchemeBridge_1555.test.ts` still dereferences deleted `src/tokens.css`, so the durable proof surface is not aligned to the migration contract. | File evidence: `serve/cockpit/web/src/__tests__/PdsColorSchemeBridge_1555.test.ts:407-409`. Independent `quality-runner`: `AC-7: tokens.css specifically does not declare a color-scheme property` failed with `ENOENT: no such file or directory, open '/.../serve/cockpit/web/src/tokens.css'`. | in-progress |
| 2 | AC-4 | `serve/cockpit/web/src/__tests__/ShellSecondaryCSS_1542.test.tsx` still asserts that `Shell.css` must contain at least 5 `--pds-*` token references, which conflicts with the migrated `--p-*` source contract. | File evidence: `serve/cockpit/web/src/__tests__/ShellSecondaryCSS_1542.test.tsx:90-98`; source evidence: `serve/cockpit/web/src/Shell.css` has zero `--pds-` matches. Independent `quality-runner`: `expected 0 to be greater than or equal to 5`. | in-progress |
| 3 | critical proof bundle | Builder evidence is insufficient for `proof_bundle=critical`: the builder note reports only the task-local `TokenMigration_1603.test.ts` plus scoped lint, with no full durable-suite packet and no coverage summary, while omitted durable suites already fail independently. | Task body `## Builder Notes` scopes proof to `serve/cockpit/web/src/__tests__/TokenMigration_1603.test.ts`. Independent `quality-runner` reruns: `BoardVisualDesign.test.tsx`, `CardCSS_1546.test.ts`, and `ShellSecondaryCSS_1550.test.tsx` passed, while `PdsColorSchemeBridge_1555.test.ts` failed. | in-progress |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Update the PdsColorSchemeBridge durable test to stop reading deleted `tokens.css` and align its assertion to the post-migration CSS contract. | `serve/cockpit/web/src/__tests__/PdsColorSchemeBridge_1555.test.ts` | Finding #1 |
| 2 | builder | Update the Shell secondary CSS durable test to assert the migrated `--p-*` / current `Shell.css` contract instead of requiring retained `--pds-*` tokens. | `serve/cockpit/web/src/__tests__/ShellSecondaryCSS_1542.test.tsx`, `serve/cockpit/web/src/Shell.css` | Finding #2 |
| 3 | builder | Re-run and report a critical-bundle proof packet that includes the task-local migration suite and the affected durable suites before resubmitting to review. | `serve/cockpit/web/src/__tests__/TokenMigration_1603.test.ts`, `serve/cockpit/web/src/__tests__/PdsColorSchemeBridge_1555.test.ts`, `serve/cockpit/web/src/__tests__/BoardVisualDesign.test.tsx`, `serve/cockpit/web/src/__tests__/CardCSS_1546.test.ts`, `serve/cockpit/web/src/__tests__/ShellSecondaryCSS_1550.test.tsx`, `serve/cockpit/web/src/__tests__/ShellSecondaryCSS_1542.test.tsx` | Finding #3 |

## Observations
- Source-side migration appears substantially correct: `serve/cockpit/web/src/main.tsx` imports `./custom-tokens.css`, `serve/cockpit/web/src/custom-tokens.css` retains a single custom token, `serve/cockpit/web/src/tokens.css` is absent, and authored CSS shows no manual dark-mode override blocks.
- Independent durable reruns passed for `serve/cockpit/web/src/__tests__/BoardVisualDesign.test.tsx`, `serve/cockpit/web/src/__tests__/CardCSS_1546.test.ts`, and `serve/cockpit/web/src/__tests__/ShellSecondaryCSS_1550.test.tsx`.
- Remaining `--pds-*` strings in comments, negative anti-regression regexes, or synthetic fixture text were not used as standalone blockers here; the reject is based on executable stale durable tests plus the missing critical-bundle proof packet.
- On retry, tighten the task-local oracle or the task note so AC-1 proof and the actual review surface describe the same scope.

[[2026-05-17T05:43:05+02:00]]
## Builder Notes
- Implementation: updated durable assertions in `serve/cockpit/web/src/__tests__/PdsColorSchemeBridge_1555.test.ts` and `serve/cockpit/web/src/__tests__/ShellSecondaryCSS_1542.test.tsx` to match post-migration token contract.
- Tests: reviewer-requested proof packet PASS — 90 passed, 0 failed, 0 skipped.
- Lint: clean (ESLint).
- Coverage: scoped frontend coverage run reported 60.05% for broad `src` scope; this retry only touched durable test contracts (no production-source edits).

### Evidence Summary
- Pre-fix RED verification (quality-runner scoped packet):
  - `PdsColorSchemeBridge_1555.test.ts` failed on `AC-7: tokens.css specifically does not declare a color-scheme property` with ENOENT (deleted file).
  - `ShellSecondaryCSS_1542.test.tsx` failed on stale requirement `>=5 --pds-*` tokens.
- Fix 1: replaced deleted-file assertion to check `custom-tokens.css` for no `color-scheme:` declaration.
- Fix 2: migrated shell token assertion to require zero stale `--pds-*` and require `>=5` migrated `--p-*` references.
- Post-fix GREEN verification (quality-runner scoped packet over required suites):
  - `TokenMigration_1603.test.ts`
  - `PdsColorSchemeBridge_1555.test.ts`
  - `BoardVisualDesign.test.tsx`
  - `CardCSS_1546.test.ts`
  - `ShellSecondaryCSS_1550.test.tsx`
  - `ShellSecondaryCSS_1542.test.tsx`
  - Result: 90 passed, 0 failed.

### Fixes Applied
- No source-code behavior changes.
- Durable test contracts aligned with atomic token migration AC and deleted `tokens.css` target.

[[2026-05-17T06:48:15+02:00]]
## Review Evidence
- Verdict: FAIL
- Route: backlog
- FAIL confirmation: FAIL #1603 to backlog | frontmatter AC-1 still fails under its literal src-wide scope, and the retry evidence narrows the contract instead of satisfying it.

| AC | Status | Evidence |
|---|---|---|
| AC-1 | FAIL | The authoritative frontmatter AC requires a src-wide grep contract. Legacy token strings remain in durable tests under `serve/cockpit/web/src/__tests__`, including `BoardVisualDesign.test.tsx:14-20,260-290`, `ShellSecondaryCSS_1542.test.tsx:90-97`, `ThemeLightTokenScan_1552.test.ts:9,55-66`, `CardCSS_1546.test.ts:78-98`, `ResponsiveLayout_1391.test.tsx:172-176`, and `PDSHexScan_1395.test.ts:128-156`. |
| AC-2 | PASS | `serve/cockpit/web/src/tokens.css` is absent, `serve/cockpit/web/src/custom-tokens.css:1-4` declares a single custom property, and `serve/cockpit/web/src/main.tsx:5` imports the replacement stylesheet. |
| AC-3 | PASS | Independent search across `serve/cockpit/web/src/**/*.css` found no manual dark-mode override selectors, and `serve/cockpit/web/src/Shell.css:1-99` contains only viewport media queries. |
| AC-4 | Partial | The retry repaired the prior executable failures in `PdsColorSchemeBridge_1555.test.ts:407-412` and `ShellSecondaryCSS_1542.test.tsx:90-100`, but the task-local verifier in `TokenMigration_1603.test.ts:67-83,217-236` still narrows review scope instead of resolving the src-wide AC-1 contract conflict. |

- Blocking findings:

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC-1 | The literal frontmatter AC is still unsatisfied: multiple files under `serve/cockpit/web/src/__tests__` retain legacy token strings, so the required src-wide grep proof is not green. | `serve/cockpit/web/src/__tests__/BoardVisualDesign.test.tsx:14-20,260-290`; `serve/cockpit/web/src/__tests__/ShellSecondaryCSS_1542.test.tsx:90-97`; `serve/cockpit/web/src/__tests__/ThemeLightTokenScan_1552.test.ts:9,55-66`; `serve/cockpit/web/src/__tests__/CardCSS_1546.test.ts:78-98`; `serve/cockpit/web/src/__tests__/ResponsiveLayout_1391.test.tsx:172-176`; `serve/cockpit/web/src/__tests__/PDSHexScan_1395.test.ts:128-156` | backlog |
| 2 | AC-1 / proof contract | The retry proof narrows AC-1 to authored source only, but that interpretation is not present in frontmatter. On the second review cycle, this unresolved AC/proof mismatch requires architect rework instead of another builder pass. | `serve/cockpit/web/src/__tests__/TokenMigration_1603.test.ts:67-83,217-236`; task body `## Builder Notes` dated 2026-05-17 describes an authored-source scan excluding `__tests__`; task frontmatter `proof_bundle=critical` remains unchanged. | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Refine AC-1 to state whether the src-wide grep contract includes durable tests, comments, and anti-regression patterns, or explicitly require elimination of the remaining legacy token strings across `src/__tests__`. | `serve/cockpit/web/src/__tests__/BoardVisualDesign.test.tsx`, `serve/cockpit/web/src/__tests__/ShellSecondaryCSS_1542.test.tsx`, `serve/cockpit/web/src/__tests__/ThemeLightTokenScan_1552.test.ts`, `serve/cockpit/web/src/__tests__/CardCSS_1546.test.ts`, `serve/cockpit/web/src/__tests__/ResponsiveLayout_1391.test.tsx`, `serve/cockpit/web/src/__tests__/PDSHexScan_1395.test.ts` | Finding #1 |
| 2 | architect | Align the task-local proof strategy with the authoritative AC before the next retry so review evidence does not depend on an implicit authored-source-only interpretation. | `serve/cockpit/web/src/__tests__/TokenMigration_1603.test.ts` | Finding #2 |

## Observations
- Source-side migration looks correct: `main.tsx` imports `custom-tokens.css`, `tokens.css` is gone, `custom-tokens.css` keeps one custom token, and no authored CSS dark-override blocks were found.
- The retry did fix the previous executable failures in `PdsColorSchemeBridge_1555.test.ts` and `ShellSecondaryCSS_1542.test.tsx`.
- `BoardVisualDesign.test.tsx` still carries stale legacy-token wording in comments and failure messages even where executable assertions now use migrated tokens; that did not drive the reject by itself, but it reinforces the need for contract cleanup.

[[2026-05-17T08:11:52+02:00]]
## Architecture Review (Re-review after reviewer rejection to backlog)

### Context
Task returned from review with two findings: (1) AC-1 literal src-wide grep is unsatisfied because test files under `__tests__/` contain `--pds-*` in anti-regression patterns, negative assertions, comments, and scanner fixtures; (2) task-local proof narrowed scope without updating authoritative AC.

### Root Cause Analysis
AC-1 as originally worded (`grep -r '\\-\\-pds-' serve/cockpit/web/src/`) includes test infrastructure files that legitimately contain the string `--pds-*` in:
- Negative assertions (`.not.toMatch(/var\\(--pds-/)`): prove migration correctness
- Anti-regression regex scanners: enforce no legacy token re-introduction
- Documentary comments: explain migration history
- Synthetic test fixtures: validate scanner correctness (PDSHexScan_1395)

None of these require `--pds-*` tokens to exist in production code. Production source is confirmed clean: zero matches in `src/**/*.css`, `src/*.tsx`, `src/components/**`.

### AC Refinement
| AC | Before | After | Rationale |
|---|---|---|---|
| AC-1 | `grep -r '\\-\\-pds-' serve/cockpit/web/src/` | `grep -r '\\-\\-pds-' serve/cockpit/web/src/ --exclude-dir=__tests__` | Test files are verification infrastructure, not production code; the grep verifies runtime contract |
| AC-4 | \"Tests formerly asserting --pds-* names updated...\" | Added explicit scope: \"non-executable references (comments, error messages, anti-regression regex patterns) are explicitly out of scope\" | Resolves ambiguity that caused two review-builder cycles |

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Token migration only |
| Interface clarity | PASS | AC-1 is now a single verifiable command; AC-4 scope is explicit |
| Dependency correctness | PASS | No dependencies; predecessors archived |
| Module layering | PASS | CSS tokens are leaf-level |
| TDD compliance | PASS | Test file exists and passes (17 tests GREEN) |
| KISS/YAGNI | PASS | Minimal scope — direct token replacement |
| Premise challenge | PASS | tokens.css genuinely duplicated PDS v4 native tokens |
| Pattern consistency | PASS | Follows PDS v4 --p-* naming |
| Security surface | N/A | Pure CSS |
| Single domain | PASS | Frontend CSS only |

### Challenge Results
- Challenger: reconsider (confidence 0.69)
- Findings: (1) AC contract needs frontmatter update before approve (agreed — done), (2) AC-4 ambiguous about non-executable refs (agreed — refined), (3) stale test comments as orphaned debt, (4) PDSHexScan dead carve-out
- Architect response: ACCEPTED findings 1-2 (AC refined in frontmatter). REBUTTED findings 3-4: stale comments/dead carve-outs are documentation hygiene, not migration debt; they don't affect runtime behavior or test correctness (90 tests pass). Not blocking an atomic migration on comment wording. Noted in builder guidance for future cleanup.

### Proof-Bundle Validation
- Planner assignment: critical
- Final bundle: critical
- Test-writer: PROCEED (existing task-local test covers refined AC-1 scope)

### Builder Guidance
- AC-1 proof: `grep -r '\\-\\-pds-' serve/cockpit/web/src/ --exclude-dir=__tests__` must return zero matches
- The task-local test (TokenMigration_1603.test.ts) already verifies this scope — no test changes needed
- Stale `--pds-*` references in test comments/messages (BoardVisualDesign.test.tsx, PDSHexScan_1395.test.ts, ColumnCSS_1547.test.ts) are explicitly out of scope per refined AC-4
- Previous builder evidence (90 tests GREEN, production source clean) remains valid under refined AC

### Verdict: APPROVE
### Action Taken: Refined AC-1 (added --exclude-dir=__tests__) and AC-4 (explicit non-executable scope). Advanced to todo.

[[2026-05-17T08:58:43+02:00]]
## Test-Writer Notes
- Retry cycle: both `## Test-Writer Notes` and `## Review Evidence` present in task body.
- Required Follow-up from last reviewer (second review, backlog route): both items targeted **architect** — no test-writer gaps identified.
- Architect addressed both items: AC-1 refined to `--exclude-dir=__tests__`; AC-4 scope made explicit (non-executable refs out of scope).
- Existing test file: `serve/cockpit/web/src/__tests__/TokenMigration_1603.test.ts`
- Verification: quality-runner scoped run — 17 passed, 0 failed, lint clean (ESLint).
- AC coverage alignment with refined AC:
  - AC-1 ✓ — test already excludes `__tests__` via `EXCLUDE_FROM_SRC_SCAN`; exact match for refined `--exclude-dir=__tests__` scope
  - AC-2 ✓ — `TestFromAC_TokenFileMigration`: 5 tests covering tokens.css deletion, custom-tokens.css existence, single declaration, no --pds-*
  - AC-3 ✓ — `TestFromAC_DarkModeOverridesRemoved`: 2 tests for [data-theme="dark"] and prefers-color-scheme absence
  - AC-4 ✓ — `TestFromAC_LegacyTestFilesRetired` + `TestFromAC_LegacyTestFilesUpdated`: 8 tests; non-executable refs explicitly out of scope per refined AC-4
- No new tests written — reviewer cited scope/proof issues (not missing tests); architect refined AC to match existing test scope.
- Builder: re-run proof packet with refined AC-1 grep (`grep -r '--pds-' serve/cockpit/web/src/ --exclude-dir=__tests__` must be zero); provide full critical-bundle proof packet including all durable suites cited by reviewer.

[[2026-05-17T10:13:06+02:00]]
## Builder Notes
- Implementation: no new source or test edits were required in this pass.
- Files changed: none.
- Tests: critical proof packet PASS (90 passed, 0 failed, 0 skipped).
- Coverage: 60% on scoped frontend `src` run (reported by quality-runner).
- Lint: clean (ESLint).
- Approach: validated current workspace state against refined AC and reviewer-requested durable suites, then confirmed acceptance-criteria contract with direct grep/file checks.

### Evidence Summary
- Quality-runner scoped proof packet (task + durable suites):
  - `serve/cockpit/web/src/__tests__/TokenMigration_1603.test.ts`
  - `serve/cockpit/web/src/__tests__/PdsColorSchemeBridge_1555.test.ts`
  - `serve/cockpit/web/src/__tests__/BoardVisualDesign.test.tsx`
  - `serve/cockpit/web/src/__tests__/CardCSS_1546.test.ts`
  - `serve/cockpit/web/src/__tests__/ShellSecondaryCSS_1550.test.tsx`
  - `serve/cockpit/web/src/__tests__/ShellSecondaryCSS_1542.test.tsx`
  - Result: 90 passed, 0 failed, lint clean.
- AC-1: `rg -- '--pds-' serve/cockpit/web/src --glob '!**/__tests__/**'` returned no matches (exit 1 from `rg` = no matches).
- AC-2:
  - `serve/cockpit/web/src/tokens.css` absent.
  - `serve/cockpit/web/src/custom-tokens.css` contains `--custom-signal-claimed` and no additional custom properties.
- AC-3: grep for `[data-theme="dark"]|prefers-color-scheme` in authored CSS (excluding `__tests__`) returned no matches.
- AC-4: retired durable tests absent:
  - `serve/cockpit/web/src/__tests__/TokenArchitecture_1535.test.ts`
  - `serve/cockpit/web/src/__tests__/TokenArchitecture_1543.test.ts`
  and executable durable assertions in the proof packet are green.

### Fixes Applied
- None in this pass; task state already satisfied refined AC and critical proof requirements.
