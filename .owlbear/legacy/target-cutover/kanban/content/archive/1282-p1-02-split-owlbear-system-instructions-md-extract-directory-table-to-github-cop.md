---
id: 1282
title: 'P1-02: Split owlbear-system.instructions.md — extract directory table to .github/copilot-instructions.md'
status: archived
priority: medium
created: 2026-05-02T16:01:10.599380+00:00
updated: 2026-05-03T10:08:52.176335+00:00
tags:
- phase-1
- scope:docs
- shared-layer
- type:docs
parent: 1280
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1280 and `.owlbear/briefs/draft-neutral-shared/brief.md`

## Acceptance Criteria

- [ ] `### Directory Structure` subsection (heading + table) removed from `share/instructions/owlbear-system.instructions.md` §2; the `For file placement rules...` line stays (td:0)
- [ ] `## Directory Structure` table in `.github/copilot-instructions.md` replaced with the richer extracted table — drop stale `scripts/` row, keep `tests/` row (td:0)
- [ ] `owlbear-system.instructions.md` retains §1 Decision Heuristics, Tech Stack, Pipeline, §3 Memory Governance, §4 Operational Fundamentals (td:0)
- [ ] `owlbear-system.instructions.md` frontmatter `description` updated from `"OwlBear system instructions — ..."` to `"System instructions — ..."` (td:0)
- [ ] No `serve/` paths remain in `owlbear-system.instructions.md` (MCP server names excluded — validated by existing `test_instructions_have_no_serve_refs`) (td:0)
- [ ] `@pytest.mark.xfail` removed from `test_instructions_have_no_serve_refs` in `tests/test_neutral_shared_1281.py` (td:0)
- [ ] `tests/test_neutral_shared_1281.py` suite passes green (td:0)

