# Operating OwlBear

> What OwlBear installed, how to run, update or remove it, how the Delivery workflow runs day to
> day, and how to customize an installed project.

Install first with the [setup guide](setup-guide.md). Multi-project and teammate workflows live in
the [sharing guide](sharing-guide.md).

| You want to... | Section |
| --- | --- |
| See what OwlBear installed on your Mac and in a project | [What OwlBear Installs](#what-owlbear-installs) |
| Start, stop, pause, or check OwlBear | [Running OwlBear](#running-owlbear) |
| Update OwlBear | [Upgrading OwlBear](#upgrading-owlbear) |
| Run a Change from idea to merge | [Delivery Workflow](#delivery-workflow) |
| See what the optional agent workspace setup wrote | [What Setup Creates](#what-setup-creates) |
| Understand what an OwlBear update changes in the agent workspace | [Shared vs Copied](#shared-vs-copied) |
| Replace seeded editor and lint configuration | [Refreshing Consumer Configs](#refreshing-consumer-configs) |
| Remove OwlBear | [Uninstalling](#uninstalling) |
| Add project-local agents, instructions, or servers | [Project-Specific Customization](#project-specific-customization) |

---

## What OwlBear Installs

OwlBear keeps everything it runs and records under `~/.owlbear/` on your Mac:

| Path | Purpose |
| --- | --- |
| `runtime` | The active version: the clone you installed, and after the first update a link to a folder under `versions/` |
| `versions/<tag>/`, `repo.git` | Installed versions, each with its own environment, and the clone they are fetched from |
| `projects/<id>/` | Each registered project's Delivery state |
| `worktrees/` | The worktrees OwlBear's agents work in |
| `design-pack/` | The pinned design pack Delivery's design checks use |
| `machine.json` | The registered projects and the machine's settings |
| `data.json` | Which shared settings repository OwlBear uses |
| `host.log` | The running host's log; `owlbear logs` shows its end |

Only with your yes at `owlbear install`, OwlBear also adds:

| Path | Purpose |
| --- | --- |
| `~/.local/bin/owlbear` | A link to the command |
| `~/.copilot/agents/owlbear-shaper.agent.md`, `~/.copilot/skills/owlbear-change-shaping` | Links to the shaping agent and its skill, which **New Change** opens |
| `~/Library/LaunchAgents/com.owlbear.host.plist` | The login item; `owlbear autostart on` or `off` changes it |
| `~/.owlbear/completion.zsh` | The zsh completion, always written; nothing edits `~/.zshrc` |

In a project, `owlbear setup --repo PATH` writes only with your yes, and lists each file in the
clone's `.git/info/exclude`:

| File | Entry |
| --- | --- |
| `.mcp.json` | The `owlbear-delivery` chat server, so the project's chats reach Delivery |
| `.vscode/settings.json` | `chat.defaultToCopilotHarness: true`, for New Change's Copilot chat |

The clone's Git folder also holds `owlbear-delivery/`, with the project's id and format marker.
Opening the project in VS Code never starts or changes OwlBear.

## Running OwlBear

One OwlBear runs per Mac and serves every project added on its pages. It keeps advancing a
project's Changes while that project's VS Code window is closed.

| Command | What it does |
| --- | --- |
| `owlbear` | Starts OwlBear if it is stopped, else shows its status |
| `owlbear start [--paused]` | Starts it in the background, running, or paused until you press **Resume** |
| `owlbear stop` | Stops it; running steps finish on their own |
| `owlbear restart [--paused]` | Stops it, then starts it running or paused as it was |
| `owlbear status` | Its address, pause, projects, and login item |
| `owlbear logs [-n N]` | The end of its log |
| `owlbear doctor` | Checks Git, the GitHub CLI and its sign-in, uv, the Copilot CLI, whether the login item's saved PATH and `COPILOT_CLI_PATH` find them, and each project's readiness, with the fix |
| `owlbear update` | Runs updates now |
| `owlbear versions [--prepare]` | The version it runs and the one it would take next; `--prepare` installs and checks that one without switching |
| `owlbear autostart on` or `off` | Starts OwlBear at login, or not; `on` saves this shell's PATH and `COPILOT_CLI_PATH` as they are now, so run it again after adding or removing a tool or Node version |
| `owlbear setup --repo PATH` | Checks a project's readiness, confirms its profile and registers its chat server |
| `owlbear data [PATH]` | Shows or sets the shared settings repository |
| `owlbear home` | Shows OwlBear's folder on this Mac |
| `owlbear install`, `owlbear uninstall` | Adds or removes the command link, the shaping agent links and the login item |

`owlbear --help` lists every command, including the project commands that take `--repo PATH`.

**Pause Delivery** in the bar stops new automatic agent steps on every project until you press
**Resume**; your own actions, such as settings, memory and **New Change**, still run. While paused,
**Pause and stop when idle** stops OwlBear once the running steps end. Automatic memory curation
after a merge and when idle each has its own setting in **Settings → This machine**: off, on, or on
even while paused; **Curate now** on the Maintenance page always runs.

A shared settings repository is a local clone of a Git repository you choose, set with
`owlbear data PATH` and used after `owlbear restart`. When one is set, project settings, agent
memory and the backlog live there, and OwlBear commits and pushes each save, so they follow you
across clones and machines. Without one, they stay on this Mac in `~/.owlbear/projects/<id>/`.

## Upgrading OwlBear

OwlBear's versions are Git tags such as `v1.0`. OwlBear installs a new version beside the running
one, checks it, and switches only while nothing runs; it never moves to an older version.

- By default it takes every new minor version after 15 minutes without use, announced on open
  pages 2 minutes ahead. **Settings → This machine** chooses major versions only, and whether it
  updates when idle or while paused.
- **Run updates now** on a paused page, or `owlbear update`, updates at once.
- After an update, the pages say once which version OwlBear now runs. A chat whose Delivery server
  is older answers `OwlBear updated: …`: reload the VS Code window, or in the Copilot runtime run
  **Restart Local Agent Host**; a window reload does not restart that runtime's tool servers.

The agent workspace follows these updates: setup writes its paths through `~/.owlbear/runtime`, so
they stay valid. Rerun setup from the project root after an update to refresh copied files:

```shell
uv run --project ~/.owlbear/runtime python ~/.owlbear/runtime/setup/init.py
```

**Expected result:** setup preserves your edits; see
[Refreshing Consumer Configs](#refreshing-consumer-configs) for the editor and lint files.

---

## What Setup Creates

The optional agent workspace setup (`setup/init.py`, see the
[setup guide](setup-guide.md#optional-agent-workspace)) lists the following files and asks before
writing them into your project directory:

| File / Directory | Purpose | Idempotency |
| --- | --- | --- |
| `.vscode/settings.json` | Points VS Code at OwlBear agents, skills, and instructions, and carries the seeded Copilot workspace settings | Merged (OwlBear keys as defaults; your existing keys are preserved) |
| `.vscode/mcp.json` | Registers 4 MCP servers (3 OwlBear stdio, including Browser access seeded for wildcard testing, + markitdown) | Merged (OwlBear servers as defaults; your existing servers are preserved) |
| `.owlbear/install-manifest.json` | Records seed paths created or merged by setup, their installed digests, claimed settings/MCP values, setup-created directories and the Git exclude lines for conservative uninstall | Rewritten atomically on each successful setup; removed when uninstall completes unchanged |
| `.owlbear/hooks/deny-src-writes.py` | Constrains test-only roles to `tests/`, `__tests__/`, and scratch surfaces | Seeded if missing; differing existing hook files prompt/skip/replace (or require `--replace-hooks` non-interactively) |
| `.owlbear/scripts/test-root.py` | Test-root resolver — discovers toolchain and CWD for a given test file | Always written |
| `.owlbear/knowledge/.gitkeep` | Knowledge store placeholder | Always written |
| `store/knowledge/.gitkeep` | Knowledge store placeholder | Always written |
| `.github/copilot-instructions.md` | Consumer scaffold for project-specific Copilot instructions — placeholder sections for Project Identity, Directory Structure, Tech Stack, and Resources | Skipped if file already exists |
| `.editorconfig` | Editor formatting rules | Skipped if file already exists; refreshable with `--refresh-configs` |
| `.gitattributes` | Git line-ending and diff rules | Skipped if file already exists |
| `.markdownlint-cli2.jsonc` | Markdown linting configuration | Skipped if file already exists; refreshable with `--refresh-configs` |
| `.markdownlint.json` | Markdown linting rules | Skipped if file already exists; refreshable with `--refresh-configs` |
| `.markdownlintignore` | Markdown lint exclusion patterns | Skipped if file already exists; refreshable with `--refresh-configs` |
| `.yamllint.yml` | YAML linting configuration | Skipped if file already exists; refreshable with `--refresh-configs` |

Setup does not edit the project's `.gitignore`. In a Git repository it writes one block, between
`# OwlBear agent workspace (setup/init.py) — begin` and `— end`, into the local exclude file that
`git rev-parse --git-path info/exclude` names (worktrees included). The block lists each file and
directory setup created, so `git status` shows nothing new; when `.owlbear/` already existed it
also keeps OwlBear's runtime files there (scratch, knowledge and memory databases, vectors, Delivery
runtime folders and lock files) out of Git. Reruns replace the block rather than adding another.
A file Git already tracks cannot be hidden; the list before the question marks it
`tracked: your change will show as modified`. Outside a Git repository setup hides nothing.

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

Setup does not create Delivery state, worktrees, or Delivery settings; OwlBear keeps those under
`~/.owlbear/` ([What OwlBear Installs](#what-owlbear-installs)).

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

- **Shared live surfaces:** `share/agents/`, `share/skills/`, `share/instructions/`, and
  `share/prompts/` stay in the OwlBear runtime and are read live by VS Code.
- **Copied runtime surfaces:** files under `seed/` are copied into your project by `init.py`; this
  includes `.owlbear/hooks/` and project-local editor/runtime configuration.

This split is why an OwlBear update changes shared agents and skills immediately, while copied
runtime files may need a later `init.py` run to refresh. The update also changes the Memory,
Knowledge and Browser server code that their next start runs
([Upgrading OwlBear](#upgrading-owlbear)).

## Refreshing Consumer Configs

Rerunning `init.py` preserves existing editor and lint configuration so project-specific changes
are not overwritten. The refreshable files are `.editorconfig`, `.markdownlint-cli2.jsonc`,
`.markdownlint.json`, `.markdownlintignore`, and `.yamllint.yml`.

From the consumer project root, check for missing or customized files without changing them:

```shell
uv run --project ~/.owlbear/runtime python ~/.owlbear/runtime/setup/init.py --check-configs
```

The command exits successfully when the files match the owlbear seed and exits with status 1 when
one or more files are missing or different. To intentionally replace those five files with the
current seed versions, run:

```shell
uv run --project ~/.owlbear/runtime python ~/.owlbear/runtime/setup/init.py --refresh-configs
```

`--refresh-configs` asks the same question before writing unless you add `--yes`. It does not
overwrite `.github/copilot-instructions.md`, hook files, or other project-specific files that are
outside the refreshable set.

## Uninstalling

### Removing OwlBear from your Mac

1. On the page, press **Pause Delivery**, then **Pause and stop when idle**, and wait until
   `owlbear status` reports `OwlBear is not running`. Plain `owlbear stop` stops the host but lets
   running agent steps finish on their own, and deleting their folders under them loses their work.
2. Remove the command link, the shaping agent links, the completion and the login item:

   ```shell
   owlbear uninstall
   ```

   **Expected result:** one `removed ...` line per link; the runtime and every project stay.
3. In each project, delete the `owlbear-delivery` entry from `.mcp.json` and
   `chat.defaultToCopilotHarness` from `.vscode/settings.json` if setup wrote them, and their lines in
   `.git/info/exclude`.
4. To remove everything, delete `~/.owlbear`. This deletes every project's Delivery state and
   cannot be undone; your projects' own files, branches and pull requests stay.

To stop serving only one project, use **Remove project** on its page. OwlBear forgets the project
and deletes nothing; its clone keeps its id.

### Removing the agent workspace from a project

To remove the OwlBear setup from a consumer project, run this command from the project root:

```shell
uv run --project ~/.owlbear/runtime python ~/.owlbear/runtime/setup/init.py --uninstall
```

An interactive terminal asks for confirmation and prints the files it removes or updates. Preview
the plan without changing files by adding `--dry-run`. A non-interactive uninstall requires
explicit confirmation:

```shell
uv run --project ~/.owlbear/runtime python ~/.owlbear/runtime/setup/init.py --uninstall --yes
```

**Expected result:** an interactive run asks before changing anything; `--dry-run` reports the
planned removals without mutation; `--yes` applies the receipt-backed cleanup without prompting.

The command uses `.owlbear/install-manifest.json` to distinguish surfaces created by setup from
files that existed before it ran. A receipt-owned file is removed only when its installed digest is
unchanged. Receipt-claimed settings and MCP values are removed only when the complete merged file
still matches the post-install digest; later edits, including JSONC comments, preserve the whole
file. Uninstall removes the OwlBear block from the local exclude file when it still holds the lines
the receipt records, leaving your other exclude lines; an edited block stays. The managed
`.gitignore` section that older installs wrote is removed by its recorded line additions, so
unrelated rules remain.
Freshly created editor and lint configuration files are removed; pre-existing files remain even
when their content happens to equal the seed. Setup-created empty directories are removed only when
the receipt records them as created.

If the receipt is absent, uninstall takes the conservative path and preserves recognized surfaces;
it refuses to operate in a directory with no receipt or recognizable OwlBear surface. It also
refuses the OwlBear checkout and any descendant of that checkout. A non-interactive call requires
`--yes` or `--dry-run`, as setup itself does; `--check-configs` takes neither.

Custom seed files, unrelated VS Code settings and MCP servers, custom ignore rules, Delivery
state, runtime data, knowledge and memory data, and user-local VS Code profile settings are
preserved. In particular, uninstall does not revert the global Copilot reasoning settings that
interactive setup may have written; those settings are shared across projects and remain under the
user's control.

**Expected result:** unchanged setup-owned files and claimed settings or MCP entries are removed or
updated, while customized files, unrelated configuration, Delivery state, runtime data, knowledge,
memory, and user-local profile settings remain in place.

MCP memory entries are markdown files in the project's folder of the shared data repository (`<folder>/memory/`),
with Global memory at that repository's `memory/`; a workspace no folder there claims keeps them in
`.owlbear/memory/` ([memory server configuration](../serve/memory-mcp/README.md#configuration)). The
`owlbear-memory` server creates the directory when it starts, so setup does not seed a memory store.

---

## Delivery Workflow

OwlBear's pages run Changes; open them at the address `owlbear status` prints.

1. **New Change** on the Changes page opens a shaping chat in VS Code. When several projects are
   shown, it asks which one first. The chat asks what it needs and saves a brief.
2. Approve the brief on the Changes page. OwlBear plans, builds and reviews the Change in its own
   worktrees and publishes it as a pull request.
3. When a Change waits for you, its status says why, with **Answer** for a question or
   **Approve merge** for merge consent.
4. Once the pull request's checks and your branch rules pass, OwlBear merges it and the Change
   shows as done.

The other pages serve the same projects:

| Page | What it holds |
| --- | --- |
| Backlog | Improvement ideas and findings, kept as issues in the shared settings repository |
| Memory | Agent memory per project and Global memory that every project's agents read |
| Settings | Settings for this project, this machine, and all projects |
| Maintenance | Maintenance actions and their runs, such as the test review, and agent use |

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

To register your local agent directory, add to `.vscode/settings.json`. Keep the OwlBear entry
that setup wrote: a relative path to `~/.owlbear/runtime`, shown here for a project at
`~/Projects/app`:

```json
{
  "chat.agentFilesLocations": {
    "../../.owlbear/runtime/share/agents": true,
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
