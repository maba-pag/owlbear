---
id: 36
title: Rename todo tool reference to todos in all .agent.md files
status: archived
priority: medium
created: 2026-03-26 18:45:04.748447+01:00
updated: 2026-03-27 12:45:51.830304+01:00
started: 2026-03-27 12:45:46.802168+01:00
completed: 2026-03-27 12:45:46.802168+01:00
tags:
- phase-1
- scope:agents
class: standard
archival_reason: completed
archival_refs: []
---

[[2026-03-27]] Fri 02:57

## Acceptance Criteria

- [ ] All 11 `.agent.md` files in `.github/agents/` reference `todos` (not `todo`) in their tools list
- [ ] No other content in the files is changed (only the tool name in YAML frontmatter)
- [ ] VS Code agent diagnostics show `todos` tool resolved for at least one agent (manual spot-check)

## Research

Trivial rename. See `docs/research/rename-todo-to-todos.md` for scope and file list (11 files, 1 line each).

VS Code cheat sheet confirms `#todos` is the built-in tool name. Setting `chat.tools.todos.showWidget` also uses plural. Current `todo` references are silently ignored (no-ops). Prior research #4 identified this gap.

[[2026-03-27]] Fri 04:29

## Architecture Review

**Verdict:** Approve

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| All 11 agent.md files reference todos in tools list | Clear, verifiable via grep | Keep |
| No other content changed (only YAML frontmatter tool name) | Clear, verifiable via diff | Keep |
| VS Code diagnostics show todos tool resolved (manual spot-check) | Reasonable manual gate | Keep |

### Architecture Notes

Trivial YAML config rename. No application code touched. TDD not applicable (no behavior to test). Grep confirms 10 multi-line entries (`todo,`) and 1 inline entry (`todo]` in orchestrator). Body text references to `todo` status must remain unchanged. Research doc scope matches codebase state exactly.

### Changes Made

- Approved to todo, released claim

### Dependencies

- None required. Standalone config task.

[[2026-03-27]] Fri 07:55

## Test-Writer Notes

- Test file: tests/test_rename_todo_to_todos.py
- Classes: TestFromAC_AgentMdToolRename
- Tests per category: happy 11 (todos in tools), error 11 (no bare todo in tools)
- Total: 22 tests, all FAIL (AssertionError) âœ“
- ruff: clean
- AC coverage:
  AC1 (all 11 files reference todos in tools): test_tools_list_contains_todos[{file}] x11
  AC1 (bare todo not in tools): test_tools_list_has_no_bare_todo[{file}] x11
  AC2 (no other content changed): non-automatable in RED phase â€” builder constraint
  AC3 (VS Code diagnostics): manual spot-check, not automatable
- Note: test_argument_hint_skills.py (pre-staged from another agent) was included in
  the commit unintentionally â€” it was already in the git index before staging.

[[2026-03-27]] Fri 08:40

## Builder Notes

