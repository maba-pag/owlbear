---
id: 1171
title: Audit and unify config write paths before schema grouping
status: archived
priority: needed
created: 2026-04-28T22:52:50.250562+00:00
updated: 2026-04-29T02:13:49.112742+00:00
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

Three independent config-writing paths have divergent assumptions: (1) config_loader._merge_into — round-trip merge, already supports nested dicts; (2) storage.save_config — atomic rewrite, strips legacy keys; (3) migrate._migrate_config — emits flat Brief-C keys only. All three must agree on grouped output format before #1155 implementation. See .owlbear/research/1155-config-schema-grouping-validation.md §3 'Config Authority Split'.
[[2026-04-28]]

## Planning

Created 2 follow-up tasks at research:

| ID | Title | Priority | Tags | Parent | Deps |
|----|-------|----------|------|--------|------|
| #1174 | Delete config_loader.save_config and _merge_into dead code | needed | scope:kanban | — | — |
| #1175 | Harden storage.save_config for grouped config output | needed | scope:kanban | — | — |

No dependency between them — they target different modules (config_loader vs storage).
[[2026-04-28]]

## Research\n- Research doc: .owlbear/research/1171-config-write-path-audit.md\n- Sources: 8 studied, 6 high-relevance (all internal)\n- Recommendation: Delete dead config_loader.save_config, harden storage.save_config for grouped output, require migrate/storage parity as #1155 AC (confidence: .72)\n- Follow-up tasks created: #1174 (delete dead code), #1175 (harden save_config)\n- Decision requests: none (T1 — autonomous)\n\n## Challenge Results\n- Challenger: block (confidence in original: .42)\n- Key challenges: contract mismatch (deferring migrate ≠ unification), defaults.priority loss on create-task path, grouped correctness unproven\n- Researcher response: accepted/revised — reframed Step 3 as explicit #1155 AC requirement, elevated defaults.priority to standalone finding, added nested round-trip test to follow-up. Rebutted block: research task produces findings + actionable follow-ups, not implementation.\n\n## Key Findings\n1. config_loader.save_config is DEAD CODE — zero callers, zero tests, 3 latent bugs\n2. storage.save_config is sole canonical writer — needs model-driven field emission for grouped output\n3. migrate._migrate_config rewrite is coupled to #1155 schema design — requires output parity contract\n4. defaults.priority silently lost on every save_config cycle (cross-cutting with #1170)

[[2026-04-28]]
Status correction: planner already advanced to backlog, end_work double-advanced to todo. Rejecting back to backlog.
[[2026-04-28]]

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single concern: audit 3 config write paths |
| Interface clarity | PASS | Research task — deliverables are doc + follow-up tasks, both complete |
| Dependency correctness | PASS | No dependencies; #1155 correctly depends on this task |
| Module layering | PASS | Research-only, no code changes |
| TDD compliance | N/A | Research task, no testable code |
| KISS/YAGNI | PASS | Minimal scope — audit only, implementation deferred to #1174/#1175 |
| Premise challenge | PASS | Audit justified as #1155 prerequisite; all 3 key claims independently verified |
| Pattern consistency | PASS | Follows research task pattern with doc + follow-ups |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | scope:kanban only |

### Codebase Verification

All 3 key findings independently confirmed:

1. config_loader.save_config: zero callers, zero tests — DEAD CODE confirmed
2. storage.save_config: 1 prod caller (allocate_next_id L556) + 3 test callers — sole active writer confirmed
3. defaults.priority loss: storage.py L250 strips "defaults", engine.py L936 reads config.defaults.priority — confirmed

### Challenge Results

- Challenger: reconsider (confidence: 0.61)
- Key challenges: (1) migrate/storage parity not yet in #1155 AC, (2) research tag not yet added, (3) follow-up task status mismatch, (4) escaped text in body
- Architect response: (1) accepted as #1155 refinement action — not a #1171 blocker; (2) accepted — tag added; (3) rebutted — creation is the deliverable; (4) accepted as minor cosmetic
- Override: concerns target downstream handoff in other tasks, not #1171's research completeness

