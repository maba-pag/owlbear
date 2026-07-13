---
id: 563
title: Expand mcp-kanban SKILL.md with agent workflow pattern and per-tool 
  reference
status: archived
priority: medium
created: 2026-04-03 07:45:59.821346+02:00
updated: 2026-04-03 15:09:23.845944+02:00
started: 2026-04-03 15:09:23.394274+02:00
completed: 2026-04-03 15:09:23.394274+02:00
tags:
- phase-2
- docs
- scope:agent-config
parent: 483
depends_on:
- 562
class: standard
archival_reason: completed
archival_refs: []
---

## Acceptance Criteria

- [ ] New section `## Agent Workflow Pattern` documenting the 3-step MCP lifecycle: start_work (claim+read) -> edit_task (Channel B) -> end_work (note+advance+release)
- [ ] Per-tool parameter reference subsections expanding the existing `## Tools` summary table with full parameter names, types, and defaults for all 8 tools. Do NOT duplicate the existing summary table; add a new `## Per-Tool Parameter Reference` section after it with one subsection per tool.
- [ ] Channel B protocol section showing edit_task(append_body=..., timestamp=true) as MCP alternative to `kanban-md edit -a ... -t`
- [ ] Compound vs single tool guidance: when to use start_work/end_work vs individual calls
- [ ] Error handling differences: already documented correctly in existing `## Error handling` section (ToolError for show/move/pick/edit vs `error:` string for list/create/start/end). Builder must PRESERVE this content, not rewrite it. Mark as pre-satisfied.
- [ ] Claim/release pitfall for edit_task (same-call claim+release forbidden, as with CLI)
- [ ] All existing CLI content preserved (MCP is additive)
- [ ] Must pass #562 validation test (tests/test_mcp_tool_references_483.py)

## Scope

Single file: skills/mcp-kanban/SKILL.md. This is the primary reference that all other agent/skill files will point to.

## Builder Notes

**Section ordering:** Insert new sections into the existing file in this order:
1. (existing) ## Tools â€” summary table, keep as-is
2. (existing) ## start_work details â€” keep as-is
3. (existing) ## end_work details â€” keep as-is
4. (NEW) ## Agent Workflow Pattern â€” 3-step lifecycle
5. (NEW) ## Per-Tool Parameter Reference â€” expanded per-tool subsections
6. (NEW) ## Channel B Protocol â€” MCP equivalent of CLI Channel B
7. (NEW) ## Compound vs Single Tool Guidance â€” decision matrix
8. (NEW) ## Pitfalls â€” claim/release same-call issue
9. (existing) ## Error handling â€” already correct, preserve
10. (existing) ## Binary discovery â€” keep as-is
11. (existing) ## Configuration â€” keep as-is