- Files changed: 11 .github/agents/*.agent.md files (frontmatter tools only)
- Tests: 22 passed in tests/test_rename_todo_to_todos.py
- Coverage: not collected because coverage plugin flags are unsupported in this workspace pytest
- Lint: ruff check tests/test_rename_todo_to_todos.py passed
- Evidence: red run failed 22 tests, green run passed 22 tests, and git diff showed only 11 one-line frontmatter edits
- Fixes applied: replaced tools list entry todo with todos in all 11 agent files
- Spot check: diagnostics for .github/agents/orchestrator.agent.md reported no errors

[[2026-03-27]] Fri 10:28
## Review Evidence

### Review: #36 - Rename todo tool reference to todos in all .agent.md files

### Test Results

- pytest: 22 passed, 0 failed
- Evidence: scoped pytest run for tests/test_rename_todo_to_todos.py passed.

### Lint Results

- ruff: clean on tests/test_rename_todo_to_todos.py

### Coverage

- Not run. This task changes YAML agent frontmatter only; no Python implementation module changed.

### Pass 1 - CRITICAL

#### Test-Writer AC Coverage

- AC1: COVERED by TestFromAC_AgentMdToolRename::test_tools_list_contains_todos and TestFromAC_AgentMdToolRename::test_tools_list_has_no_bare_todo. Both would fail immediately if any agent file reverted to bare todo or lost todos.
- AC2: Manual-only diff constraint for a config-only rename. Verified directly in AC Compliance using committed diff evidence.
- AC3: Manual editor-diagnostics gate. Verified directly in AC Compliance using current diagnostics on orchestrator.agent.md.

#### Security Review

- No security issues found. The builder commit touched YAML tool identifiers only.

#### Test Integrity

- Original TestFromAC file was introduced in commit 827957f.
- Current tests/test_rename_todo_to_todos.py still contains TestFromAC_AgentMdToolRename at line 60 and both original test methods at lines 64 and 71.
- Assessment: PRESERVED for both tests. No weakened or removed assertions found.

#### Test Quality

- Assertion specificity: STRONG. The tests assert exact presence of todos and exact absence of bare todo.
- Negative and error paths: STRONG for this task shape. The forbidden-token assertion is the negative path.
- Mutation reasoning: STRONG. Reverting any one of the 11 files to todo would fail the parametrized suite.
- Test independence: STRONG. Tests only read files and share no mutable state.
- Descriptive names: STRONG.

#### Data Safety

- No data safety issues found.

#### Implementation-Aware Test Gaps

- No significant untested paths. Commit 15eec5b changed exactly 11 agent files with 11 insertions and 11 deletions, and the diff scope is limited to frontmatter tool token replacements.

### Pass 2 - INFORMATIONAL

- No informational findings.

### AC Compliance

- AC1 PASS: all 11 agent files now list todos in frontmatter tool entries: .github/agents/architect.agent.md:20, .github/agents/auditor.agent.md:20, .github/agents/builder.agent.md:24, .github/agents/curator.agent.md:22, .github/agents/kanban-planner.agent.md:20, .github/agents/orchestrator.agent.md:18, .github/agents/planner.agent.md:16, .github/agents/researcher.agent.md:26, .github/agents/reviewer.agent.md:20, .github/agents/test-writer.agent.md:22, .github/agents/writer.agent.md:24. A focused search found no remaining bare todo tool entries. Scoped pytest passed 22 out of 22 tests.
- AC2 PASS: builder commit 15eec5b touched exactly the 11 .github agent files. Commit stat was 11 files changed, 11 insertions, 11 deletions. Commit diff on those files is limited to replacing todo with todos in the YAML frontmatter tools entries; no body text changes were present.
- AC3 PASS: current editor diagnostics report no errors for .github/agents/orchestrator.agent.md, and that file uses todos at line 18.

### Verdict: PASS (confidence .95)

### Action Taken

- Appended review evidence and prepared the task for docs.

[[2026-03-27]] Fri 12:45
## Audit

### AC Verification (against committed state at HEAD)

| AC Line | Evidence | Status |
|---------|----------|--------|
| All 11 .agent.md reference todos in tools | git show HEAD:.github/agents/{all 11 files} confirmed todos present. Builder commit 15eec5b: 11 files, 11 insertions, 11 deletions. | PASS |
| No other content changed (YAML frontmatter only) | Commit 15eec5b stat shows tools-line-only diffs across all 11 files. No body text modifications. | PASS |
| VS Code diagnostics show todos resolved | Builder and reviewer both confirmed orchestrator.agent.md diagnostics clean. | PASS |

### Test Results

- pytest (task-specific): 22/22 FAIL against working tree. Root cause: staged uncommitted changes from external source reverted todos back to todo in all 11 files. Committed state at HEAD is correct.
- pytest (full suite): 2 collection errors (test_process_supervisor.py, test_validate_skills.py) from missing modules (unrelated to task 36).
- ruff: clean on tests/test_rename_todo_to_todos.py

### Cross-Task Regression Alert

CRITICAL: All 11 .github/agents/*.agent.md files have STAGED uncommitted changes that revert todos back to todo while adding new tools (execute/runTask, execute/testFailure, execute/runTests). These staged changes will destroy task 36 deliverable if committed. Likely cause: VS Code agent tool auto-sync re-serialized the frontmatter. Next agent committing agent files must preserve todos.

### Architect Quality

- AC specificity: Clear, grep-verifiable criteria for all 3 items
- Edge case coverage: Adequate. Architect noted inline vs multi-line format difference.
- Design direction: Correct minimal-change approach for config rename.
- AC quality score: 4 (adequate, minor format note filled by test-writer)

### Confidence: .95

Committed deliverable at HEAD passes all AC. Working tree contamination is external (staged by another source), not from task 36 pipeline.

### Action: archive
