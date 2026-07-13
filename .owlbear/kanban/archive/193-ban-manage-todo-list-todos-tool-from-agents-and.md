---
id: 193
title: Ban manage_todo_list/todos tool from agents and validator
status: archived
priority: medium
created: 2026-03-29 22:56:35.373614+02:00
updated: 2026-03-30 19:32:36.744981+02:00
started: 2026-03-30 19:30:33.102910+02:00
completed: 2026-03-30 19:30:33.102910+02:00
tags:
- phase-1
- tooling
- agent
- config
class: standard
archival_reason: completed
archival_refs: []
---

## Objective

Ban the todos/manage_todo_list tool from agent definitions and the validator. The tool does not function in subagent context (see docs/research/manage-todo-list-subagent-removal.md).

## Acceptance Criteria

- [ ] `validate_agents.py`: new check flags `todos` on the `tools:` frontmatter line (scoped to tools: only, not argument-hint or body text) with error message stating the tool is disabled for subagents
- [ ] `validate_agents.py`: new check flags `manage_todo_list` anywhere in agent file (full-file scope, same pattern as `resolveMemoryFileUri` check) with error message stating the tool is disabled
- [ ] `validate_agents.py`: existing bare `todo` check message updated from "should be 'todos'" to state that the tool is disabled for subagents
- [ ] `.github/copilot-instructions.md`: remove the `manage_todo_list extensively` process habit line (currently line 27)
- [ ] Validator passes clean on all 11 current `agents/*.agent.md` files
- [ ] Tests cover: file with `todos` on tools: line produces error; file with `manage_todo_list` in body produces error; bare `todo` shows updated message; clean file produces no error

## Files to touch

- `scripts/validate_agents.py` (~20 LOC: add 2 checks, update 1 message)
- `tests/test_validate_agents.py` (~30 LOC: add test cases for new checks)
- `.github/copilot-instructions.md` (remove 1 line)

## Context

See docs/research/manage-todo-list-subagent-removal.md for full research findings (.90 confidence).
Related: #198 (broader validator expansion) is a separate nice-to-have improvement.
Merged: #199 (identical scope, created by researcher before AC rewrite) deleted as duplicate.

## Patterns to follow

- `resolveMemoryFileUri` check: full-file string search, same approach for `manage_todo_list`
- `_BARE_TODO_RE`: regex on `_tools_text()`, extend with a similar `_TODOS_RE` for the todos check
- Test fixtures: `test_validate_agents.py` uses `tmp_path`-based `.agent.md` file creation

[[2026-03-30]] Mon 00:07
## Architecture Review
**Verdict:** BLOCK (back to ideation)

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Audit validate_agents.py | Research completed: only 2 checks (bare todo, resolveMemoryFileUri), both correct | No action needed |
| Audit validate_skills.py | Research completed: no tool name validation in this script | No action needed |
| Audit other files for stale names | Research completed: all 11 agents use todos, no stale refs found | No action needed |
| Research canonical tool list | Done in docs/research/stale-tool-names.md at .95 confidence | Complete |
| Fix stale tool name references | Research found NONE to fix, premise was inverted | Moot |
| Fix elsewhere | No stale references found | Moot |
| Ensure validators correct | Already correct | Moot |
| Run validators | Would pass, nothing changed | Moot |

