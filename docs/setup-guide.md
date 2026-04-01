# OwlBear Setup Guide

> From clone to working VS Code workspace.

## Prerequisites

Before running setup, ensure the following are installed on your machine:

| Requirement | Why | How to get it |
|-------------|-----|---------------|
| Python 3.12+ | OwlBear runtime | [python.org](https://www.python.org/downloads/) |
| [uv](https://docs.astral.sh/uv/) | Package manager and MCP server launcher | `pip install uv` or see uv docs |
| VS Code | IDE | [code.visualstudio.com](https://code.visualstudio.com/) |
| GitHub Copilot extension | Chat and agents | VS Code Extensions marketplace |
| Git | Clone and version control | [git-scm.com](https://git-scm.com/) |

> **Windows limitation:** owlbear and your project must be on the **same drive**.
> `setup.py` uses relative paths, and `os.path.relpath` raises `ValueError` when
> resolving paths across different Windows drive letters (e.g., `C:\` vs `D:\`).

---

## Quick Start

```powershell
# 1. Clone owlbear alongside your project directory
git clone https://github.com/your-org/owlbear.git

# 2. Create your project directory (must be on the same drive as owlbear)
mkdir my-project

# 3. Bootstrap the OwlBear workspace from inside your project directory
cd my-project
python ..\owlbear\scripts\setup.py

# 4. Download kanban-md (Windows only)
.\kanban\setup.ps1

# 5. Open the project in VS Code
code .
```

---

## What Setup Creates

Running `setup.py` writes the following files into your project directory:

| File / Directory | Purpose | Idempotency |
|------------------|---------|-------------|
| `.vscode/settings.json` | Points VS Code at owlbear agents, skills, and instructions | Merged (owlbear keys as defaults; your existing keys are preserved) |
| `.vscode/mcp.json` | Registers 4 MCP servers (GitHub remote + 3 owlbear stdio) | Skipped if file already exists |
| `kanban/config.yml` | Kanban board configuration (fresh `next_id: 1`) | Skipped if file already exists |
| `kanban/setup.ps1` | Script to download `kanban-md.exe` | Skipped if file already exists |
| `kanban/tasks/` | Empty task directory | Created if missing |
| `data/knowledge/` | Knowledge store directory | Created if missing |
| `.github/copilot-instructions.md` | Project-level Copilot system prompt | Skipped if file already exists |
| `owlbear-project.json` | Project metadata (name, type, owlbear path) | Skipped if file already exists |

After running `kanban/setup.ps1`, a `kanban/kanban-md.exe` binary is also downloaded.

---

## Verify It Works

After opening the project in VS Code, use the **Diagnostics view** to confirm everything loaded correctly:

1. Open the Copilot Chat panel.
2. Open the **Chat Customizations** window (from Chat settings or Command Palette).
3. Verify each of the following appears:

| What to check | How to verify |
|---------------|---------------|
| OwlBear agents loaded | Chat Customizations shows agents from `../owlbear/agents/` |
| OwlBear skills loaded | Chat Customizations shows skills from `../owlbear/skills/` |
| Instructions loaded | Chat Customizations shows `*.instructions.md` files from `../owlbear/instructions/` |
| MCP servers running | Run `MCP: List Servers` from the Command Palette — owlbearKanban should show `running` |

For runtime debugging, use **"Show Agent Debug Logs"** (Chat view ellipsis `…` menu) —
this shows chronological tool calls, LLM requests, and prompt discovery events.

> **MCP server status:** Only `owlbearKanban` is fully operational. `owlbearKnowledge`
> and `owlbearProject` are under development and will show startup errors — this is
> expected and non-blocking.

---

## Project-Specific Customization

### Adding local agents

Place `.agent.md` files anywhere in your project (e.g., `.github/agents/`). VS Code loads
agents from all configured locations simultaneously — both owlbear agents and your project
agents will appear in the agent picker.

**Important:** Use unique names for your project agents. VS Code does not deduplicate
same-name agents from different locations — if you create `reviewer.agent.md` locally,
both your version and the owlbear version will appear, which is confusing. Prefer names
like `my-project-reviewer.agent.md`.

To register your local agent directory, add to `.vscode/settings.json`:

```json
{
  "chat.agentFilesLocations": {
    "../owlbear/agents": true,
    ".github/agents": true
  }
}
```

### Overriding instructions

Edit `.github/copilot-instructions.md` to add project-specific rules. This file is
auto-detected by VS Code and takes priority over repository-level instructions. You can
also add a `*.instructions.md` file in your project and register its directory in
`chat.instructionsFilesLocations`.

### Adding project-specific MCP servers

Edit `.vscode/mcp.json` to add additional servers alongside the owlbear defaults:

```json
{
  "servers": {
    "owlbearKanban": { ... },
    "myProjectServer": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "-m", "my_project_mcp_server"]
    }
  }
}
```

> Note: `mcp.json` is not updated on subsequent `setup.py` runs (skipped if the file
> exists). Edit it manually to add or update server entries.

### Configuring the kanban MCP server

The `owlbearKanban` server supports environment variables to customise its behaviour.
Set these in `.vscode/mcp.json` under the server's `env` key:

```json
{
  "servers": {
    "owlbearKanban": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "--project", "../owlbear", "-m", "owlbear_mcp_kanban"],
      "env": {
        "KANBAN_BIN": "/path/to/custom/kanban-md",
        "KANBAN_TOOLS_EXCLUDE": "create_task,move_task,edit_task,pick_task"
      }
    }
  }
}
```

| Variable | Description |
|----------|-------------|
| `KANBAN_BIN` | Override the path to the `kanban-md` binary |
| `KANBAN_TOOLS_EXCLUDE` | Comma-separated tool names to hide (e.g. for read-only access) |

### Configuring the knowledge MCP server

The `owlbearKnowledge` server supports environment variables to customise its behaviour.
Set these in `.vscode/mcp.json` under the server's `env` key:

```json
{
  "servers": {
    "owlbearKnowledge": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "--project", "../owlbear", "-m", "owlbear_mcp_knowledge"],
      "env": {
        "OWLBEAR_KB_PATH": "/path/to/knowledge.db",
        "KNOWLEDGE_TOOLS_EXCLUDE": "ingest_document,list_entities"
      }
    }
  }
}
```

| Variable | Description |
|----------|-------------|
| `OWLBEAR_KB_PATH` | Override the path to the SQLite knowledge database |
| `OWLBEAR_MODEL` | Override the LLM model used by the entity extractor |
| `KNOWLEDGE_TOOLS_EXCLUDE` | Comma-separated tool names to hide (e.g. for query-only access) |

### Configuring the project MCP server

The `owlbearProject` server supports environment variables to customise its behaviour.
Set these in `.vscode/mcp.json` under the server's `env` key:

```json
{
  "servers": {
    "owlbearProject": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "--project", "../owlbear", "-m", "owlbear_mcp_project"],
      "env": {
        "OWLBEAR_ROOT": "/path/to/owlbear",
        "PROJECT_TOOLS_EXCLUDE": "project_list,project_structure"
      }
    }
  }
}
```

| Variable | Description |
|----------|-------------|
| `OWLBEAR_ROOT` | Override the path to the owlbear installation root |
| `PROJECT_TOOLS_EXCLUDE` | Comma-separated tool names to hide |

---

## Troubleshooting

| Symptom | Likely cause | Resolution |
|---------|-------------|------------|
| Agents not appearing in picker | Wrong path in `chat.agentFilesLocations` | Open Diagnostics view; verify path relative to project root matches owlbear location |
| Skills not auto-loading | `chat.agentSkillsLocations` missing or path wrong | Check `.vscode/settings.json`; re-run `setup.py` if the key is absent |
| Instructions ignored | `chat.instructionsFilesLocations` missing | Check `.vscode/settings.json`; verify `*.instructions.md` files exist in the registered directory |
| MCP server fails to start | Stub server (`owlbearKnowledge`, `owlbearProject`) or `uv` not on PATH | For stub servers: expected, non-blocking. For `uv` issues: run `uv --version` to confirm installation |
| `ValueError` on setup | Cross-drive path resolution | Place owlbear and your project on the same Windows drive |
| Agent name conflict | Same-name agent in both owlbear and project locations | Give project agents unique names (see Customization section above) |
| `kanban-md.exe` missing | `kanban/setup.ps1` not run yet | Run `.\kanban\setup.ps1` from your project directory |

For deeper debugging, use **"Show Chat Debug View"** (Chat view ellipsis `…` menu) to inspect
raw LLM request/response payloads.
