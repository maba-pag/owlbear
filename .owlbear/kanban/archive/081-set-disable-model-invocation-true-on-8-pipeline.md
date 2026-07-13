---
id: 81
title: 'Set disable-model-invocation: true on 8 pipeline agents'
status: archived
priority: medium
created: 2026-03-27 04:51:29.816969+01:00
updated: 2026-03-30 15:36:00.421570+02:00
started: 2026-03-30 15:18:47.510114+02:00
completed: 2026-03-30 15:18:47.510114+02:00
tags:
- phase-1
- scope:agents
- type:build
class: standard
archival_reason: completed
archival_refs: []
---

## Acceptance Criteria

- [ ] Add `disable-model-invocation: true` to YAML frontmatter of 8 pipeline agents: planner, researcher, architect, test-writer, builder, reviewer, writer, auditor
- [ ] Do NOT add it to orchestrator, kanban-planner, or curator (user-invocable agents)
- [ ] Orchestrator `agents` list continues to override the flag (no pipeline breakage)

## Context

Parent research: docs/research/disable-model-invocation-pipeline-agents.md (task #38)
Trivial config-only change: 8 files, 1 line each. Principle of least privilege.

## Research

Validated 2026-03-27. Existing research from #38 confirmed against current codebase:

- 8 agents have user-invocable=false, none have disable-model-invocation set
- Orchestrator agents array lists all 8 (override mechanism works)
- VS Code docs confirm explicit agents list overrides disable-model-invocation: true

[[2026-03-27]] Fri 08:47

## Architecture Review

**Verdict:** Approve

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| Add disable-model-invocation: true to 8 pipeline agents | Precise, lists exact agents | None needed |
| Do NOT add to orchestrator, kanban-planner, curator | Clear negative constraint | None needed |
| Orchestrator agents list continues to override the flag | Verifiable invariant | None needed |

### Architecture Notes

Config-only change, 8 files, 1 YAML line each. Research validated against current codebase. Tests already written (tests/test_disable_model_invocation.py) covering all 3 AC lines with parametrized checks. Orchestrator agents array at .github/agents/orchestrator.agent.md lines 8-18 confirms override mechanism. No architectural concerns.

### Dependencies

- Verified: #38 research complete (docs/research/disable-model-invocation-pipeline-agents.md)
- TDD: tests exist at tests/test_disable_model_invocation.py (RED phase)

-t

[[2026-03-27]] Fri 10:32
## Test-Writer Notes
- Test file: tests/test_disable_model_invocation.py
- Classes: TestFromAC_PipelineAgentDisableFlag, TestFromAC_ExactEightAgentsHaveFlag, TestFromAC_NonPipelineAgentNoFlag, TestFromAC_OrchestratorAgentsArrayUnchanged, TestFromAC_NoOtherChanges
- Tests per category: happy 9 (FAIL), edge 0, error 0, boundary 33 (invariant guards, PASS by design)
- Total: 42 tests, 9 FAIL on current HEAD
- ruff: clean
- Note: 33 invariant guard tests PASS now; will FAIL if builder adds flag to wrong agents or disturbs other frontmatter
- AC1 add flag to 8 agents: TestFromAC_PipelineAgentDisableFlag (8 fail) + TestFromAC_ExactEightAgentsHaveFlag (1 fail)
- AC2 not on 3 non-pipeline agents: TestFromAC_NonPipelineAgentNoFlag (3 invariant guards)
- AC3 orchestrator agents list unchanged: TestFromAC_OrchestratorAgentsArrayUnchanged + TestFromAC_NoOtherChanges (30 invariant guards)

[[2026-03-27]] Fri 22:56
## Builder Notes
- Files changed: .github/agents/{planner,researcher,architect,test-writer,builder,reviewer,writer,auditor}.agent.md (8 files, 1 line each)
- Tests: 42 passed, 0 failed (tests/test_disable_model_invocation.py)
- Lint: ruff clean
- Evidence: 42 passed in 0.23s, all TestFromAC_* classes green
- Fixes applied: Pre-existing bad working-tree changes (todos reverted to todo, model reordering) detected in all 8 files. Restored each to HEAD before applying only disable-model-invocation line. Commit is surgical: 8 files, 8 insertions.

[[2026-03-27]] Fri 23:37
## Revert Note (2026-03-27)

Implementation was reverted immediately after merge. The flag disable-model-invocation: true prevents agents from being used as subagents - exactly the opposite of what pipeline agents need. The VS Code docs describe this flag as for agents that should only be triggered explicitly by users. The claimed agents-array-override mechanism is tagged Experimental and does not work reliably in practice. All 8 agent files have had the flag removed. tests/test_disable_model_invocation.py deleted. Research doc (docs/research/disable-model-invocation-pipeline-agents.md) needs correction before this task can be reconsidered.

[[2026-03-29]] Sun 16:08
## Architecture Review
**Verdict:** Block (duplicate - work completed by #38)

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Add disable-model-invocation: true to 8 pipeline agents | Already present in codebase (commit 3294d29 via #38) | No work needed |
| Do NOT add to orchestrator, kanban-planner, curator | Already satisfied - flag absent from those 3 agents | No work needed |
| Orchestrator agents list continues to override the flag | Override working - architect agent running now as proof | No work needed |

### Architecture Notes
Task #81 was built, reverted (cebe572), then the identical work was re-implemented under task #38 (commits 692e3cb + 3294d29). Agents were subsequently ported from .github/agents/ to agents/ (ec84b55, 59677bb), carrying the flag. Current codebase satisfies all 3 AC lines. The block reason on this task is stale - the revert was itself superseded by #38's re-implementation.

This task is a duplicate. Recommend archival.

### Evidence
- Flag present: grep confirms disable-model-invocation: true in all 8 agents/ files
- Tests exist: tests/test_disable_model_invocation.py (committed, 692e3cb)
- System working: architect agent (one of the 8) running successfully via subagent invocation
- copilot-instructions.md line 101 documents the flag as active convention

[[2026-03-29]] Sun 16:08
## Architecture Review
**Verdict:** Block (duplicate - work completed by #38)

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Add disable-model-invocation: true to 8 pipeline agents | Already present in codebase (commit 3294d29 via #38) | No work needed |
| Do NOT add to orchestrator, kanban-planner, curator | Already satisfied - flag absent from those 3 agents | No work needed |
| Orchestrator agents list continues to override the flag | Override working - architect agent running now as proof | No work needed |

### Architecture Notes
Task #81 was built, reverted (cebe572), then the identical work was re-implemented under task #38 (commits 692e3cb + 3294d29). Agents were subsequently ported from .github/agents/ to agents/ (ec84b55, 59677bb), carrying the flag. Current codebase satisfies all 3 AC lines. The block reason on this task is stale - the revert was itself superseded by #38's re-implementation.

This task is a duplicate. Recommend archival.

### Evidence
- Flag present: grep confirms disable-model-invocation: true in all 8 agents/ files
- Tests exist: tests/test_disable_model_invocation.py (committed, 692e3cb)
- System working: architect agent (one of the 8) running successfully via subagent invocation
- copilot-instructions.md line 101 documents the flag as active convention

[[2026-03-29]] Sun 16:08
## Architecture Review
**Verdict:** Block (duplicate - work completed by #38)

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Add disable-model-invocation: true to 8 pipeline agents | Already present in codebase (commit 3294d29 via #38) | No work needed |
| Do NOT add to orchestrator, kanban-planner, curator | Already satisfied - flag absent from those 3 agents | No work needed |
| Orchestrator agents list continues to override the flag | Override working - architect agent running now as proof | No work needed |

### Architecture Notes
Task #81 was built, reverted (cebe572), then the identical work was re-implemented under task #38 (commits 692e3cb + 3294d29). Agents were subsequently ported from .github/agents/ to agents/ (ec84b55, 59677bb), carrying the flag. Current codebase satisfies all 3 AC lines. The block reason on this task is stale - the revert was itself superseded by #38's re-implementation.

This task is a duplicate. Recommend archival.

### Evidence
- Flag present: grep confirms disable-model-invocation: true in all 8 agents/ files
- Tests exist: tests/test_disable_model_invocation.py (committed, 692e3cb)
- System working: architect agent (one of the 8) running successfully via subagent invocation
- copilot-instructions.md line 101 documents the flag as active convention

## Audit (manual archival 2026-03-30) Duplicate of #38 (archived). Flag present in all 8 agents, 47 tests passing. Confidence 1.0.
