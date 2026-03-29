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

Download the kanban-md binary, then open VS Code:

```powershell
kanban\setup.ps1
code .
```

## Adding MCP Servers

Edit `.vscode/mcp.json` to add project-specific servers. VS Code provides IntelliSense autocomplete for all fields.

**stdio** (local Python tool via `uv run`):

```json
"my-tool": { "type": "stdio", "command": "uv", "args": ["run", "my_package/server.py"] }
```

**http** (remote endpoint):

```json
"remote-tool": { "type": "http", "url": "https://example.com/mcp" }
```

**Secrets**: use `${input:var-id}` references in `"env"` and declare an `"inputs"` array at the
top level. VS Code prompts once and stores securely. Never hardcode API keys in `mcp.json`.

```json
"inputs": [{ "id": "api-key", "type": "promptString", "description": "API Key" }],
"env": { "API_KEY": "${input:api-key}" }
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
