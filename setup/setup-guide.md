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
asks before each of two local writes: the Delivery chat server in `.mcp.json`, and
`chat.defaultToCopilotHarness` in `.vscode/settings.json`.

**Expected result:** `Profile vN confirmed and saved`, then
`written: <project>/.mcp.json (kept out of git by .git/info/exclude)` and the same line for the
settings file. Reload the project's VS Code window; the **Setup required** note disappears.

Setup never writes a file Git tracks. For a tracked `.mcp.json` it prints the server entry to add
under `"servers"` with **MCP: Open User Configuration** instead.

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

## Optional agent workspace

OwlBear's shared agents, skills, instructions and prompts, and its Memory, Knowledge and Browser
tool servers, can be loaded into a project's VS Code workspace for your own Copilot chats. Delivery
does not need this. `setup/init.py` writes it into the project only after you agree, and hides the
files it creates from Git, so nothing shows as new.

Run setup through the runtime alias `~/.owlbear/runtime`. Setup writes its paths through that alias
rather than the version folder behind it, so OwlBear's self-updates keep them valid.

### 1. Open a terminal in the project root

```shell
cd ~/work/my-project
```

**Expected result:** `pwd` prints your project directory; OwlBear is installed in
`~/.owlbear/runtime` by the [Quick Start](#quick-start).

### 2. Run setup from the project root

```shell
uv run --project ~/.owlbear/runtime python ~/.owlbear/runtime/setup/init.py
```

Setup first lists every path it would create, merge into or replace, and the lines it would add to
the repository's local exclude file, then asks
`Write the OwlBear agent workspace into <project>? [y/N]`. Add `--dry-run` to see the list without
writing anything, or `--yes` to agree without the question; a non-interactive run without `--yes`
writes nothing and exits with status 1. After you agree, interactive setup may still ask about
differing hook files and user-local Copilot profile settings.

**Expected result:** setup creates or merges `.vscode/settings.json` and `.vscode/mcp.json` and
copies the project-local hooks and runtime templates. It lists the paths it created in one
OwlBear block of the repository's local exclude file (`git rev-parse --git-path info/exclude`), so
`git status` shows nothing new; it does not edit the project's `.gitignore`. A file Git already
tracks, such as a committed `.vscode/settings.json`, cannot be hidden: the list marks it
`tracked: your change will show as modified`. Outside a Git repository setup hides nothing and
says so.
The complete inventory is in
[What Setup Creates](operating-owlbear.md#what-setup-creates).

### 3. Open the project in VS Code

```shell
code .
```

**Expected result:** VS Code opens the project directory, not the OwlBear checkout. The shared
agents, skills, instructions, and prompts are loaded through `~/.owlbear/runtime`.

### 4. Confirm it loaded

1. Open Copilot Chat and run **Chat: Open Customizations**.
2. Confirm that OwlBear agents, skills, instructions, and prompts are listed.
3. Run **MCP: List Servers** and confirm these four servers show `running`:
   `owlbear-knowledge`, `owlbear-memory`, `owlbear-browser`, and `markitdown`.

**Expected result:** the four seeded MCP server processes are running and the shared OwlBear
customization roots appear in Chat Customizations. Browser capability readiness is a separate
check below because it also depends on the selected browser and its allowlist.

If a customization root is missing, inspect `.vscode/settings.json` and compare its relative
OwlBear path with the location of `~/.owlbear/runtime`. If a server is missing, inspect `.vscode/mcp.json`,
run `uv sync --locked --all-packages --all-extras --all-groups` in `~/.owlbear/runtime`, and rerun
setup from the project root.

Chromium is optional. Install it when you select Browser MCP Chromium mode; the default managed Edge
mode needs stable Microsoft Edge.

### Browser readiness

Check MCP startup, browser capability, and Knowledge ingestion separately. A running MCP process
does not prove that the selected browser launched, that a target is authenticated, or that a
Browser-to-Knowledge round is ready.

1. **MCP process startup:** Run **MCP: List Servers** and confirm `owlbear-browser` and
   `owlbear-knowledge` show `running`.

   **Expected result:** both stdio processes are available; this confirms startup only.
2. **Browser readiness:** An unset `BROWSER_MODE` selects managed Edge and its fixed OwlBear
   profile. Confirm stable Microsoft Edge is installed before starting the Browser MCP. For
   Chromium mode, install Chromium for the OwlBear runtime from
   the consumer project root:

    ```shell
    uv run --project ~/.owlbear/runtime playwright install chromium
    ```

   This download is not required for managed Edge mode. To select Chromium explicitly, set
   `BROWSER_MODE` to `chromium` in the local `owlbear-browser` server environment; an
   invalid mode is reported as `invalid-mode` rather than silently falling back to another browser.
   `PLAYWRIGHT_USER_DATA_DIR` only affects Chromium and should be an absolute path; managed Edge
   always uses `~/.owlbear/edge-profile` and ignores that override.

   Check `BROWSER_ALLOWED_DOMAINS` in the `owlbear-browser` entry of `.vscode/mcp.json`. The fresh
   seed uses `"*"` for local testing across public sites; use exact hostnames for normal or
   production use.

   Restart the `owlbear-browser` MCP server and call `browser_status`; it reports `not-launched`
   before any browser action. The first `acquire` or `navigate` call against an allowed URL launches
   the selected visible browser; complete the organization's login flow manually if needed.

    **Expected result:** `acquire` on an allowed URL returns rendered content or a structured
    acquisition result. `browser_status` reports `ready` while an OwlBear-owned window remains open;
    closing a shared page while another owned window remains open keeps it `ready`, and the next
    action reopens that page. It reports `not-launched` before first use or after the last owned
    window closes, and `unavailable` with a startup reason when launch fails. Readiness does not prove
    sign-in or authenticated access. Exact-host entries explicitly
   permit private, loopback, and link-local DNS results for that hostname; wildcard mode does not.
   Reserved and unspecified addresses are always rejected. The current SSRF preflight does not
   fully prevent DNS rebinding or an allowlisted server redirecting to a private address; these
   are accepted limits, so keep the allowlist narrow. See the
   [Browser MCP guide](../serve/browser-mcp/README.md) for the full policy.
3. **Managed SSO readiness:** The default is a visible managed Edge session using the
   fixed `~/.owlbear/edge-profile`; `PLAYWRIGHT_USER_DATA_DIR` and `SSO_EXTENSION_PATH` do not
   configure managed Edge. Call an allowed `navigate` or `acquire` action to launch the browser,
   then verify one permitted target site with the organization's normal login flow. Chromium mode
   uses a separate profile and can load only an explicitly configured extension directory. A ready
   browser or loaded extension is not proof of tenant authentication, MFA, Conditional Access, or
   device compliance. Do not collect cookies or tokens, weaken enterprise policy, or claim SSO
   support from MCP startup.
4. **Knowledge ingestion readiness:** Register an approved browser source with
   `register_knowledge_source` as `kind: "url_list"` and `fetch_method: "browser"`. Call
   `list_knowledge_sources` to get its `source_id` and registered `urls`; acquire each URL and
   submit the captures together in one bound `knowledge_ingest` call for that source. Call
   `list_knowledge_sources` again to check its health.

   **Expected result:** a fully successful round reports `ok`. See the
   [Knowledge operations guide](../share/skills/h-knowledge-ops/SKILL.md) for the source and
   capture contract, including other health outcomes.

See the [Browser-to-Knowledge vertical test](../tests/test_browser_knowledge_vertical.py) for the
exercised end-to-end workflow.

### Copilot profile settings

When setup runs interactively, it inspects VS Code's workspace profile association for the
consumer project directory that `setup/init.py` is initializing before changing any Copilot profile
data:

1. If a profile is associated with the project, setup shows the target and asks for confirmation.
2. If no profile is associated, setup explains that it will offer the default profile and asks for
  confirmation.
3. After confirmation, setup updates only the following model entries in that profile's
  `chatLanguageModels.json` file:

  | Model | Reasoning effort |
  | --- | --- |
  | `gpt-6-luna` | `max` |
  | `gpt-6-sol` | `high` |
  | `claude-opus-5.5` | `medium` |

The file is written atomically, unrelated profile entries are preserved, and a missing file or
Copilot entry is created minimally. Malformed profile JSON is left unchanged with a warning. To
target a named profile instead of the default fallback, open
the project in VS Code, run `Profiles: Switch Profile`, and rerun `setup/init.py`. Setup does not
take a profile-selection command-line argument. Noninteractive setup skips this user-local profile
mutation.

### Managed Mac browser pilot

Run this pilot on the managed Mac before relying on SharePoint or Confluence access. Keep the two
approved target URLs local; do not put URLs, hostnames, page content, credentials, or session files in
the repository or in a Change's brief, answers, or status.

1. Install stable Microsoft Edge and start the `owlbear-browser` MCP server. Leave
  `BROWSER_MODE` and `PLAYWRIGHT_USER_DATA_DIR` unset for the managed default. Configure
  `BROWSER_ALLOWED_DOMAINS` locally for only the two approved target hosts.

  **Expected result:** before any browser action, `browser_status` reports `managed-edge`,
  `per-user-owned`, `not-launched`, null startup reason, and unavailable visible authentication.
  Stop if the mode is invalid; do not switch to Chromium or the operator's daily Edge profile.
2. Call `acquire` with one locally supplied, operator-approved SharePoint URL. The first action
  launches the visible Edge window with the fixed OwlBear profile. Complete first-use sign-in, site
  trust, consent, or MFA directly in that window; no interactive MCP tool participates.
  Do not send credentials or session material through an OwlBear request or result.

  **Expected result:** the Edge window is live and the operator confirms authenticated SharePoint
  content. Browser readiness alone does not count as authentication.
3. Repeat the action with one locally supplied, operator-approved Confluence URL and confirm its
  authenticated content in the owned Edge window.

  **Expected result:** the operator confirms authenticated Confluence content in the same owned
  session; record no page content, URL, or hostname.
4. Close the last OwlBear-owned Edge window and call `browser_status`, then call `acquire` for one
  approved target. Closing only the shared page while another owned window remains open keeps status
  `ready`; the next `acquire` reopens that page without relaunching the browser.

  **Expected result:** status reports `not-launched` after the last owned window closes; the next
  `acquire` relaunches the fixed profile and the operator confirms the target remains authenticated.
5. Restart the `owlbear-browser` MCP server, repeat an allowed action for each target, and confirm
  that the fixed profile retains session availability. Stop the server normally afterward.

  **Expected result:** both targets remain authenticated after restart, no `--no-sandbox` or
  unsupported-flag warning appears, and only OwlBear-owned browser resources close. Record only each
  target class (`SharePoint` or `Confluence`) and `pass` or `fail`; include no URL, hostname, page
  content, credential, or session data.

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
| The Copilot runtime in VS Code 1.143 offers only Auto (and HydraFusion) | More than one GitHub account is signed in to VS Code, and the runtime uses the first one, which has no Copilot | Sign the other GitHub accounts out of VS Code (Accounts menu), then run **Restart Local Agent Host**; `gh` keeps its accounts |
| `not written: ... is tracked` from setup | The file is tracked in Git | Add the printed server entry with **MCP: Open User Configuration** |
| Agents not appearing in picker (agent workspace) | Wrong path in `chat.agentFilesLocations` | Run **Chat: Open Customizations**; verify the path relative to project root matches owlbear location |
| Skills not auto-loading | `chat.agentSkillsLocations` missing or path wrong | Check `.vscode/settings.json`; re-run `init.py` if the key is absent |
| Instructions ignored | `chat.instructionsFilesLocations` missing | Check `.vscode/settings.json`; verify `*.instructions.md` files exist in the registered directory |
| MCP server fails to start | Missing dependency or `uv` not on PATH | Run `uv --version` to confirm installation; check MCP server logs in VS Code Output panel |
| Hook file not refreshed on rerun | Existing local `.owlbear/hooks/` file differs from seed | Re-run `init.py --replace-hooks` to overwrite, or choose `replace` when prompted interactively |
| Agent name conflict | Same-name agent in both owlbear and project locations | Give project agents unique names; see [Adding local agents](operating-owlbear.md#adding-local-agents) |

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
