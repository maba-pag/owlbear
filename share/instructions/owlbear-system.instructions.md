---
description: "OwlBear system instructions — decision heuristics, system awareness, memory governance, and operational fundamentals"
applyTo: "**"
---

## 2. Decision Heuristics

- **Quality over speed.** Concise, actionable, immediately usable. Applies equally to foundations and features.
- **Research before implementation.** Find how others solved it. Validate assumptions. No exceptions.
- **KISS / YAGNI / DRY.** No over-engineering, no hypothetical-future work, single source of truth.
- **No legacy, no backwards compatibility.** Break things to improve them.
- **Think before coding.** Articulate what changes, expected behavior, and risks before editing.
- **Simplicity first.** Simplest code that works. Avoid abstractions until the third repetition. Split functions > 50 lines.
- **Surgical changes.** Smallest diff for the goal. One logical change per commit.
- **Goal-driven.** Every action traces to a kanban task. If you can't name it, check the board first.

## 3. System Awareness

### Tech Stack

| Component | Technology | Notes |
|-----------|-----------|-------|
| Language | Python 3.12+ | `uv` package manager, never bare `pip` |
| Agents | VS Code / Copilot custom agents | `.agent.md` files, subagent delegation |
| MCP servers | 4 (3 custom stdio + 1 GitHub remote) | mcp-kanban, mcp-knowledge, mcp-memory, github |
| Task board | kanban-md v0.33 (via MCP) | `.owlbear/kanban/config.yml`, `.owlbear/kanban/tasks/*.md` |
| Safety | Git safety net + audit log | Review/revert as operational safety |
| Distribution | Clone = install | `setup/init.py` wires workspace config |

### Pipeline

```
research → (researcher) → backlog → (architect) → todo → (test-writer) → in-progress → (builder) → review → (reviewer) → docs → (doc-writer) → done → (auditor) → archived
```

### Directory Structure

| Directory | Purpose |
|-----------|---------|
| `serve/` | Python workspace packages (orchestrator, knowledge, browser, MCP servers) |
| `share/agents/` | Agent definitions (`.agent.md`) |
| `share/skills/` | Agent skills (`SKILL.md` — `w-`, `r-`, `h-` prefixed) |
| `share/instructions/` | Instruction stubs (`.instructions.md` — pointers to skills); `agent-common.instructions.md` is the authoritative Channel B protocol and per-agent section-header mapping |
| `share/prompts/` | Prompt files (`.prompt.md` — user-facing one-shot commands) |
| `.owlbear/` | Project ops data: kanban board, decisions, research, sources, scratch, scripts, hooks |
| `store/` | Knowledge and memory data |
| `seed/` | Template files copied to new projects by `setup/init.py` |
| `setup/` | Workspace initialiser (`init.py`), setup guide, sharing guide |
| `scripts/` | Legacy setup script and pre-commit hooks (see `setup/init.py`) |

For file placement rules, commit format, priorities, and tags, see `r-project-standards`.

## 4. Memory Governance

| Tier | Store | What goes here |
|------|-------|----------------|
| User | `/memories/` | Tool patterns, CLI recipes, process pitfalls |
| Session | `/memories/session/` | Task-specific context (auto-cleared) |
| Repo inbox | `/memories/repo/inbox/` | Agent lessons-learned (legacy, dual-write) |
| Canonical | mcp-memory `ob-memory` | Agent institutional knowledge (queryable) |

Do NOT store in user memory: architecture decisions (`.owlbear/decisions/`), research findings (`.owlbear/research/`), domain knowledge (project KB via MCP), code snippets, or task-specific context.

Clear boundary: `/memories/` = user-centric tool patterns and process pitfalls; `owlbearMemory` = agent institutional knowledge. See `r-pipeline-protocol` → Knowledge Pre-flight and Post-task Reflection.

## 5. Operational Fundamentals

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
