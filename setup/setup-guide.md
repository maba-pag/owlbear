# OwlBear Setup Guide

> From clone to working VS Code workspace.

## Prerequisites

Before running setup, ensure the following are installed on your machine:

| Requirement | Why | How to get it |
|-------------|-----|---------------|
| Python 3.14+ | OwlBear runtime | [python.org](https://www.python.org/downloads/) |
| [uv](https://docs.astral.sh/uv/) | Package manager and MCP server launcher | `pip install uv` or see uv docs |
| VS Code | IDE | [code.visualstudio.com](https://code.visualstudio.com/) |
| GitHub Copilot extension | Chat and agents | VS Code Extensions marketplace |
| Git | Clone and version control | [git-scm.com](https://git-scm.com/) |
| Chromium | Browser MCP runtime | Run `playwright install chromium` after setup |

> **Windows limitation:** owlbear and your project must be on the **same drive**.
> `init.py` uses relative paths, and `os.path.relpath` raises `ValueError` when
> resolving paths across different Windows drive letters (e.g., `C:\` vs `D:\`).

<!-- separate blockquotes -->

> **macOS and Linux:** No additional prerequisites — Python, uv, VS Code, and Git
> work natively on all platforms.

---

## Quick Start

```shell
# 1. Clone owlbear alongside your project directory
git clone https://github.com/your-org/owlbear.git

# 2. Create your project directory
mkdir my-project

# 3. Bootstrap the OwlBear workspace from inside your project directory
cd my-project
python ../owlbear/setup/init.py

# 4. Open the project in VS Code
code .
```

> **Windows:** use backslashes: `python ..\owlbear\setup\init.py`. owlbear and your
> project must be on the same drive.

---

## What Setup Creates

Running `init.py` writes the following files into your project directory:

| File / Directory | Purpose | Idempotency |
|------------------|---------|-------------|
| `.vscode/settings.json` | Points VS Code at owlbear agents, skills, and instructions; enables `mermaid-chat.enabled` for Mermaid diagram rendering in chat | Merged (owlbear keys as defaults; your existing keys are preserved) |
| `.vscode/mcp.json` | Registers 5 MCP servers (4 owlbear stdio, including browser access, + markitdown) | Merged (owlbear servers as defaults; your existing servers are preserved) |
| `.owlbear/changes/` | Native product intent, design, decisions, delivery graph, plans, and receipts | Created if missing; existing change records are preserved |
| `.owlbear/kanban/jobs/` and `archive/` | Active and completed native delivery jobs | Created if missing; existing jobs are preserved |
| `.owlbear/kanban/requests/{pending,resolved}/` | Native Decision and Action Requests | Created if missing; existing requests are preserved |
| `.owlbear/kanban/attempts/` and `findings/` | Immutable attempt events and corrective findings | Created if missing; existing evidence is preserved |
| `.owlbear/kanban/activity.jsonl` | Native delivery activity stream | Created if missing; never truncated on rerun |
| `.owlbear/hooks/allow-stances-only.py` | Restricts ideation agents to approved stance outputs | Seeded if missing; differing existing hook files prompt/skip/replace (or require `--replace-hooks` non-interactively) |
| `.owlbear/hooks/deny-src-writes.py` | Constrains test-only roles to `tests/`, `__tests__/`, and scratch surfaces | Seeded if missing; differing existing hook files prompt/skip/replace (or require `--replace-hooks` non-interactively) |
| `.owlbear/hooks/deny-writes.py` | Constrains read-only roles to scratch workspace writes only | Seeded if missing; differing existing hook files prompt/skip/replace (or require `--replace-hooks` non-interactively) |
| `.owlbear/hooks/lint-changed.py` | Builder lint feedback hook — runs `uv run ruff check` on edited `.py` files; silently no-ops if `ruff` is not in your project's deps | Seeded if missing; differing existing hook files prompt/skip/replace (or require `--replace-hooks` non-interactively) |
| `.owlbear/hooks/session-context.py` | Injects current git branch + recent commits into agent prompts; silently no-ops if `git` is unavailable | Seeded if missing; differing existing hook files prompt/skip/replace (or require `--replace-hooks` non-interactively) |
| `.owlbear/scripts/test-root.py` | Test-root resolver — discovers toolchain and CWD for a given test file | Always written |
| `.owlbear/knowledge/.gitkeep` | Knowledge store placeholder | Always written |
| `store/knowledge/.gitkeep` | Knowledge store placeholder | Always written |
| `.github/copilot-instructions.md` | Consumer scaffold for project-specific Copilot instructions — placeholder sections for Project Identity, Directory Structure, Tech Stack, and Resources | Skipped if file already exists |
| `.editorconfig` | Editor formatting rules | Skipped if file already exists |
| `.gitattributes` | Git line-ending and diff rules | Skipped if file already exists |
| `.gitignore` | Gitignore rules; owlbear section appended if marker absent | Appended if owlbear marker absent; idempotent once present |
| `.markdownlint-cli2.jsonc` | Markdown linting configuration | Skipped if file already exists |
| `.markdownlint.json` | Markdown linting rules | Skipped if file already exists |
| `.markdownlintignore` | Markdown lint exclusion patterns | Skipped if file already exists |
| `.yamllint.yml` | YAML linting configuration | Always written |

`init.py` creates only native authority and work stores. It does not create the retired
`tasks/`, `decisions/`, or board configuration paths, and reruns do not overwrite native records.

## Shared vs Copied

OwlBear uses two different update models:

- **Shared live surfaces:** `share/agents/`, `share/skills/`, `share/instructions/`, and `share/prompts/` stay in the owlbear clone and are read live by VS Code.
- **Copied runtime surfaces:** files under `seed/` are copied into your project by `init.py`; this includes `.owlbear/hooks/`, `.owlbear/kanban/`, and other project-local runtime state.

This split is why `git pull` updates shared agents and skills immediately, while copied
runtime files may need a later `init.py` run to refresh.

MCP memory entries are stored as markdown files under `.owlbear/memory/`. The
`ob-memory` server creates that directory when it starts or writes the first
entry, so setup does not seed a separate memory store.

---

## Native Delivery Workflow

Use `/ideate` when the starting idea needs a one-question-at-a-time refinement interview. Use
`/design` to create or resume the durable native change under `.owlbear/changes/<change-id>/`.
The designer keeps product intent, decisions, technical design, delivery obligations, and proof
boundaries together, then validates and admits the exact approved revision.

After admission, invoke `/orchestrate <change-id>`. The orchestrator asks the engine for eligible
native jobs and delegates each started job to its purpose-specific planner, builder, acceptor, or
auditor. Jobs reference authoritative change targets; they do not copy specifications into task
files.

```text
/ideate -> /design -> explicit admission -> /orchestrate
Specification: design and validate
Delivery: plan -> build -> accept -> audit
```

Successful work creates immutable receipts in the native change. Attempts, requests, findings, and
activity remain inspectable in the work store. Historical records from the retired workflow, when
present, live under `.owlbear/legacy/` as hash-verified read-only inventory and are never execution
authority.

---

## Verify It Works

After opening the project in VS Code, use the **Diagnostics view** to confirm everything loaded correctly:

1. Open the Copilot Chat panel.
2. Open the **Chat Customizations** window (from Chat settings or Command Palette).
3. Verify each of the following appears:

| What to check | How to verify |
|---------------|---------------|
| OwlBear agents loaded | Chat Customizations shows agents from `../owlbear/share/agents/` |
| OwlBear skills loaded | Chat Customizations shows skills from `../owlbear/share/skills/` |
| Instructions loaded | Chat Customizations shows `*.instructions.md` files from `../owlbear/share/instructions/` |
| MCP servers running | Run `MCP: List Servers` from the Command Palette — `ob-kanban`, `ob-memory`, and `ob-knowledge` should show `running` |

For runtime debugging, use **"Show Agent Debug Logs"** (Chat view ellipsis `…` menu) —
this shows chronological tool calls, LLM requests, and prompt discovery events.

---

## Launch Cockpit

Cockpit is the browser UI for native changes, delivery jobs, requests, evidence, Memory, Ideas, and
immutable legacy inventory. Launch it from the project root
so it reads this project's `.owlbear/kanban/` and `.owlbear/memory/` directories.

1. Open a terminal in the project directory.

   Expected outcome: `pwd` or `$PWD` points to your project, not the owlbear clone.

2. Start Cockpit using the sibling owlbear installation.

   macOS / Linux:

   ```shell
   uv run --project ../owlbear cockpit
   ```

   Windows PowerShell:

   ```powershell
   uv run --project ..\owlbear cockpit
   ```

   Expected outcome: Cockpit opens `http://127.0.0.1:8420` and shows this project's
  native workspace. Use `COCKPIT_NO_OPEN=1` to suppress browser auto-open.

3. If your owlbear clone is not a sibling directory, replace `../owlbear` with the path
   to the clone.

  Expected outcome: uv resolves the `cockpit` command from owlbear while Cockpit keeps
  the current project directory as its runtime working directory. If you run the command
  from somewhere else, add `--directory /path/to/project`.

---

## Project-Specific Customization

### Adding local agents

Place `.agent.md` files anywhere in your project (e.g., `.owlbear/agents/`). VS Code loads
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
    "../owlbear/share/agents": true,
    ".owlbear/agents": true
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
    "ob-kanban": { ... },
    "myProjectServer": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "-m", "my_project_mcp_server"]
    }
  }
}
```

> Note: `mcp.json` is merged on subsequent `init.py` runs — owlbear servers are written
> as defaults and your existing entries are preserved. Edit it manually to add new server
> entries or customize existing ones.

### Configuring the knowledge MCP server

The `ob-knowledge` server supports environment variables to customise its behaviour.
Set these in `.vscode/mcp.json` under the server's `env` key:

```json
{
  "servers": {
    "ob-knowledge": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "--project", "../owlbear", "-m", "owlbear_mcp_knowledge"],
      "env": {
        "OWLBEAR_KB_PATH": "/path/to/knowledge.db",
        "KNOWLEDGE_TOOLS_EXCLUDE": "knowledge_ingest"
      }
    }
  }
}
```

| Variable | Description |
|----------|-------------|
| `OWLBEAR_KB_PATH` | Override the path to the SQLite knowledge database |
| `KNOWLEDGE_TOOLS_EXCLUDE` | Comma-separated tool names to hide (e.g. for query-only access) |

---

## Troubleshooting

| Symptom | Likely cause | Resolution |
|---------|-------------|------------|
| Agents not appearing in picker | Wrong path in `chat.agentFilesLocations` | Open Diagnostics view; verify path relative to project root matches owlbear location |
| Skills not auto-loading | `chat.agentSkillsLocations` missing or path wrong | Check `.vscode/settings.json`; re-run `init.py` if the key is absent |
| Instructions ignored | `chat.instructionsFilesLocations` missing | Check `.vscode/settings.json`; verify `*.instructions.md` files exist in the registered directory |
| MCP server fails to start | Missing dependency or `uv` not on PATH | Run `uv --version` to confirm installation; check MCP server logs in VS Code Output panel |
| `uv run cockpit` says the command is missing | Command was run from the consumer project without `--project` | Use `uv run --project ../owlbear cockpit` from the project root |
| Cockpit shows the wrong workspace or cannot find `.owlbear/kanban` | Cockpit was launched from the wrong working directory | Run from the project root, add `--directory /path/to/project`, or set `OWLBEAR_WORK_ROOT` explicitly |
| `ValueError` on setup | Cross-drive path resolution | Place owlbear and your project on the same Windows drive |
| Hook file not refreshed on rerun | Existing local `.owlbear/hooks/` file differs from seed | Re-run `init.py --replace-hooks` to overwrite, or choose `replace` when prompted interactively |
| Agent name conflict | Same-name agent in both owlbear and project locations | Give project agents unique names (see Customization section above) |

For deeper debugging, use **"Show Chat Debug View"** (Chat view ellipsis `…` menu) to inspect
raw LLM request/response payloads.
