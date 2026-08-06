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
uv run --project ../owlbear python ../owlbear/setup/init.py

# 4. Open the project in VS Code
code .
```

> **Windows:** use backslashes:
> `uv run --project ..\owlbear python ..\owlbear\setup\init.py`. owlbear and your project
> must be on the same drive.

---

## What Setup Creates

Running `init.py` writes the following files into your project directory:

| File / Directory | Purpose | Idempotency |
|------------------|---------|-------------|
| `.vscode/settings.json` | Points VS Code at owlbear agents, skills, and instructions; enables `mermaid-chat.enabled` for Mermaid diagram rendering in chat | Merged (owlbear keys as defaults; your existing keys are preserved) |
| `.vscode/mcp.json` | Registers 5 MCP servers (4 owlbear stdio, including browser access, + markitdown) | Merged (owlbear servers as defaults; your existing servers are preserved) |
| `.owlbear/delivery/config.json` | Declares the Delivery integration branch; roots, single-worker capacities, agent routing, and models come from workspace conventions and agent definitions | Seeded once, ignored by Git, and preserved on rerun so local policy changes remain intact |
| `.owlbear/target/changes/` | Admitted semantic authority and per-change runtime evidence | Fresh setup activates an empty store; reruns preserve target records |
| `.owlbear/target-cutover-request.json` | Exact activation request loaded by target MCP and Cockpit startup | Published for a fresh workspace; preserved on rerun |
| `.owlbear/target-cutover.json` | Immutable receipt authorizing target mutation | Published only after snapshot, staging, and smoke verification succeed |
| `.owlbear/legacy/target-cutover/` | Hash-verified snapshot of the retired bootstrap source | Created during activation; never runtime authority |
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

For a fresh workspace, `init.py` activates only the empty target authority store. It does not create
retired task, decision, board, accept, or audit stores, and reruns do not overwrite target records.
If `.owlbear/kanban/` already exists, setup preserves it and publishes no target store or receipt.

### Existing Pre-Cutover Workspaces

1. Run `init.py` with the command above.

  Expected outcome: copied setup files are refreshed, while `.owlbear/kanban/` remains unchanged
  and target mutation remains blocked.

2. Place the reviewed migration request at `.owlbear/target-cutover-request.json`. The request must
  contain current source digests, explicit classifications, target authority, code revision, and
  activation approval; do not hand-create a receipt.

  Expected outcome: the request names every source and unfinished semantic identity that must be
  preserved or reintroduced.

3. Invoke the cutover service directly from the project root:

  ```shell
  uv run --project ../owlbear python ../owlbear/setup/finalize.py \
    --workspace . --request .owlbear/target-cutover-request.json
  ```

  Expected outcome: the command returns `"ok": true`, snapshots and retires the source stores,
  smoke-checks target authority/runtime, and only then publishes `.owlbear/target-cutover.json`.

## Shared vs Copied

OwlBear uses two different update models:

- **Shared live surfaces:** `share/agents/`, `share/skills/`, `share/instructions/`, and `share/prompts/` stay in the owlbear clone and are read live by VS Code.
- **Copied runtime surfaces:** files under `seed/` are copied into your project by `init.py`; this includes `.owlbear/hooks/` and project-local editor/runtime configuration.

This split is why `git pull` updates shared agents and skills immediately, while copied
runtime files may need a later `init.py` run to refresh.

MCP memory entries are stored as markdown files under `.owlbear/memory/`. The
`ob-memory` server creates that directory when it starts or writes the first
entry, so setup does not seed a separate memory store.

---

## Target Delivery Workflow

This section is the canonical operator procedure. The
[Kanban MCP reference](../serve/mcp-kanban/README.md) lists the exact public tools and startup
configuration, [WIRING.md](../share/WIRING.md) maps agent authority and loading, and the
[Cockpit package guide](../serve/cockpit/README.md) covers launch and configuration for the human
control surface.

### Specification

Use `/ideate` when a rough idea needs a one-question-at-a-time refinement interview. Use `/design`
to create or resume one durable change. The Designer reads the current owner-computed package
identity, revises the complete authored intent and design through compare-and-swap, checkpoints the
unchanged revision, derives and validates Delivery authority, and asks for explicit approval before
admission. A stale package identity returns to read and reconcile; agents never edit package
internals or reconstruct package identity.

Expected outcome: one approved Specification revision is admitted under the configured target root
with deterministic outcomes, dependencies, commitments, and proof boundaries.

### Delivery

After admission, invoke `/orchestrate <change-id>`. Each cycle lists current work, acquires a bounded
ordered set of launch packages, dispatches only the worker named by each package, forwards the
worker's transition unchanged, and invokes Integration only for engine-provided ready change IDs.

- Planning reads one typed plan context, publishes one independently reviewed task chain, and
  returns `advance`, `retry`, `return`, or `block`.
- Build reads one typed task and custody context, commits only its maintained surfaces, publishes
  one independently reviewed exact-commit result, and returns the same transition set.
- Reviewers return only `pass` or `finding` with source-grounded evidence. They never publish,
  repair, choose transitions, or mutate lifecycle state.

Expected outcome: outcomes move through Planning and Build under separate execution and writer
capacity without Orchestrator scheduling judgment or conversation-derived authority.

### Correction And Recovery

Worker transitions keep correction finite and typed:

| Condition | Owner and control | Resume behavior |
|-----------|-------------------|-----------------|
| Local implementation defect | Builder creates a bounded follow-up commit and requests fresh exact-commit review | Continue the same Build claim only after a fresh pass |
| Missing user decision or action | Worker returns `block` with an embedded request | Answer the request in Cockpit; fresh context carries the structured resolution |
| Requestless condition is satisfied | User clears the block in Cockpit | Engine recomputes eligibility |
| Retryable worker condition | Worker returns `retry` with exact claim and source boundary | Runtime clears the claim and recomputes same-stage eligibility |
| Planning or Design premise failed | Worker returns `return` with evidence and target | Runtime persists successor context; Design reopen is currently manual through `/design` |
| Claim owner is confirmed dead | User recovers the exact claim in Cockpit | Runtime preserves or clears custody according to exact workspace evidence |
| Earlier valid stage is required | User selects an invariant-checked backward move in Cockpit | Runtime resets only the selected outcome and its affected successors |

Do not recover a live claim or infer recovery from elapsed time alone. Request answers, requestless
unblock, confirmed-dead claim recovery, backward movement, and Integration retry remain user-owned
Cockpit controls rather than agent MCP operations.

### Integration And Completed History

When every outcome is complete and the reviewed source boundary is current, a normal orchestration
cycle asks the runtime to integrate the engine-provided ready change ID. Integration validates the
package, reviewed source, target identity, and completed-history boundary before publishing the
product tree and recoverable package snapshot atomically to the configured target.

Failure preserves completed outcomes and publishes typed Integration attention with unchanged
heads and a retry condition. Use Cockpit to inspect the attention and retry conditions that do not
require source repair. For `merge-conflict`, invoke `/integration-repair <change-id>`: Builder may
create one additive repair commit limited to the original conflict paths, obtain independent review,
and admit only a pass. Repair admission advances the reviewed source boundary; it does not update
the target. Run normal `/orchestrate <change-id>` afterward so the runtime owns the Integration
retry. Cockpit and the MCP completed-change tools provide bounded list, search, and exact lookup of
published history.

### Current Manual Boundaries

- Assembly remains a live stage, projection, and required startup policy type, but current compiled
  contracts do not require it and the agent MCP surface has no Assembly context or result-publication
  operation. An unexpected Assembly launch is recovered by exact claim identity rather than run.
- Design return persists structured successor context, but reopening and revising the Specification
  currently starts with a manual `/design` invocation.
- Merge-conflict repair is deliberately user-invoked; neither Orchestrator nor Integration edits
  source automatically.
- Files under `.owlbear/research/` are frozen comparison evidence, not operational or runtime
  authority. Files under `.owlbear/legacy/` are immutable historical evidence only.

```text
/ideate -> /design -> explicit admission -> /orchestrate
Specification: read/revise -> checkpoint -> derive -> validate -> approve/admit
Delivery: acquire -> plan/build -> publish -> worker transition
Correction: retry | return | block -> typed successor context
Integration: ready -> publish target + completed package -> completed lookup
```

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

Cockpit is the browser UI for target work items, requests, typed attention, recovery controls,
completed history, Memory, Ideas, and immutable legacy inventory. Launch it from the project root
so it reads this project's target request/receipt, `.owlbear/target/`, and `.owlbear/memory/`.

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
  target workspace. Use `COCKPIT_NO_OPEN=1` to suppress browser auto-open.

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
| `ob-kanban` reports `ERR_DELIVERY_STARTUP_UNCONFIGURED` | `.owlbear/delivery/config.json` is absent from the project root | Re-run `init.py`; setup recreates the file only when it is missing |
| `uv run cockpit` says the command is missing | Command was run from the consumer project without `--project` | Use `uv run --project ../owlbear cockpit` from the project root |
| Target MCP or Cockpit refuses to start after an update | A pre-cutover store has no valid target request and receipt | Prepare the reviewed request and invoke `setup/finalize.py` directly as described above |
| Cockpit shows the wrong workspace or cannot find `.owlbear/target` | Cockpit was launched from the wrong working directory | Run from the project root, add `--directory /path/to/project`, or set `OWLBEAR_WORKSPACE_ROOT` explicitly |
| `ValueError` on setup | Cross-drive path resolution | Place owlbear and your project on the same Windows drive |
| Hook file not refreshed on rerun | Existing local `.owlbear/hooks/` file differs from seed | Re-run `init.py --replace-hooks` to overwrite, or choose `replace` when prompted interactively |
| Agent name conflict | Same-name agent in both owlbear and project locations | Give project agents unique names (see Customization section above) |

For deeper debugging, use **"Show Chat Debug View"** (Chat view ellipsis `…` menu) to inspect
raw LLM request/response payloads.
