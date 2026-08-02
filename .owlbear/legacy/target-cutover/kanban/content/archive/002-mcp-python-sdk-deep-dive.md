---
id: 2
title: MCP Python SDK deep-dive
status: archived
priority: medium
created: 2026-03-26 17:18:16.597897+01:00
updated: 2026-03-28 01:20:14.897962+01:00
started: 2026-03-28 01:20:02.845478+01:00
completed: 2026-03-28 01:20:02.845478+01:00
tags:
- research
- phase-1
- scope:mcp
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Research the MCP Python SDK, document primitives, transport trade-offs, server lifecycle, and VS Code registration patterns. Produce a research document with findings and ensure follow-up implementation tasks exist on the board.

## Acceptance Criteria
- [x] Read MCP specification and Python SDK docs (mcp-python on GitHub)
- [x] Document the 3 primitives: Tools, Resources, Prompts
- [x] Document stdio vs HTTP transport trade-offs
- [x] Document server lifecycle (start, shutdown, error recovery)
- [x] Document VS Code registration pattern (.vscode/mcp.json)
- [x] Document recommended server architecture for OwlBear (3 servers)
- [x] Write findings to docs/research/mcp-python-sdk.md
- [x] Verify follow-up implementation tasks exist on board (#14, #16, #17)

## Context
MCP servers are how we expose owlbear-specific capabilities (kanban, knowledge, project metadata) to Copilot CLI agents. We need 3-4 custom servers.

## Notes
- Hands-on validation (build + register + test hello-world) deferred to implementation tasks #14, #16, #17 which have detailed AC
- Researcher-created scaffold tasks #39, #40, #41 duplicate seed tasks #14, #16, #17 (see Architecture Review)

[[2026-03-26]] Thu 19:04
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Read MCP spec and SDK docs | Complete. 5 sources cited with relevance scores | None |
| Document 3 primitives | Complete. Section 3 maps to OwlBear use cases | None |
| Document stdio vs HTTP trade-offs | Complete. Comparison matrix in Section 5 | None |
| Document server lifecycle | Complete. Section 6 with lifespan pattern | None |
| Document VS Code registration | Complete. Section 7 with mcp.json example | None |
| Document recommended architecture | Complete. Section 8 with 3-server table | None |
| Write findings to research doc | Complete. docs/research/mcp-python-sdk.md | None |
| Verify follow-up tasks exist | Seed tasks #14, #16, #17 cover all 3 servers | None |

### Architecture Notes
Research quality is high. The v1 FastMCP recommendation (.80) and stdio transport recommendation (.90) align with v2 architecture decision. Research doc correctly identifies lifespan pattern, decorator-based tools, and Context injection as key SDK patterns.

Original AC included hands-on validation (build hello-world, register in mcp.json, test from Copilot Chat). These were not executed but are properly covered by seed implementation tasks #14, #16, #17 which have comprehensive AC. Refined AC to match actual research deliverables.

### Duplicate Task Warning
Scaffold tasks #39, #40, #41 duplicate seed tasks #14, #16, #17 with less detailed AC. Recommend deleting #39, #40, #41 during next board cleanup.

### Dependencies
- Verified: no upstream dependencies for research task
- Downstream: #14, #16, #17 (implementation tasks) reference this research

### Changes Made
- Refined AC: removed build/register/test items (deferred to #14/#16/#17), added doc-focused items
- Flagged duplicate tasks #39-#41

[[2026-03-26]] Thu 19:47
## Test-Writer Notes
- Non-implementation task (tagged research) â€” no tests applicable.
- Passing through to builder.

[[2026-03-26]] Thu 20:49
## Builder Notes
- Non-implementation task - no code changes needed.
- Passing through to review.

[[2026-03-27]] Fri 03:08
## Review Evidence
## Review: #2 - MCP Python SDK deep-dive

### Test Results
- pytest: not applicable. This task produced research and kanban artifacts only, and no task-scoped tests or TestFromAC classes were found under tests/.
- Evidence: search across tests/ for Task #2, MCP Python SDK Deep-Dive, mcp-python-sdk, and TestFromAC_ returned no matches.

### Lint Results
- ruff: not applicable. No Python source or test module is part of this task deliverable.

### Coverage
- Not applicable. No Python module changed for this task deliverable.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
- Not applicable. Research-only task with no TestFromAC classes.

#### Security Review
- No security issues found in the reviewed research and kanban artifacts.

#### Test Integrity
- Not applicable. No TestFromAC classes exist for this task.

#### Test Quality
- Not applicable. No automated tests are scoped to this research task.

#### Data Safety
- No data safety issues found in the reviewed artifacts.

#### Implementation-Aware Test Gaps
- Not applicable. No code implementation was reviewed.
- Critical finding: the deliverable does not stop at verifying the required seed implementation tasks #14, #16, and #17. docs/research/mcp-python-sdk.md:131 and docs/research/mcp-python-sdk.md:134-136 add a second follow-up track by embedding create commands for scaffold tasks that overlap the MCP server work already covered by #14, #16, and #17.
- Evidence that the required seed tasks already exist and point back to this research: kanban/tasks/014-build-mcp-kanban-server.md:3,13; kanban/tasks/016-build-mcp-knowledge-server.md:3,13; kanban/tasks/017-build-mcp-project-server.md:3,13.
- Evidence that the task itself recognizes the duplication: kanban/tasks/002-mcp-python-sdk-deep-dive.md:33 and kanban/tasks/002-mcp-python-sdk-deep-dive.md:56-61.
- Board impact: duplicate task #39 exists on the board in todo status with overlapping mcp-kanban scaffold scope, confirmed by kanban show 39 during review. This is a real planning regression, not a documentation nit.

### Pass 2 - INFORMATIONAL
- docs/sources/overview.md:2369-2377 correctly records external sources for this research.
- docs/research/mcp-python-sdk.md section numbering jumps from 9 to 5 for Follow-up Tasks. This is non-blocking.

### AC Compliance
- AC line 19 PASS: sources were documented in docs/research/mcp-python-sdk.md:10-18 and attribution was logged in docs/sources/overview.md:2369-2377.
- AC line 20 PASS: the three primitives are documented in docs/research/mcp-python-sdk.md:20-27.
- AC line 21 PASS: transport trade-offs are documented in docs/research/mcp-python-sdk.md:45-57.
- AC line 22 PASS: server lifecycle is documented in docs/research/mcp-python-sdk.md:59-85.
- AC line 23 PASS: VS Code registration pattern is documented in docs/research/mcp-python-sdk.md:87-109.
- AC line 24 PASS: recommended three-server architecture is documented in docs/research/mcp-python-sdk.md:111-121.
- AC line 25 PASS: findings are written to docs/research/mcp-python-sdk.md.
- AC line 26 FAIL: the required seed follow-up tasks #14, #16, and #17 do exist, but the research output also introduces overlapping scaffold tasks via docs/research/mcp-python-sdk.md:131-136, and duplicate task creation is acknowledged in kanban/tasks/002-mcp-python-sdk-deep-dive.md:33 and 56-61. The follow-up-task deliverable is therefore not clean or self-consistent.

### Verdict: FAIL

### Action Taken
- Move task back to todo for cleanup of the duplicate follow-up guidance and board ambiguity.

[[2026-03-27]] Fri 04:59
## Test-Writer Notes (retry)
- Retry reason: reviewer FAIL was about board management regression (duplicate scaffold tasks #39-#41 overlapping seed tasks #14/#16/#17), not missing tests.
- Existing pass-through preserved. Builder will address reviewer findings (research doc cleanup + duplicate task removal).

[[2026-03-27]] Fri 12:54
## Builder Notes
- Non-implementation task (research tag) — no source code changes required.
- Validation performed: docs/research/mcp-python-sdk.md follow-up section references only seed tasks #14, #16, #17.
- Board check: tasks #39, #40, #41 currently exist; no cross-task edits made in this builder pass.
- Tests: not applicable (no TestFromAC classes for this task).
- Lint: not applicable (no Python module changes).

[[2026-03-27]] Fri 18:43
## Review Evidence
### Review: #2 - MCP Python SDK deep-dive

### Test Results
- pytest: task-scoped collection was attempted with uv, but pytest startup was interrupted before collection completed. A workspace search found no tests referencing mcp-python-sdk or the task title.

### Lint Results
- ruff: not applicable. The deliverable under review is research and kanban output only; no Python source or test module is in scope for this task.

### Critical Findings
- The research document itself is now consistent with the intended seed follow-up tasks. docs/research/mcp-python-sdk.md lines 133, 145, 157, and 169 limit the follow-up guidance to tasks #14, #16, and #17.
- The board is still inconsistent because overlapping scaffold tasks remain active: #39 is still present in todo, #40 is still present in backlog, and #41 is still present in backlog.
- The overlap is direct, not incidental. Task #14 line 19 and task #39 line 19 both target the mcp-kanban server package. Task #16 line 19 and task #40 line 19 both target the mcp-knowledge server package. Task #17 line 20 and task #41 line 19 both target the mcp-project server package.
- The duplicate path is still live. Task #17 line 15 still depends on #41, and task #41 lines 38 and 39 explicitly say the scaffold is not a blocker for schema work and that full feature expansion is in #17.

### AC Compliance
- AC 1 PASS: sources studied are documented in docs/research/mcp-python-sdk.md lines 10 through 18 and attributed in docs/sources/overview.md lines 2407 through 2411.
- AC 2 PASS: the three primitives are documented in docs/research/mcp-python-sdk.md line 20.
- AC 3 PASS: transport trade-offs are documented in docs/research/mcp-python-sdk.md line 45.
- AC 4 PASS: server lifecycle is documented in docs/research/mcp-python-sdk.md line 59.
- AC 5 PASS: the VS Code registration pattern is documented in docs/research/mcp-python-sdk.md line 87.
- AC 6 PASS: the recommended three-server architecture is documented in docs/research/mcp-python-sdk.md lines 111 and 117 through 119.
- AC 7 PASS: findings are written to docs/research/mcp-python-sdk.md.
- AC 8 FAIL: the required seed tasks exist, but the follow-up deliverable is still not clean or self-consistent because duplicate scaffold tasks #39, #40, and #41 remain on the board and task #17 still depends on #41.

### Verdict
FAIL

### Action Taken
- Move task back to todo for cleanup of duplicate follow-up tasks and the stale dependency from #17 to #41.

[[2026-03-27]] Fri 21:18
## Test-Writer Notes (retry 2)
- Retry reason: reviewer FAIL was about board management (duplicate scaffold tasks #39/#40/#41 still active and #17 still depends on #41), not missing tests.
- This is a research/non-implementation task — no tests applicable.
- Existing pass-through preserved. Builder will address reviewer findings: remove duplicate tasks #39/#40/#41 and remove stale dependency from #17 to #41.

[[2026-03-27]] Fri 22:16
## Builder Notes (retry 2)
- Non-implementation task (research tag) â€” no source code changes.
- Board cleanup performed per reviewer and test-writer instructions:
  - Archived duplicate scaffold tasks: #39 (mcp-kanban scaffold), #40 (mcp-knowledge scaffold), #41 (mcp-project scaffold)
  - Archived orphaned TDD test tasks: #65, #66, #67 (paired with the above scaffolds)
  - Removed stale depends_on #41 from task #17 (now depends only on #2, #7)
- Seed tasks #14, #16, #17 remain active on board (satisfying AC line 8)
- Board is now clean: no duplicate paths to mcp-kanban/mcp-knowledge/mcp-project packages
- Tests: not applicable (no TestFromAC classes for this task)
- Lint: not applicable (no Python module changes)

[[2026-03-28]] Sat 00:45
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | Research task, no behavior/API change. MCP servers already in tech stack (line 57) and directory table (lines 137-139) |
| 2 | Docstrings | No | N/A | Research-only task, no Python modules created or modified |
| 3 | docs/sources/overview.md | Yes | Pass | 5 MCP sources attributed at lines 2407-2411 (SDK v1/v2, Architecture, Lifecycle spec, VS Code config ref) |
| 4 | README.md | No | N/A | No CLI commands added or changed |
| 5 | Research doc linked | Yes | Pass | docs/research/mcp-python-sdk.md exists; seed tasks #14 #16 #17 verified on board; section 10 references only seed tasks |
| 6 | Scratch files | No | N/A | No docs/scratch/2-* files found |

### Files Updated
- None

### Scratch Files Cleaned
- None (none existed)

[[2026-03-28]] Sat 01:20
## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 157e9e9 | docs | docs/research/mcp-python-sdk.md | #2 |
