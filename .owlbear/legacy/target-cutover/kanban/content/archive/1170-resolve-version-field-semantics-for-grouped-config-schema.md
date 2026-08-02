---
id: 1170
title: Resolve version field semantics for grouped config schema
status: archived
priority: medium
created: 2026-04-28T22:52:50.036092+00:00
updated: 2026-04-29T02:14:31.273092+00:00
tags:
- scope:kanban
- research
parent:
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---

Version field contradiction: AC on #1155 specifies version bump 10→11, but engine.py L471-475 treats presence of version field as legacy schema marker, and storage.save_config strips version from new-schema output. Must decide: (a) grouped configs are versionless like current new-schema, or (b) rewrite engine migration gate to use different detection. See .owlbear/research/1155-config-schema-grouping-validation.md §3 'Version Field Contradiction'.
[[2026-04-28]]

## Research

- Research doc: .owlbear/research/1170-version-field-semantics.md
- Sources: 8 studied, 6 high-relevance (7 internal + 1 external)
- Recommendation: Option B — new `schema` field for grouped and future formats (confidence: .75)
- Follow-up tasks created: none (resolves #1155 dependency directly)
- Decision requests: none new (feeds into existing T3 DR .owlbear/decisions/pending/1155-config-schema-grouping.md)

## Key Findings

1. `version` is a deprecation marker across all 4 modules — never functioned as schema tracker
2. Pure versionless (Option A) works for 1 transition but breaks at 3+ formats due to `extra='allow'` vendor-field ambiguity
3. Repurposing `version` (Option C) requires rewriting 10+ sites in 4 modules — high blast radius
4. New `schema: grouped` field (Option B) adds 1 field, touches no existing detection, scales to future formats
5. Docker Compose deprecated their version field for the same reason — structure-based detection

## Challenge Results

- Challenger: reconsider (overall risk: high)
- Confidence in original: .52
- Key challenges accepted: ordered-migration blind spot (critical → added schema field), vendor-field ambiguity with extra='allow' (moderate → explicit field addresses it)
- Revised from pure versionless (.82) to schema field approach (.75)

## AC Impact on #1155

- Remove: "Live config migrated via version bump (10 → 11)"
- Add: "Grouped configs include `schema: grouped` at top level"
- Add: "Detection cascade: schema field → key-based → legacy"
[[2026-04-28]]

## Acceptance Criteria

- [ ] Research doc at `.owlbear/research/1170-version-field-semantics.md` analyzes version field usage across engine.py, models.py, storage.py, migrate.py
- [ ] Recommendation selects from three options (versionless / new field / repurpose version) with codebase evidence and rationale
- [ ] AC corrections for #1155 are specified: what to remove (version bump) and what to add (schema field, detection cascade)
- [ ] Findings are challenger-reviewed with confidence and revision documented

## Architect Notes for #1155 Re-review

When #1155 returns to backlog, the architect should additionally:

1. Correct AC line `_normalise_legacy handles both flat (v10) and grouped (v11)` — remove v10/v11 framing, use schema-marker language per this research
2. Scope rollout surface: version fixtures exist in 6+ cross-package test suites (cockpit read API, MCP server, OCC wire, engine storage, storage_1050, guidance server)
3. Address `schema` field's status as `extra='allow'` vendor metadata vs first-class BoardConfig field — implementation must decide and document
[[2026-04-28]]

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: resolve version field semantics contradiction |
| Interface clarity | PASS (after REFINE) | Added 4 verifiable AC checkboxes for research deliverables |
| Dependency correctness | PASS | No upstream deps; #1155 depends_on this task — completing #1170 satisfies that gate |
| Module layering | N/A | Research task, no code changes |
| TDD compliance | PASS | Tagged `research` for pipeline pass-through |
| KISS/YAGNI | PASS | Scoped to one question with three concrete options |
| Premise challenge | PASS | Contradiction is real — verified version field is legacy marker in engine.py L471-475, storage.py L250, migrate.py L62-68, models.py L210 |
| Pattern consistency | PASS | Research format follows established .owlbear/research/ conventions |
| Security surface | PASS | No new boundaries |
| Single domain | PASS | scope:kanban only |

### Challenge Results

- Challenger: reconsider (confidence .66)
- Key challenges: (1) "zero changes to existing detection" overclaim — accepted as advisory for #1155, not blocking for research scope; (2) AC correction incomplete (misses _normalise_legacy v10/v11 line) — accepted, added to architect notes; (3) dependency closure ambiguity — rebutted: completing research satisfies depends_on, DR is separate gate; (4) config marker proof gap — rebutted: implementation concern for #1155
- Architect response: proceed with APPROVE. Challenges are about downstream implementation, not research quality. Added #1155 re-review notes addressing all accepted concerns.

### Verdict: APPROVE (REFINE → APPROVE)

### Action Taken

1. Added 4 verifiable AC checkboxes scoped to research deliverables
2. Added `research` pass-through tag
3. Added architect notes for #1155 re-review (3 items from challenger findings)
4. Advanced to todo
[[2026-04-28]]

## Test-Writer Notes

- Non-implementation task (tagged `research`) — no tests applicable.
- Passing through to builder.
[[2026-04-29]]

## Builder Notes

- Implementation: none (non-implementation research pass-through).
- Files changed: none.
- Tests: not applicable for `research` task; no `TestFromAC_*` execution required.
- Coverage: not applicable (no code touched).
- Ruff: not applicable (no code touched).
- Evidence summary: confirmed research deliverable exists at `.owlbear/research/1170-version-field-semantics.md` and includes option comparison, recommendation with confidence, challenger revision, and explicit AC corrections for #1155.
[[2026-04-29]]

## Review Evidence

### Test Results

- N/A for this review. Task 1170 is tagged `research`, builder notes report `Files changed: none`, and workspace search found no task-scoped test files matching `tests/**/*1170*`.

### Lint

- N/A for the same reason. VS Code diagnostics reported no errors in `.owlbear/research/1170-version-field-semantics.md`.

### Coverage

- N/A. No runtime modules were changed in this review cycle.

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage

- N/A. Non-implementation research task; no `TestFromAC_*` classes or task-scoped tests apply.

#### Security Review

- No issues. Review scope is the research artifact and task handoff only; no builder code changes were introduced.

#### Test Integrity

- N/A. Builder notes report no changed files, and there are no task-scoped tests for this task.

#### Test Quality

- N/A. No task-scoped tests exist for 1170.

#### Data Safety

- No issues. This task ships a research decision, not executable write-path changes.

#### Implementation-Aware Gaps

- No research-scope gaps found. The research doc's core premise matches live code:
  - `version` presence gates legacy detection in `serve/kanban/src/owlbear_kanban/engine.py:473-475`
  - `_normalise_legacy` keys off `version` in `serve/kanban/src/owlbear_kanban/models.py:210`
  - `save_config` strips `version` in `serve/kanban/src/owlbear_kanban/storage.py:250`
  - `_LEGACY_CONFIG_KEYS` includes `version` and `_is_config_migrated()` rejects legacy keys in `serve/kanban/src/owlbear_kanban/migrate.py:65-72` and `serve/kanban/src/owlbear_kanban/migrate.py:325-333`
  - Package-wide search of `serve/kanban/src/owlbear_kanban/` found no numeric config-version comparisons, supporting the doc's conclusion that `version` is a legacy marker rather than a schema counter.

#### Builder Process Quality

| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### AC Compliance

| AC Line | Evidence | Status |
|--------|----------|--------|
| Research doc at `.owlbear/research/1170-version-field-semantics.md` analyzes version field usage across engine.py, models.py, storage.py, migrate.py | `.owlbear/research/1170-version-field-semantics.md:32-40` summarizes all four modules, and the cited live-code checks above match current implementation. | PASS |
| Recommendation selects from three options (versionless / new field / repurpose version) with codebase evidence and rationale | `.owlbear/research/1170-version-field-semantics.md:44-78` contains the three-option comparison matrix; `.owlbear/research/1170-version-field-semantics.md:81-95` records the recommendation and rationale. | PASS |
| AC corrections for #1155 are specified: what to remove (version bump) and what to add (schema field, detection cascade) | `.owlbear/research/1170-version-field-semantics.md:106-109` specifies the exact remove/add changes. The upstream task still contains the stale AC line at `.owlbear/kanban/tasks/1155-implement-config-yml-schema-grouping-nested-sub-models.md:36`, so the correction is concrete and necessary. | PASS |
| Findings are challenger-reviewed with confidence and revision documented | `.owlbear/research/1170-version-field-semantics.md:96-97` records the challenge outcome, confidence, and revision from pure versionless to schema-field approach. | PASS |

### Pass 2 — INFORMATIONAL

- External-source logging is present at `.owlbear/sources/overview.md:5-9`, so the Docker Compose precedent used in the research doc is properly attributed.
- Adjacent upstream cleanup remains for `.owlbear/kanban/tasks/1155-implement-config-yml-schema-grouping-nested-sub-models.md:32` (`_normalise_legacy handles both flat (v10) and grouped (v11) inputs`). Task 1170 already captures that in its Architect Notes, so this is informational rather than a failure against 1170's own AC.

### Deductions

- 0. The research artifact is current, internally consistent, and grounded in the live codebase.

### Verdict

- PASS -> docs | confidence .96

### Action

- Advance to docs.
[[2026-04-29]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | Research-only task; no behavior, API, CLI, config, or package structure changed |
| 2 | Module docstrings | No | N/A | Builder notes: "Files changed: none" — no Python modules created or modified |
| 3 | External attribution | Yes | Verified | Review Evidence confirms Docker Compose precedent logged at `.owlbear/sources/overview.md:5-9` — no action needed |
| 4 | Research doc | Yes | Verified | `.owlbear/research/1170-version-field-semantics.md` exists; linked in task body; all 4 AC checkboxes pass per review evidence |
| 5 | Diagram maintenance (describes match) | No | N/A | No changed source files — no describes-match possible |
| 6 | Explicit diagram creation | No | N/A | No diagram creation request in task body |
| 7 | Deletion detection | No | N/A | No deleted files in this task |

### Scope Classification

| File | Scope | Action |
|------|-------|--------|
| `.owlbear/research/1170-version-field-semantics.md` | IN | Verified (no edits needed) |

### Files Updated

- None

### Child Tasks Created

- None

### Scratch Files Cleaned

- None found
[[2026-04-29]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| Research doc at `.owlbear/research/1170-version-field-semantics.md` analyzes version field usage across engine.py, models.py, storage.py, migrate.py | Doc §3 has 4-row module table: engine.py L471-475, models.py L210, storage.py L250, migrate.py L68/L332 | PASS |
| Recommendation selects from three options (versionless / new field / repurpose version) with codebase evidence and rationale | Doc §3 has 7-criterion comparison matrix; §4 selects Option B at .75 confidence with rationale | PASS |
| AC corrections for #1155 are specified: what to remove (version bump) and what to add (schema field, detection cascade) | Doc §5 has explicit remove/add items for #1155 AC | PASS |
| Findings are challenger-reviewed with confidence and revision documented | Doc §4 bottom: revised from .82 to .75 after challenger reconsider; task body Challenge Results section confirms | PASS |

### Research Task Verification (Step 1a)

- ✅ Research doc exists at `.owlbear/research/1170-version-field-semantics.md`
- ✅ No new follow-up tasks — justified: resolves #1155 dependency directly, feeds existing T3 DR at `.owlbear/decisions/pending/1155-config-schema-grouping.md`
- ✅ Committed upstream: `3386a1b2`

### Test Results

- pytest: 2828 passed, 123 failed, 4 skipped — all failures pre-existing (zero task-scoped code changes)
- ruff: 4 violations in unrelated modules (knowledge, mcp-knowledge, mcp-memory, orchestrator) — none task-scoped

### Reviewer Evidence

Present, detailed, PASS at .96. All 4 AC lines mapped with file:line citations. Implementation-aware gap check verified doc claims against live code. Trusted.

### Architect Quality: 4/5

4 specific, verifiable checkboxes scoped to research deliverables. Good refinement from open body to testable criteria. Challenger review at arch stage raised valid downstream concerns, all captured in Architect Notes for #1155.

### Deduction Breakdown

- AC lines without evidence: 0 (4/4 PASS) → 0
- Lint violations in task scope: 0 → 0
- AC quality ≤ 3: no (4/5) → 0
- Missing reviewer evidence: no → 0
- Suite failures in task scope: 0 → 0

### Confidence: .98

### Action: archive
