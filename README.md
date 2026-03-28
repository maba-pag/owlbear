# OwlBear

On-demand, laptop-resident AI development system built around GitHub Copilot CLI.

## Overview

OwlBear receives user intent, plans work, executes it through Copilot CLI agent
workflows, and delivers results through shared workspace artifacts (code, kanban
board, sessions). It is not a daemon — it runs on demand when invoked through
VS Code or CLI commands.

VS Code is the IDE for interactive work. OwlBear and VS Code share the filesystem
as the integration point.

## Prerequisites

- **Python 3.12+**
- **[uv](https://docs.astral.sh/uv/)** package manager
- **[VS Code](https://code.visualstudio.com/)** with the GitHub Copilot extension
- **[Copilot CLI](https://docs.github.com/en/copilot/github-copilot-in-the-cli)** (`gh extension install gh-copilot`)

## Setup

```bash
git clone https://github.com/your-org/owlbear.git
cd owlbear
uv sync                        # install dependencies
```

Download the kanban-md binary (PowerShell):

```powershell
kanban\setup.ps1
```

Open the project in VS Code:

```bash
code .
```

Agents, skills, and instructions auto-load from their respective directories.
MCP servers are configured in `.vscode/mcp.json`.

## Directory Layout

| Directory                 | Purpose                                                |
|---------------------------|--------------------------------------------------------|
| `packages/orchestrator/`  | ACP client, dispatch planning, orchestration CLI hooks |
| `packages/knowledge/`     | Knowledge engine (graph + vector)                      |
| `packages/mcp-kanban/`    | MCP server wrapping kanban operations                  |
| `packages/mcp-knowledge/` | MCP server exposing knowledge operations               |
| `packages/mcp-project/`   | MCP server for project metadata and lifecycle          |
| `agents/`                 | Agent definitions (`.agent.md`)                        |
| `skills/`                 | Agent skills (`SKILL.md`, agentskills.io style)        |
| `instructions/`           | Shared instruction files (`*.instructions.md`)         |
| `docs/`                   | Research, decisions, sources, and supporting docs      |
| `kanban/`                 | Kanban board data and tooling                          |
| `scripts/`                | Project tooling scripts (setup, skill validation)      |
| `v1/`                     | Archived v1 codebase for reference                     |

## Usage

1. Open VS Code: `code .`
2. Open Copilot Chat and select an agent from `agents/`
3. Skills from `skills/` auto-load by relevance
4. MCP servers (kanban, knowledge, project) are available via `.vscode/mcp.json`

For task management, use `kanban\kanban-md.exe` (see `kanban/README.md`).

## Development

```bash
uv sync --all-extras           # install with dev dependencies
```

### Testing

```bash
uv run pytest tests/ -m "not api" -q --tb=short

# With coverage
uv run pytest tests/ --cov --cov-report=term-missing -q
```

### Linting

```bash
uv run ruff check src/ tests/
uv run ruff format --check
```

## License

MIT
