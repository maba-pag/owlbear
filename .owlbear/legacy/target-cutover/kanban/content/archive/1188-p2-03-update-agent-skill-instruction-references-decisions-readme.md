---
id: 1188
title: 'P2-03: Update agent/skill/instruction references + decisions README'
status: archived
priority: medium
created: 2026-04-30T00:52:05.085246+00:00
updated: 2026-04-30T06:18:57.244395+00:00
tags:
- phase-2
- scope:agents
- type:impl
- agent
parent: 1179
depends_on:
- 1186
- 1187
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---

## Acceptance Criteria

- 7 agent files updated (researcher, test-writer, builder, doc-writer, reviewer, auditor, orchestrator): scribe removed from `agents:` list, DR instructions replaced with `h-decision-requests` skill reference
- `share/skills/r-pipeline-protocol/SKILL.md`: all scribe references replaced with create_dr tool usage
- `share/skills/w-orchestration/SKILL.md`: "dispatch scribe" pattern removed from orchestration cycle
- `share/instructions/pipeline-agents.instructions.md`: scribe references removed (if present)
- `.owlbear/decisions/README.md` rewritten for new format: 5-field schema, Cockpit as primary resolve path, file-edit as fallback
- All static tests from #1186 pass (no stale scribe refs)

## Scope

