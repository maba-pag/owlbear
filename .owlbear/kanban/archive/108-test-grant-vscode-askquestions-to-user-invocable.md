---
id: 108
title: 'Test: Grant vscode/askQuestions to user-invocable agents'
status: archived
priority: medium
created: 2026-03-28 15:10:25.072916+01:00
updated: 2026-03-29 01:17:31.219303+01:00
started: 2026-03-29 01:17:30.921945+01:00
completed: 2026-03-29 01:17:30.921945+01:00
tags:
- phase-2
- scope:agents
- type:test
- test
class: standard
archival_reason: completed
archival_refs: []
---

## Acceptance Criteria
- [ ] Test orchestrator.agent.md tools list includes vscode/askQuestions
- [ ] Test kanban-planner.agent.md tools list includes vscode/askQuestions
- [ ] Test curator.agent.md tools list includes vscode/askQuestions
- [ ] Test no pipeline-only agent (builder, reviewer, writer, test-writer, auditor, planner, architect, researcher) has vscode/askQuestions in tools list
- [ ] All tests FAIL on current HEAD
- [ ] ruff clean

## Context
Test task for #101. Pattern: follow test_resolve_memory_file_uri_removal.py (parse YAML frontmatter, check tool presence/absence). Use agents/ directory and ALL_AGENT_NAMES list from test_agent_port_v2.py.

See docs/research/vs-code-new-tools-evaluation.md for background.

[[2026-03-28]] Sat 16:26
## Test-Writer Notes
- Test file: tests/test_grant_vscode_askquestions_to_user_invocable.py
- Classes: TestFromAC_UserInvocableAgentsHaveAskQuestions, TestFromAC_PipelineAgentsExcludeAskQuestions
- Tests per category: happy 3, edge 0, error 0, boundary 0, exclusivity 8
- Total: 11 tests written; AC1-3 FAIL (3), AC4 guardrails PASS (8) on current HEAD
- ruff: clean
- Note: AC4 exclusivity tests pass on current HEAD by design -- pipeline agents do not have vscode/askQuestions yet. They guard against accidental addition during builder GREEN phase.
- AC coverage:
  AC1 test_orchestrator_tools_include_ask_questions FAIL
  AC2 test_kanban_planner_tools_include_ask_questions FAIL
  AC3 test_curator_tools_include_ask_questions FAIL
  AC4 (x8) test_*_does_not_have_ask_questions PASS (guardrail)

-t

[[2026-03-28]] Sat 21:15
## Builder Notes
- Files changed: agents/orchestrator.agent.md, agents/kanban-planner.agent.md, agents/curator.agent.md
- Tests: 11 passed (3 were FAIL now GREEN; 8 guardrails stayed PASS)
- Lint: ruff clean
- Evidence: 11 passed in 0.09s
- Fixes applied: Added vscode/askQuestions to tools frontmatter in orchestrator (inline list), kanban-planner (multi-line list), curator (multi-line list)

[[2026-03-28]] Sat 22:12
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | Tool restriction is agent-local; copilot-instructions.md does not document per-agent tool lists |
| 2 | Docstrings | No | N/A | No .py source modules changed; test file has full docstrings on all public items |
| 3 | docs/sources/overview.md | No | N/A | Pattern from internal test file; no external attribution needed |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc | Pass | Pass | docs/research/vs-code-new-tools-evaluation.md exists and referenced in task body |

### Files Updated
- None

### Scratch Files Cleaned
- None (no docs/scratch/108-* files existed)

[[2026-03-29]] Sun 01:17
## Audit
### AC Verification
| AC | Evidence | Status |
|---|---|---|
| AC1: orchestrator has askQuestions | grep: tools line includes vscode/askQuestions; test passes | PASS |
| AC2: kanban-planner has askQuestions | grep: tools block includes vscode/askQuestions; test passes | PASS |
| AC3: curator has askQuestions | grep: tools block includes vscode/askQuestions; test passes | PASS |
| AC4: pipeline agents excluded | 8 guardrail tests pass (builder, reviewer, writer, test-writer, auditor, planner, architect, researcher) | PASS |
| AC5: tests FAIL on pre-builder HEAD | Test-writer notes confirm AC1-3 FAIL, AC4 PASS before builder | PASS (verified via notes) |
| AC6: ruff clean | ruff check on deliverables: All checks passed | PASS |

### Test Results
- pytest (task-specific): 11 passed in 0.03s
- pytest (full suite): 435 passed, 55 failed (all pre-existing from other tasks: rename-bearclaw-voice, rename-todo-to-todos, voice-package-scaffolding, scratch-dir, validate-skills-ci, v2-test-infrastructure)
- ruff: clean

### Commit Verification
- 702396f feat: grant vscode/askQuestions to user-invocable agents (#108, builder) -- includes test file and agent edits
- Note: test-writer did not commit separately (minor process gap, builder included tests)

### AC Quality Score: 4/5
AC was specific and measurable. Minor gap: AC5 (tests fail on current HEAD) is a process requirement that becomes moot after builder implements. Otherwise well-structured with clear pass/fail criteria.

### Confidence: .97
### Action: archive
