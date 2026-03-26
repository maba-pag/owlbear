---
id: 766
title: Triage orphaned research tasks — backfill follow-ups
status: archived
priority: needed
created: 2026-03-13T09:31:39.352134+01:00
updated: 2026-03-21T03:39:36.2920152+01:00
started: 2026-03-13T10:28:09.5098994+01:00
completed: 2026-03-21T03:39:32.3165535+01:00
tags:
    - research
    - process
class: standard
---

## Context

Audit found ~11 research tasks that produced docs but never created follow-up kanban tasks.
See session plan for the full list.

## Acceptance Criteria

- [ ] Review each orphaned research task: #127, #137, #141, #16, #22, #246, #253, #255, #262, #263, #264
- [ ] For each: either create follow-up tasks at ideation, file a decision request, or add explicit 'no action needed' justification to the research doc
- [ ] Verify no other archived research tasks are missing follow-ups
- [ ] All orphaned research docs in docs/ root (agent-quality-analysis.md, code-quality-audit.md, graph-expansion-benchmark-results.md) have Follow-up Tasks sections

[[2026-03-20]] Fri 17:57

## Refined Task Contract

The original AC above is stale and is superseded by the contract below.

1. docs/research/orphaned-research-triage.md is updated so every disposition matches current board and codebase state, including: #137 marked as already covered by the implemented MCP follow-ups in src/owlbear/tools/mcp_registry.py and src/owlbear/tools/mcp_servers.py; #262 marked as closed because #776 duplicates archived #274; and the root-doc table updated to reflect that docs/agent-quality-analysis.md, docs/code-quality-audit.md, and docs/graph-expansion-benchmark-results.md already contain follow-up or explicit no-action sections.
2. For each archived task in the original orphaned list (#16, #22, #127, #137, #141, #246, #253, #255, #262, #263, #264), the final disposition is recorded in either the originating research doc Follow-up Tasks section or docs/research/orphaned-research-triage.md, with a concrete reference to the replacement task, implemented module, or explicit no-action justification.
3. The final task update lists any still-open backlog items that only exist because of this orphaned-follow-up sweep and gives a concrete recommended disposition for each without editing those other tasks. Current candidates: #574 and #776.
4. The task ends with a verification note describing how the archived-research audit was rerun and explicitly stating whether any additional orphaned research docs or tasks remain. If any remain, list the new ideation task IDs or decision request paths created from this sweep; otherwise state no additional orphaned research tasks found.

## Architecture Review

Verdict: APPROVED

### AC Assessment

- Original AC1 was partial: the source list was useful, but it did not identify the output artifact or account for board changes since 2026-03-13. Superseded with a contract anchored to docs/research/orphaned-research-triage.md and current-state reconciliation.
- Original AC2 was partial: the disposition categories were right, but superseded-by-implementation cases like #137 were not explicit and could trigger duplicate work. Superseded with a requirement to cite the replacement task, implemented module, or explicit no-action justification.
- Original AC3 was weak: it required a broad audit without an evidence trail. Superseded with a required verification note that states the rerun method and whether any orphaned items remain.
- Original AC4 was stale: docs/agent-quality-analysis.md, docs/code-quality-audit.md, and docs/graph-expansion-benchmark-results.md already satisfy the intent, and #574 already tracks the old audit gap. Superseded with current-state reconciliation instead of recreating already-completed doc sections.

### Architecture Notes

This is a single-domain process and docs reconciliation task, not a new implementation sweep. The authoritative artifact is already docs/research/orphaned-research-triage.md, so the task contract should update that artifact to current state rather than repeat the original March 13 audit from scratch.
Current board and code evidence shows the original AC is stale: docs/agent-quality-analysis.md, docs/code-quality-audit.md, and docs/graph-expansion-benchmark-results.md already contain follow-up or no-action sections; src/owlbear/tools/mcp_registry.py and src/owlbear/tools/mcp_servers.py already cover the concrete MCP follow-ups that #137 called for; and kanban/tasks/776-add-graph-community-detection-leiden-algorithm-to.md is already marked as a duplicate of archived kanban/tasks/274-add-graph-community-detection-leiden-algorithm.md.
TDD compliance is not applicable because the refined scope is documentation and board reconciliation only and does not call for .py or test changes.

### Changes Made

- Added a superseding refined task contract tied to docs/research/orphaned-research-triage.md.
- Removed the obsolete expectation to recreate root-doc follow-up sections by replacing it with current-state verification.
- Advanced #766 from backlog to todo.

### Dependencies

- Verified: docs/research/orphaned-research-triage.md is the source artifact for this task.
- Verified: kanban/tasks/574-add-follow-up-tasks-to-3-research-docs-missing.md and kanban/tasks/776-add-graph-community-detection-leiden-algorithm-to.md are stale-task candidates to document, not tasks to mutate from #766.
- Verified: no TDD predecessor is required because the refined task is docs and process only.

[[2026-03-20]] Fri 18:51

## Test-Writer Notes

Non-implementation task (tagged: research, process) — no tests applicable.
Architecture review explicitly states: 'TDD compliance is not applicable because the refined scope is documentation and board reconciliation only and does not call for .py or test changes.'
Passing through to builder.

test append probe

lineA
lineB

[[2026-03-21]] Sat 02:37
## Review Evidence
Review: #766 - Triage orphaned research tasks - backfill follow-ups

### Test Results
- uv run pytest tests/test_mcp_registry.py tests/test_mcp_servers.py -q --tb=short
- Result: 47 passed, 0 failed (2 optional-dependency warnings)

### Lint Results
- uv run ruff check src/owlbear/tools/mcp_registry.py src/owlbear/tools/mcp_servers.py
- Result: All checks passed

### Coverage
- N/A. Task scope is documentation and board reconciliation only.

### Pass 1 - CRITICAL
- Security review: No security findings in reviewed changes.
- Test integrity: N/A for docs/process task (no TestFromAC contract for this task).
- Test quality: N/A for docs/process task (no task-owned test edits).
- Data safety: No data-safety findings; no persistence or concurrency code changed.

### Pass 2 - INFORMATIONAL
- Task body has no Builder Notes section; review evidence is based on direct diff inspection and independent verification commands.

### AC Compliance
- AC1 PASS: docs/research/orphaned-research-triage.md now records #137 as covered via mcp_registry.py and mcp_servers.py, #262 as closed via #776 duplicate of archived #274, and updates the root-doc table.
- AC2 PASS: docs/research/orphaned-research-triage.md section 2 records dispositions for all 11 required IDs (#16, #22, #127, #137, #141, #246, #253, #255, #262, #263, #264).
- AC3 PASS: docs/research/orphaned-research-triage.md recommendation section lists still-open backlog items #574 and #776 with concrete archive recommendations.
- AC4 PASS: docs/research/orphaned-research-triage.md verification note documents rerun method and explicitly states no additional orphaned research docs/tasks remain.

### Verdict
PASS
Confidence: .93

### Action Taken
- Move #766 from review to docs.

[[2026-03-21]] Sat 02:59
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Process/doc reconciliation task - no behavior, API, or convention change |
| 2 | Docstrings complete | No | N/A | No .py files created or modified; architecture review explicitly states no code changes |
| 3 | docs/sources/overview.md | No | N/A | No external patterns or repos used - internal audit only |
| 4 | README.md | No | N/A | No CLI commands added or modified |
| 5 | Research doc linked | Yes | Pass | docs/research/orphaned-research-triage.md exists, is comprehensive (6 sections), and is linked in task body |
| 6 | Scratch files | None | Pass | No docs/scratch/766-* files found |

### Files Updated
- None

### Scratch Files Cleaned
- None

[[2026-03-21]] Sat 03:39
## Audit
### AC Verification (Refined Contract)
| AC | Evidence | Status |
|-----|----------|--------|
| AC1: Research doc updated with current-state dispositions | #137 = Covered (mcp_registry.py + mcp_servers.py verified), #262 = Closed (#776 dup of #274), root-doc table updated with line refs | PASS |
| AC2: All 11 orphaned tasks have final disposition | Section 2 table covers all 11 IDs with concrete references | PASS |
| AC3: Still-open backlog items listed with recommendations | Section 4 lists #574 (archive as superseded) and #776 (archive as dup of #274) | PASS |
| AC4: Verification note with rerun methodology | Section 6 documents 4-step audit methodology and explicitly states no additional orphaned tasks found | PASS |

### Test Results
- pytest: 3691 passed, 90 failed (all pre-existing: numpy compat, bootstrap unpacking, AgentRegistry args), 20 skipped, 2 collection errors (missing modules). No task-related regressions.
- ruff: 461 pre-existing errors. No task-related code changes.
- Task scope: docs/process only — no .py files modified.

### Confidence: .97
### Action: archive

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 8b1022a | docs | docs/research/orphaned-research-triage.md | #766 |
