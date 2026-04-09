# OwlBear

On-demand AI development system built on GitHub Copilot.

## Overview

OwlBear supercharges your VS Code workflow with a curated set of Copilot agents, skills,
and MCP servers that work together out of the box. Clone once, run one setup command, and
every project on your machine gains access to a consistent set of AI-powered development
tools without any per-project configuration overhead.

Agents handle structured tasks (research, architecture, testing, implementation, review),
skills carry domain knowledge that loads automatically by relevance, and MCP servers give
every agent live access to your project's kanban board, knowledge base, and persistent
memory — all scoped to your project directory and shared through the filesystem.

## Prerequisites

| Requirement | Why | How to get it |
|-------------|-----|---------------|
| Python 3.12+ | OwlBear runtime | [python.org](https://www.python.org/downloads/) |
| [uv](https://docs.astral.sh/uv/) | Package manager and MCP server launcher | `pip install uv` or see uv docs |
| VS Code | IDE | [code.visualstudio.com](https://code.visualstudio.com/) |
| GitHub Copilot extension | Chat and agents | VS Code Extensions marketplace |
| Git | Clone and version control | [git-scm.com](https://git-scm.com/) |

> **Windows:** owlbear and your project must be on the **same drive**. The setup script
> uses relative paths; cross-drive paths are not supported.

## Quick Start

```powershell
# 1. Clone owlbear to a convenient parent directory
git clone https://github.com/your-org/owlbear.git C:\Dev\owlbear

# 2. Create (or navigate to) your project directory — must be on the same drive
mkdir C:\Dev\my-project
cd C:\Dev\my-project

# 3. Bootstrap the OwlBear workspace
python ..\owlbear\setup\init.py

# Optional: set a project name and type
python ..\owlbear\setup\init.py --name my-project --type webapp

# 4. Open the project in VS Code
code .
```

Setup creates `.vscode/settings.json`, `.vscode/mcp.json`, a kanban board directory, and
an `owlbear-project.json` file in your project directory. All paths are relative — the
owlbear repo can be shared across multiple projects on your machine.

For more detail on what each file does and how to customise see
[setup/setup-guide.md](setup/setup-guide.md).

## Directory Layout

| Directory | Purpose |
|-----------|---------|
| `share/agents/` | Agent definitions (`.agent.md`) — loaded into VS Code automatically |
| `share/skills/` | Agent skills (`SKILL.md`) — domain knowledge loaded by relevance |
| `share/instructions/` | Shared instruction files (`*.instructions.md`) |
| `serve/mcp-kanban/` | MCP server for kanban board operations |
| `serve/mcp-memory/` | MCP server for persistent agent memory (SQLite-backed) |
| `serve/mcp-project/` | MCP server for project metadata |
| `serve/mcp-knowledge/` | MCP server exposing the knowledge base |
| `seed/` | Template files copied to new projects during `setup/init.py` |
| `setup/` | Workspace initialiser (`init.py`), setup guide, and sharing guide |

## Verification

After VS Code opens, verify the installation loaded correctly:

1. Open the Copilot Chat panel.
2. Open **Chat Customizations** (Chat settings or Command Palette → `Chat: Open Customizations`).
3. Confirm the following appear:

| What to check | How to verify |
|---------------|---------------|
| OwlBear agents loaded | Chat Customizations lists agents from the owlbear `agents/` directory |
| OwlBear skills loaded | Chat Customizations lists skills from the owlbear `skills/` directory |
| Instructions loaded | Chat Customizations includes `*.instructions.md` files from owlbear |
| MCP servers running | Command Palette → `MCP: List Servers` — `owlbearKanban` shows `running` |

> If agents or skills do not appear, check that `chat.agentFilesLocations` and
> `chat.agentSkillsLocations` in `.vscode/settings.json` point to the correct relative
> path to your owlbear clone.

## Updates

To pull the latest agents, skills, and fixes:

```powershell
cd C:\Dev\owlbear
git pull
```

No reinstall or re-run of `setup/init.py` is needed after a pull — VS Code reads agents
and skills directly from the owlbear directory at runtime.

## Sharing with Teammates

To give a teammate access on their machine, they need to clone both the owlbear repository
and your project, then run `setup/init.py` from their project directory. See
[setup/sharing-guide.md](setup/sharing-guide.md) for the step-by-step walkthrough.