- IN: reference updates across agent/skill/instruction files + decisions README rewrite
- OUT: new skill creation (done in #1187), code changes, Cockpit

Brief: see parent #1179

[[2026-04-30]]
## Research

Trivial docs-only task — gate items 1–4 N/A (rationale: mechanical reference update, schema implemented in `decisions.py`, format documented in `h-decision-requests` skill).

### Findings

- 5 of 6 AC bullets already satisfied by #1187 (agent files, r-pipeline-protocol, w-orchestration all clean).
- 2 remaining edits:
  1. `share/instructions/pipeline-agents.instructions.md` line 31: "create AR via scribe" → "create AR via `create_dr`"
  2. `.owlbear/decisions/README.md`: full rewrite per brief — 5-field YAML schema (task_id, agent, request_type, created, response), Cockpit as primary resolve path (Phase 3: #1190), file-edit as current fallback, remove all scribe references.
- #1186 tests already pass and will continue to pass (they don't cover these 2 files directly; just need to not re-introduce scribe in agent/skill files).

### Tier: T1 — Autonomous

Pure docs/reference cleanup. No new capability, no architecture change, no user decision needed.

### Implementation Notes for Builder

- pipeline-agents.instructions.md: one-line fix at line 31 ("via scribe" → "via `create_dr`")
- decisions/README.md: rewrite (~60 lines). Structure: (1) directory layout, (2) 5-field schema table, (3) For Users section with Cockpit as primary + file-edit as fallback, (4) For Agents section pointing to `h-decision-requests` skill. Remove CLI/bearclaw references (doesn't exist yet). Remove all scribe mentions.
- Run `uv run pytest tests/test_dr_skill_replacement_1186.py` as gate check after edits.


## Architecture Review

### AC with Test Depth

- 7 agent files verified clean (no scribe refs) (td:0)
- `r-pipeline-protocol/SKILL.md` verified clean (td:0)
- `w-orchestration/SKILL.md` verified clean (td:0)
- `pipeline-agents.instructions.md`: scribe reference removed (td:0)
- `.owlbear/decisions/README.md` rewritten for new format (td:0)
- All static tests from #1186 pass (td:0)

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One scope: remove stale scribe refs + rewrite README |
| Interface clarity | PASS | AC specifies exact files and target content |
| Dependency correctness | PASS | #1186 (tests), #1187 (skill+agent cleanup) both archived |
| Module layering | PASS | N/A — no code modules |
| TDD compliance | PASS | #1186 provides structural gate tests |
| KISS/YAGNI | PASS | Minimal mechanical edits |
| Premise challenge | PASS | Stale refs confirmed present (line 31, README lines 6/70) |
| Pattern consistency | PASS | Follows #1187 replacement pattern |
| Security surface | PASS | No system boundaries |
| Single domain | PASS | Agent/docs domain only |

### Design Diverge
- Trigger: skipped — single obvious approach (find-and-replace + README rewrite)

### Challenge Results
- Challenger: SKIPPED — all td:0
- Architect response: N/A

### Test Depth
- Max depth: 0
- Test-writer: SKIP

### Verdict: APPROVE
### Action Taken: Added `agent` pass-through tag. Advanced to todo.
[[2026-04-30]]
## Architecture Review — Summary

Verified codebase: only 2 stale scribe references remain (pipeline-agents.instructions.md line 31, decisions/README.md lines 6+70). Agent files, r-pipeline-protocol, and w-orchestration confirmed clean by #1187. Dependencies #1186/#1187 both archived. All 10 criteria PASS. All AC td:0 → Test-writer: SKIP. Added `agent` pass-through tag.
[[2026-04-30]]
## Test-Writer Notes
- Non-implementation task (tagged `agent`) — no tests applicable.
- All AC lines are (td:0) per architect: reference updates across agent/skill/instruction files + decisions README rewrite only.
- Passing through to builder.
[[2026-04-30]]
## Builder Notes
- Implementation: updated `share/instructions/pipeline-agents.instructions.md` and rewrote `.owlbear/decisions/README.md`.
- Fixes applied:
  - Replaced stale architect action text from `create AR via scribe` to `create AR via create_dr`.
  - Rewrote Decision Requests README to the new format with 5-field schema (`task_id`, `agent`, `request_type`, `created`, `response`), Cockpit-primary resolution guidance, and file-edit fallback.
  - Removed stale scribe/CLI-specific references from the README.
- Tests: `tests/test_dr_skill_replacement_1186.py` -> 9 passed, 0 failed, 0 skipped.
- Coverage: N/A for this docs-only scoped run.
- ruff: clean (non-Python lint paths skipped as expected by quality-runner).
- Evidence summary: AC-targeted stale references in both required files are now resolved and scoped static gate is green.

Post-task reflection:
- Non-impl pass-through notes should not skip verification when AC explicitly names pending file edits.
- For docs/reference tasks, a single scoped static suite is enough to prove no stale references were reintroduced.
- Keeping the diff to just AC-named files prevented collateral instruction churn.
[[2026-04-30]]
## Review Evidence

### Scope and Diff Reconstruction
- Builder commit hash was not recorded in the task body, so changed-file scope was reconstructed from builder notes and direct artifact inspection.
- Reconstructed changed files: `share/instructions/pipeline-agents.instructions.md`, `.owlbear/decisions/README.md`.
- Review depth: td:0 overall, but AC explicitly requires the #1186 static suite to pass, so I ran that suite independently in addition to the td:0 artifact review.

### Test Results
- quality-runner pytest: `uv run pytest tests/test_dr_skill_replacement_1186.py -q --tb=short`
- Result: 9 passed, 0 failed, 0 skipped.
- Key AC-mapped assertions are specific and binding:
  - `tests/test_dr_skill_replacement_1186.py:90-108` fails if any agent file still contains `scribe`.
  - `tests/test_dr_skill_replacement_1186.py:113-127` fails if `share/skills/r-pipeline-protocol/SKILL.md` lacks `create_dr` or still contains `scribe`.
  - `tests/test_dr_skill_replacement_1186.py:132-146` fails if `share/skills/w-orchestration/SKILL.md` still references `scribe`.

### Lint
- quality-runner ruff: `uv run ruff check tests/test_dr_skill_replacement_1186.py`
- Result: clean.
- Note: the changed markdown/instructions files are outside ruff scope for this workflow, so those artifacts were verified by direct content inspection.

### Coverage
- Not requested / not applicable for this docs/reference scoped run.

### Pass 1 - Critical
#### Test-Writer AC Coverage
- No `TestFromAC_*` classes are in scope for this task. The task-owned static suite uses direct file-content assertions rather than pass-through smoke checks.

#### Security Review
- No issues found. The builder changed documentation/instruction files only; no executable boundary, dependency, secret-handling, or persistence logic changed.

#### Test Integrity
- No `TestFromAC_*` modifications in scope.

#### Test Quality
- STRONG. The static suite uses exact file existence and file-content assertions (`tests/test_dr_skill_replacement_1186.py:72-146`) that would fail on a stale `scribe` reference or missing `create_dr` replacement.

#### Data Safety
- No issues found. No runtime data flow or mutation path changed.

#### Implementation-Aware Gap Analysis
- No blocking gaps found. The only AC not covered by the #1186 static suite was the two-file documentation cleanup in this task; both were reviewed directly against the written contract.

#### Necessity Check
- Skipped. No dependency, integration, or external capability was added.

#### Builder Process Quality
- CLEAN. One `## Builder Notes` section, no retry loop evidence.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| 7 agent files verified clean (no scribe refs) | `tests/test_dr_skill_replacement_1186.py:90-108` plus green pytest run (9 passed) proves agent-file scan is clean; `share/agents/orchestrator.agent.md:8-18` shows the `agents:` list no longer includes `scribe`. | `test_no_scribe_references_in_agent_files` | PASS |
| `share/skills/r-pipeline-protocol/SKILL.md` verified clean | File contains `create_dr` guidance at `share/skills/r-pipeline-protocol/SKILL.md:55-57`, `:63-64`, `:246-267`; static assertions at `tests/test_dr_skill_replacement_1186.py:113-127` passed. | `test_r_pipeline_protocol_contains_create_dr`, `test_r_pipeline_protocol_does_not_contain_scribe` | PASS |
| `share/skills/w-orchestration/SKILL.md` verified clean | Independent inspection of `share/skills/w-orchestration/SKILL.md:1-197` found no `scribe` dispatch/prose; static assertions at `tests/test_dr_skill_replacement_1186.py:132-146` passed. | `test_w_orchestration_does_not_reference_scribe`, `test_w_orchestration_does_not_contain_scribe_subagent_dispatch` | PASS |
| `share/instructions/pipeline-agents.instructions.md`: scribe reference removed | `share/instructions/pipeline-agents.instructions.md:31` now says `create AR via create_dr`; direct inspection of `:24-36` shows the updated user-action responsibility table and no stale scribe wording. | manual artifact review | PASS |
| `.owlbear/decisions/README.md` rewritten for new format | `.owlbear/decisions/README.md:8-18` defines the 5-field schema (`task_id`, `agent`, `request_type`, `created`, `response`); `:22-30` makes Cockpit the primary path with file-edit fallback; `:51-53` points agents to `h-decision-requests`. | manual artifact review | PASS |
| All static tests from #1186 pass | quality-runner pytest result: `9 passed in 0.38s`; no failures or skips. | full suite `tests/test_dr_skill_replacement_1186.py` | PASS |

### Deductions
- -0.02 confidence: no automated check in the #1186 suite directly covers `share/instructions/pipeline-agents.instructions.md` or `.owlbear/decisions/README.md`; mitigated by direct line-by-line artifact review of both files.

### Verdict
- PASS -> docs | confidence 0.96

### Action
- Advancing to `docs`.

### Post-task Reflection
- Docs-only tasks still need direct artifact inspection when AC names specific files; green scoped pytest alone would be a false green here.
- The builder note omitted a commit hash, so diff scoping had to be reconstructed from the task body and live files.
- The #1186 static suite is strong for stale-reference regression detection, but it does not cover the two 1188-only documentation artifacts, so manual proof remains necessary.
[[2026-04-30]]
## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | No IN-scope prose docs (README.md, setup-guide.md, share/README.md) reference scribe or the decisions README format. `serve/kanban/README.md` mentions Decision Requests in engine pipeline context — no scribe wording, no change needed. |
| 2 | Module docstrings | No | N/A | No Python modules changed. Builder modified markdown/instructions files only. |
| 3 | External attribution | No | N/A | Mechanical reference-update task. No external patterns used. |
| 4 | Research doc | No | N/A | Research is inline in task body; no separate `.owlbear/research/` file created. |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/project-overview.excalidraw` has `describes: serve/*/pyproject.toml, share/**, setup/**, .owlbear/**` — matches both changed files (`share/instructions/pipeline-agents.instructions.md` via `share/**`; `.owlbear/decisions/README.md` via `.owlbear/**`). Footer updated: `Last verified: 2026-04-30 (f4dceb71)`. Committed: a6d5b269. |
| 6 | Explicit diagram creation | No | N/A | No explicit diagram creation request in task body. |
| 7 | Deletion detection | No | N/A | No files deleted. No orphaned IN-scope docs detected. |

### Scope Classification

| File | Scope | Action |
|------|-------|--------|
| `share/instructions/pipeline-agents.instructions.md` | OUT (agent-executable `.instructions.md`) | N/A — not edited by doc-writer |
| `.owlbear/decisions/README.md` | IN (documentation file, rewritten by builder as primary deliverable) | Verified accurate: 5-field schema table present, Cockpit-primary path documented, file-edit fallback present, `h-decision-requests` pointer present, no scribe references |
| `share/diagrams/project-overview.excalidraw` | IN (diagram with describes-match) | Footer updated |

### Files Updated
- `share/diagrams/project-overview.excalidraw` (footer only — commit a6d5b269)

### Child Tasks Created
- None

### Scratch Files Cleaned
- None found (`.owlbear/scratch/1188-*` — no matches)
[[2026-04-30]]
## Audit

### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| 7 agent files clean (no scribe refs) | test_dr_skill_replacement_1186.py:90-108 green (9 passed, 0 failed) | PASS |
| r-pipeline-protocol/SKILL.md clean | test_dr_skill_replacement_1186.py:113-127 green | PASS |
| w-orchestration/SKILL.md clean | test_dr_skill_replacement_1186.py:132-146 green | PASS |
| pipeline-agents.instructions.md: scribe removed | Direct inspection L24-36: "create AR via create_dr" confirmed | PASS |
| decisions/README.md rewritten | Direct inspection: 5-field schema table, Cockpit primary path, file-edit fallback, h-decision-requests pointer, no scribe refs | PASS |
| All static tests from #1186 pass | Full suite: test_dr_skill_replacement_1186.py 9/9 passed | PASS |

### Test Results
- pytest: 3262 passed, 67 failed (all pre-existing background debt: tasks 1068, 1050, 1015, 1101, 1189), 4 skipped
- ruff: 4 violations in unrelated packages (knowledge, mcp-knowledge, mcp-memory, orchestrator)
- No task-scoped failures

### Upstream Commits
- f37d8910 docs: update DR references and README format (#1188, builder)
- a6d5b269 docs: update project-overview diagram footer (#1188, doc-writer)

### Architect Quality: 4/5
Specific file targets, clear scope boundaries, td:0 appropriate for docs-only reference task. Minor gap: README rewrite AC could specify exact expected sections rather than "rewritten for new format."

### Deduction Breakdown
- AC lines without evidence: 0 (all 6 verified)
- Lint violations in task scope: 0
- AC quality: 4/5 (above threshold)
- Reviewer evidence: present, detailed, PASS
- Task-scoped test failures: 0
- Total deductions: 0

### Confidence: 1.00
### Action: archive

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| c3f1380b | chore | .owlbear/kanban/tasks/1188-*.md | #1188 |