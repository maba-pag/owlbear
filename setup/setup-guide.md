# OwlBear Setup Guide

> From clone to a running OwlBear, one added project and one completed change.

This guide owns installation and first success. Day-to-day operation, updates, uninstall, and
customization live in [Operating OwlBear](operating-owlbear.md); teammate and multi-project
workflows live in the [sharing guide](sharing-guide.md).

## Prerequisites

OwlBear supports macOS only. Linux and Windows are not supported yet; the `owlbear` command stops
on them with `OwlBear runs on macOS only for now`.

Before running setup, ensure the following are installed on your Mac:

| Requirement | Why | How to get it |
| --- | --- | --- |
| Python 3.14.8 | OwlBear runtime; OwlBear supports the 3.14 series only | [python.org](https://www.python.org/downloads/) |
| [uv](https://docs.astral.sh/uv/) | Installs OwlBear's dependencies and launches its tool servers | [Installation guide](https://docs.astral.sh/uv/getting-started/installation/) |
| Git, with `user.name` and `user.email` set | Clone, and the commits of each Change | [git-scm.com](https://git-scm.com/) |
| [GitHub CLI](https://cli.github.com/), signed in (`gh auth login`) | Pull requests; needs push access to your project | [Installation guide](https://cli.github.com/manual/installation) |
| GitHub Copilot CLI | Runs OwlBear's agent sessions | `brew install --cask copilot-cli`, or set `COPILOT_CLI_PATH` to its absolute path |
| VS Code | New Change's shaping chat opens there | [code.visualstudio.com](https://code.visualstudio.com/) |
| GitHub Copilot extension | Chat and agents | VS Code Extensions marketplace |

Install the Copilot CLI with Homebrew, not `npm install -g`: a Node version manager such as fnm or
nvm keeps global npm packages per Node version, so switching Node hides that copy. VS Code's
`copilot` launcher then answers on `PATH` and asks whether to install the CLI, which a background
session cannot answer; OwlBear skips it and reports the CLI as missing.

If your Git configuration signs commits, OwlBear checks that the signing key is usable before it
works on a project.

---

## Quick Start

This is the complete first-time path. OwlBear installs once per Mac into `~/.owlbear/runtime` and
serves every project you add; your projects stay where they are.

### 1. Clone OwlBear into its runtime folder

```shell
git clone https://github.com/maba-pag/owlbear.git ~/.owlbear/runtime
cd ~/.owlbear/runtime
uv sync --locked
```

**Expected result:** `~/.owlbear/runtime` holds the OwlBear checkout on `main`, its default branch,
with its environment in `~/.owlbear/runtime/.venv`.

### 2. Install the command

```shell
.venv/bin/owlbear install
```

It writes the zsh completion to `~/.owlbear/completion.zsh` and names the line to add to `~/.zshrc`
if you want it. Then it asks three separate questions:

1. Link `~/.local/bin/owlbear`, so `owlbear` runs in any shell.
2. Link the shaping agent and its skill into `~/.copilot`, so **New Change** finds them. Answer yes;
   New Change needs them.
3. Start OwlBear at login, paused until you press **Resume**.

**Expected result:** each answer is confirmed in one line, such as `linked ~/.local/bin/owlbear`.
If `~/.local/bin` is not on your `PATH`, the command says so. Until it is, use
`~/.owlbear/runtime/.venv/bin/owlbear` wherever this guide writes `owlbear`.

### 3. Start OwlBear

```shell
owlbear start
```

**Expected result:** `OwlBear started, running: http://127.0.0.1:<port>/#token=…`. Open that
address; `owlbear status` prints it again. OwlBear listens only on this Mac's loopback address, on a
free port it picks at start. If the login item already started it, it runs paused: the bar at the top
says **Delivery is paused**; press **Resume** so your Changes advance.

If you keep project settings, agent memory and the backlog in a shared settings repository, set it
now, before adding projects; skip this otherwise:

```shell
owlbear data https://github.com/OWNER/SETTINGS.git
owlbear restart
```

OwlBear clones it into `~/.owlbear/data`, or adopts a checkout of it already there. See
[The shared settings repository](operating-owlbear.md#the-shared-settings-repository).

### 4. Add your project

On the page, open **Add project** in the bar at the top, enter the folder of your project's clone
and press **Add**. Adding a project here is the only way OwlBear starts serving it; opening the
project in VS Code never starts or changes OwlBear.

**Expected result:** the project appears in the project selector and its Changes page opens.

### 5. Connect the project's chats

If the page shows **Setup required**, run the command it names in a terminal, for example:

```shell
owlbear setup --repo ~/work/my-project
```

Setup checks readiness and stops at the first problem with a `Next:` line naming the fix. Then it
shows the detected project profile, asks for anything unknown and asks you to confirm it. Last, it
asks before each of three local writes: the Delivery chat server in `.mcp.json`, the memory server
New Change's shaping chat recalls and saves memory with, also in `.mcp.json`, and
`chat.defaultToCopilotHarness` in `.vscode/settings.json`.

**Expected result:** `Profile vN confirmed and saved`, then one
`written: <project>/.mcp.json (kept out of git by .git/info/exclude)` line per server and the same
line for the settings file. Reload the project's VS Code window; the **Setup required** note
disappears.

The `.mcp.json` entries name OwlBear's Python through `${HOME}` and no project path: VS Code and the
Copilot CLI start them in the project folder, so they serve whichever project they sit in.

Setup never writes a file Git tracks. For a tracked `.mcp.json` it prints the Delivery server entry
to add instead, under `"servers"` with **MCP: Open User Configuration** or under `"mcpServers"` in Copilot's
shared `~/.copilot/mcp-config.json` (`$COPILOT_HOME/mcp-config.json` when that is set); that entry names the
project with `--repo`, because a user-level server has no project folder of its own. The page counts an entry in
either file only with exactly one `--repo PATH` or `--repo=PATH` naming the project; setup reads these files and
never writes them. An MCP file it can't read or parse is named on the project's line on the page, with the error,
and in the host log. The memory server has no such
fallback: without it the shaping chat works on without memory. Setup offers it only once a folder in the
shared data repository holds the project, because that folder is where the memory lives; without one it
prints `Memory server not registered:` and the reason.

## Verify the installation

1. Run `owlbear status`.

   **Expected result:** `OwlBear is running: <address>`, your project listed as `loaded` with its
   path, and the login item's state.
2. Run `owlbear doctor`.

   **Expected result:** `all checks passed`. Otherwise each line names a problem and its fix.
3. Open the project's Changes page.

   **Expected result:** no **Setup required** note, and **New Change** is available.

## First successful workflow

After verification, prove the installation with one small outcome on the Changes page:

1. Press **New Change** and describe the outcome in the shaping chat it opens in VS Code.

   **Expected result:** the chat asks what it needs and saves a brief for your approval.
2. Approve the brief on the Changes page.

   **Expected result:** OwlBear plans, builds, reviews and publishes the Change as a pull request;
   when it needs you, it asks on the Changes page.
3. When the Changes page asks you to approve the merge, review the pull request and approve it
   there, or merge it in GitHub. Once checks and branch rules pass, OwlBear merges on its own.

   **Expected result:** the Change shows as done.

See [Delivery Workflow](operating-owlbear.md#delivery-workflow) for daily operation.

---

## Troubleshooting

| Symptom | Likely cause | Resolution |
| --- | --- | --- |
| `owlbear: command not found` | The link was declined or `~/.local/bin` is not on `PATH` | Use `~/.owlbear/runtime/.venv/bin/owlbear`, or add `~/.local/bin` to `PATH` |
| `run this from the installed runtime` | `owlbear install` ran from another checkout | Run `~/.owlbear/runtime/.venv/bin/owlbear install` |
| `OwlBear ended at once` or `did not answer` after `owlbear start` | The host failed to start | Read `owlbear logs` (the end of `~/.owlbear/host.log`) |
| Setup prints a `FIX` line | A readiness check failed | Apply the fix on its `Next:` line, then run `owlbear setup --repo PATH` again |
| A project shows as failed on the page | Its folder or store could not be loaded | Read the reason shown beside it; `owlbear doctor` names each project's fix |
| **New Change** opens no shaping chat | The shaping agent is not linked into `~/.copilot` | Run `owlbear install` again and answer yes to the shaping agent |
| `owlbear install` says `not done, no terminal to answer` | It ran without a terminal, for example from an agent; nothing was linked or added | Run `owlbear install` yourself in a terminal |
| The Copilot runtime in VS Code 1.143 offers only Auto (and HydraFusion) | More than one GitHub account is signed in to VS Code, and the runtime uses the first one, which has no Copilot; the agent host's log says `Found 0 models` | Sign the other GitHub accounts out of VS Code (Accounts menu), then run **Restart Local Agent Host**; `gh` keeps its accounts |
| `not written: ... is tracked` from setup | The file is tracked in Git | Add the printed server entry with **MCP: Open User Configuration**, or under `"mcpServers"` in the shared file it names (`~/.copilot/mcp-config.json`, or under `$COPILOT_HOME`) |
| A project on the page says `... cannot be read: ...` | An MCP file setup checks isn't valid JSON or can't be opened | Fix or remove the named file; the line goes on the next refresh |
| MCP server fails to start | Its command, `~/.owlbear/runtime/.venv/bin/python`, is missing or lacks a package | Read the server's output (**MCP: List Servers** → the server → **Show Output**); check that interpreter exists, and for a missing module run `uv sync --locked --all-packages --all-groups` in `~/.owlbear/runtime` |

For deeper debugging, use **"Show Chat Debug View"** (Chat view ellipsis `…` menu) to inspect
raw LLM request/response payloads.

## Next

| You want to... | Go to |
| --- | --- |
| Know exactly what setup wrote, and how to undo it | [Operating OwlBear](operating-owlbear.md) |
| Update OwlBear | [Upgrading OwlBear](operating-owlbear.md#upgrading-owlbear) |
| Run Changes day to day | [Delivery Workflow](operating-owlbear.md#delivery-workflow) |
| Add project-local agents, instructions, or MCP servers | [Project-Specific Customization](operating-owlbear.md#project-specific-customization) |
| Set a teammate up on the same installation | [Sharing guide](sharing-guide.md) |
