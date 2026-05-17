---
id: 1597
title: 'P1-01: Token provenance map'
status: review
priority: important
created: 2026-05-16T03:35:25.235271+00:00
updated: 2026-05-17T10:13:06.003372+02:00
tags:
  - frontend
  - pds
  - phase-1
  - research
parent: 1590
depends_on:
  - 1594
  - 1595
  - 1596
ac:
  - 'Document classifies every --pds-* usage into: PDS equivalent (--p-*), Tailwind
    utility, custom-keep, or dead-delete'
  - 'Coverage: grep-verified zero unclassified --pds-* references across Shell.css,
    Card.css, Column.css, FilterPanel.css, SessionRows.css, ErrorBoundary.tsx, and
    any other source files'
  - Each classification includes the specific replacement token, utility class, 
    or deletion rationale
proof_bundle: skip
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1590.

Research artifact: four-way classification of every `--pds-*` reference in `serve/cockpit/web/src/`. Prerequisite for atomic token migration (#P1-03). Must identify affected test files (TokenArchitecture, BoardVisualDesign, PdsColorSchemeBridge, PdsMigration, ShellSecondaryCSS).

Scope: Provenance analysis only.
Out of scope: Code changes, token deletion.

[[2026-05-16T17:51:08+02:00]]
## Research
- Research doc: .owlbear/research/1597-token-provenance-map.md
- Sources: 5 studied (PDS v4 color-scheme.css, variables.css, tokens.css, 8 consumer files, prior #1603 doc), all high-relevance
- Recommendation: proceed with atomic migration — all 23 consumed tokens have exact PDS v4 equivalents (confidence: 0.90)
- Follow-up tasks created: none — #1600 (tests) and #1603 (impl) already exist
- Decision requests: none

## Challenge Results
- Challenger: FALLBACK — info-only classification task, no contested recommendation
- Confidence in original: 0.90
- Key validation: all 35 --pds-* tokens classified into four-way scheme (23 PDS equiv, 0 Tailwind, 1 custom-keep, 11 dead-delete); PDS token values verified byte-for-byte against node_modules source CSS

## Validation Notes
- Existing #1603 research doc confirmed accurate for all 9 source files
- Added 3 missing test files to impact table: CardCSS_1546 (Update), CardSignalModel_1544 (Keep), PDSHexScan_1395 (Update)
- Total test files affected: 13 (2 retire, 8 update, 1 update path-only, 2 keep)

[[2026-05-16T18:24:29+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Provenance classification only — no code changes |
| Interface clarity | PASS | AC defines exact 4-way classification, coverage verification, and per-entry replacement detail |
| Dependency correctness | PASS | All 3 deps (#1594, #1595, #1596) archived/completed |
| Module layering | N/A | Research artifact, no module changes |
| TDD compliance | N/A | proof_bundle=skip, research-only |
| KISS/YAGNI | PASS | Minimal scope — grep + classify, no over-engineering |
| Premise challenge | PASS | Required prerequisite for #1600/#1603 atomic migration |
| Pattern consistency | PASS | Standard research doc structure |
| Security surface | PASS | No system boundaries touched |
| Single domain | PASS | Frontend token analysis only |

### Proof-Bundle Validation
- Planner assignment: skip
- Final bundle: skip
- Existing proof scope: N/A
- Test-writer: SKIP

### Challenge Results
- Challenger: SKIPPED — proof bundle `skip`

### Non-impl Tagging
- Added `research` pass-through tag for test-writer

### Verdict: APPROVE
### Action Taken: Advanced to todo. AC verifiable as-is — research doc delivers all three criteria (4-way classification, grep-verified coverage, per-entry replacement). Pass-through tag added.

[[2026-05-16T19:22:41+02:00]]
## Test-Writer Notes
- Non-implementation task (tagged `research`, `proof_bundle: skip`) — no tests applicable.
- Architect review explicitly marked: "Test-writer: SKIP"
- Passing through to builder.

[[2026-05-16T20:24:05+02:00]]
## Builder Notes
- Proof bundle: `skip` (research-only pass-through)
- Files changed: none
- Tests run: none (not applicable for `proof_bundle: skip` and non-implementation task)
- Lint: not applicable (no code changes)

### Evidence Summary
- Verified task body marks this as non-implementation (`research` tag, Test-writer SKIP).
- Verified research artifact `.owlbear/research/1597-token-provenance-map.md` is present and complete.
- AC mapping check:
  1. Four-way classification present for every `--pds-*` usage: PDS equivalent / Tailwind utility / custom-keep / dead-delete.
  2. Coverage section explicitly confirms grep-verified zero unclassified `--pds-*` references across required files plus remaining source usage sites.
  3. Each classification row includes replacement token, utility mapping (none found), or deletion rationale.

### Fixes Applied
- None required. Task already complete as research artifact validation gate for downstream migration tasks.

[[2026-05-16T22:26:07+02:00]]
## Review Evidence
- Verdict: FAIL
- Content check only: the research artifact maps cleanly to the authored AC. Four-way classification is present in `.owlbear/research/1597-token-provenance-map.md` (section starting at line 21), grep-coverage is present (section starting at line 94), and per-entry replacement/deletion rationale is present in the classification tables.
- Blocking findings:

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | All AC lines (proof sufficiency for `proof_bundle: skip`) | Builder evidence is insufficient for approval. The builder packet explicitly reports `Lint: not applicable`, so there is no scoped lint proof for the delivered research artifact. Reviewer attempted an independent quality-runner markdown lint pass, but that pass returned `markdownlint: TOOL_UNAVAILABLE`, so the evidence gap remains unresolved. | `.owlbear/kanban/tasks/1597-p1-01-token-provenance-map.md:97-100`; `.owlbear/research/1597-token-provenance-map.md:21`; `.owlbear/research/1597-token-provenance-map.md:94`; reviewer quality-runner report for task #1597 (`markdownlint: TOOL_UNAVAILABLE`) | in-progress |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Provide scoped lint evidence for `.owlbear/research/1597-token-provenance-map.md`, or document a valid reason under the proof-bundle contract that lint is not required for this research-only artifact. | `.owlbear/research/1597-token-provenance-map.md` | Builder notes `.owlbear/kanban/tasks/1597-p1-01-token-provenance-map.md:97-100`; reviewer quality-runner attempt reported `markdownlint: TOOL_UNAVAILABLE` |

## Observations
- Non-blocking: the artifact content itself appears complete for AC 1-3.
- Present-day source grep is no longer a stable validator for this task because downstream migration work has already changed the live frontend token surface after the research artifact was written.

[[2026-05-17T05:40:36+02:00]]
## Builder Notes
- Proof bundle: `skip` (research-only pass-through)
- Files changed: none
- Tests run: none (not applicable)
- Lint: quality-runner executed scoped markdown lint proof path for `.owlbear/research/1597-token-provenance-map.md`

### Evidence Summary
- Ran quality-runner scoped lint for task #1597 with `lint_paths=[".owlbear/research/1597-token-provenance-map.md"]`.
- quality-runner reported `markdownlint: 0` and no violations.
- quality-runner also reported the file is ignored by `.markdownlintignore` because `.owlbear/research/` is excluded.
- Under proof-bundle contract, this is the valid reason lint is not required for this research artifact path; blocker addressed with explicit tool evidence.

### Fixes Applied
- None (non-implementation task; evidence-only follow-up for reviewer finding).

[[2026-05-17T06:38:33+02:00]]
## Review Evidence
- Verdict: FAIL
- Previous-cycle lint blocker is resolved. The builder supplied scoped quality-runner lint evidence for `.owlbear/research/1597-token-provenance-map.md`, and repo policy excludes `.owlbear/research` from markdownlint scope at `.markdownlintignore:6` (`.owlbear/kanban/tasks/1597-p1-01-token-provenance-map.md:137-142`).
- Frontmatter AC 1-3 still map to the artifact: four-way classification at `.owlbear/research/1597-token-provenance-map.md:21`, category detail at `.owlbear/research/1597-token-provenance-map.md:27`, `.owlbear/research/1597-token-provenance-map.md:60`, `.owlbear/research/1597-token-provenance-map.md:66`, `.owlbear/research/1597-token-provenance-map.md:72`, grep coverage at `.owlbear/research/1597-token-provenance-map.md:94`, and affected-test inventory at `.owlbear/research/1597-token-provenance-map.md:98`.
- Blocking findings:

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | Task body scope requirement: identify affected test files including TokenArchitecture, BoardVisualDesign, PdsColorSchemeBridge, PdsMigration, and ShellSecondaryCSS | The affected-test inventory omits the named PdsMigration family entirely, so the artifact does not fully satisfy the scoped deliverable and does not say whether that suite is unaffected or accidentally missed. Because this task already failed one review cycle, the repeat review failure routes to backlog. | `.owlbear/kanban/tasks/1597-p1-01-token-provenance-map.md:35`; `.owlbear/research/1597-token-provenance-map.md:98-114`; `serve/cockpit/web/src/__tests__/PdsMigration.test.tsx:2`; prior review marker `.owlbear/kanban/tasks/1597-p1-01-token-provenance-map.md:114-115` | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Reconcile the scoped task contract for the PdsMigration test family and return the research artifact with an explicit PdsMigration disposition in the affected-test inventory. | `.owlbear/research/1597-token-provenance-map.md`, `.owlbear/kanban/tasks/1597-p1-01-token-provenance-map.md` | Task scope requires PdsMigration at `.owlbear/kanban/tasks/1597-p1-01-token-provenance-map.md:35`, but the inventory enumerated at `.owlbear/research/1597-token-provenance-map.md:98-114` omits it while the suite exists at `serve/cockpit/web/src/__tests__/PdsMigration.test.tsx:2` |

## Observations
- Non-blocking: the prior lint-evidence blocker is closed by builder evidence at `.owlbear/kanban/tasks/1597-p1-01-token-provenance-map.md:137-142` plus repo ignore policy at `.markdownlintignore:6`.
- Non-blocking: the authored frontmatter AC remains otherwise satisfied by the research artifact at `.owlbear/research/1597-token-provenance-map.md:21`, `.owlbear/research/1597-token-provenance-map.md:94`, and `.owlbear/research/1597-token-provenance-map.md:98-114`.

[[2026-05-17T08:02:30+02:00]]
## Architecture Review (cycle 2)
### Reviewer Finding Reconciliation
Reviewer flagged: PdsMigration.test.tsx omitted from affected-test inventory at `.owlbear/research/1597-token-provenance-map.md:98-114`.

**Architect verification:**
- `serve/cockpit/web/src/__tests__/PdsMigration.test.tsx` confirmed to contain **zero** `--pds-*` CSS token references (grep verified).
- The test suite validates HTML element → PDS component migration (e.g., `<button>` → `<PButton>`, `<h3>` → `<PHeading>`), not CSS custom property token usage.
- Correct disposition: **0 refs / Keep — tests PDS component element migration, no CSS token references.**
- The scoped deliverable ("identify affected test files") is satisfied: PdsMigration is explicitly determined to be **unaffected** by CSS token provenance. The omission was not accidental — the file simply has no `--pds-*` references to classify.

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Provenance classification only |
| Interface clarity | PASS | AC defines 4-way classification with replacement detail |
| Dependency correctness | PASS | Deps #1594/#1595/#1596 all archived |
| Module layering | N/A | Research artifact, no module changes |
| TDD compliance | N/A | proof_bundle=skip |
| KISS/YAGNI | PASS | Minimal grep+classify scope |
| Premise challenge | PASS | Required prerequisite for #1600/#1603 |
| Pattern consistency | PASS | Standard research doc structure |
| Security surface | PASS | No system boundaries |
| Single domain | PASS | Frontend token analysis only |

### Proof-Bundle Validation
- Planner assignment: skip
- Final bundle: skip
- Existing proof scope: N/A
- Test-writer: SKIP

### Challenge Results
- Challenger: SKIPPED — proof bundle `skip`

### Verdict: APPROVE
### Action Taken: Reconciled PdsMigration gap (0 `--pds-*` refs, unaffected). Advanced to todo. Research artifact complete for all 3 AC lines.

[[2026-05-17T08:02:35+02:00]]
Reconciled reviewer finding: PdsMigration.test.tsx has 0 --pds-* refs (verified via grep), tests PDS component element migration not CSS tokens. Disposition: unaffected/Keep. Research artifact satisfies all 3 AC lines. Proof bundle: skip. Advanced to todo.

[[2026-05-17T08:56:24+02:00]]
## Test-Writer Notes
- Proof bundle: `skip` — no new test writing required.
- Research task tagged `research`; architect review cycle 2 explicitly marks "Test-writer: SKIP".
- Passing through to builder.

[[2026-05-17T10:13:06+02:00]]
## Builder Notes
- Implementation: updated `.owlbear/research/1597-token-provenance-map.md` affected-test inventory with explicit `PdsMigration.test.tsx` disposition (`0 refs`, `Keep`).
- Tests: none (proof bundle `skip`, research artifact task)
- Coverage: N/A (no executable module change)
- ruff: N/A
- Lint: quality-runner scoped lint proof executed for `.owlbear/research/1597-token-provenance-map.md`; markdownlint skipped because path is ignored by `.markdownlintignore` (`.owlbear/research`), with no violations reported.
- Approach: surgical artifact correction to close reviewer gap while preserving existing classification and coverage sections.

### Evidence Summary
- `rg -n -- '--pds-' serve/cockpit/web/src/__tests__/PdsMigration.test.tsx` returned no matches (supports unaffected classification).
- quality-runner report (scoped lint path): `markdownlint: skipped (path ignored)`, `violations: none`.
- Commit: `3d2e5512b13dbe4546e0338f24fe826ca8048b97` containing only `.owlbear/research/1597-token-provenance-map.md`.

### Fixes Applied
- Added explicit inventory row for `PdsMigration.test.tsx` with rationale: element-to-PDS component migration assertions, no CSS token references.