### Architecture Notes
Research (.95 confidence) invalidated the task premise. The user believed todos was the OLD name and todo the current one. The evidence shows the opposite: todo was v1, todos is current (confirmed by VS Code cheat sheet, prior research #4, and existing test suite). The validator correctly flags bare todo. All 11 agent files already use todos.

There is nothing for a builder to implement. The task AC asks to fix stale references, but none exist.

Quality gap: research doc claims a decision request was created at docs/decisions/pending/193-todos-vs-todo-tool-name.md but that file does not exist. The researcher either failed to create it or it was deleted.

Follow-up task #198 (Expand validator to check ALL tool names) was correctly created at ideation as the real improvement opportunity.

### Changes Made
- Blocked task to ideation pending user decision: close as won't-fix or redefine scope

### Dependencies
- #198 (Expand validator) supersedes this task's improvement intent

## User decision
- User researched and found out that manage_todo_list is not usable by subagents. This makes this task obsolete. User decided to have the manage_todo_list tool removed from all agents, including the orchestrator, until this is fixed by Microsoft. User also decided to have the validate_agents.py script updated to check for any reference to manage_todo_list and fail if found, to prevent future stale references. This should be implemented instead of the original AC items related to fixing stale tool names, which are moot. So Architect has to change the AC to reflect this new scope: Validation shall check for todo/todos/manage_todo_list references in agent definitions and fail if found, and all agent files shall be updated to remove any reference to manage_todo_list.

[[2026-03-30]] Mon 01:33

[[2026-03-30]] Mon 02:43
## Research
- **Finding (.90 confidence):** todos/manage_todo_list does not function in subagent context (user tested + architectural inference from 3 sources)
- **Codebase audit:** Zero agent files reference the tool. Only .github/copilot-instructions.md (line 27) and 3 historical research docs mention it
- **Validator needs 3 new checks:** flag todos in tools:, flag manage_todo_list anywhere, update bare-todo message
- **Follow-up:** #199 (Ban manage_todo_list/todos tool from agents and validator) created at ideation
- **#198** (Expand validator to all tool names) remains valid as separate nice-to-have improvement
- **Doc:** docs/research/manage-todo-list-subagent-removal.md

[[2026-03-30]] Mon 03:14
## Architecture Review (2026-03-30 cycle 3)
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Flag todos on tools: line | Precise scope (tools: only, not argument-hint) -- verifiable | Keep |
| Flag manage_todo_list full-file | Mirrors existing resolveMemoryFileUri pattern -- verifiable | Keep |
| Update bare todo message | Single string change -- verifiable | Keep |
| Remove copilot-instructions line | 1-line removal -- verifiable | Keep |
| Validator passes clean | All 11 agents confirmed clean of todos/manage_todo_list in tools: lines | Keep |
| Test coverage for new checks | 4 test scenarios specified -- verifiable | Keep |

### Architecture Notes
Codebase verified: zero agents reference todos or manage_todo_list in tools: lines. The todos hits in orchestrator.agent.md and planner.agent.md are in argument-hint free text (kanban status references), not tool names -- the scoped tools:-only check handles this correctly.

Existing patterns to follow:
- resolveMemoryFileUri check: full-file string search, same approach for manage_todo_list
- _BARE_TODO_RE: regex on _tools_text(), extend with a similar _TODOS_RE for the todos check
- Test fixtures: test_validate_agents.py uses tmp_path-based .agent.md file creation

validate_skills.py has no tool name validation and is out of scope. #198 (broader expansion) remains valid as separate nice-to-have.

### Changes Made
- Rewrote #193 title and AC to the refined user-directed scope
- Merged #199 (duplicate created by researcher before rewrite) -- deleted
- Approved to todo

### Dependencies
- None required -- all prerequisite research is complete
- #198 (broader validator expansion) is independent nice-to-have

[[2026-03-30]] Mon 04:23
## Test-Writer Notes
- Test file: tests/test_validate_agents.py
- Classes: TestFromAC_BanTodosToolCheck, TestFromAC_BanManageTodoListCheck, TestFromAC_DeprecatedTodoMessage, TestFromAC_CopilotInstructionsCleanup
- Tests per category: happy 0, edge 0, error 9, boundary 1
- Total: 10 tests, all FAIL confirmed
- ruff: clean
- AC coverage:
  - todos in tools: line produces error: test_todos_in_tools_line_produces_error, test_todos_error_mentions_disabled_for_subagents, test_todos_with_other_tools_still_errors
  - manage_todo_list full-file: test_manage_todo_list_in_tools_line_produces_error, test_manage_todo_list_in_body_produces_error, test_manage_todo_list_in_frontmatter_produces_error, test_manage_todo_list_error_mentions_disabled
  - bare todo message updated: test_bare_todo_error_message_not_says_should_be_todos, test_bare_todo_error_message_says_disabled_for_subagents
  - copilot-instructions cleanup: test_manage_todo_list_not_in_copilot_instructions
- Note: file was already included in HEAD commit e0663d4 by concurrent agent (VS Code auto-stage)

[[2026-03-30]] Mon 05:27
## Builder Notes
- BLOCK: cannot implement without breaking existing TestFromAC tests
- Conflict: TestFromAC_BanTodosToolCheck (new) requires tools:[todos] to error; TestFromAC_ValidateAgentsTodoCheck::test_tools_todos_passes (old, currently passing) asserts tools:[todos] returns no errors
- Same conflict: test_argument_hint_with_todos_does_not_trigger asserts tools:[todos, read/readFile] returns no errors; test_todos_with_other_tools_still_errors asserts same content errors
- Both are TestFromAC classes -- neither can be modified per builder rules
- Resolution options: (1) test-writer updates old TestFromAC_ValidateAgentsTodoCheck to remove/update the 3 contradicting tests since the AC has changed; (2) architect explicitly approves removing those old tests as obsolete
- 10 new tests confirmed failing before this block; 19 tests currently passing would be at risk

[[2026-03-30]] Mon 05:27
## Builder Notes
- BLOCK: Cannot implement without modifying TestFromAC_* classes (forbidden)
- Conflict: TestFromAC_ValidateAgentsTodoCheck.test_tools_todos_passes (task #134) asserts tools:[todos, read/readFile] returns [] (no errors)
- Conflict: TestFromAC_BanTodosToolCheck.test_todos_with_other_tools_still_errors (task #193) asserts same input produces errors
- Also: test_multiline_tools_todos_passes expects todos in tools: to pass cleanly
- Resolution needed: Test-writer must remove or update the now-contradicted tests in TestFromAC_ValidateAgentsTodoCheck (test_tools_todos_passes and test_multiline_tools_todos_passes) before implementation can proceed

[[2026-03-30]] Mon 16:06
## Test-Writer Notes (retry)
- Retry reason: Builder BLOCK -- contradicted TestFromAC_* from prior task #134
- Removed: test_tools_todos_passes, test_multiline_tools_todos_passes (asserted todos in tools: returns empty -- directly contradicts #193 AC)
- Updated 3 fixture tests to use read/readFile instead of todos
- 10 target tests FAIL: BanTodosToolCheck x3, BanManageTodoListCheck x4, DeprecatedTodoMessage x2, CopilotInstructionsCleanup x1
- 17 pre-existing tests PASS, 20 pre-existing #198 tests FAIL (unchanged)
- ruff: clean -- commit: 3203734

[[2026-03-30]] Mon 17:13
## Builder Notes
- Files changed: scripts/validate_agents.py, .github/copilot-instructions.md, agents/test-assign.agent.md
- Tests: 27 passed (17 pre-existing + 10 new #193); 20 pre-existing #198 tests still fail (unchanged)
- Lint: ruff clean
- Coverage: N/A -- scripts/validate_agents.py is not an installed package
- Fixes applied: Added _TODOS_RE + _MANAGE_TODO_LIST checks; updated bare-todo error message; removed manage_todo_list line from copilot-instructions.md; removed bare todo from test-assign.agent.md tools list

[[2026-03-30]] Mon 17:59
## Review Evidence\nSee docs/scratch/193-reviewer.md for full evidence.

[[2026-03-30]] Mon 18:26
## Docs Gate

[[2026-03-30]] Mon 18:26
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | Yes | PASS | manage_todo_list line removed by builder (commit 3203734); grep confirms absent |
| 2 | Docstrings | Yes | PASS | validate_agents.py: module docstring + all 4 public functions have docstrings |
| 3 | sources/overview.md | No | N/A | Internal patterns only (resolveMemoryFileUri); no external sources |
| 4 | README.md | No | N/A | No CLI commands added or changed |
| 5 | Research doc | Yes | PASS | docs/research/manage-todo-list-subagent-removal.md exists and linked in task body |

### Files Updated
- None (all docs changes were committed by builder; no new gaps found)

### Scratch Files Cleaned
- Deleted docs/scratch/193-reviewer.md

[[2026-03-30]] Mon 19:32
## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| e179e1d | chore | kanban/tasks/193-*.md | #193 |

[[2026-03-30]] Mon 19:32
## Commits
Commit e179e1d: chore: archive task #193 (kanban/tasks/193-*.md)