Test-writer: SKIP — all AC lines are td:0 (mechanical content migration; tests already exist from #1281).

## Scope

- IN: `share/instructions/owlbear-system.instructions.md` edit, `.github/copilot-instructions.md` table replacement, `tests/test_neutral_shared_1281.py` xfail removal
- OUT: Cross-reference updates (#1283), init.py changes (#1284)

[[2026-05-02]]
## Research
- Research doc: .owlbear/research/split-system-instructions-1282.md
- Sources: 6 studied, 4 high-relevance (all codebase)
- Recommendation: 4-step extraction (remove table, replace in copilot-instructions, update frontmatter, remove xfail) (confidence: 0.92)
- Follow-up tasks created: none (siblings #1283, #1284 already cover remaining P1 scope)
- Decision requests: none (T1 Autonomous — straightforward content migration)

Key findings:
1. Only one non-exempt `serve/` reference in owlbear-system.instructions.md (line 40, Directory Structure table). Extraction resolves AC5.
2. `.github/copilot-instructions.md` already has a simpler Directory Structure section (added by #1281 builder). Replace with richer extracted table.
3. `scripts/` directory no longer exists — drop stale row from extracted table.
4. xfail marker on `test_instructions_have_no_serve_refs` must be removed as part of #1282 AC (per #1281 downstream note).
5. Frontmatter description: "OwlBear system instructions" → "System instructions"

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: extract directory table from shared instructions to project-local file |
| Interface clarity | PASS | AC specifies exact sections, files, and transformations |
| Dependency correctness | PASS | No deps; sibling tasks #1283/#1284 are independent |
| Module layering | N/A | No code modules involved |
| TDD compliance | PASS | Tests exist from #1281; this task makes them pass (GREEN for cross-task RED) |
| KISS/YAGNI | PASS | Minimal mechanical migration, no abstractions |
| Premise challenge | PASS | Directory table IS project-specific and belongs in project-local copilot-instructions, not the shared distributable |
| Pattern consistency | PASS | Follows established separation: shared instructions vs project-local copilot-instructions |
| Security surface | N/A | No system boundaries affected |
| Single domain | PASS | docs domain only |

### Verdict

APPROVE — AC is precise, all mechanical, tests pre-exist from #1281.

Challenger: SKIPPED — all AC lines td:0, no design decisions.
Design-diverge: SKIPPED — single obvious approach (content extraction), no competing designs.
[[2026-05-02]]
## Architecture Review — Verdict: APPROVE

AC refined: added explicit xfail removal line (AC6), td:0 annotations on all lines, Test-writer: SKIP directive. Added `type:docs` pass-through tag. Scope section updated to include test file edit.

Codebase verified: single `serve/` reference at `owlbear-system.instructions.md:40` (Directory Structure table). `.github/copilot-instructions.md` already has a simpler table to replace. `scripts/` directory confirmed absent — stale row to drop. xfail marker at `tests/test_neutral_shared_1281.py:72` confirmed.

No dependencies, no design decisions, no architecture risk. Challenger and design-diverge both skipped (all td:0).
[[2026-05-02]]
## Test-Writer Notes
- All AC lines are (td:0) — test-writer skipped.
- Task tagged `type:docs`; body includes explicit `Test-writer: SKIP` directive.
- Tests already exist from #1281 (`tests/test_neutral_shared_1281.py`); AC6 requires removing xfail from that file (also td:0, builder work).
- Passing through to builder.
[[2026-05-02]]
## Builder Notes
- Implementation: updated `share/instructions/owlbear-system.instructions.md`, `.github/copilot-instructions.md`, and `tests/test_neutral_shared_1281.py`.
- AC alignment:
  - Removed `### Directory Structure` subsection from `owlbear-system.instructions.md` while preserving the `For file placement rules...` line.
  - Updated frontmatter description in `owlbear-system.instructions.md` to `System instructions — ...`.
  - Replaced `.github/copilot-instructions.md` `## Directory Structure` table with the richer extracted structure, dropped stale `scripts/` row, retained `tests/` row.
  - Removed `@pytest.mark.xfail` from `test_instructions_have_no_serve_refs`.
- Tests: `tests/test_neutral_shared_1281.py` -> 10 passed, 0 failed, 0 skipped.
- Coverage: not requested in scoped quality-runner pass for this td:0 docs migration.
- ruff: clean (after removing now-unused `pytest` import introduced by xfail removal).
- Commit: `84ecd857` with message `docs: extract directory structure table (#1282, builder)`.

Post-task reflection:
- Removing xfail can surface secondary lint fallout; here it revealed an unused import and was fixed immediately.
- Keeping edits constrained to AC files prevented any cross-task drift.
- Task-scoped quality-runner checks were sufficient evidence for this mechanical migration.
[[2026-05-03]]
## Review Evidence
### Test Results
- quality-runner pytest: 10 passed, 0 failed, 0 skipped
- Suite rerun independently on `tests/test_neutral_shared_1281.py`; all listed tests passed, including `TestFromAC_SystemInstructionNeutrality::test_instructions_have_no_serve_refs`

### Lint
- quality-runner ruff: clean
- Command run by subagent: `uv run ruff check tests/test_neutral_shared_1281.py --show-fixes`

### Coverage
- Not run. This is a td:0 docs migration and AC only requires the existing suite to pass green.

### Pass 1 — Critical
#### Test-Writer AC Coverage
- td:0 task. Test-writer correctly skipped per task body; reviewer independently reran the existing suite because AC7 explicitly requires it.

#### Security Review
- No issues. Changed files are two documentation files and one Python test file; no production runtime surface, secrets handling, or input boundary logic changed.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `test_instructions_have_no_serve_refs` | Reconstructed diff shows xfail decorator removed; current file also no longer imports `pytest` at [tests/test_neutral_shared_1281.py](tests/test_neutral_shared_1281.py#L12) | STRENGTHENED |
| Other `TestFromAC_*` tests | No assertion or logic changes found in reconstructed diff summary | PRESERVED |

#### Test Quality
- Existing assertions remain discriminating. [tests/test_neutral_shared_1281.py](tests/test_neutral_shared_1281.py#L70) still accumulates concrete `serve/` violations and fails on `assert not violations`; this would fail if AC5 regressed.

#### Data Safety
- N/A. No data-handling or concurrency code changed.

#### Necessity Check
- N/A. No dependency, integration, or external capability was added.

#### Builder Process Quality
- CLEAN. One `## Builder Notes` section and no prior `## Review Evidence` section in the task body.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| Remove `### Directory Structure` subsection from `owlbear-system.instructions.md` while keeping `For file placement rules...` line | [share/instructions/owlbear-system.instructions.md](share/instructions/owlbear-system.instructions.md#L30) is followed by retained line at [share/instructions/owlbear-system.instructions.md](share/instructions/owlbear-system.instructions.md#L36); grep for `### Directory Structure` returned no matches | N/A (td:0 content check) | PASS |
| Replace `.github/copilot-instructions.md` directory table with richer extracted table; drop stale `scripts/` row; keep `tests/` row | Directory section begins at [.github/copilot-instructions.md](.github/copilot-instructions.md#L16); extracted rows include [share/instructions row](.github/copilot-instructions.md#L23) and [tests row](.github/copilot-instructions.md#L29); grep for `scripts/` returned no matches | `TestFromAC_CopilotInstructionsDirectoryStructure::*` | PASS |
| Retain Decision Heuristics, Tech Stack, Pipeline, Memory Governance, Operational Fundamentals | Present at [share/instructions/owlbear-system.instructions.md](share/instructions/owlbear-system.instructions.md#L6), [share/instructions/owlbear-system.instructions.md](share/instructions/owlbear-system.instructions.md#L19), [share/instructions/owlbear-system.instructions.md](share/instructions/owlbear-system.instructions.md#L30), [share/instructions/owlbear-system.instructions.md](share/instructions/owlbear-system.instructions.md#L38), [share/instructions/owlbear-system.instructions.md](share/instructions/owlbear-system.instructions.md#L51) | N/A (td:0 content check) | PASS |
| Update frontmatter description to `System instructions — ...` | [share/instructions/owlbear-system.instructions.md](share/instructions/owlbear-system.instructions.md#L2) | N/A (td:0 content check) | PASS |
| No `serve/` paths remain in `owlbear-system.instructions.md` | grep for `serve/` in `share/instructions/owlbear-system.instructions.md` returned no matches; quality-runner also passed `TestFromAC_SystemInstructionNeutrality::test_instructions_have_no_serve_refs` | `TestFromAC_SystemInstructionNeutrality::test_instructions_have_no_serve_refs` | PASS |
| Remove `@pytest.mark.xfail` from `test_instructions_have_no_serve_refs` | [tests/test_neutral_shared_1281.py](tests/test_neutral_shared_1281.py#L70) has the test with no decorator; grep for `xfail` and `import pytest` returned no matches | N/A (td:0 content check) | PASS |
| `tests/test_neutral_shared_1281.py` suite passes green | quality-runner pytest: 10 passed, 0 failed, 0 skipped | `tests/test_neutral_shared_1281.py` | PASS |

### Deductions
- -0.02 confidence: test-integrity check used reconstructed pre/post diff evidence instead of direct `git show`, but current file inspection and subagent reconstruction agree the test-file change was limited to xfail removal plus import cleanup.

### Verdict
- PASS
- Confidence: 0.96

### Action
- Advance to docs.
[[2026-05-03]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | All changed files are OUT-scope (agent-executable). No IN-scope prose docs (READMEs, setup guides, share/README.md) reference the extracted Directory Structure section. |
| 2 | Module docstrings | No | N/A | No Python modules created or modified. |
| 3 | External attribution | No | N/A | All 6 research sources are codebase files; no external repos or articles. |
| 4 | Research doc | Yes | Verified | `.owlbear/research/split-system-instructions-1282.md` exists and is linked from task body. Follow-ups: siblings #1283/#1284 cover remaining P1 scope per research doc. |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/memory-layers.excalidraw` and `share/diagrams/pipeline.excalidraw` both have `describes` globs matching `share/instructions/owlbear-system.instructions.md`. Footers updated to `Last verified: 2026-05-03 (91a14158)`. Committed as f064ed43. |
| 6 | Explicit diagram creation | No | N/A | No explicit diagram creation request in task body. |
| 7 | Deletion detection | No | N/A | No files deleted; all changes were edits. |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| `share/instructions/owlbear-system.instructions.md` | OUT | N/A (agent-executable) |
| `.github/copilot-instructions.md` | OUT | N/A (agent-executable) |
| `tests/test_neutral_shared_1281.py` | OUT | N/A (test file) |
| `share/diagrams/memory-layers.excalidraw` | IN | Footer updated (diagram describes-match) |
| `share/diagrams/pipeline.excalidraw` | IN | Footer updated (diagram describes-match) |

### Files Updated
- `share/diagrams/memory-layers.excalidraw` — footer: `Last verified: 2026-05-03 (91a14158)`
- `share/diagrams/pipeline.excalidraw` — footer: `Last verified: 2026-05-03 (91a14158)`

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no scratch files found for task 1282)
[[2026-05-03]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Remove Directory Structure subsection from owlbear-system.instructions.md; keep "For file placement rules..." line | Heading absent; retained line at owlbear-system.instructions.md:36 | PASS |
| Replace copilot-instructions.md directory table; drop scripts/ row; keep tests/ row | Richer table at copilot-instructions.md:16; grep scripts/ = 0 matches; tests/ row present | PASS |
| Retain Decision Heuristics, Tech Stack, Pipeline, Memory Governance, Operational Fundamentals | Sections at owlbear-system.instructions.md L6, L19, L30, L38, L51 | PASS |
| Update frontmatter description to "System instructions ..." | Confirmed at owlbear-system.instructions.md:2 | PASS |
| No serve/ paths remain in owlbear-system.instructions.md | grep serve/ = 0 matches | PASS |
| Remove xfail from test_instructions_have_no_serve_refs | grep xfail in test file = 0 matches | PASS |
| test_neutral_shared_1281.py suite passes green | 10 passed, 0 failed, 0 skipped (0.41s) | PASS |

### Test Results
- pytest (task-scoped): 10 passed, 0 failed
- pytest (full suite): 551 passed, 1 failed (pre-existing: test_engine_accessor_migration.py dead-code check, unrelated to #1282)
- ruff (task-scoped): All checks passed

### Architect Quality: 5/5
Precise mechanical instructions with explicit file paths and section names. No ambiguity, no builder improvisation needed.

### Deduction Breakdown
No deductions applied. All 7 AC lines have direct file evidence, reviewer section is detailed with PASS verdict, full suite has zero task-scoped failures, lint clean. Pre-existing failure in test_engine_accessor_migration.py is outside task scope (engine dead code).

### Confidence: .98
### Action: archive