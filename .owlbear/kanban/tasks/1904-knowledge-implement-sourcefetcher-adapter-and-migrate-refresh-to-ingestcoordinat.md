---
id: 1904
title: 'Knowledge: Implement SourceFetcher adapter and migrate refresh to IngestCoordinator
  (Phase B2b)'
status: backlog
priority: needed
created: 2026-05-27T23:24:10.601235+02:00
updated: 2026-05-28T04:38:09.440549+02:00
tags:
  - knowledge
  - layer-4
  - cleanup
  - quality
parent:
depends_on:
  - 1900
proof_bundle: skip
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Role
Parent coordination container. All implementation work is delegated to subtasks:

| ID | Title | Status |
|----|-------|--------|
| #1909 | Knowledge: Implement CompositeSourceFetcher adapter | review |
| #1910 | Knowledge: Fix IngestCoordinator.refresh() to propagate fetch errors | todo |
| #1911 | Knowledge: Wire SourceFetcher in MCP server and replace refresh handler | backlog (blocked on #1909, #1910) |

This task carries no implementation AC — completion is gated on subtask completion.

## Context
- Research: .owlbear/research/mcp-knowledge-legacy-removal-b2.md §3.3
- SourceFetcher protocol: `serve/knowledge/src/owlbear_knowledge/protocols/fetcher.py`

[[2026-05-28T01:41:57+02:00]]
## Planning
Research complete. Created 3 follow-up subtasks at backlog:

| ID | Title | Depends on |
|----|-------|------------|
| #1909 | Knowledge: Implement CompositeSourceFetcher adapter | — |
| #1910 | Knowledge: Fix IngestCoordinator.refresh() to propagate fetch errors | — |
| #1911 | Knowledge: Wire SourceFetcher in MCP server and replace refresh handler | #1909, #1910 |

Dependency graph: #1909 and #1910 are independent; #1911 depends on both.
All tasks: priority=needed, tags=knowledge,layer-4,cleanup, parent=#1904.

