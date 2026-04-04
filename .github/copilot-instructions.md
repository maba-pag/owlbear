# OwlBear — Copilot Workspace Instructions

## 1. Project Identity

OwlBear is a laptop-resident AI development system built around Copilot CLI. It plans work via kanban, executes through agent workflows, and delivers through shared workspace artifacts. VS Code is the IDE; the filesystem is the integration point.

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
| MCP servers | 5 (4 custom stdio + 1 GitHub remote) | mcp-kanban, mcp-knowledge, mcp-project, mcp-memory, github |
| Task board | kanban-md v0.33 (via MCP) | `kanban/config.yml`, `kanban/tasks/*.md` |
| Safety | Git safety net + audit log | Review/revert as operational safety |
| Distribution | Clone = install | `scripts/setup.py` wires workspace config |

### Pipeline

```
ideation → (researcher) → backlog → (architect) → todo → (test-writer) → in-progress → (builder) → review → (reviewer) → docs → (doc-writer) → done → (auditor) → archived
```

### Directory Structure

| Directory | Purpose |
|-----------|---------|
| `packages/` | Python workspace packages (orchestrator, knowledge, MCP servers, voice) |
| `.github/agents/` | Agent definitions (`.agent.md`) |
| `.github/skills/` | Agent skills (`SKILL.md` — `w-`, `r-`, `h-` prefixed) |
| `.github/instructions/` | Instruction stubs (`.instructions.md` — pointers to skills); `agent-common.instructions.md` is the authoritative Channel B protocol and per-agent section-header mapping |
| `.github/prompts/` | Prompt files (`.prompt.md` — user-facing one-shot commands) |
| `docs/` | Research, decisions, sources, scratch |
| `kanban/` | Board data and tooling |
| `scripts/` | Setup, validation, hooks |

For file placement rules, commit format, priorities, and tags, see `r-project-standards`.

## 4. Memory Governance

| Tier | Store | What goes here |
|------|-------|----------------|
| User | `/memories/` | Tool patterns, CLI recipes, process pitfalls |
| Session | `/memories/session/` | Task-specific context (auto-cleared) |
| Repo inbox | `/memories/repo/inbox/` | Agent lessons-learned (legacy, dual-write) |
| Canonical | mcp-memory `owlbearMemory` | Agent institutional knowledge (queryable) |

Do NOT store in user memory: architecture decisions (`docs/decisions/`), research findings (`docs/research/`), domain knowledge (project KB via MCP), code snippets, or task-specific context.

Clear boundary: `/memories/` = user-centric tool patterns and process pitfalls; `owlbearMemory` = agent institutional knowledge. See `r-pipeline-protocol` → Knowledge Pre-flight and Post-task Reflection.

GitHub-hosted Copilot Memory is disabled to preserve local-first operation.

## 5. Operational Fundamentals

- **Skill authority.** Skills override dispatch prompts. Dispatch prompts provide context, not procedure.
- **Tool failure.** Capture error → diagnose root cause → adapt approach. Never retry identical commands.
- **Loop detection.** Tier 1: same call twice — change approach. Tier 2: two different approaches failed — consider skipping. Tier 3: 3+ attempts — stop, write what failed, hand off.
- **Terminal.** `uv run` for all Python tools. Chain with `;` (never `&&` — PowerShell 5.1).
- **Commits.** Follow `r-project-standards` for format, types, and git discipline.
