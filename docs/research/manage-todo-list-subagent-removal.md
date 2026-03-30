# Disable manage_todo_list / todos tool for subagents

> **Owning task:** #193 — Fix stale VS Code tool names in validation scripts and agent files
> **Date:** 2026-03-30 **Status:** Complete

## 1. Context and Question

The original task investigated stale tool names (`todo` vs `todos`). The
architect review (.95 confidence) found the codebase is already correct — no
stale references exist. The user then independently tested and found that
`manage_todo_list` (the `todos` built-in tool) **does not function when invoked
by subagents**. The user decided to:

1. Ban the tool from all agent definitions
2. Update the validator to catch future re-introduction
3. Update the copilot-instructions process habit

This research validates the user's finding and audits the full scope of changes.

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | VS Code Cheat Sheet (2026-03-25) | https://code.visualstudio.com/docs/copilot/reference/copilot-vscode-features | .95 — describes `todos` as "Track implementation and progress of a chat request" |
| 2 | VS Code Agent Tools docs (2026-03-25) | https://code.visualstudio.com/docs/copilot/agents/agent-tools | .85 — tool enabling, tool sets, approval model |
| 3 | VS Code Subagents docs (2026-03-25) | https://code.visualstudio.com/docs/copilot/agents/subagents | .90 — context isolation, tool inheritance, collapsed execution |
| 4 | VS Code Custom Agents docs (2026-03-25) | https://code.visualstudio.com/docs/copilot/customization/custom-agents | .90 — `tools:` frontmatter, "tool not available = ignored" |
| 5 | Prior research: stale-tool-names.md | docs/research/stale-tool-names.md (#193) | .90 — confirmed `todos` is canonical, `todo` was v1 |
| 6 | User empirical testing | Task #193 body (user decision section) | .95 — direct observation: tool non-functional in subagent |

## 3. Analysis

### Why `todos` doesn't work in subagents

The `todos` tool is described as tracking "implementation and progress of **a chat
request**" with a visible widget (`chat.tools.todos.showWidget` setting). Key
architectural facts from the subagent docs:

- Subagents run in **isolated context**, appearing as a collapsed tool call
- Subagent results are summarized and returned to the parent agent
- The `todos` widget is bound to the main chat request's UI lifecycle

A UI-bound progress tracker has no rendering surface inside a collapsed subagent
context. The user's empirical test confirms this: the tool silently fails or is
unavailable when called from a subagent. The custom agents docs note: "If a given
tool is not available when using the custom agent, it is ignored."

**Confidence:** .90 — user empirical evidence + architectural inference from 3
independent sources. No explicit VS Code documentation of this limitation found.

### Codebase audit

| Location | `manage_todo_list` | `todos` in tools: | `todo` in tools: | Action |
|----------|-------------------|-------------------|-----------------|--------|
| `agents/*.agent.md` (11 files) | 0 refs | 0 refs | 0 refs | None needed |
| `.github/copilot-instructions.md` | 1 ref (line 27) | 0 | 0 | Update habit |
| `scripts/validate_agents.py` | 0 | 0 | Checks bare `todo` | Expand checks |
| `tests/test_validate_agents.py` | 0 | 0 | Tests `todo` check | Add new tests |
| `docs/research/*.md` (3 files) | 3 refs | 0 | 0 | Historical, no action |

### Validator current state vs required state

| Check | Current behavior | Required behavior |
|-------|-----------------|-------------------|
| bare `todo` in tools: | Flags, says "should be `todos`" | Flag, say "tool disabled for subagents" |
| `todos` in tools: | Not checked | Flag as disabled tool |
| `manage_todo_list` anywhere | Not checked | Flag as disabled tool |
| `resolveMemoryFileUri` anywhere | Flags correctly | No change needed |

### Relationship with task #198

Task #198 ("Expand validator to check ALL tool names against canonical registry")
is a broader `nice-to-have` expansion. The #193 changes are a focused subset that
can land independently. #198 remains valid as a follow-up improvement.

### copilot-instructions.md update

Line 27 reads: `- **manage_todo_list extensively.** Track progress, create
checkpoints, add a reflection step at the end.`

Since the tool is disabled, this instruction is misleading. Options:

| Option | Trade-off |
|--------|-----------|
| **(rec:) Remove the line entirely** | Simplest; agents track progress via kanban board and session memory already |
| Replace with session memory habit | Adds complexity; session memory is already covered elsewhere |
| Replace with kanban-md progress tracking | Redundant with existing "goal-driven execution" habit |

**Recommendation (.85 confidence):** Remove the line. The behavior it encouraged
(tracking progress) is already covered by kanban-md task management, session
memory, and the "goal-driven execution" habit in the same file.

## 4. Recommendation (.90 confidence)

Create a single implementation task covering all three changes:
1. Expand `validate_agents.py` to flag `todos`, `manage_todo_list`, and update
   the existing `todo` check message
2. Update the copilot-instructions process habit
3. Add corresponding tests

The scope is small (< 50 LOC changes across 3 files) and tightly coupled.

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Ban manage_todo_list/todos tool from agents and validator" --priority needed --status ideation --tags phase-1,tooling,agent,config --body "## Objective\nDisable the todos/manage_todo_list tool across the codebase. The tool does not function in subagent context (see docs/research/manage-todo-list-subagent-removal.md).\n\n## Acceptance Criteria\n- [ ] validate_agents.py: flag 'todos' in tools: line as disabled tool\n- [ ] validate_agents.py: flag 'manage_todo_list' anywhere in file (like resolveMemoryFileUri check)\n- [ ] validate_agents.py: update existing bare 'todo' check message from 'should be todos' to 'tool disabled for subagents'\n- [ ] .github/copilot-instructions.md: remove the manage_todo_list process habit line\n- [ ] tests/test_validate_agents.py: add tests for todos detection, manage_todo_list detection\n- [ ] tests/test_validate_agents.py: update existing todo check tests if error message changed\n- [ ] Run validator on all 11 agent files — clean pass\n\n## Context\nSee docs/research/manage-todo-list-subagent-removal.md for full findings.\nParent: #193. Related: #198 (broader validator expansion, still valid).\n\n## Files to touch\n- scripts/validate_agents.py\n- tests/test_validate_agents.py\n- .github/copilot-instructions.md\n\n## Constraints\n- Scope is ~50 LOC across 3 files\n- Do NOT touch docs/research/*.md historical references"
```
