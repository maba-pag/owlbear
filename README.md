# OwlBear

On-demand AI development system built on GitHub Copilot.

## Overview

OwlBear receives user intent, plans work, and executes it through Copilot agent
workflows. VS Code is the IDE; OwlBear and VS Code share the filesystem as the
integration point.

## Prerequisites

- **Python 3.12+**
- **[uv](https://docs.astral.sh/uv/)** package manager
- **[VS Code](https://code.visualstudio.com/)** with the GitHub Copilot extension
- **[Copilot CLI](https://docs.github.com/en/copilot/github-copilot-in-the-cli)** (`gh extension install gh-copilot`)

## Quick Start

```bash
git clone https://github.com/your-org/owlbear.git
cd owlbear
uv sync
```

Run `.owlbear\kanban\setup.ps1` to download the kanban-md binary, then open VS Code with `code .`.

## Directory Layout

| Directory                 | Purpose                                                |
|---------------------------|--------------------------------------------------------|
| `serve/orchestrator/`     | ACP client, dispatch planning, orchestration CLI hooks |
| `serve/knowledge/`        | Knowledge engine (graph + vector)                      |
| `serve/mcp-kanban/`       | MCP server wrapping kanban operations                  |
| `serve/mcp-knowledge/`    | MCP server exposing knowledge operations               |
| `serve/mcp-project/`      | MCP server for project metadata and lifecycle          |
| `serve/mcp-memory/`       | MCP server for persistent agent memory (SQLite-backed) |
| `serve/voice/`            | Voice addon (speech recognition + TTS)                 |
| `share/agents/`           | Agent definitions (`.agent.md`)                        |
| `share/skills/`           | Agent skills (`SKILL.md`, agentskills.io style)        |
| `share/instructions/`     | Shared instruction files (`*.instructions.md`)         |
| `share/prompts/`          | User-facing one-shot prompt files (`*.prompt.md`)      |
| `.owlbear/`               | Project ops data: kanban board, decisions, research, sources, scratch, scripts, hooks |
| `store/`                  | Knowledge and memory data                              |
| `seed/`                   | Template files copied to new projects by `setup/init.py` |
| `setup/`                  | Workspace initialiser (`init.py`), setup guide, sharing guide |
| `scripts/`                | Legacy setup script and pre-commit hooks (see `setup/init.py`) |
| `v1/`                     | Archived v1 codebase for reference                     |

## How It Works

**Agents** in `share/agents/` appear in VS Code's agent picker, each owning a pipeline
stage (research → architect → test-writer → builder → reviewer → writer → auditor).

**Skills** in `share/skills/` auto-load by relevance, carrying domain knowledge and
reusable workflows for each agent role.

**MCP servers** (`mcp-kanban`, `mcp-knowledge`, `mcp-project`, `mcp-memory`) expose the kanban
board, knowledge base, project metadata, and persistent agent memory as tools inside VS Code.

**Orchestrator** dispatches work via ACP over Copilot CLI, coordinating agents
through a shared kanban board in `.owlbear/kanban/`.

## Orchestrator CLI

After `uv sync`, the `owlbear` CLI is available:

```bash
# Dispatch a specific task by ID
uv run owlbear dispatch <task_id>

# Dispatch the top-priority actionable task
uv run owlbear run

# Loop until no actionable tasks remain
uv run owlbear run --all

# Show task counts per status and any blocked tasks
uv run owlbear status
```

All commands require the Copilot CLI (`gh extension install github/gh-copilot`).

## Knowledge Base

Populate the knowledge base from a sources manifest:

```bash
uv run python -m owlbear_knowledge.loader --manifest store/knowledge/general/sources.yaml --root .
```

The manifest at `store/knowledge/general/sources.yaml` includes all research docs, skills, and instructions by default. Set `OWLBEAR_KB_PATH` to override the default `store/knowledge/knowledge.db` location.

## Memory Migration

To bulk-import existing `/memories/repo/` files into memory.db:

```bash
uv run --project serve/mcp-memory python -m owlbear_mcp_memory.migrate \
  --source-dir <path-to-GitHub.copilot-chat/memory-tool/memories/repo/>
```

Optional flags:

- `--db-path PATH` — override the default `data/memory/memory.db` location (or set `OWLBEAR_MEMORY_DB_PATH`)
- `--dry-run` — print entries that would be imported without writing to the DB

## Memory Approval

To review pending memory entries (approve, reject, or skip):

```bash
# List pending entries as a numbered table
uv run --project serve/mcp-memory python -m owlbear_mcp_memory.approve

# Batch approve or reject by entry ID (first 8 chars or full UUID)
uv run --project serve/mcp-memory python -m owlbear_mcp_memory.approve --approve <id1> <id2>
uv run --project serve/mcp-memory python -m owlbear_mcp_memory.approve --reject <id1> <id2>

# Interactive mode: approve (a), reject (r), skip (s) per entry
uv run --project serve/mcp-memory python -m owlbear_mcp_memory.approve --interactive
```

Optional flags:

- `--db-path PATH` — override the default `data/memory/memory.db` location (or set `OWLBEAR_MEMORY_DB_PATH`)

If `data/memory/curation-report.json` is present, a recommendation column is shown in the listing table.

Exit codes: 0 on full success, 1 if any operation failed.

## Development

```bash
uv sync --all-extras
uv run pytest tests/ serve/ -m "not api" -q --tb=short
uv run pytest tests/ serve/ -m "not api" -q --tb=short --cov --cov-report=term-missing
uv run ruff check serve/ tests/
```

## Pre-commit Hooks

Two local hooks guard agent and skill file quality:

- **`validate-skills`** — runs on every commit, validates all `share/skills/*/SKILL.md` frontmatter.
- **`validate-agents`** — runs when any `share/agents/*.agent.md` file is staged, checking for:
  - Bare `todo` (instead of `todos`) in the `tools:` list
  - Stale `resolveMemoryFileUri` tool references anywhere in the file

### VS Code auto-staging trap

VS Code silently re-serializes and re-stages `.agent.md` files when it detects new
tool capabilities (e.g. `execute/runTask`, `execute/testFailure`). This can revert
manual edits before commit. Always run `git diff --cached share/agents/` before committing
and unstage any auto-generated reverts with `git reset HEAD <file>`.

## License

MIT
