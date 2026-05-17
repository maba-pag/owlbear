---
description: "System instructions — decision heuristics, system awareness, memory governance, and operational fundamentals"
applyTo: "**"
---

## 1. Decision Heuristics

- **Quality over speed.** Concise, actionable, immediately usable. Applies equally to foundations and features.
- **Research before implementation.** Find how others solved it. Validate assumptions. No exceptions.
- **KISS / YAGNI / DRY.** No over-engineering, no hypothetical-future work, single source of truth.
- **No legacy, no backwards compatibility.** Break things to improve them.
- **Think before coding.** Articulate what changes, expected behavior, and risks before editing.
- **Simplicity first.** Simplest code that works. Avoid abstractions until the third repetition. Split functions > 50 lines.
- **Surgical changes.** Smallest diff for the goal. One logical change per commit.
- **Goal-driven.** Every action traces to a kanban task. If you can't name it, check the board first.

## 2. System Awareness

### Tech Stack

| Component | Technology | Notes |
|-----------|-----------|-------|
| Language | Python 3.12+ | `uv` package manager, never bare `pip` |
| Agents | VS Code / Copilot custom agents | `.agent.md` files, subagent delegation |
| MCP servers | 4 (3 custom stdio + 1 GitHub remote) | mcp-kanban, mcp-knowledge, mcp-memory, github |
| Task board | kanban-md v0.33 (via MCP) | Fixed product topology in code; storage under `.owlbear/kanban/tasks/*.md`, `.owlbear/kanban/archive/*.md`, `.owlbear/kanban/decisions/` |
| Safety | Git safety net + audit log | Review/revert as operational safety |
| Distribution | Clone = install | `setup/init.py` wires workspace config |

### Pipeline

```
research → (researcher) → backlog → (architect) → todo → (test-writer) → in-progress → (builder) → review → (reviewer) → docs → (doc-writer) → done → (auditor) → archived
```

For file placement rules, commit format, priorities, and tags, see `r-project-standards`.

## 3. Memory Governance

| Store | What goes here |
|-------|----------------|
| mcp-memory `ob-memory` | Agent institutional knowledge: durable, scoped lessons for future agents |
| Task body / `.owlbear/kanban/decisions/` | Task-specific context, blockers, decisions, and action requests |
| `.owlbear/research/` | Research findings and source-grounded analysis |
| Project knowledge MCP | Domain knowledge and external-source knowledge |

The VS Code built-in `/memories/` store is retired for OwlBear agents. Do not write user, session, repo inbox, or fallback notes there; if the built-in memory tool appears, treat it as unavailable for agent learning. Use `ob-memory` for institutional memory and normal project artifacts for task context.

Do NOT store as memory: architecture decisions, research findings, code snippets, or task-specific working notes. See `r-pipeline-protocol` → Knowledge Pre-flight and Post-task Reflection.

## 4. Operational Fundamentals

- **MCP Tool Bootstrap.** Some tools in your `tools:` list are MCP-provided and start **deferred** — they won't appear in your available tools until loaded. If a tool is missing, call `tool_search` with the query from this table:

  | MCP server | `tools:` prefix | Runtime tool ID | `tool_search` query |
  |---|---|---|---|
  | OwlBear Kanban | `ob-kanban/*` | `mcp_ob-kanban_<tool>` | `"kanban"` |
  | OwlBear Memory | `ob-memory/*` | `mcp_ob-memory_<tool>` | `"memory"` |
  | DDGS | `ddgs/*` | `mcp_ddgs_<tool>` | `"web search"` |
  | MarkItDown | `markitdown/*` | `mcp_markitdown_<tool>` | `"markdown convert"` |

- **Skill authority.** Skills override dispatch prompts. Dispatch prompts provide context, not procedure.
- **Tool failure.** Capture error → diagnose root cause → adapt approach. Never retry identical commands.
- **Loop detection.** Tier 1: same approach twice — change approach. Tier 2: two different approaches failed — narrow scope (deliver what you can, note what you can't). Tier 3: 3+ attempts — stop, write what failed, escalate per §5 Escalation Routing in `r-pipeline-protocol`.
- **Terminal.** `uv run` for all Python tools.
- **Scratch files.** Terminal output, temp/debug files, and one-off scripts go to `.owlbear/scratch/`, never the project root.
- **Commits.** Follow `r-project-standards` for format, types, and git discipline.
