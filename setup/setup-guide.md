# OwlBear Setup Guide

> From clone to working VS Code workspace.

## Prerequisites

Before running setup, ensure the following are installed on your machine:

| Requirement | Why | How to get it |
| --- | --- | --- |
| Python 3.14.6+ | OwlBear runtime | [python.org](https://www.python.org/downloads/) |
| [uv](https://docs.astral.sh/uv/) | Package manager and MCP server launcher | [Installation guide](https://docs.astral.sh/uv/getting-started/installation/) |
| VS Code | IDE | [code.visualstudio.com](https://code.visualstudio.com/) |
| GitHub Copilot extension | Chat and agents | VS Code Extensions marketplace |
| Git | Clone and version control | [git-scm.com](https://git-scm.com/) |

> **Windows limitation:** owlbear and your project must be on the **same drive**.
> `init.py` uses relative paths, and `os.path.relpath` raises `ValueError` when
> resolving paths across different Windows drive letters (e.g., `C:\` vs `D:\`).

<!-- separate blockquotes -->

> **macOS and Linux:** Python, uv, VS Code, and Git work natively on both platforms. Browser-backed
> commands still require the separate Chromium download described below.

Chromium is optional for setup. Install it later only when you use the Browser MCP or run
Cockpit's browser-backed tests; see the [Cockpit package guide](../serve/cockpit/README.md#browser-backed-tests).

---

## Quick Start

This is the complete first-time path. Run it from the parent directory of both repositories.
If your project is already checked out, skip its clone command. Replace `OWNER/PROJECT` with the
project's GitHub identity.

### 1. Put both repositories side by side

```shell
# Only if the project is not already checked out.
git clone https://github.com/OWNER/PROJECT.git my-project
git clone https://github.com/maba-pag/owlbear.git owlbear
cd my-project
```

**Expected result:** the OwlBear checkout and the project are siblings, for example
`~/work/owlbear` and `~/work/my-project`. On Windows they are on the same drive.

### 2. Run setup from the project root

```shell
uv run --project ../owlbear python ../owlbear/setup/init.py \
  --github-repository OWNER/PROJECT
```

If the project has a GitHub `origin`, setup can infer the repository and the final flag may be
omitted. Use `--remote` or `--target-branch` only when your publication policy differs from the
defaults `origin` and `main`.

**Expected result:** setup creates or merges `.vscode/settings.json` and `.vscode/mcp.json`, writes
tracked `.owlbear/delivery/config.json`, and copies the project-local hooks and runtime templates.

### 3. Open the project in VS Code

```shell
code .
```

**Expected result:** VS Code opens the project directory, not the OwlBear checkout. The shared
agents, skills, instructions, and prompts are loaded from the sibling OwlBear path.

### 4. Verify the installation

Open **Chat: Open Customizations** and then **MCP: List Servers**. The exact checks are in
[Verify the installation](#verify-the-installation).

**Expected result:** the five seeded MCP servers are running and the shared OwlBear customization
roots appear in Chat Customizations.

## Verify the installation

1. Open Copilot Chat and run **Chat: Open Customizations**.
2. Confirm that OwlBear agents, skills, instructions, and prompts are listed.
3. Run **MCP: List Servers** and confirm these five servers show `running`:
   `owlbear-delivery`, `owlbear-knowledge`, `owlbear-memory`, `owlbear-browser`, and `markitdown`.

If a customization root is missing, inspect `.vscode/settings.json` and compare its relative
OwlBear path with the location of the checkout. If a server is missing, inspect `.vscode/mcp.json`,
run `uv sync --all-extras` in the OwlBear checkout, and rerun setup from the project root.

## First successful workflow

After verification, prove the installation with one small outcome:

1. Run `/ideate` and describe the outcome.
2. Continue with `/design`, review the proposed work, and approve admission. When it succeeds,
   note the returned lowercase, hyphenated Change ID, for example `improve-search`.
3. Run `/orchestrate improve-search` after admission. Planning and Build work then proceed in order.
4. Launch Cockpit from the project root and confirm the Change is visible.

```shell
uv run --project ../owlbear cockpit
```

Expected result: Cockpit opens at `http://127.0.0.1:8420`, reads the current project, and shows one
Change with visible work and a clear next action. Use the
[Delivery workflow reference](#delivery-workflow) only when you need the detailed correction,
publication, acceptance, or recovery procedure.

> The remaining sections are optional setup and reference material. The first successful workflow
> above is the shortest path to a working project.

## macOS Copilot profile settings

When setup runs interactively on macOS, it inspects VS Code's workspace profile association for the
consumer project directory that `setup/init.py` is initializing before changing any Copilot profile
data:

1. If a profile is associated with the project, setup shows the target and asks for confirmation.
2. If no profile is associated, setup explains that it will offer the default profile and asks for
  confirmation.
3. After confirmation, setup updates only the following model entries in that profile's
  `chatLanguageModels.json` file:

  | Model | Reasoning effort |
  | --- | --- |
  | `gpt-5.6-luna` | `max` |
  | `gpt-5.6-sol` | `high` |
  | `claude-opus-5` | `medium` |

The file is written atomically, unrelated profile entries are preserved, and a missing file or
Copilot entry is created minimally. Malformed profile JSON is left unchanged with a warning. To
target a named profile instead of the default fallback, open
the project in VS Code, run `Profiles: Switch Profile`, and rerun `setup/init.py`. Setup does not
take a profile-selection command-line argument. Noninteractive setup skips this user-local profile
mutation.

For development-only browser-backed tests, use the [Cockpit package guide](../serve/cockpit/README.md#browser-backed-tests).

---

## What Setup Creates

Running `init.py` writes the following files into your project directory:

| File / Directory | Purpose | Idempotency |
| --- | --- | --- |
| `.vscode/settings.json` | Points VS Code at owlbear agents, skills, and instructions; enables `mermaid-chat.enabled` for Mermaid diagram rendering in chat | Merged (owlbear keys as defaults; your existing keys are preserved) |
| `.vscode/mcp.json` | Registers 5 MCP servers (4 owlbear stdio, including browser access, + markitdown) | Merged (owlbear servers as defaults; your existing servers are preserved) |
| `.owlbear/delivery/config.json` | Declares the Git remote, pull-request target branch, and exact GitHub `owner/name` identity; host-local writer and execution capacity may be configured separately in ignored `.owlbear/delivery/runtime/host.json` | Tracked in Git; exact schema-1 policy is migrated once and schema-2 project edits are preserved on rerun |
| `.owlbear/hooks/allow-stances-only.py` | Restricts ideation agents to approved stance outputs | Seeded if missing; differing existing hook files prompt/skip/replace (or require `--replace-hooks` non-interactively) |
| `.owlbear/hooks/deny-src-writes.py` | Constrains test-only roles to `tests/`, `__tests__/`, and scratch surfaces | Seeded if missing; differing existing hook files prompt/skip/replace (or require `--replace-hooks` non-interactively) |
| `.owlbear/hooks/deny-writes.py` | Constrains read-only roles to scratch workspace writes only | Seeded if missing; differing existing hook files prompt/skip/replace (or require `--replace-hooks` non-interactively) |
| `.owlbear/hooks/lint-changed.py` | Builder lint feedback hook — runs `uv run ruff check` on edited `.py` files; silently no-ops if `ruff` is not in your project's deps | Seeded if missing; differing existing hook files prompt/skip/replace (or require `--replace-hooks` non-interactively) |
| `.owlbear/hooks/session-context.py` | Injects current git branch + recent commits into agent prompts; silently no-ops if `git` is unavailable | Seeded if missing; differing existing hook files prompt/skip/replace (or require `--replace-hooks` non-interactively) |
| `.owlbear/scripts/test-root.py` | Test-root resolver — discovers toolchain and CWD for a given test file | Always written |
| `.owlbear/.gitignore` | Ignores OwlBear-local scratch, runtime, database, vector, and lock artifacts | Managed rules are merged on rerun; custom rules are preserved |
| `.owlbear/knowledge/.gitkeep` | Knowledge store placeholder | Always written |
| `store/knowledge/.gitkeep` | Knowledge store placeholder | Always written |
| `.github/copilot-instructions.md` | Consumer scaffold for project-specific Copilot instructions — placeholder sections for Project Identity, Directory Structure, Tech Stack, and Resources | Skipped if file already exists |
| `.editorconfig` | Editor formatting rules | Skipped if file already exists; refreshable with `--refresh-configs` |
| `.gitattributes` | Git line-ending and diff rules | Skipped if file already exists |
| `.gitignore` | Project-wide Gitignore rules; OwlBear-local rules live in `.owlbear/.gitignore` | Preserves user content and removes retired root rules on rerun |
| `.markdownlint-cli2.jsonc` | Markdown linting configuration | Skipped if file already exists; refreshable with `--refresh-configs` |
| `.markdownlint.json` | Markdown linting rules | Skipped if file already exists; refreshable with `--refresh-configs` |
| `.markdownlintignore` | Markdown lint exclusion patterns | Skipped if file already exists; refreshable with `--refresh-configs` |
| `.yamllint.yml` | YAML linting configuration | Skipped if file already exists; refreshable with `--refresh-configs` |

For a fresh workspace, `init.py` writes tracked Delivery configuration. It does not create mutable
Delivery runtime, worktrees, verification profiles, or retired task, decision, board, accept, or
audit stores. Existing legacy state is preserved unchanged.

Finalization evidence is collected for the exact reviewed Change head in its managed worktree. The
checks and procedures may differ by Change; Delivery retains their typed observations and an
independent exact-commit review. This evidence does not claim that GitHub can merge the Change or
that the merged result passes.

## Shared vs Copied

OwlBear uses two different update models:

- **Shared live surfaces:** `share/agents/`, `share/skills/`, `share/instructions/`, and `share/prompts/` stay in the owlbear clone and are read live by VS Code.
- **Copied runtime surfaces:** files under `seed/` are copied into your project by `init.py`; this includes `.owlbear/hooks/` and project-local editor/runtime configuration.

This split is why `git pull` updates shared agents and skills immediately, while copied
runtime files may need a later `init.py` run to refresh.

## Refreshing Consumer Configs

Rerunning `init.py` preserves existing editor and lint configuration so project-specific changes
are not overwritten. The refreshable files are `.editorconfig`, `.markdownlint-cli2.jsonc`,
`.markdownlint.json`, `.markdownlintignore`, and `.yamllint.yml`.

From the consumer project root, check for missing or customized files without changing them:

```shell
uv run --project ../owlbear python ../owlbear/setup/init.py --check-configs
```

The command exits successfully when the files match the owlbear seed and exits with status 1 when
one or more files are missing or different. To intentionally replace those five files with the
current seed versions, run:

```shell
uv run --project ../owlbear python ../owlbear/setup/init.py --refresh-configs
```

`--refresh-configs` does not overwrite `.github/copilot-instructions.md`, hook files, or other
project-specific files that are outside the refreshable set.

MCP memory entries are stored as markdown files under `.owlbear/memory/`. The
`owlbear-memory` server creates that directory when it starts or writes the first
entry, so setup does not seed a separate memory store.

---

## Delivery Workflow

This section is the canonical operator procedure. The
[Delivery MCP reference](../serve/delivery-mcp/README.md) lists the exact public tools and startup
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
ordered set of launch packages, dispatches only the worker named by each package, and forwards the
worker's transition unchanged. Tasks execute sequentially in the managed Change worktree and their
promoted commits advance the Change branch directly.

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
| --- | --- | --- |
| Local implementation defect | Builder creates a bounded follow-up commit and requests fresh exact-commit review | Continue the same Build claim only after a fresh pass |
| Missing user decision or action | Worker returns `block` with an embedded request | Answer the request in Cockpit; fresh context carries the structured resolution |
| Requestless condition is satisfied | User clears the block in Cockpit | Engine recomputes eligibility |
| Retryable worker condition | Worker returns `retry` with exact claim and source boundary | Runtime clears the claim and recomputes same-stage eligibility |
| Planning or Design premise failed | Worker returns `return` with evidence and target | Runtime persists successor context; Design reopen is currently manual through `/design` |
| Claim owner is confirmed dead | User recovers the exact claim in Cockpit | Runtime preserves or clears custody according to exact workspace evidence |
| Earlier valid stage is required | User selects an invariant-checked backward move in Cockpit | Runtime resets only the selected outcome and its affected successors |

Do not recover a live claim or infer recovery from elapsed time alone. Request answers, requestless
unblock, confirmed-dead claim recovery, backward movement, and retained legacy Integration attention
remain user-owned Cockpit controls rather than agent MCP operations.

### Publication, Acceptance, And Completed History

When every outcome is complete and the reviewed source boundary is current, run the finalization
workflow for the exact Change head. Delivery publishes or reconciles a draft pull request for the
Change branch, observes the required checks, and marks the PR ready only when the finalized head is
unchanged. Target synchronization, when required, merges only the configured remote-tracking target
into the managed Change worktree; it never updates the target branch or the user checkout.

The user merges the pull request in GitHub. Delivery never merges, enables auto-merge, updates the
target branch, or completes from local evidence. After the merge, read-only acceptance observation
requires the exact repository, PR, base, finalized head, merged state, merge time, and provider-
reported merge commit. Completed history preserves the finalized Change head and accepted merge
commit as separate identities. An open or unmerged PR waits or is deferred; it cannot complete.

Persisted legacy Integration attention remains visible through compatibility surfaces only. Use
Cockpit or `/resolve-delivery-attention <change-id> <attention-id>` to inspect that exact legacy
attention. New Integration repair claims, candidates, reviews, and admissions are retired. Treat a
merge conflict without a current legacy claim as an authority gap; if persisted legacy claim context
supplies exact attempt and claim identities, use the exact recovery operation and preserve its
evidence. Do not edit the target or worktree directly. Cockpit and the MCP completed-change tools
provide bounded list, search, and exact lookup of receipt-backed history.

### Current Manual Boundaries

- External Change-head adoption proves provenance only. Explicit promotion is required before an
  adopted head becomes review authority, and finalization binds the exact reviewed head.
- Design return persists structured successor context, but reopening and revising the Specification
  currently starts with a manual `/design` invocation.
- Target-sync conflict repair remains in the managed Change worktree; Delivery never mutates the
  configured target ref, and merge-conflict repair production is retired outside that bounded path.
- Files under `.owlbear/research/` are frozen comparison evidence, not operational or runtime
  authority. Files under `.owlbear/legacy/` are immutable historical evidence only.

```text
/ideate -> /design -> explicit admission -> /orchestrate
Specification: read/revise -> checkpoint -> derive -> validate -> approve/admit
Delivery: acquire -> plan/build -> publish -> worker transition
Correction: retry | return | block -> typed successor context
Publication: checkpoint -> draft PR -> finalized head -> ready PR
Acceptance: user merges PR -> observe merged evidence -> completed lookup
```

---

---

## Cockpit details

Cockpit is the browser UI for target work items, requests, typed attention, recovery controls,
completed history, Memory, Ideas, and immutable legacy inventory. Launch it from the project root
so it reads this project's `.owlbear/delivery/config.json`, Delivery state, and `.owlbear/memory/`.

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
    "owlbear-delivery": { ... },
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

### Knowledge MCP storage

The `owlbear-knowledge` server stores its SQLite database and vectors under
`.owlbear/knowledge/` in the current workspace. Launch it from the project root; it has no storage
override or tool-exclusion environment settings.

---

## Troubleshooting

| Symptom | Likely cause | Resolution |
| --- | --- | --- |
| Agents not appearing in picker | Wrong path in `chat.agentFilesLocations` | Open Diagnostics view; verify path relative to project root matches owlbear location |
| Skills not auto-loading | `chat.agentSkillsLocations` missing or path wrong | Check `.vscode/settings.json`; re-run `init.py` if the key is absent |
| Instructions ignored | `chat.instructionsFilesLocations` missing | Check `.vscode/settings.json`; verify `*.instructions.md` files exist in the registered directory |
| MCP server fails to start | Missing dependency or `uv` not on PATH | Run `uv --version` to confirm installation; check MCP server logs in VS Code Output panel |
| `owlbear-delivery` reports `ERR_DELIVERY_STARTUP_UNCONFIGURED` | `.owlbear/delivery/config.json` is absent from the project root | Re-run `init.py`; setup recreates the file only when it is missing |
| `uv run cockpit` says the command is missing | Command was run from the consumer project without `--project` | Use `uv run --project ../owlbear cockpit` from the project root |
| Delivery or Cockpit reports that `.owlbear/target` or `.owlbear/worktrees` requires migration | A retired live-state root is still nonempty | Preserve the root unchanged. From the project root, preview with `uv run --project /path/to/owlbear migrate-delivery-state .`, then apply with the same command plus `--apply`. Re-running `--apply` recovers an interrupted attempt before retrying. |
| Cockpit shows the wrong workspace or cannot find `.owlbear/delivery/config.json` | Cockpit was launched from the wrong working directory | Run from the project root or add `--directory /path/to/project` |
| `ValueError` on setup | Cross-drive path resolution | Place owlbear and your project on the same Windows drive |
| Hook file not refreshed on rerun | Existing local `.owlbear/hooks/` file differs from seed | Re-run `init.py --replace-hooks` to overwrite, or choose `replace` when prompted interactively |
| Agent name conflict | Same-name agent in both owlbear and project locations | Give project agents unique names (see Customization section above) |

For deeper debugging, use **"Show Chat Debug View"** (Chat view ellipsis `…` menu) to inspect
raw LLM request/response payloads.
