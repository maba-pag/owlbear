# Rename `todo` Tool Reference to `todos`

> **Owning task:** #36 — Rename todo tool reference to todos in all .agent.md files
> **Date:** 2026-03-27 **Status:** Complete

## 1. Context and Question

Task #4 (agent-md-format validation) identified that all 11 `.agent.md` files reference `todo` as a tool name, but the VS Code built-in tool is named `todos`. This task validates that finding and defines the AC for the rename.

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | VS Code Cheat Sheet — Chat Tools | <https://code.visualstudio.com/docs/copilot/reference/copilot-vscode-features> | .95 — canonical list: `#todos` is the built-in tool name |
| 2 | VS Code Cheat Sheet — Planning | same URL, Planning section | .90 — setting `chat.tools.todos.showWidget` confirms plural |
| 3 | Prior research: agent-md-format.md | `docs/research/agent-md-format.md` §4 | .90 — original finding: `todo` needs rename to `todos` |

## 3. Analysis

N/A — trivial rename. No design decision, no trade-offs, no alternatives.

**Scope:** 11 files, 1 line change each. Two YAML formats:

| Format | Files | Current | Target |
|--------|-------|---------|--------|
| Array (multi-line) | 10 agents | `    todo,` | `    todos,` |
| Inline array | orchestrator | `todo]` | `todos]` |

**Files:**

1. `.github/agents/architect.agent.md` (line 20)
2. `.github/agents/auditor.agent.md` (line 20)
3. `.github/agents/builder.agent.md` (line 24)
4. `.github/agents/curator.agent.md` (line 22)
5. `.github/agents/kanban-planner.agent.md` (line 20)
6. `.github/agents/orchestrator.agent.md` (line 18)
7. `.github/agents/planner.agent.md` (line 16)
8. `.github/agents/researcher.agent.md` (line 26)
9. `.github/agents/reviewer.agent.md` (line 20)
10. `.github/agents/test-writer.agent.md` (line 22)
11. `.github/agents/writer.agent.md` (line 24)

## 4. Recommendation (.95 confidence)

Rename `todo` to `todos` in all 11 agent tool lists. KISS-aligned: one-line change per file, no structural impact. VS Code silently ignores unavailable tools, so current `todo` references are no-ops — the rename restores functionality.

## 5. Follow-up Tasks

No new follow-up tasks needed — task #36 is itself the implementation action for this rename.