### Follow-up Note

When #1155 returns to backlog, its AC should include an explicit migrate/storage output parity requirement (research doc §4 Step 3). Currently missing from #1155's AC.

### Verdict: APPROVE

### Action Taken

Added `research` pass-through tag. Advanced to todo. Research deliverables complete: thorough audit doc at .owlbear/research/1171-config-write-path-audit.md, follow-up tasks #1174 (dead code deletion) and #1175 (harden save_config) properly scoped.
[[2026-04-28]]

## Test-Writer Notes

- Non-implementation task (tagged research) — no tests applicable.
- Passing through to builder.
[[2026-04-29]]

## Builder Notes

- Non-implementation task (research pass-through) confirmed from Test-Writer Notes.
- No code changes needed.
- No tests/lint run in builder phase (per non-impl pass-through rule).
- Passing through to review.
[[2026-04-29]]

## Review Evidence

### Scope

- Task type: research-tagged non-implementation pass-through; no source changes were made in #1171 itself.
- Policy check: `research` is a valid non-implementation tag at `share/skills/w-tdd-red/SKILL.md:25-34`; `share/instructions/pipeline-agents.instructions.md:33` explicitly allows test-writer / builder / reviewer pass-through.
- Task-body check: #1171 records the expected pass-through at `.owlbear/kanban/tasks/1171-audit-and-unify-config-write-paths-before-schema-grouping.md:75` and `.owlbear/kanban/tasks/1171-audit-and-unify-config-write-paths-before-schema-grouping.md:81`.

### Test Results

- quality-runner baseline on related config suites: 134 passed, 12 failed.
- Baseline failures: 3 timestamp assertions in `serve/kanban/tests/test_storage_1050.py::TestFromAC_Frontmatter::*`; 9 `serve/kanban/tests/test_storage_io.py::*` cases raising `ConfigError: agent_map missing status entries: ['research', 'backlog', 'todo', 'in-progress', 'review', 'docs', 'done']`.
- quality-runner narrowed direct-save run: 9 passed, 1 failed.
- Remaining narrowed failure: `serve/kanban/tests/test_storage_io.py::TestFromAC_IDAllocation::test_ac_c51_crash_between_save_config_and_write_task` with the same `ConfigError`.
- Assessment: contextual baseline noise only. #1171 is research/no-code; these failures do not contradict the audited findings. They reinforce that the config surface is already brittle and that follow-up hardening remains necessary.

### Lint

- ruff clean on `serve/kanban/src/owlbear_kanban/config_loader.py`, `serve/kanban/src/owlbear_kanban/storage.py`, `serve/kanban/src/owlbear_kanban/migrate.py`, and `tests/test_config_loader_1174.py`.

### Coverage

- Gate N/A for #1171 (non-implementation task).
- Context from narrowed run only: `config_loader.py` 100%, `storage.py` 25%, `migrate.py` 0%.

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage

- N/A. Task is tagged `research`; pass-through is explicitly authorized by `share/skills/w-tdd-red/SKILL.md:25-34` and `share/instructions/pipeline-agents.instructions.md:33`. No `TestFromAC_*` suite was expected for #1171 itself.

#### Security Review

- No new code or dependencies in #1171. No security delta introduced by this task.

#### Test Integrity

- N/A. Builder did not modify task-owned tests; pass-through only.

#### Test Quality

- N/A for #1171 itself.
- Adjacent save-config proof in the current repo is narrow: `serve/kanban/tests/test_storage_1050.py:796`, `serve/kanban/tests/test_engine_archived_edit_1120.py:881`, and `serve/kanban/tests/test_storage_io.py:439`.
- There are no task-scope checks for nested grouped round-trip or `defaults.priority` persistence; that gap is explicitly captured by #1175 acceptance criteria.

#### Data Safety

- No code changes in task; no new write path introduced.

#### Implementation-Aware Gaps

