---
id: 1597
title: 'P1-01: Token provenance map'
status: in-progress
priority: important
created: 2026-05-16T03:35:25.235271+00:00
updated: 2026-05-16T20:26:07.413017+00:00
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