**Test coverage note:** RED tests (#562) validate only AC item 1 (Agent Workflow heading with start_work, end_work, edit_task keywords). AC items 2-4 and 6 have no automated validation. The reviewer must manually verify these items.

**AC item 5 is pre-satisfied.** The existing Error handling section already correctly groups ToolError (show/move/pick/edit) vs error: string (list/create/start/end). Do not rewrite.

## Notes

See docs/research/mcp-tool-references-alongside-cli.md sections 3a-3d for CLI-to-MCP mapping, compound workflow, and pitfalls.
See docs/research/expand-mcp-kanban-skill-reference.md for validation research.

[[2026-04-03]] Fri 11:33
## Architecture Review
**Verdict:** APPROVED
**DR Verification:** N/A - T1 documentation for existing capabilities, not research-driven

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Agent Workflow Pattern section | Clear, testable (RED test validates heading + keywords) | Keep |
| Per-tool parameter reference | Clarified: expand existing Tools table into per-tool subsections, not duplicate | Refined in body |
| Channel B protocol section | Clear, testable | Keep |
| Compound vs single guidance | Clear, testable | Keep |
| Error handling differences | Pre-satisfied: existing SKILL.md already correct | Marked pre-satisfied |
| Claim/release pitfall | Clear, testable | Keep |
| Existing content preserved | Clear, verifiable at review | Keep |
| Pass #562 validation test | Clear, automated test exists | Keep |

### Architecture Notes
Single-file documentation task. Existing skills/mcp-kanban/SKILL.md has solid structure. New sections integrate between end_work details and Error handling sections. No code changes, no new interfaces. Builder must preserve all existing content while adding ~60-80 lines of new documentation.

Existing patterns: SKILL.md uses markdown tables for tool params, prose sections for behavioral details. New sections should follow the same pattern.

Error handling grouping (verified against server.py): ToolError for show/move/pick/edit; error: string for list/create/start/end. AC item 5 text was wrong (had edit in wrong group) but existing SKILL.md is already correct. Marked pre-satisfied.

### Changes Made
- Refined AC: corrected error handling grouping, clarified per-tool reference scope, added section ordering guidance
- Added builder notes: section ordering, test coverage gap, pre-satisfied item 5
- Added docs tag (test-writer pass-through, no Python code produced)
- Removed type:build tag (documentation task, not code build)
- Fixed leading-space tag artifacts (scope:agent-config)

### Dependencies
- Verified: #562 (test task) archived
- Parent: #483 (Phase A: MCP tool references)

### Challenge Results
- Challenger: reconsider (confidence .62)
- Key challenges: (1) RED tests cover only AC item 1, not items 2-6; (2) AC item 5 pre-satisfied; (3) AC item 2 scope ambiguous vs existing table; (4) no section ordering guidance
- Architect response: All four accepted and incorporated. Refined AC to mark item 5 pre-satisfied, clarified item 2 scope (extend not duplicate), added builder notes with section ordering, acknowledged test gap for reviewer. Confidence raised by addressing all challenger concerns in AC revision.

[[2026-04-03]] Fri 11:42
## Test-Writer Notes
- Non-implementation task (tagged docs) — no new tests applicable.
- Existing validation tests: tests/test_mcp_tool_references_483.py (from archived #562)
- TestFromAC_McpKanbanSkillWorkflowPattern covers AC item 1 (Agent Workflow heading + start_work/end_work/edit_task keywords).
- AC items 2-4 and 6: no automated validation per architect builder notes — reviewer manual verification required.
- Passing through to builder.

[[2026-04-03]] Fri 14:31
## Review Evidence

### Test Results
- pytest TestFromAC_McpKanbanSkillWorkflowPattern: 4 passed, 0 failed
- ruff: All checks passed!

### TestFromAC Integrity
- 4 tests in TestFromAC_McpKanbanSkillWorkflowPattern: PRESERVED
- AC items 2-6: no automated tests (acknowledged by architect), manually verified

### AC Compliance

All 8 AC items PASS (manual verification of items 2-4, 6; automated for items 1, 8)

- AC1 Agent Workflow Pattern: heading + start_work/edit_task/end_work lifecycle documented; 4 TestFromAC tests PASS
- AC2 Per-Tool Parameter Reference: all 8 tools covered with full param tables (list_tasks 10 params, show-task 1, create_task 8, move_task 2, edit_task 15, pick_task 4, start_work 2, end_work 6)
- AC3 Channel B Protocol: section present; edit_task(append_body=..., timestamp=True) with Python example
- AC4 Compound vs Single Guidance: 6-row decision table covering all cases
- AC5 Error handling preserved: ToolError for show/move/pick/edit; error: string for list/create/start/end
- AC6 Claim/release pitfall: Pitfalls section with WRONG/CORRECT examples + end_work recommendation
- AC7 CLI content preserved: Server registration, Tools table, start_work details, end_work details, Error handling, Binary discovery, Configuration all intact
- AC8 Pass test_mcp_tool_references_483.py: 4/4 TestFromAC_McpKanbanSkillWorkflowPattern PASS

### Security
N/A - documentation-only change, zero code modified

### Verdict: PASS
### Confidence: .95

[[2026-04-03]] Fri 14:40
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | SKILL.md expansion only; no behavior/API/convention change to the project |
| 2 | Docstrings | No | N/A | Pure documentation task; no Python files modified |
| 3 | sources/overview.md | No | N/A | All content derived from internal source code (server.py, test files); no external patterns |
| 4 | README.md | No | N/A | No CLI commands added or changed |
| 5 | Research docs linked | Yes | Pass | docs/research/expand-mcp-kanban-skill-reference.md and mcp-tool-references-alongside-cli.md both exist and linked in task body |

### Files Updated
- None

### Scratch Files Cleaned
- None (no docs/scratch/563-* files found)

[[2026-04-03]] Fri 15:09
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Agent Workflow Pattern section | SKILL.md L72-100: heading + 3-step lifecycle with start_work/edit_task/end_work | PASS |
| Per-tool parameter reference | SKILL.md L104-230: 8 subsections with full param tables | PASS |
| Channel B protocol section | SKILL.md L234-250: edit_task example with timestamp=True | PASS |
| Compound vs single guidance | SKILL.md L254-270: 6-row decision table | PASS |
| Error handling preserved (pre-satisfied) | SKILL.md L290-295: ToolError/error: grouping intact | PASS |
| Claim/release pitfall | SKILL.md L274-290: WRONG/CORRECT examples + end_work | PASS |
| Existing CLI content preserved | All original sections intact (Tools, start_work, end_work, Error handling, Binary discovery, Configuration) | PASS |
| Pass #562 validation test | 73/73 TestFromAC_McpKanbanSkillWorkflowPattern PASS | PASS |

### Test Results
- pytest (task-specific): 73 passed, 0 failed (test_mcp_tool_references_483.py)
- pytest (full suite): 3287 passed, 238 failed (all failures pre-existing, none in task scope)
- ruff: 2 violations in untracked test_necessity_check_196.py, not task-related

### Architect Quality
- AC specificity: 8 measurable items, each describing a section with content requirements
- Edge case coverage: Pre-satisfied item 5 identified, builder notes added for section ordering
- Design direction: Detailed section ordering, challenge responses incorporated
- AC quality score: 5

### Reviewer Evidence
Detailed, covers all 8 AC items with manual + automated verification. Confidence .95.

### Upstream Commits
- a2c67ab docs: expand mcp-kanban SKILL.md with agent workflow pattern and per-tool reference (#563, builder)

### Deduction breakdown: none (all AC verified, no lint in scope, AC quality 5, reviewer evidence present)
### Confidence: 1.0
### Action: archive