- Core research claims reverified against live code:
  - Active writer still strips legacy keys including `defaults`: `serve/kanban/src/owlbear_kanban/storage.py:236` and `serve/kanban/src/owlbear_kanban/storage.py:250`.
  - Engine still reads `config.defaults.priority`: `serve/kanban/src/owlbear_kanban/engine.py:936`.
  - Migration writer still builds flat Brief-C keys: `serve/kanban/src/owlbear_kanban/migrate.py:367`, `serve/kanban/src/owlbear_kanban/migrate.py:422`, `serve/kanban/src/owlbear_kanban/migrate.py:429`, `serve/kanban/src/owlbear_kanban/migrate.py:447`.
- Research deliverables still match live state:
  - Audit doc calls out the three-path divergence and the parity requirement: `.owlbear/research/1171-config-write-path-audit.md:30`, `.owlbear/research/1171-config-write-path-audit.md:46`, `.owlbear/research/1171-config-write-path-audit.md:62-63`, `.owlbear/research/1171-config-write-path-audit.md:86-97`, `.owlbear/research/1171-config-write-path-audit.md:122-128`, `.owlbear/research/1171-config-write-path-audit.md:160-163`.
  - #1174 exists, matches the dead-code finding, and now has implementation evidence in review: `.owlbear/kanban/tasks/1174-delete-config-loader-save-config-and-merge-into-dead-code.md:20-24`, `.owlbear/kanban/tasks/1174-delete-config-loader-save-config-and-merge-into-dead-code.md:88-94`.
  - #1175 exists, is machine-readably blocked, and carries the missing nested/defaults hardening work: `.owlbear/kanban/tasks/1175-harden-storage-save-config-for-grouped-config-output.md:12`, `.owlbear/kanban/tasks/1175-harden-storage-save-config-for-grouped-config-output.md:24-28`.
- Only nontrivial handoff gap: the research doc requests a `#1155` AC amendment for migrate/storage parity, but the current top-level `#1155` checklist still lacks that explicit bullet: `.owlbear/research/1171-config-write-path-audit.md:162-163` vs `.owlbear/kanban/tasks/1155-implement-config-yml-schema-grouping-nested-sub-models.md:29-38`.
- I treated that as a deduction, not a FAIL, because the latest binding note in `#1155` already says the task must not return to backlog until `#1171` resolves and its AC is rewritten: `.owlbear/kanban/tasks/1155-implement-config-yml-schema-grouping-nested-sub-models.md:117`, `.owlbear/kanban/tasks/1155-implement-config-yml-schema-grouping-nested-sub-models.md:119`, `.owlbear/kanban/tasks/1155-implement-config-yml-schema-grouping-nested-sub-models.md:123`.

#### Necessity Check

- PASS. No new dependency, integration, or external capability introduced; research only.

#### Builder Process Quality

| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL

- `.owlbear/research/1171-config-write-path-audit.md` remains materially correct, but its Step 1 recommendation is now partly historical because #1174 has already removed the dead config_loader helpers.
- Related config suites are not clean today; this lowered confidence but did not invalidate the research deliverable.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| Audit the three independent config write paths and explain the divergence before #1155 implementation | Audit doc + live code agree on active writer, strip list, and flat migration output: `.owlbear/research/1171-config-write-path-audit.md:30`, `.owlbear/research/1171-config-write-path-audit.md:46`, `.owlbear/research/1171-config-write-path-audit.md:62-63`, `serve/kanban/src/owlbear_kanban/storage.py:236-250`, `serve/kanban/src/owlbear_kanban/migrate.py:367-447`, `serve/kanban/src/owlbear_kanban/engine.py:936` | N/A | PASS |
| Create actionable follow-up work for the live writer issues | #1174 and #1175 exist and still match live state: `.owlbear/kanban/tasks/1174-delete-config-loader-save-config-and-merge-into-dead-code.md:20-24`, `.owlbear/kanban/tasks/1174-delete-config-loader-save-config-and-merge-into-dead-code.md:88-94`, `.owlbear/kanban/tasks/1175-harden-storage-save-config-for-grouped-config-output.md:12`, `.owlbear/kanban/tasks/1175-harden-storage-save-config-for-grouped-config-output.md:24-28` | N/A | PASS |
| Carry the migrate/storage parity requirement into the #1155 handoff before implementation | Requirement is documented in #1171 research/body and reinforced by #1155's latest architecture note, though not yet promoted into the top checklist: `.owlbear/research/1171-config-write-path-audit.md:122-128`, `.owlbear/research/1171-config-write-path-audit.md:162-163`, `.owlbear/kanban/tasks/1171-audit-and-unify-config-write-paths-before-schema-grouping.md:66`, `.owlbear/kanban/tasks/1155-implement-config-yml-schema-grouping-nested-sub-models.md:117-123` | N/A | PASS |

