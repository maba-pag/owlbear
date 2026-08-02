---
id: 562
title: 'Test: Validate MCP tool references in agents, skills, and instructions'
status: archived
priority: medium
created: 2026-04-03 07:45:45.881938+02:00
updated: 2026-04-03 11:00:04.345617+02:00
started: 2026-04-03 10:59:59.553792+02:00
completed: 2026-04-03 10:59:59.553792+02:00
tags:
- phase-2
- ' scope:agent-config'
- ' type:test'
- ' test'
parent: 483
class: standard
archival_reason: completed
archival_refs: []
---

## Acceptance Criteria

- [ ] Pytest test file `tests/test_mcp_tool_references_483.py` validates MCP tool references exist alongside CLI in all target files
- [ ] Checks mcp-kanban SKILL.md has agent workflow pattern section (start_work/end_work lifecycle) and per-tool parameter reference
- [ ] Checks agent-common.instructions.md has MCP syntax (edit_task, start_work, end_work) in Channel B and task coordination sections
- [ ] Checks research-docs.instructions.md has MCP syntax where CLI kanban references exist
- [ ] Checks all pipeline agent .agent.md files contain MCP tool examples in body text (not just tools: YAML). Pipeline agents (10): architect, auditor, builder, curator, kanban-planner, planner, researcher, reviewer, test-writer, writer. Scribe excluded (utility agent, no pipeline stage ownership).
- [ ] Checks all skill SKILL.md files with `## kanban-md Commands` sections have MCP tool rows/columns alongside CLI (8 skills: arch-review, code-review, curation-workflow, docs-gate, task-decomposition, task-verification, tdd-red, tdd-workflow)
- [ ] All checks fail initially (RED phase -- references don't exist yet)
- [ ] Test uses grep/regex patterns, not brittle exact-string matching. Prefer collision-free markers (start_work, end_work) per research doc.

## Scope

Single test file. Structural .md validation targeting body text (not frontmatter) -- requires frontmatter stripping and section-aware scanning per research doc section 3c.

File named with parent task ID (_483) because it covers the RED phase for all sibling tasks #563-#566 under parent #483.

## Notes

Target files: 10 pipeline agents (see AC list), 8 skills with cheatsheets (see AC list), agent-common.instructions.md, research-docs.instructions.md.

Research docs:
- docs/research/mcp-tool-references-alongside-cli.md (full CLI-to-MCP mapping)
- docs/research/mcp-tool-ref-validation-test.md (test design, false-positive strategy, 4-class structure)

[[2026-04-03]] Fri 09:07
## Architecture Review
**Verdict:** Approved
**DR Verification:** N/A -- T1 classification (adding documentation for existing capabilities, no design decisions). Parent #483 research confirmed T1.

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Test file test_mcp_tool_references_483.py | Clear output, parent ID justified | Kept, added rationale in Scope |
| mcp-kanban SKILL.md workflow section | Verifiable (heading + content check) | Kept |
| agent-common MCP syntax | Verifiable (edit_task/start_work/end_work in sections) | Kept |
| research-docs MCP syntax | ADDED -- was missing, needed for #564 coverage | Added |
| Pipeline agent body refs | Corrected: explicit 10-agent list, scribe excluded | Rewrote (was vague 10) |
| Skill cheatsheet MCP refs | Corrected: explicit 8-skill list enumerated | Refined |
| RED phase (all fail) | Verifiable, confirmed zero MCP refs on HEAD | Kept |
| Regex patterns | Added collision-free marker guidance | Refined |

### Architecture Notes
- Follows structural .md validation pattern (cf. test_argument_hint_skills.py) but targets body text, not frontmatter -- fundamentally different scanning problem
- 10 pipeline agents enumerated explicitly. Scribe excluded: utility agent, no pipeline stage, different lifecycle (check-create-resolve vs claim-work-release)
- 8 skills with kanban cheatsheets enumerated. research-workflow has inline refs only (covered by #566 separately)
- Collision-free markers (start_work, end_work) recommended to avoid asyncio.create_task false positives
- Test covers RED phase for all sibling tasks #563-#566 under parent #483
- Parent #483 deps all archived: #470, #471, #472, #475, #476, #477

### Changes Made
- Rewrote AC: corrected agent count (explicit list of 10, scribe excluded with rationale), added research-docs AC line, enumerated 8 skills, added collision-free marker guidance, body-text scanning clarification in Scope
- No new tasks created (decomposition already complete via#483 planning)

### Dependencies
- Verified: no depends_on needed (RED phase test, checks absence)
- Parent #483 deps all archived (confirmed #470-#477)
- Sibling tasks #563-#566 depend on #562

### Challenge Results
- Challenger: reconsider (confidence in original: .55)
- Key challenges: (1) scribe gap with dynamic discovery -- accepted, resolved by explicit 10-agent list; (2) AC not persisted -- accepted, corrected via body rewrite; (3) missing research-docs AC -- accepted, added AC line; (4) filename convention -- rebutted, _483 intentional for parent-scoped RED test
- Architect response: accepted 3 of 4, rebutted filename convention. Revised AC incorporates all accepted feedback.

## Builder Notes
- Files changed: none (tests/test_mcp_tool_references_483.py already committed by test-writer at 0a9fc21)
- RED phase verified: 47 tests, all FAIL on current HEAD as expected
- Lint: ruff clean (all checks passed)
- Evidence: 47 FAILED -- all TestFromAC_* classes fail because MCP refs absent in target files
- Fixes applied: None -- test file is the deliverable; RED phase is the correct state for this task

[[2026-04-03]] Fri 09:53
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | Test-only task (RED phase), no behavior/API/convention change |
| 2 | Docstrings | Yes | Pass | Module docstring accurate (lines 1-11). _strip_frontmatter and _get_section_content have docstrings. All 5 test classes and all test methods have docstrings. |
| 3 | docs/sources/overview.md | No | N/A | All sources studied are internal codebase files (no external repos/articles) |
| 4 | README.md | No | N/A | No CLI commands added or changed |
| 5 | Research docs | Yes | Pass | Both research docs exist and are linked in task body: mcp-tool-ref-validation-test.md (owning task #562) and mcp-tool-references-alongside-cli.md. Follow-up tasks #563-#566 created under parent #483. |

### Files Updated
- None

### Scratch Files Cleaned
- None (no scratch files found for #562)

[[2026-04-03]] Fri 10:59
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Test file test_mcp_tool_references_483.py | Committed 0a9fc21, 300 lines, 5 test classes | PASS |
| mcp-kanban SKILL.md workflow checks | TestFromAC_McpKanbanSkillWorkflowPattern: 4 tests (heading, start_work, end_work, edit_task) | PASS |
| agent-common MCP syntax checks | TestFromAC_AgentCommonMcpSyntax: 4 tests (Channel B edit_task/end_work, task coord start_work/end_work) | PASS |
| research-docs MCP syntax checks | TestFromAC_ResearchDocsMcpSyntax: 3 tests (create_task, start_work, end_work) | PASS |
| 10 pipeline agents body refs | TestFromAC_PipelineAgentMcpBodyRefs: 20 parametrized tests (10 agents x 2 markers) | PASS |
| 8 skill cheatsheet MCP refs | TestFromAC_SkillCheatsheetMcpRefs: 16 parametrized tests (8 skills x 2 markers) | PASS |
| All fail initially (RED phase) | 47 FAILED confirmed in full suite run | PASS |
| Regex patterns, not brittle matching | re.search with IGNORECASE, _get_section_content helper, _strip_frontmatter | PASS |

### Test Results
- pytest: 3180 passed, 270 failed (47 from this task = expected RED phase; 223 from other RED-phase sibling tasks), 1 error, 8 skipped
- ruff: clean on test_mcp_tool_references_483.py (exit 0)

### AC Quality Score: 5
AC was specific (enumerated exact 10 agents, 8 skills), complete (no improvisation needed), and guided a clean implementation.

### Reviewer Evidence
Missing Review Evidence section in task body. Deducting -.02.

### Deduction breakdown
- -.02 missing reviewer evidence section
### Confidence: .98
### Action: archive
