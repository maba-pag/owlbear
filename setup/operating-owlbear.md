# Operating OwlBear

> What setup created, how to update or remove it, how the Delivery workflow runs day to day, and
> how to customize an installed project.

Install first with the [setup guide](setup-guide.md). Multi-project and teammate workflows live in
the [sharing guide](sharing-guide.md).

| You want to... | Section |
| --- | --- |
| See what setup wrote into your project | [What Setup Creates](#what-setup-creates) |
| Understand what `git pull` updates | [Shared vs Copied](#shared-vs-copied) |
| Upgrade OwlBear and migrate Delivery state | [Upgrading OwlBear](#upgrading-owlbear) |
| Replace seeded editor and lint configuration | [Refreshing Consumer Configs](#refreshing-consumer-configs) |
| Remove OwlBear from a project | [Uninstalling](#uninstalling) |
| Run, correct, publish, and accept a Change | [Delivery Workflow](#delivery-workflow) |
| Launch Cockpit for memory and ideas | [Cockpit details](#cockpit-details) |
| Add project-local agents, instructions, or servers | [Project-Specific Customization](#project-specific-customization) |

---

## What Setup Creates

Running `init.py` writes the following files into your project directory:

| File / Directory | Purpose | Idempotency |
| --- | --- | --- |
| `.vscode/settings.json` | Points VS Code at OwlBear agents, skills, and instructions, and carries the seeded Copilot workspace settings | Merged (OwlBear keys as defaults; your existing keys are preserved) |
| `.vscode/mcp.json` | Registers 4 MCP servers (3 OwlBear stdio, including Browser access seeded for wildcard testing, + markitdown) | Merged (OwlBear servers as defaults; your existing servers are preserved) |
| `.owlbear/install-manifest.json` | Records seed paths created or merged by setup, their installed digests, claimed settings/MCP values, and setup-created directories for conservative uninstall | Rewritten atomically on each successful setup; removed when uninstall completes unchanged |
| `.owlbear/hooks/deny-src-writes.py` | Constrains test-only roles to `tests/`, `__tests__/`, and scratch surfaces | Seeded if missing; differing existing hook files prompt/skip/replace (or require `--replace-hooks` non-interactively) |
| `.owlbear/scripts/test-root.py` | Test-root resolver — discovers toolchain and CWD for a given test file | Always written |
| `.owlbear/.gitignore` | Ignores OwlBear-local scratch, runtime, database, vector, and lock artifacts | Managed rules are merged on rerun; custom rules are preserved |
| `.owlbear/knowledge/.gitkeep` | Knowledge store placeholder | Always written |
| `store/knowledge/.gitkeep` | Knowledge store placeholder | Always written |
| `.github/copilot-instructions.md` | Consumer scaffold for project-specific Copilot instructions — placeholder sections for Project Identity, Directory Structure, Tech Stack, and Resources | Skipped if file already exists |
| `.editorconfig` | Editor formatting rules | Skipped if file already exists; refreshable with `--refresh-configs` |
| `.gitattributes` | Git line-ending and diff rules | Skipped if file already exists |
| `.gitignore` | Project-wide Gitignore rules; OwlBear-local rules live in `.owlbear/.gitignore` | Preserves user content and merges current managed rules on rerun |
| `.markdownlint-cli2.jsonc` | Markdown linting configuration | Skipped if file already exists; refreshable with `--refresh-configs` |
| `.markdownlint.json` | Markdown linting rules | Skipped if file already exists; refreshable with `--refresh-configs` |
| `.markdownlintignore` | Markdown lint exclusion patterns | Skipped if file already exists; refreshable with `--refresh-configs` |
| `.yamllint.yml` | YAML linting configuration | Skipped if file already exists; refreshable with `--refresh-configs` |

Review `.vscode/settings.json` as part of trusting the workspace. The seeded settings include an
additional read-access path for the OwlBear checkout, a list of terminal commands that VS Code may
auto-approve, and `chat.tools.terminal.blockDetectedFileWrites: "never"`. These settings make the
agent workflow usable but are trust-sensitive; adjust them to your project's policy after setup.
Rerunning setup merges OwlBear defaults and preserves existing project values.

Open `.github/copilot-instructions.md` after setup and replace its placeholder project identity,
directory, technology, and resource guidance with the facts and conventions of the consumer
project. Setup skips this file on later runs so those project-specific instructions remain yours.
The seeded Browser MCP entry uses `BROWSER_ALLOWED_DOMAINS: "*"` for local testing; replace it with
exact hostnames before using Browser against production or sensitive sites.

Setup does not create Delivery state, worktrees, verification profiles, or retired task, decision,
board, accept, or audit stores; the Delivery engine keeps its own settings and state.

### Where these files come from

The source tree is [`seed/`](../seed/) in the OwlBear checkout. `init.py` walks every file in that
tree into the target project, which is why `seed/` intentionally contains no `README.md`: a root
README there would be copied into the consumer project and could overwrite its front door. This
guide is the canonical explanation of the seed tree instead.

Two neighbouring trees are never copied. [`share/`](../share/README.md) holds the portable agents,
skills, instructions, and prompts that VS Code reads live from the OwlBear checkout, and
[`serve/`](../serve/README.md) holds the runtime packages and MCP servers launched from it.
Repository-only CI automation lives in the OwlBear checkout's `.github/` tree and is not
installed into consumer projects.

## Shared vs Copied

OwlBear uses two different update models:

- **Shared live surfaces:** `share/agents/`, `share/skills/`, `share/instructions/`, and `share/prompts/` stay in the owlbear clone and are read live by VS Code.
- **Copied runtime surfaces:** files under `seed/` are copied into your project by `init.py`; this includes `.owlbear/hooks/` and project-local editor/runtime configuration.

This split is why `git pull` updates shared agents and skills immediately, while copied
runtime files may need a later `init.py` run to refresh. A pull also changes the Delivery code that
the next MCP or Cockpit start runs, so update the checkout through
[Upgrading OwlBear](#upgrading-owlbear) rather than a plain `git pull`.

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

## Upgrading OwlBear

The new Delivery engine's pages replace the retired `/upgrade-delivery` prompt: **Run updates now**
takes the newest version, and the engine also updates itself when idle. Then rerun setup from the
project root to refresh copied files:

```shell
uv run --project ../owlbear python ../owlbear/setup/init.py
```

**Expected result:** setup preserves your edits; see
[Refreshing Consumer Configs](#refreshing-consumer-configs) for the editor and lint files.

## Uninstalling

To remove the OwlBear setup from a consumer project, run this command from the project root:

```shell
uv run --project ../owlbear python ../owlbear/setup/init.py --uninstall
```

An interactive terminal asks for confirmation and prints the files it removes or updates. Preview
the plan without changing files by adding `--dry-run`. A non-interactive uninstall requires
explicit confirmation:

```shell
uv run --project ../owlbear python ../owlbear/setup/init.py --uninstall --yes
```

**Expected result:** an interactive run asks before changing anything; `--dry-run` reports the
planned removals without mutation; `--yes` applies the receipt-backed cleanup without prompting.

The command uses `.owlbear/install-manifest.json` to distinguish surfaces created by setup from
files that existed before it ran. A receipt-owned file is removed only when its installed digest is
unchanged. Receipt-claimed settings and MCP values are removed only when the complete merged file
still matches the post-install digest; later edits, including JSONC comments, preserve the whole
file. Managed ignore rules are removed by recorded line additions, so unrelated rules remain.
Freshly created editor and lint configuration files are removed; pre-existing files remain even
when their content happens to equal the seed. Setup-created empty directories are removed only when
the receipt records them as created.

If the receipt is absent, uninstall takes the conservative path and preserves recognized surfaces;
it refuses to operate in a directory with no receipt or recognizable OwlBear surface. It also
refuses the OwlBear checkout and any descendant of that checkout. A non-interactive call requires
`--yes` or `--dry-run`, and `--yes` and `--dry-run` are valid only with `--uninstall`.

Custom seed files, unrelated VS Code settings and MCP servers, custom ignore rules, Delivery
records, runtime data, knowledge and memory data, and user-local VS Code profile settings are
preserved. In particular, uninstall does not revert the global Copilot reasoning settings that
interactive setup may have written; those settings are shared across projects and remain under the
user's control.

**Expected result:** unchanged setup-owned files and claimed settings or MCP entries are removed or
updated, while customized files, unrelated configuration, Delivery state, runtime data, knowledge,
memory, and user-local profile settings remain in place.

MCP memory entries are stored as markdown files under `.owlbear/memory/`. The
`owlbear-memory` server creates that directory when it starts or writes the first
entry, so setup does not seed a separate memory store.

---

## Delivery Workflow

The new Delivery engine's Changes page runs Changes. **New Change** opens a shaping chat that
turns an idea into a brief; you approve the brief on the page, and the engine plans, builds,
reviews and publishes the Change. Its questions, merge consent and recovery are answered on that
page. It replaces the old engine's `/continue-change`, `/inspect-change`,
`/resolve-delivery-attention`, `/address-pr-feedback`, `/finalize-change`, `/repair-delivery` and
`/resolve-target-conflict` prompts and Cockpit's old Delivery view, which are retired; the tag
`delivery-v1-final` archives them.

---

## Cockpit details

Cockpit is the browser UI for Memory and Ideas. Launch it from the project root so it reads this
project's `.owlbear/memory/` and `.owlbear/ideas.md`.

1. Open a terminal in the project directory.

   Expected outcome: `pwd` or `$PWD` points to your project, not the owlbear clone.

2. Start Cockpit using the sibling owlbear installation.

   macOS / Linux:

   ```shell
   uv run --project ../owlbear cockpit
   ```

    Expected outcome: Cockpit opens `http://127.0.0.1:8420` and shows this project's
    Memory workspace. Use `COCKPIT_NO_OPEN=1` to suppress browser auto-open.

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
    "owlbear-memory": { ... },
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

When something does not behave as described here, use
[Troubleshooting](setup-guide.md#troubleshooting) in the setup guide.