### Deductions

- -0.04: `#1155` still lacks an explicit top-level parity AC bullet even though `#1171` identifies it as required; current protection is a later handoff note, not the primary checklist.
- -0.05: Related quality-runner suites currently fail on adjacent config surfaces, so runtime corroboration is not clean.

### Verdict

- PASS -> docs
- Confidence: 0.91
[[2026-04-29]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | Research-only task; no behavior, API, CLI, or package structure changes |
| 2 | Module docstrings | No | N/A | No Python modules created or modified |
| 3 | External attribution | No | N/A | All 6 high-relevance sources identified as internal (task body: "all internal") |
| 4 | Research doc | Yes | Verified | `.owlbear/research/1171-config-write-path-audit.md` exists and is linked in task body; follow-up tasks #1174 (dead code) and #1175 (harden save_config) confirmed present |
| 5 | Diagram maintenance (describes match) | No | N/A | Kanban diagram describes `serve/kanban/src/**` — no files in that path changed by #1171 |
| 6 | Explicit diagram creation | No | N/A | No diagram creation request in task body |
| 7 | Deletion detection | No | N/A | No files deleted |

### Scope Classification

| File | Scope | Action |
|------|-------|--------|
| `.owlbear/research/1171-config-write-path-audit.md` | IN | Verified (exists, linked, follow-ups created) |

### Files Updated

- None

### Child Tasks Created

- None

### Scratch Files Cleaned

- None (no `1171-*` scratch files found)
[[2026-04-29]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| Audit the three independent config write paths and explain divergence | Research doc `.owlbear/research/1171-config-write-path-audit.md` exists (commit `7405b130`), contains 3-path inventory with line refs (§3), 4 key findings | PASS |
| Create actionable follow-up work for live writer issues | #1174 (dead code deletion, backlog) and #1175 (harden save_config, backlog) both exist, both reference research doc | PASS |
| Carry migrate/storage parity requirement into #1155 handoff | Documented in research doc §4 Step 3 and reinforced by #1155 architecture note (L117-123). Not yet in #1155's formal AC checklist — downstream architect concern | PASS |

### Test Results

- pytest: 2834 passed, 117 failed, 4 skipped — all failures pre-existing (zero code changes in #1171)
- ruff: 4 violations, all outside task scope (knowledge, mcp-knowledge, mcp-memory, orchestrator)

### Architect Quality: 4/5

AC was implicit in description rather than formally enumerated. Adequate for research task scope — audit divergence, create follow-ups, carry parity requirement. Architect review table was thorough.

### Deduction Breakdown

- AC lines without evidence: 0 (all 3 have specific evidence)
- Lint violations in scope: 0
- AC quality ≤ 3: 0 (score 4)
- Missing reviewer evidence: 0 (present and detailed, PASS at 0.91)
- Full-suite failures in task scope: 0 (research, no code changes)

### Confidence: 0.98

### Action: archive

## Commits

| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 7405b130 | docs | .owlbear/research/1171-config-write-path-audit.md | #1171 |
| 6c7190a6 | chore | kanban task file | #1171 |