[[2026-05-28T01:52:16+02:00]]
## Architecture Review
Decomposition complete — planner created 3 subtasks (#1909, #1910, #1911) covering the full scope. Parent task advanced as coordination container; individual subtasks will receive architecture review at backlog.

[[2026-05-28T02:24:58+02:00]]
## Test-Writer Notes
- Non-impl pass-through: parent coordination container with `ac: []` (authoritative empty).
- Architecture Review confirmed this task is a delegation shell — all testable behavior lives in subtasks #1909 (CompositeSourceFetcher, behavioral), #1910 (IngestCoordinator error propagation, smoke), #1911 (MCP server wiring).
- No tests written at this level. Subtasks will each receive TDD RED treatment independently.

[[2026-05-28T02:49:13+02:00]]
## Builder Notes
- Implementation: no code changes (non-implementation parent coordination container)
- Tests: none required at parent level; all executable behavior delegated to subtasks #1909, #1910, #1911
- Coverage: n/a (no touched modules)
- ruff: n/a (no source edits)
- Approach: followed explicit pass-through trigger from Test-Writer Notes (`ac: []`, \"Non-impl pass-through\"), advanced container task only after verifying scope is delegation-only

[[2026-05-28T03:15:17+02:00]]
## Review Evidence
- Verdict: FAIL
- FAIL #1904 -> backlog | parent task contract is inconsistent: the task was reviewed as an empty-AC coordination shell, but its body still asserts unfinished MCP integration work that remains open.
- Resolution: Architect normalized body to remove stale implementation sections. Task now explicitly states parent-shell role with no implementation AC.

[[2026-05-28T03:33:58+02:00]]
## Architecture Review (re-review after reviewer rejection)
### Resolution
Reviewer correctly identified that the parent task body contained stale implementation assertions (Objective/Changes/Verification) contradicting its actual role as a coordination shell with `ac: []`. Normalized the body to explicitly declare parent-shell role and remove all implementation-level sections. Subtask status table replaces the former deliverable assertions.

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Coordination container only — no implementation scope |
| Interface clarity | PASS | ac: [] is authoritative; body states gating on subtask completion |
| Dependency correctness | PASS | depends_on=[1900] (archived); children #1909/#1910/#1911 carry their own deps |
| KISS/YAGNI | PASS | No abstractions — pure parent grouping |
| Pattern consistency | PASS | Follows standard parent-shell pattern |

### Proof-Bundle Validation
- Planner assignment: null
- Final bundle: skip
- Existing proof scope: N/A
- Test-writer: SKIP

### Challenge Results
- Challenger: SKIPPED — proof bundle `skip`

### Verdict: APPROVE (after REFINE)
### Action Taken: Removed stale Objective/Changes/Verification sections, added coordination framing with subtask status table, set proof_bundle=skip, added `quality` pass-through tag. Advanced to todo.

[[2026-05-28T03:57:28+02:00]]
## Test-Writer Notes
- Proof bundle: skip — no new test writing required.
- Passing through to builder.

[[2026-05-28T04:04:25+02:00]]
## Builder Notes
- Implementation: no code changes (parent coordination container pass-through)
- Tests: none required at parent level (`proof_bundle: skip`, `ac: []`, Test-Writer notes indicate "Non-impl pass-through")
- Coverage: n/a (no touched modules)
- ruff: n/a (no source edits)
- Evidence summary: task remains a delegation shell; executable behavior is delegated to subtasks #1909, #1910, and #1911
- Fixes applied: none

[[2026-05-28T04:38:09+02:00]]
## Review Evidence
- Verdict: FAIL
- FAIL #1904 -> backlog | parent coordination shell is in review before its own child-completion gate is satisfied.
- Blocking findings:
| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | Parent shell completion gate | The parent task says completion is gated on subtask completion, but child #1911 remains at backlog while #1904 is already in review. | .owlbear/kanban/tasks/1904-knowledge-implement-sourcefetcher-adapter-and-migrate-refresh-to-ingestcoordinat.md:5,33; .owlbear/kanban/tasks/1911-knowledge-wire-sourcefetcher-in-mcp-server-and-replace-refresh-handler.md:4 | backlog |
| 2 | Parent coordination state | The parent shell's child-status table is stale: it still shows #1909 as review and #1910 as todo even though both child tasks are done. As a coordination-only shell, its own coordination artifact is not current. | .owlbear/kanban/tasks/1904-knowledge-implement-sourcefetcher-adapter-and-migrate-refresh-to-ingestcoordinat.md:29,30; .owlbear/kanban/tasks/1909-knowledge-implement-compositesourcefetcher-adapter.md:4; .owlbear/kanban/tasks/1910-knowledge-fix-ingestcoordinator-refresh-to-propagate-fetch-errors.md:4 | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Return #1904 to a coordination-only holding state and define the parent-shell completion rule so it cannot advance to review until all delegated subtasks are complete. | .owlbear/kanban/tasks/1904-knowledge-implement-sourcefetcher-adapter-and-migrate-refresh-to-ingestcoordinat.md | 1904:5,33 and 1911:4 |
| 2 | architect | Refresh the parent coordination table to match live child statuses, or remove static child-status snapshots if they will drift. | .owlbear/kanban/tasks/1904-knowledge-implement-sourcefetcher-adapter-and-migrate-refresh-to-ingestcoordinat.md, .owlbear/kanban/tasks/1909-knowledge-implement-compositesourcefetcher-adapter.md, .owlbear/kanban/tasks/1910-knowledge-fix-ingestcoordinator-refresh-to-propagate-fetch-errors.md | 1904:29,30 vs 1909:4 and 1910:4 |

## Observations
- The normalized parent-shell framing is otherwise consistent with a `skip` proof bundle and no local code or test changes; the failure is workflow and coordination state, not implementation proof.
- This is a re-review cycle, so backlog routing is consistent with the loop-break rule.
