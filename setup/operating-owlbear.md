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
| Back up what only this Mac holds | [Backing Up](#backing-up) |
| Run a Change from idea to merge | [Delivery Workflow](#delivery-workflow) |
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
| `design-pack/` | Impeccable, the pinned design skills and detector Delivery's design checks use; the folder keeps its name from before the rename |
| `machine.json` | The registered projects and the machine's settings |
| `data/` | The [shared settings repository](#the-shared-settings-repository)'s checkout, unless you set one elsewhere; updates and uninstalling never delete it |
| `data.json`, `data.lock` | Which shared settings repository OwlBear uses and where it is cloned from, and the lock held while that changes |
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
| `.mcp.json` | The `owlbear-memory` server, with its own yes, so New Change's shaping chat recalls and saves memory |
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
| `owlbear status` | Its address, pause, projects, shared settings repository, and login item |
| `owlbear logs [-n N]` | The end of its log |
| `owlbear doctor` | Checks Git, the GitHub CLI and its sign-in, uv, the Copilot CLI, whether the login item's saved PATH and `COPILOT_CLI_PATH` find them, whether the shared settings repository can be used, and each project's readiness, with the fix |
| `owlbear update` | Runs updates now |
| `owlbear versions [--prepare]` | The version it runs and the one it would take next; `--prepare` installs and checks that one without switching |
| `owlbear impeccable [--install]` | Shows the Impeccable this version pins; `--install` downloads and verifies what is missing. `owlbear design-pack` is its old name, kept so versions from before the rename can install it |
| `owlbear autostart on` or `off` | Starts OwlBear at login, or not; `on` saves this shell's PATH and `COPILOT_CLI_PATH` as they are now, so run it again after adding or removing a tool or Node version |
| `owlbear setup --repo PATH` | Checks a project's readiness, confirms its profile and registers its chat server |
| `owlbear data` | Shows the shared settings repository and what only this Mac's checkout of it holds |
| `owlbear data URL` | Clones that repository into `~/.owlbear/data`, or adopts the checkout of it already in use or there |
| `owlbear data PATH` | Uses a checkout you keep elsewhere instead of `~/.owlbear/data` |
| `owlbear data --move [DEST]` | With OwlBear stopped, moves the checkout to DEST, by default `~/.owlbear/data`; see [Moving it](#moving-the-shared-settings-repository) |
| `owlbear home` | Shows OwlBear's folder on this Mac |
| `owlbear prepare --repo PATH` | Before a reboot: binds the clone's store id and records its boot session with a format fence. Nothing is copied or switched; refused while any legacy producer is unfenced, and refused with no changes when the clone holds no legacy store to move (its store is already external or new, or a move already completed) |
| `owlbear finish --repo PATH` | After a reboot, from a different boot session: proves the preparation and moves the store to its folder. The clone's old store is kept in place as a non-authoritative source, not deleted |
| `owlbear install`, `owlbear uninstall` | Adds or removes the command link, the shaping agent links and the login item |

`owlbear --help` lists every command, including the project commands that take `--repo PATH`.

Moving a project's store to its folder is manual and needs a reboot: run `owlbear prepare --repo PATH`, reboot, then run `owlbear finish --repo PATH` from the new boot. Prepare records durable preparation and installs the format fence, but copies or switches nothing. Finish refuses an unknown or dirty OwlBear build, a changed or split install, and an unchanged boot, and it never runs on its own. The clone's old store payload is non-authoritative, but that does not make the whole directory deletable: startup still needs the clone id, the SWITCHED receipt, and the bound directory identity at the original source path. A backup does not make deleting, renaming, or recreating that directory safe, and there is no cleanup command.

The fixed gate contracts are maintained in the `state_store/legacy_family` tables. Historical build tables stay
fixed; refresh only CURRENT literals against the composed source, including critical delegated controls, when that
source changes, and record why. A function digest excludes its leading docstring; a whole-module digest includes
the entire syntax tree, including docstrings. The CURRENT file set remains the union of its literal tables, not
an arbitrary import closure. There is no switch that skips these checks.

Format markers must be regular files. Registration, store reads and selfcheck report unreadable or nonregular
markers without following a marker link or waiting on a pipe; only a genuinely missing entry counts as absent.
Missing target markers are created exclusively; a concurrent existing marker is validated and made durable,
never replaced. Ordinary admission and Finish revalidate authority after reading an absent target marker and before
creating it, leaving both a replaced target and the detached original untouched on refusal.
Settlement and admission validate the complete preparation and original source identity through
held descriptors. Repeated Prepare refuses a completed move or malformed receipt, even while its backup payload remains.
Prepare rechecks the exact source marker and preparation after id synchronization and immediately before publishing
either metadata file; a changed or blank marker refuses without replacing the owner's entries. Read-only switched-store
lookups validate the target's identity, issued proof, quarantine state and existing marker through a held descriptor;
they recheck its named directory after those reads and leave an absent target marker for store open to repair.
Current lookup, registration and selfcheck keep the retained source descriptor through target validation and
recheck the source's named directory before accepting its receipt. Unreadable UTF-8 enters the normal diagnostic channel.
Selfcheck keeps both authority observations through its remaining project-marker and settings reads; a late witness
change reports a problem instead of a compatibility pass, without opening or migrating the store.
Source witness images and the held target's proof and marker must stay stable across later validation reads.
Quarantined target entries are checked again, but ordinary active-store atomic writes remain valid: directory
timestamps alone are not authority. A witness change refuses without replacing owner state; a newly installed newer
marker keeps its upgrade diagnostic. These are bounded read-set checks, not an atomic filesystem snapshot.
Source and target payload checks retain every descendant's image through the final witness reads. Initial target
validation also confirms those images before writing its marker; later sibling reads cannot hide an earlier edit.
After a validated switch, selfcheck checks the active store's settings rather than the retained backup's
`config.json`; the source's identity, receipt and fence remain required.
A failed project load whose target cannot be proven retains an unlocated maintenance reservation, rather than taking
an absent run record in that target as evidence that nobody owns the work.
The same reservation is kept when the source fence is unreadable, missing or newer than this runtime. Ordinary
store opens recheck source preparation, format and clone id plus target proof after making markers durable, and
guard the source-fence replacement after its temporary file is synced. Active-store edits remain valid: opening
does not compare them against the historical copied payload. Registration and adoption retain the id their
authority check admitted through id synchronization and revalidate before recording it.
Canonical registration keeps marker, ID and receipt image stamps under a held clone directory through its remaining
reads, even without a move receipt. A late newer marker refuses without overwriting it or publishing the registry.
Registration also holds the local `.git`, linked-worktree and repository-config binding images through those reads;
directory aliases and control-file symlinks retain their resolution chains and referent images too. Redirecting
either refuses rather than publishing the cached clone; an unchanged symlink layout remains supported.
The move receipt is part of the retained observation, not just an earlier lookup: replacing it during target
validation or temporary-file synchronization refuses without overwriting the owner's receipt. Registration and
adoption also guard the registry's final replacement after its temporary file is synced, leaving the previous
registration intact when the admitted clone changes.

**Pause Delivery** in the bar stops new automatic agent steps on every project until you press
**Resume**; your own actions, such as settings, memory and **New Change**, still run. While paused,
**Pause and stop when idle** stops OwlBear once the running steps end. Automatic memory curation
after a merge and when idle each has its own setting in **Settings → This machine**: off, on, or on
even while paused; **Curate now** on the Maintenance page always runs.

Retro looks back at finished work: it grades the Spotter's records against what happened later and
proposes cases, lessons and fixes, each challenged before you see it. Its two switches sit beside
curation's and work the same way: `retro_after_change` for a Change that ended, and `retro_when_idle`
for chats in the folders listed in `enrolled_chats`, once a chat has been quiet for a day and only
while OwlBear is idle. Each run stops at `retro_run_credit_limit`. `owlbear improvement retro run`
with `--change PROJECT/SLUG`, `--chat SESSION` or `--synthetic [NAME]` queues a run for the machine
host (one per synthetic unit), even while paused or switched off; `owlbear improvement retro status` lists the latest runs,
and `--plan UNIT` shows how many judging calls a run would make, without spending credits.

The **Metrics** page shows every credit OwlBear spent on this Mac: every agent session it ran
(Delivery's workers, judges, picker and lookups, the curator, Impeccable runs, Spotter looks, Retro),
summed, split by project, agent (subagents included), model, day, Change or step, and filtered by
period, project, agent, model, Change, or runs stopped at their credit limit. Each session writes
its start and end to `~/.owlbear/spend/`, kept for good, even when it is cancelled or fails;
earlier spend is read from the Changes, the Spotter's records and the runtime's own logs. Credits
that were not reported count as unknown, never as zero, and spend whose day or agent is not known
closely is said apart. Metrics never limit any work. Your own chats' spend is not recorded.

### The shared settings repository

A shared settings repository is a Git repository you choose for project settings, agent memory and
the backlog. When one is set, they live in its checkout on this Mac, and OwlBear commits and pushes
each save, so they follow you across clones and machines. Without one, they stay on this Mac in
`~/.owlbear/projects/<id>/`.

- `owlbear data URL` clones it into `~/.owlbear/data`. A checkout already there, or the one this Mac
  already uses, is adopted when it is a checkout of the same repository, and refused otherwise; it is
  never cloned twice.
- `owlbear data PATH` uses a checkout you keep elsewhere instead; that setting wins over
  `~/.owlbear/data`.
- Run `owlbear restart` after either. Each start adopts a checkout found at `~/.owlbear/data` when none
  is set, and when a clone was asked for but did not finish, tries it again in the background every 10 minutes.
- `owlbear status` names the checkout in use and whether it is the default or your own;
  `owlbear status`, `owlbear doctor` and `owlbear data` say when it cannot be used, and why.
- Updates, `owlbear uninstall` and removing an old version never delete it, wherever it is.

#### Moving the shared settings repository

`owlbear data --move [DEST]` moves the checkout this Mac uses to DEST, by default `~/.owlbear/data`,
and points OwlBear at it. It keeps everything the checkout holds: files not committed, commits no
remote has, stashes, and its linked worktrees elsewhere, which it repairs to point at the new place.
It lists them before the move and checks them after it.

1. Stop OwlBear with `owlbear stop`, and end the chats whose OwlBear servers use the repository
   (memory, Delivery). The move refuses while any OwlBear process or a project's recorded runner
   could still write it, and says which.
2. Run `owlbear data --move`.

   **Expected result:** `moving ...` with what only this Mac holds, then
   `moved: the shared repository is now ...`.
3. Run `owlbear start`.

A move only renames, so DEST must be on the same disk and must not exist. If the repair of a linked
worktree fails, the move stops with the reason and nothing reads either copy until you fix it and run
`owlbear data`, which finishes the move.

OwlBear's code ships no settings defaults: every model, effort, limit and switch comes from the
global settings in the shared repository, this machine's, or the project's. A setting no layer
sets shows as unset on the Settings page, and a step that needs it asks you to fill it in;
automatic memory curation does not start until its role and threshold are set. A new machine that uses your
shared repository takes its global settings; one without starts with every setting unset. Nothing
lies under the global settings, so with the Global layer chosen the page names the choice that
clears a value Unset and warns while a needed one is unset.

Three of them, in **Settings → Your instructions, skills and memory**, decide whether Delivery's agent steps
also use your own Copilot files from `~/.copilot` (or `$COPILOT_HOME`) and Copilot Memory. **Your instructions in
Delivery steps** keeps your instruction files there, each entry of `instructions/` and
`copilot-instructions.md`, links followed, beside the repository's. **Your skills in Delivery
steps** offers each skill in `skills/` beside the step's own; none is preloaded, and one named as a
Delivery skill or as the shaping skill is left out. Off, a step reads only its worktree's
instruction files and Delivery's skills. A plugin's instructions, any other instruction source
outside the worktree and your agents stay off either way.

**Copilot Memory in Delivery sessions** on lets every Delivery session recall the memories Copilot keeps for the
repository, and lets the planner, preparer, builder, updater and test curator save a new one or vote on one; other
roles are refused a save. The Spotter and Retro never use it. A memory a step saves this way skips OwlBear's memory
curation and reaches your later hand-run chats in that repository, so off is recommended: steps still have OwlBear's
own memory either way.

None of the three has a default: while one is
unset, a Change's step asks you to set it before its session starts, and an Impeccable update or
automatic memory curation ends without starting one; the shaping chat and the Spotter do not need
them. Right after the first install of a version that adds one, choose the Global layer, set
it (off for Copilot Memory, as recommended), and save.

The machine settings in **Settings → This machine** (versions, updating itself, curation per
trigger, sessions at once) work the same way: each machine follows the global ones, which you
edit there with the Global layer chosen, unless it sets its own, which you set with the This
machine layer chosen; with a project chosen they show read-only, as in use. Each start of OwlBear first
brings the shared repository up to date, so a machine follows what another one saved. With one unset in both, the
machine does not update by itself, curate automatically or start agent sessions. The first start
after this change moves the values in `machine.json` into the global settings where those have
none, then clears them, so every machine follows Global; a later machine copies nothing. Until
that is published (the shared repository is offline, or Global has an edit you have not saved),
**Settings → This machine** says why, the machine keeps its own values, and the next start tries
again. If another machine changed the global settings meanwhile, nothing is undone for you: the
page names the shared repository, where you publish or undo this machine's change by hand.

## Upgrading OwlBear

OwlBear's versions are Git tags such as `v1.0`. OwlBear installs a new version beside the running
one, checks it, and switches only while nothing runs; it never moves to an older version.

- By default it takes every new minor version after 15 minutes without use, announced on open
  pages 2 minutes ahead. **Settings → This machine** chooses major versions only, and whether it
  updates when idle or while paused.
- **Run updates now** on a paused page, or `owlbear update`, updates at once.
- After an update, the pages say once which version OwlBear now runs. Open chats keep their
  Delivery tools: a chat's `owlbear-delivery` server reads and writes nothing itself, and asks the
  host in a chat contract that later versions keep serving. With Delivery stopped, its tools say so
  and read nothing. A chat whose server the host no longer serves answers `OwlBear does not serve
  this chat's …`, and one started before OwlBear had the chat contract answers `OwlBear updated: …`
  once more: start a new Copilot-runtime chat, or focus that chat and use **MCP: List Servers** →
  `owlbear-delivery` → **Stop Server**, then **Start Server**. Neither the agent host nor the window
  needs restarting; a window reload does not restart that runtime's tool servers. A chat whose
  server is newer than the running host says so: let the update finish, or run `owlbear restart`.
- OwlBear's memory, knowledge and browser servers run from the installed version too
  (`python -m owlbear_delivery_next serve memory`, through `~/.owlbear/runtime`): each keeps the
  version it started with until its chat ends or you stop and start it, and no update removes that
  version while it runs. Chats started before and after an update can thus use two versions of a
  server over the same memory and knowledge stores, so a version that changes how they store data
  must read and write what the versions still running write, with tests that an older server's
  writes survive.

---

## Backing Up

What only this Mac holds lives in `~/.owlbear/`:

- The shared settings repository's checkout: `~/.owlbear/data`, or the folder `owlbear data` names.
  Whatever it pushed is safe on its remote; `owlbear data` lists what only this checkout holds
  (files not committed, commits no remote has, stashes, linked worktrees elsewhere), so back those up
  with it.
- `data.json` and `machine.json`: the shared repository's place and remote, and the registered projects.
- `projects/<id>/`: each project's Delivery state, which no remote holds.

Before you copy, stop everything that writes there. On the page, press **Pause Delivery**, then
**Pause and stop when idle**, and wait until `owlbear status` reports `OwlBear is not running`; plain
`owlbear stop` lets running agent steps go on writing. Then end the chats whose OwlBear tools
(decisions, memories) use the shared repository.

---

## Uninstalling

### Removing OwlBear from your Mac

Before you start, run `owlbear data`. If it names a checkout inside `~/.owlbear` other than
`~/.owlbear/data` (an older setting), move it there with `owlbear data --move` while OwlBear is still
installed; step 4 keeps only `~/.owlbear/data`.

1. On the page, press **Pause Delivery**, then **Pause and stop when idle**, and wait until
   `owlbear status` reports `OwlBear is not running`. Plain `owlbear stop` stops the host but lets
   running agent steps finish on their own, and deleting their folders under them loses their work.
2. Remove the command link, the shaping agent links, the completion and the login item:

   ```shell
   owlbear uninstall
   ```

   **Expected result:** one `removed ...` line per link, then `kept: your shared data at ...` with
   what only that checkout holds; the runtime, every project and the shared data stay.
3. In each project, delete the `owlbear-delivery` and `owlbear-memory` entries from `.mcp.json` and
   `chat.defaultToCopilotHarness` from `.vscode/settings.json` if setup wrote them, and their lines in
   `.git/info/exclude`.
4. To remove everything else, delete everything in `~/.owlbear` except `data`:

   ```shell
   find ~/.owlbear -mindepth 1 -maxdepth 1 ! -name data -exec rm -rf {} +
   ```

   This deletes every project's Delivery state and cannot be undone; your projects' own files,
   branches and pull requests stay. The shared settings repository's checkout in `~/.owlbear/data`
   is kept on purpose, and one you set elsewhere is not touched. Delete it yourself only after backing
   up what step 2 listed as only there.

To stop serving only one project, use **Remove project** on its page. OwlBear forgets the project
and deletes nothing; its clone keeps its id.

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

Cleanup verifies the preservation of work held only in a Change's worktree before removing it.
Archives retain regular-file permissions and symbolic links, including dangling links, without
following their targets. If an entry cannot be represented safely, such as a nested Git
repository, cleanup stops and leaves the worktree intact. Copy that work elsewhere or explicitly
remove the unsupported entry before retrying; a verified archive must not be assumed to contain
an entry that cleanup refused.

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

Place `.agent.md` files in the project's `.github/agents/`, which VS Code reads without any setting.
To keep them elsewhere, register that folder in `chat.agentFilesLocations` in `.vscode/settings.json`:

```json
{
  "chat.agentFilesLocations": {
    ".owlbear/agents": true
  }
}
```

Use names other than `owlbear-shaper`: VS Code lists same-name agents from different locations side
by side.

### Overriding instructions

Edit `.github/copilot-instructions.md` to add project-specific rules. This file is
auto-detected by VS Code and takes priority over repository-level instructions. You can
also add a `*.instructions.md` file in your project and register its directory in
`chat.instructionsFilesLocations`.

### Adding project-specific MCP servers

Add servers to the project's `.mcp.json`, beside the entries setup wrote:

```json
{
  "mcpServers": {
    "owlbear-delivery": { ... },
    "myProjectServer": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "-m", "my_project_mcp_server"]
    }
  }
}
```

Running setup again rewrites only its own entries and keeps yours.

### Memory MCP storage

MCP memory entries are markdown files in the project's folder of the shared data repository (`<folder>/memory/`),
with Global memory at that repository's `memory/`. Setup offers the memory server only once a folder there holds
the project; OwlBear's own repository, which no folder claims, keeps them in `.owlbear/memory/` ([memory server configuration](../serve/memory-mcp/README.md#configuration)). The
`owlbear-memory` server creates the directory when it starts.

### Knowledge MCP storage

The `owlbear-knowledge` server stores its SQLite database and vectors under
`.owlbear/knowledge/` in the current workspace. Launch it from the project root; it has no storage
override or tool-exclusion environment settings. The runtime leaves out the embedding and Qdrant
extras, so vectors are only written and searched where `owlbear-knowledge[embedding,qdrant]` is
installed; elsewhere those calls fail with `embedding_dependency_missing`.

---

When something does not behave as described here, use
[Troubleshooting](setup-guide.md#troubleshooting) in the setup guide.
