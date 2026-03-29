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

## New Project Setup

Requires Python 3.12+ and uv — see [Prerequisites](#prerequisites).

To wire OwlBear into an existing project, run `scripts/setup.py` from the target
project directory:

```bash
cd /path/to/your-project
python ../owlbear/scripts/setup.py
```

This creates:

- `.vscode/settings.json` — agent, skill, and instruction file locations pointing to OwlBear
- `.vscode/mcp.json` — MCP server entries for kanban, knowledge, and project servers
- `kanban/` — kanban board directory with a fresh config and `tasks/` subfolder
- `data/knowledge/` — knowledge base directory
- `.github/copilot-instructions.md` — minimal project instructions file

The script is idempotent: re-running it merges settings without overwriting existing files.

### Next Steps

1. Open the project in VS Code: `code /path/to/your-project`
2. Run `kanban/setup.ps1` to download the kanban-md binary
3. Verify agent discovery by opening Copilot Chat — agents and skills should appear in the agent picker
4. Edit `.vscode/mcp.json` to add project-specific MCP servers (see below)

### Adding MCP Servers

Open `.vscode/mcp.json` and add server entries. VS Code provides IntelliSense autocomplete in this file.

**stdio** (local Python tool via `uv run`):

```json
{ "servers": { "myTool": { "type": "stdio", "command": "uv", "args": ["run", "my-tool"] } } }
```

**http** (remote URL):

```json
{ "servers": { "myRemote": { "type": "http", "url": "https://my-mcp-server.example.com/mcp" } } }
```

**Secrets** — use `${input:variable-id}` with an `"inputs"` array; VS Code prompts once and stores securely:

```json
{
  "inputs": [{ "id": "myKey", "type": "promptString", "description": "API key" }],
  "servers": { "myService": { "type": "stdio", "command": "uv", "args": ["run", "my-svc"],
    "env": { "API_KEY": "${input:myKey}" } } }
}
```

See the [VS Code MCP Configuration Reference](https://code.visualstudio.com/docs/copilot/reference/mcp-configuration).

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
uv run pytest tests/ packages/ -m "not api" -q --tb=short
uv run ruff check packages/ tests/
```

## License

MIT
