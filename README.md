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

Download the kanban-md binary:

```powershell
kanban\setup.ps1
```

Open VS Code — agents and MCP servers auto-discover:

```bash
code .
```

## Directory Layout

| Directory                 | Purpose                                                |
|---------------------------|--------------------------------------------------------|
| `packages/orchestrator/`  | ACP client, dispatch planning, orchestration CLI hooks |
| `packages/knowledge/`     | Knowledge engine (graph + vector)                      |
| `packages/mcp-kanban/`    | MCP server wrapping kanban operations                  |
| `packages/mcp-knowledge/` | MCP server exposing knowledge operations               |
| `packages/mcp-project/`   | MCP server for project metadata and lifecycle          |
| `packages/voice/`         | Voice addon (speech recognition + TTS)                 |
| `agents/`                 | Agent definitions (`.agent.md`)                        |
| `skills/`                 | Agent skills (`SKILL.md`, agentskills.io style)        |
| `instructions/`           | Shared instruction files (`*.instructions.md`)         |
| `docs/`                   | Research, decisions, sources, and supporting docs      |
| `kanban/`                 | Kanban board data and tooling                          |
| `scripts/`                | Project tooling scripts (setup, skill validation)      |
| `v1/`                     | Archived v1 codebase for reference                     |

## How It Works

**Agents** in `agents/` appear in VS Code's agent picker, each owning a pipeline
stage (research → architect → test-writer → builder → reviewer → writer → auditor).

**Skills** in `skills/` auto-load by relevance, carrying domain knowledge and
reusable workflows for each agent role.

**MCP servers** (`mcp-kanban`, `mcp-knowledge`, `mcp-project`) expose the kanban
board, knowledge base, and project metadata as tools inside VS Code.

**Orchestrator** dispatches work via ACP over Copilot CLI, coordinating agents
through a shared kanban board in `kanban/`.

## Development

```bash
uv sync --all-extras
uv run pytest tests/ -m "not api" -q --tb=short
uv run ruff check src/ tests/
```

## License

MIT
