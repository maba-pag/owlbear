# OwlBear

On-demand AI development system built on GitHub Copilot.

## Overview

OwlBear supercharges your VS Code workflow with a curated set of Copilot agents, skills,
and MCP servers that work together out of the box. Clone once, run one setup command, and
every project on your machine gains access to a consistent set of AI-powered development
tools without any per-project configuration overhead.

Agents design and admit durable semantic authority, then execute bounded Planning and Build work
selected by the Delivery engine. Workers choose state transitions, reviewers provide independent
advisory evidence, and the runtime owns recovery, Integration, and completed history. Skills carry
domain knowledge that loads automatically by relevance, and MCP servers give agents access to
target changes and work, the knowledge base, persistent Memory, and browser automation, all scoped
to your project directory and shared through the filesystem.

## Prerequisites

| Requirement | Why | How to get it |
|-------------|-----|---------------|
| Python 3.14+ | OwlBear runtime | [python.org](https://www.python.org/downloads/) |
| [uv](https://docs.astral.sh/uv/) | Package manager and MCP server launcher | `pip install uv` or see uv docs |
| VS Code | IDE | [code.visualstudio.com](https://code.visualstudio.com/) |
| GitHub Copilot extension | Chat and agents | VS Code Extensions marketplace |
| Git | Clone and version control | [git-scm.com](https://git-scm.com/) |

> **Windows:** owlbear and your project must be on the **same drive**. The setup script
> uses relative paths; cross-drive paths are not supported.

## Quick Start

```powershell
# 1. Clone owlbear to a convenient parent directory
git clone https://github.com/OWNER/owlbear.git C:\Dev\owlbear

# 2. Create (or navigate to) your project directory — must be on the same drive
mkdir C:\Dev\my-project
cd C:\Dev\my-project

# 3. Bootstrap the OwlBear workspace
uv run --project ..\owlbear python ..\owlbear\setup\init.py

# 4. Open the project in VS Code
code .
```

Setup creates merged VS Code settings/MCP config, copied runtime files such as `.owlbear/hooks/`,
and a receipt-authorized empty target store under `.owlbear/target/`. Agents, skills, instructions,
and prompts still load live from the owlbear clone via relative paths, so the same owlbear repo can
be shared across multiple projects on your machine.

For more detail on what each file does and how to customise see
[setup/setup-guide.md](setup/setup-guide.md).

## Directory Layout

| Directory | Purpose |
|-----------|---------|
| `share/agents/` | Agent definitions (`.agent.md`) — loaded into VS Code automatically |
| `share/skills/` | Agent skills (`SKILL.md`) — domain knowledge loaded by relevance |
| `share/instructions/` | Shared instruction files (`*.instructions.md`) |
| `serve/delivery-mcp/` | MCP server for target authority, reviewed transformations, and recovery |
| `serve/memory-mcp/` | MCP server for persistent agent memory (markdown-file backed) |
| `serve/knowledge-mcp/` | MCP server exposing the knowledge base |
| `serve/cockpit/` | Cockpit backend package and prebuilt frontend bundle (`dist/`) used by consumers |
| `seed/` | Template files copied to new projects during `setup/init.py` |
| `setup/` | Workspace initialiser (`init.py`), setup guide, and sharing guide |

## Cockpit (Consumer Launch)

Consumer installs launch Cockpit from the prebuilt SPA bundle in `serve/cockpit/dist/`.
The consumer tree does not need `serve/cockpit/web/` and does not require Node/npm to
run Cockpit.

Run Cockpit from the consumer project root, not from the owlbear clone. `--project`
points uv at the shared owlbear installation; the current directory keeps Cockpit scoped
to the project so `.owlbear/target/` and `.owlbear/memory/` resolve correctly.

macOS / Linux:

```shell
cd ~/Dev/my-project
uv run --project ../owlbear cockpit
```

Windows PowerShell:

```powershell
cd C:\Dev\my-project
uv run --project ..\owlbear cockpit
```

Cockpit starts on `http://127.0.0.1:8420` by default and serves static assets from the
bundled `dist/` directory in the owlbear clone.

`uv run cockpit` without `--project` is only for running from inside the owlbear
repository itself. If you launch Cockpit from outside the consumer project directory,
use `uv run --project ../owlbear --directory /path/to/project cockpit` or set
`OWLBEAR_WORKSPACE_ROOT` and `MEMORY_DIR` explicitly.

| Variable | Default | Purpose |
|----------|---------|---------|
| `COCKPIT_PORT` | `8420` | Override listen port (1-65535) |
| `COCKPIT_NO_OPEN` | unset | Set to `1` to suppress browser auto-open |
| `OWLBEAR_WORKSPACE_ROOT` | `$PWD` | Override the workspace containing target authority |
| `OWLBEAR_TARGET_CUTOVER_REQUEST` | `.owlbear/target-cutover-request.json` | Override the exact activation request path |
| `MEMORY_DIR` | `$PWD/.owlbear/memory/` | Override memory directory path |

## Target Workflow

Use `/ideate` to refine a rough idea, then `/design` to create or resume one durable change under
the target design session. The designer validates the exact semantic revision and asks for explicit
approval before admission to `.owlbear/target/changes/`. Run `/orchestrate <change-id>` only after
admission. The engine then acquires bounded Planning and Build work, workers select typed
transitions, and independent reviewers return advisory evidence.

The canonical Specification, Delivery, Correction, Integration, and recovery procedure is
[Target Delivery Workflow](setup/setup-guide.md#target-delivery-workflow). Cockpit exposes current
work items, requests, typed attention, controls, and completed history. Any migrated records under
`.owlbear/legacy/` are immutable history for inspection, never executable work.

If Cockpit fails because `dist/` assets are missing, refresh from the latest `main`
branch release artifacts (the sync-to-main workflow builds and stages `serve/cockpit/dist/`).

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
| MCP servers running | Command Palette → `MCP: List Servers` — `owlbear-delivery`, `owlbear-memory`, and `owlbear-knowledge` show `running` |

> If agents or skills do not appear, check that `chat.agentFilesLocations` and
> `chat.agentSkillsLocations` in `.vscode/settings.json` point to the correct relative
> path to your owlbear clone.

## Updates

To pull the latest agents, skills, and fixes:

```powershell
cd C:\Dev\owlbear
git pull
```

Shared live surfaces update immediately after a pull because VS Code reads agents,
skills, instructions, and prompts directly from the owlbear directory at runtime.

If you want copied runtime files refreshed — especially `.owlbear/hooks/` or other
seed-managed files — re-run `setup/init.py`. Existing differing hook files are skipped
unless you pass `--replace-hooks` or choose `replace` in an interactive prompt. The
prompt shows a unified diff (seed → existing) so you can see what changed before
choosing. Re-running `init.py` after every owlbear update is the recommended way
to stay current on hooks; the script is idempotent and only touches files that
differ.

## Sharing with Teammates

To give a teammate access on their machine, they need to clone both the owlbear repository
and your project, then run `setup/init.py` through the shared uv project from their project directory. See
[setup/sharing-guide.md](setup/sharing-guide.md) for the step-by-step walkthrough.
