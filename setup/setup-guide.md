# OwlBear Setup Guide

> From clone to a working VS Code workspace and one completed change.

This guide owns installation and first success. Day-to-day operation, refresh, uninstall, and
customization live in [Operating OwlBear](operating-owlbear.md); teammate and multi-project
workflows live in the [sharing guide](sharing-guide.md).

## Prerequisites

Before running setup, ensure the following are installed on your machine:

| Requirement | Why | How to get it |
| --- | --- | --- |
| Python 3.14.8 | OwlBear runtime; OwlBear supports the 3.14 series only | [python.org](https://www.python.org/downloads/) |
| macOS or Linux (Ubuntu) | Supported operating systems | — |
| [uv](https://docs.astral.sh/uv/) | Package manager and MCP server launcher | [Installation guide](https://docs.astral.sh/uv/getting-started/installation/) |
| VS Code | IDE | [code.visualstudio.com](https://code.visualstudio.com/) |
| GitHub Copilot extension | Chat and agents | VS Code Extensions marketplace |
| [GitHub CLI](https://cli.github.com/) | GitHub publication and pull-request operations | [Installation guide](https://cli.github.com/manual/installation) |
| Git | Clone and version control | [git-scm.com](https://git-scm.com/) |

> **Windows:** Windows is unsupported. Setup uses relative paths; if running it experimentally,
> keep OwlBear and the project on the same drive because cross-drive paths cannot be resolved.

<!-- separate blockquotes -->

> **macOS and Linux:** Python, uv, VS Code, and Git work natively on both platforms. Browser MCP
> defaults to managed Microsoft Edge on macOS and Chromium elsewhere.

Chromium is optional for setup. Install it later when you select Browser MCP Chromium mode or run
Cockpit's browser-backed tests. Managed Edge requires stable Microsoft Edge installed on macOS; see
[Verify the installation](#verify-the-installation) and the
[Cockpit package guide](../serve/cockpit/README.md#browser-backed-tests).

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
`~/work/owlbear` and `~/work/my-project`. The OwlBear clone is on `main`, its default branch and the
supported consumer surface.

### 2. Run setup from the project root

```shell
uv run --project ../owlbear python ../owlbear/setup/init.py
```

If the project has a GitHub `origin`, setup infers the repository identity. In an interactive run,
the target-branch prompt suggests the currently checked-out branch, or `main` when no branch is
available; noninteractive setup uses `main`. Use `--remote`, `--target-branch`, or
`--github-repository OWNER/PROJECT` only when you need an explicit override. Interactive setup may
also ask about differing hook files and, on macOS, user-local Copilot profile settings.

When the project has no inferable GitHub remote, rerun the command with the repository identity:

```shell
uv run --project ../owlbear python ../owlbear/setup/init.py \
  --github-repository OWNER/PROJECT
```

**Expected result:** setup creates or merges `.vscode/settings.json` and `.vscode/mcp.json`, writes
tracked `.owlbear/delivery/config.json`, and copies the project-local hooks and runtime templates.
The complete inventory is in
[What Setup Creates](operating-owlbear.md#what-setup-creates).

### 3. Open the project in VS Code

```shell
code .
```

**Expected result:** VS Code opens the project directory, not the OwlBear checkout. The shared
agents, skills, instructions, and prompts are loaded from the sibling OwlBear path.

### 4. Confirm it loaded

Open **Chat: Open Customizations** and then **MCP: List Servers**. The exact checks are in
[Verify the installation](#verify-the-installation).

**Expected result:** the five seeded MCP server processes are running and the shared OwlBear
customization roots appear in Chat Customizations. Browser capability readiness is a separate
check below because it also depends on the selected browser and its allowlist.

## Verify the installation

1. Open Copilot Chat and run **Chat: Open Customizations**.
2. Confirm that OwlBear agents, skills, instructions, and prompts are listed.
3. Run **MCP: List Servers** and confirm these five servers show `running`:
   `owlbear-delivery`, `owlbear-knowledge`, `owlbear-memory`, `owlbear-browser`, and `markitdown`.
4. Before the first workflow, run `gh auth status` and confirm the GitHub CLI reports an active
  account.

### Browser readiness

Check MCP startup, browser capability, and Knowledge ingestion separately. A running MCP process
does not prove that the selected browser launched, that a target is authenticated, or that a
Browser-to-Knowledge round is ready.

1. **MCP process startup:** Run **MCP: List Servers** and confirm `owlbear-browser` and
   `owlbear-knowledge` show `running`.

   **Expected result:** both stdio processes are available; this confirms startup only.
2. **Browser readiness:** On macOS, an unset `BROWSER_MODE` selects managed Edge and its fixed
   OwlBear profile; elsewhere it selects Chromium. Confirm stable Microsoft Edge is installed before
   starting the Browser MCP on macOS. For Chromium mode or Cockpit's browser-backed tests, install
   Chromium for the sibling OwlBear checkout from the consumer project root:

  ```shell
  uv run --project ../owlbear playwright install chromium
  ```

   This download is not required for macOS managed Edge mode. To select Chromium explicitly on
   macOS, set `BROWSER_MODE` to `chromium` in the local `owlbear-browser` server environment; an
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
   acquisition result. `browser_status` reports `ready` only while a live browser session is
   available; it does not prove sign-in or authenticated access. Exact-host entries explicitly
   permit private, loopback, and link-local DNS results for that hostname; wildcard mode does not.
   Reserved and unspecified addresses are always rejected. The current SSRF preflight does not
   fully prevent DNS rebinding or an allowlisted server redirecting to a private address; these
   are accepted limits, so keep the allowlist narrow. See the
   [Browser MCP guide](../serve/browser-mcp/README.md) for the full policy.
3. **Managed SSO readiness:** On macOS, the default is a visible managed Edge session using the
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

If a customization root is missing, inspect `.vscode/settings.json` and compare its relative
OwlBear path with the location of the checkout. If a server is missing, inspect `.vscode/mcp.json`,
run `uv sync --locked --all-packages --all-extras --all-groups` in the OwlBear checkout, and rerun
setup from the project root.

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
  | `gpt-6-luna` | `max` |
  | `gpt-6-sol` | `high` |
  | `claude-opus-5.5` | `medium` |

The file is written atomically, unrelated profile entries are preserved, and a missing file or
Copilot entry is created minimally. Malformed profile JSON is left unchanged with a warning. To
target a named profile instead of the default fallback, open
the project in VS Code, run `Profiles: Switch Profile`, and rerun `setup/init.py`. Setup does not
take a profile-selection command-line argument. Noninteractive setup skips this user-local profile
mutation.

For development-only browser-backed tests, use the [Cockpit package guide](../serve/cockpit/README.md#browser-backed-tests).

## Managed Mac browser pilot

Run this pilot on the managed Mac before relying on SharePoint or Confluence access. Keep the two
approved target URLs local; do not put URLs, hostnames, page content, credentials, or session files in
the repository, Delivery requests, or status.

1. Install stable Microsoft Edge and start the `owlbear-browser` MCP server. Leave
  `BROWSER_MODE` and `PLAYWRIGHT_USER_DATA_DIR` unset for the managed default. Configure
  `BROWSER_ALLOWED_DOMAINS` locally for only the two approved target hosts.

  **Expected result:** before any browser action, `browser_status` reports `managed-edge`,
  `per-user-owned`, `not-launched`, null startup reason, and unavailable visible authentication.
  Stop if the mode is invalid; do not switch to Chromium or the operator's daily Edge profile.
2. Call `acquire` or `navigate` with one locally supplied, operator-approved SharePoint URL. The
  first action launches the visible Edge window with the fixed OwlBear profile. Complete first-use
  sign-in, site trust, consent, or MFA directly in that window. Do not send credentials or session
  material through an OwlBear tool.

  **Expected result:** the Edge window is live and the operator confirms authenticated SharePoint
  content. Browser readiness alone does not count as authentication.
3. Repeat the action with one locally supplied, operator-approved Confluence URL and confirm its
  authenticated content in the owned Edge window.

  **Expected result:** the operator confirms authenticated Confluence content in the same owned
  session; record no page content, URL, or hostname.
4. Close the OwlBear-owned Edge window and call `browser_status`, then repeat an allowed action for
  one approved target.

  **Expected result:** status reports `not-launched` after the window closes; the next action
  relaunches the fixed profile and the operator confirms the target remains authenticated.
5. Restart the `owlbear-browser` MCP server, repeat an allowed action for each target, and confirm
  that the fixed profile retains session availability. Stop the server normally afterward.

  **Expected result:** both targets remain authenticated after restart, no `--no-sandbox` or
  unsupported-flag warning appears, and only OwlBear-owned browser resources close. Record only each
  target class (`SharePoint` or `Confluence`) and `pass` or `fail`; include no URL, hostname, page
  content, credential, or session data. If a Delivery pilot request is active, answer it in Cockpit
  using only those bounded outcomes.

## First successful workflow

After verification, prove the installation with one small outcome:

1. Run `/ideate` and describe the outcome.

   **Expected result:** the Designer records a refined outcome and asks the next bounded question
   when more detail is needed.
2. Continue with `/design`, review the proposed work, and approve admission. When it succeeds,
   note the returned lowercase, hyphenated Change ID, for example `improve-search`, and the next
   prompt, `/continue-change improve-search`.

  **Expected result:** one approved Change is admitted, its verified package is backed up on the
  managed Change branch, its initial checkpoint is queued or published, and its ID is available
  for later commands. The remote recovery guarantee begins at this boundary; earlier drafts remain
  local.
3. Run `/continue-change improve-search` in Copilot Chat. It continues only that Change: Planning,
  Build, finalization, and publication proceed in order until the chat stops for you or the pull
  request is ready.

   **Expected result:** the Change advances through Planning and Build, or the chat stops and
   Cockpit shows a typed request or block that needs your action. After you act, run the same
   prompt again.
4. Launch Cockpit from the project root and confirm the Change is visible.

   ```shell
   uv run --project ../owlbear cockpit
   ```

   **Expected result:** Cockpit opens at `http://127.0.0.1:8420`, reads the current project, and
   shows the Change, its progress, and the next available action, such as
   **Copy continuation prompt**.
5. When Cockpit shows **Your decision** with the headline **Ready to merge**, review the pull
   request and approve it with
  **Approve merge**, or merge it in GitHub.

   **Expected result:** an approval merges only the exact reviewed head. After the merge, Delivery
   observes it on GitHub and the Change shows **Done**.

If a worker returns a request or block, answer the request or clear the requestless block in Cockpit
and then run `/continue-change <change-id>` again. Do not edit `.owlbear` Delivery state by hand.
Other prompts handle exceptions; see
[Exceptional entries](operating-owlbear.md#exceptional-entries).

Use the [Delivery workflow reference](operating-owlbear.md#delivery-workflow) when you need the
detailed correction, publication, acceptance, or recovery procedure.

---

## Troubleshooting

| Symptom | Likely cause | Resolution |
| --- | --- | --- |
| Agents not appearing in picker | Wrong path in `chat.agentFilesLocations` | Run **Chat: Open Customizations**; verify the path relative to project root matches owlbear location |
| Skills not auto-loading | `chat.agentSkillsLocations` missing or path wrong | Check `.vscode/settings.json`; re-run `init.py` if the key is absent |
| Instructions ignored | `chat.instructionsFilesLocations` missing | Check `.vscode/settings.json`; verify `*.instructions.md` files exist in the registered directory |
| MCP server fails to start | Missing dependency or `uv` not on PATH | Run `uv --version` to confirm installation; check MCP server logs in VS Code Output panel |
| `owlbear-delivery` reports `ERR_DELIVERY_STARTUP_UNCONFIGURED` | `.owlbear/delivery/config.json` is absent from the project root | Re-run `init.py`; setup recreates the file only when it is missing |
| `owlbear-delivery` refuses to start with `state-migration-required` | The OwlBear checkout moved to a release that needs a newer Delivery state format | Run `/upgrade-delivery` from the project; see [Upgrading OwlBear](operating-owlbear.md#upgrading-owlbear) |
| `owlbear-delivery` refuses to start with `state-newer-than-controller` | The OwlBear checkout is older than the project's Delivery state | Move the checkout forward with `/upgrade-delivery`; going back needs the upgrade backup restored first |
| Delivery reports that remote Delivery-state snapshots are unavailable | The configured `delivery_state_branch` cannot be read from the configured remote | Verify remote access and the tracked branch name, then retry from the project root; do not copy hidden refs or ignored runtime files |
| Delivery reports that local state differs from a remote snapshot | Local runtime, package, or Change coordination no longer matches the last published checkpoint | Preserve the local checkout and remote branches, inspect the typed Change attention in Cockpit, and resolve the exact divergence before acquisition |
| `uv run cockpit` says the command is missing | Command was run from the consumer project without `--project` | Use `uv run --project ../owlbear cockpit` from the project root |
| Cockpit shows the wrong workspace or cannot find `.owlbear/delivery/config.json` | Cockpit was launched from the wrong working directory | Run from the project root or add `--directory /path/to/project` |
| Hook file not refreshed on rerun | Existing local `.owlbear/hooks/` file differs from seed | Re-run `init.py --replace-hooks` to overwrite, or choose `replace` when prompted interactively |
| Agent name conflict | Same-name agent in both owlbear and project locations | Give project agents unique names; see [Adding local agents](operating-owlbear.md#adding-local-agents) |

For deeper debugging, use **"Show Chat Debug View"** (Chat view ellipsis `…` menu) to inspect
raw LLM request/response payloads.

## Next

| You want to... | Go to |
| --- | --- |
| Know exactly what setup wrote, and how to undo it | [Operating OwlBear](operating-owlbear.md) |
| Upgrade OwlBear and migrate Delivery state | [Upgrading OwlBear](operating-owlbear.md#upgrading-owlbear) |
| Run, correct, publish, and accept changes | [Delivery Workflow](operating-owlbear.md#delivery-workflow) |
| Add project-local agents, instructions, or MCP servers | [Project-Specific Customization](operating-owlbear.md#project-specific-customization) |
| Set a teammate up on the same installation | [Sharing guide](sharing-guide.md) |
