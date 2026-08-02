---
id: 473
title: Add KANBAN_TOOLS_EXCLUDE config for selective tool exposure
status: archived
priority: medium
created: 2026-03-31 05:21:29.128148+02:00
updated: 2026-04-02 15:00:26.070110+02:00
started: 2026-04-02 15:00:25.666688+02:00
completed: 2026-04-02 15:00:25.666688+02:00
tags:
- scope:mcp
- ' phase-2'
- research
class: standard
archival_reason: completed
archival_refs: []
---

## Research Deliverables

Task #473 was the research investigation for KANBAN_TOOLS_EXCLUDE. All implementation was delivered through follow-up tasks created by the researcher.

## Acceptance Criteria

- [x] Research doc complete at docs/research/kanban-tools-exclude-config.md covering approach options, FastMCP API verification, env var design, and mcp.json integration
- [x] Follow-up implementation task #491 created (mcp-kanban server) and archived (confidence .98)
- [x] Follow-up implementation task #493 created (mcp-knowledge + mcp-project servers) and archived (confidence 1.00)
- [x] All three MCP servers implement _apply_tool_exclusions via lifespan pattern (Option B per research recommendation)
- [x] Convention documented in copilot-instructions.md MCP Server Conventions section

## Design Notes

- Pattern: lifespan-level removal using FastMCP.remove_tool() called in app_lifespan before yield
- Env vars: KANBAN_TOOLS_EXCLUDE, KNOWLEDGE_TOOLS_EXCLUDE, PROJECT_TOOLS_EXCLUDE
- See docs/research/kanban-tools-exclude-config.md for full analysis

[[2026-04-02]] Thu 05:24
## Architecture Review
**Verdict:** Approve
**DR Verification:** N/A - T1 autonomous (straightforward research, no competing approaches requiring user decision)

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Research doc complete at docs/research/kanban-tools-exclude-config.md | Doc exists and covers approach analysis, API verification, env design. Minor staleness: lists 7 tools/board_context instead of 8 tools/start_work+end_work. Pattern is correct regardless. | Accept with note |
| Follow-up #491 created and archived (.98) | Verified: #491 archived with full audit trail | OK |
| Follow-up #493 created and archived (1.00) | Verified: #493 archived with full audit trail. Has separate research doc at docs/research/tools-exclude-knowledge-project.md | OK |
| All three servers implement _apply_tool_exclusions | Verified in codebase: mcp-kanban, mcp-knowledge, mcp-project all have identical pattern | OK |
| Convention documented in copilot-instructions.md | Verified: L75 documents TOOLS_EXCLUDE convention | OK |

### Architecture Notes
Research task whose deliverables (doc + follow-up tasks) are complete. Pattern correctly uses lifespan-level removal via FastMCP.remove_tool() API, matching the existing KANBAN_BIN env-read pattern. All three servers independently implement the same helper (no shared library, respecting package boundary rules). Implementation follow-ups both achieved high auditor confidence (.98, 1.00).

### Changes Made
- Rewrote task body with proper AC reflecting research deliverables
- Changed tag from type:build to research (correct for research task, enables test-writer pass-through)

### Dependencies
- None outstanding. #491 and #493 both archived.

### Challenge Results
- Challenger: reconsider (confidence .65)
- Key challenges: (1) Research doc tool inventory stale (7 vs 8, board_context vs start_work/end_work), (2) Doc scope covers only kanban server not all 3
- Architect response: Accepted doc staleness finding as valid but non-blocking. Challenger missed separate research doc for knowledge/project servers (docs/research/tools-exclude-knowledge-project.md). Implementation pattern and all functional deliverables are correct and verified. Doc staleness is cosmetic - does not affect pattern validity or implementation correctness. Per project principles, deliverables are working code and kanban tasks, not documents.
- Confidence in original: .85 (adjusted from initial for doc quality gap)

[[2026-04-02]] Thu 07:27
## Test-Writer Notes
- Non-implementation task (tagged research) â€” no tests applicable.
- Passing through to builder.

[[2026-04-02]] Thu 12:05
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | Yes | Pass | L78 documents TOOLS_EXCLUDE convention accurately |
| 2 | Docstrings | No | N/A | Research task; implementation code in #491 and #493 (both archived) |
| 3 | sources/overview.md | No | N/A | FastMCP SDK already attributed by tasks #492/#495; TOOLS_EXCLUDE pattern is OwlBear-native |
| 4 | README.md | No | N/A | No CLI commands added or changed |
| 5 | Research doc | Yes | Updated | Fixed stale tool count (7 board_context to 8 start_work end_work); doc at docs/research/kanban-tools-exclude-config.md; follow-ups #491 and #493 archived |

### Files Updated
- docs/research/kanban-tools-exclude-config.md (fixed stale tool count: 7 with board_context to 8 with start_work and end_work)

### Scratch Files Cleaned
- None

[[2026-04-02]] Thu 15:00
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Research doc at docs/research/kanban-tools-exclude-config.md | Doc exists, covers approach options, FastMCP API, env design, mcp.json. Writer fixed stale tool count (commit 5408fe0). | PASS |
| Follow-up #491 created and archived (.98) | #491 status: archived, auditor confidence .98 | PASS |
| Follow-up #493 created and archived (1.00) | #493 status: archived, auditor confidence 1.00 | PASS |
| All three servers implement _apply_tool_exclusions | Verified via #491 and #493 audit trails | PASS |
| Convention in copilot-instructions.md | L78 documents all three TOOLS_EXCLUDE env vars | PASS |

### Test Results
- pytest (full suite): 2363 passed, 285 failed (pre-existing RED-phase tests, 0 from #473)
- ruff: 2 pre-existing errors in test_necessity_check_196.py (unrelated)

### AC Quality Score: 4/5
Original AC was vague; architect rewrote with proper research deliverable AC. Final version is specific and verifiable, but required rework.

### Reviewer Evidence
No explicit Review Evidence section from reviewer. Architect challenge served as review (thorough AC assessment table, .85 confidence). Minor gap for research task.

### Deduction breakdown: -.02 missing reviewer evidence section
### Confidence: .98
### Action: archive
