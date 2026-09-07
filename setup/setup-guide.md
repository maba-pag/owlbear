# OwlBear Setup Guide

> From clone to a working VS Code workspace and one completed change.

This guide owns installation and first success. Day-to-day operation, refresh, uninstall, and
customization live in [Operating OwlBear](operating-owlbear.md); teammate and multi-project
workflows live in the [sharing guide](sharing-guide.md).

## Prerequisites

Before running setup, ensure the following are installed on your machine:

| Requirement | Why | How to get it |
| --- | --- | --- |
| Python 3.12.14+ | OwlBear runtime; the checkout defaults to Python 3.14.7 | [python.org](https://www.python.org/downloads/) |
| [uv](https://docs.astral.sh/uv/) | Package manager and MCP server launcher | [Installation guide](https://docs.astral.sh/uv/getting-started/installation/) |
| VS Code | IDE | [code.visualstudio.com](https://code.visualstudio.com/) |
| GitHub Copilot extension | Chat and agents | VS Code Extensions marketplace |
| [GitHub CLI](https://cli.github.com/) | GitHub publication and pull-request operations | [Installation guide](https://cli.github.com/manual/installation) |
| Git | Clone and version control | [git-scm.com](https://git-scm.com/) |

> **Windows limitation:** owlbear and your project must be on the **same drive**.
> `init.py` uses relative paths, and `os.path.relpath` raises `ValueError` when
> resolving paths across different Windows drive letters (e.g., `C:\` vs `D:\`).

<!-- separate blockquotes -->

> **macOS and Linux:** Python, uv, VS Code, and Git work natively on both platforms. Browser-backed
> commands still require the separate Chromium download described below.

Chromium is optional for setup. Install it later when you use the Browser MCP or run Cockpit's
browser-backed tests; see [Verify the installation](#verify-the-installation) and the
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
`~/work/owlbear` and `~/work/my-project`. On Windows they are on the same drive. The OwlBear clone
is on `main`, its default branch and the supported consumer surface.

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
check below because it also depends on Chromium and its allowlist.

## Verify the installation

1. Open Copilot Chat and run **Chat: Open Customizations**.
2. Confirm that OwlBear agents, skills, instructions, and prompts are listed.
3. Run **MCP: List Servers** and confirm these five servers show `running`:
   `owlbear-delivery`, `owlbear-knowledge`, `owlbear-memory`, `owlbear-browser`, and `markitdown`.
4. Before the first workflow, run `gh auth status` and confirm the GitHub CLI reports an active
  account.

### Browser readiness

`MCP: List Servers` confirms that the stdio processes started; it does not prove that Chromium is
installed, an approved session is authenticated, internal routing is permitted, or Knowledge
ingestion is ready. The Browser server launches a persistent Playwright Chromium context; it does
not select Microsoft Edge or attach to an existing browser through CDP. To enable and verify the
supported alpha path:

1. From the consumer project root, install Chromium for the sibling OwlBear checkout:

   ```shell
   uv run --project ../owlbear playwright install chromium
   ```

   **Expected result:** the Playwright Chromium executable is available to the Browser MCP server.
2. Review the `env` member on the `owlbear-browser` entry in `.vscode/mcp.json`. Fresh setup seeds
  wildcard testing access; replace it with exact hostnames for normal or production use. Set
  `PLAYWRIGHT_USER_DATA_DIR` only when an approved existing Chromium profile should be used; use
  an absolute path because the launcher does not expand `~` in this environment:

   ```json
   {
     "env": {
        "BROWSER_ALLOWED_DOMAINS": "example.com,docs.example.com",
        "PLAYWRIGHT_USER_DATA_DIR": "/Users/you/.owlbear/chromium-profile"
     }
   }
   ```

   **Expected result:** Browser requests are limited to the exact hostnames you named. For local
   testing across public sites only, keep `"*"`; keep exact hostnames for production. SSRF checks
   reject private, loopback, link-local, reserved, and unspecified DNS results for hostnames that
   are not exact allowlist entries.
3. Restart the `owlbear-browser` MCP server and try `acquire` or `navigate` against an allowed
   public URL. `acquire` accepts optional readiness/content selectors and returns a structured
   success or failure result; it does not expose diagnostic HTML or automatically ingest content.

   **Expected result:** the tool returns page content or its typed acquisition result. A running
   server with no configured domains still denies every hostname. Exact allowlist entries are the
   explicit approval for private, loopback, or link-local DNS results from that hostname; wildcard
   mode does not grant that approval. See the
   [Browser MCP guide](../serve/browser-mcp/README.md) for the full boundary and limitations.

- **Managed SSO readiness:** Treat managed SSO as a separate readiness check. The launcher can load an extension directory
  named by `SSO_EXTENSION_PATH` and can reuse a persistent Chromium profile, but discovering or
  loading an extension is not proof of tenant authentication, MFA, Conditional Access, or device
  compliance. On macOS, configure an approved profile or extension explicitly and verify one
  permitted target site with the organization's normal login flow. Do not collect cookies or
  tokens, weaken enterprise policy, or claim SSO support from MCP process startup alone.

- **Knowledge ingestion readiness:** Treat Knowledge ingestion as a separate, currently agent-mediated check. After inspecting a
  successful `acquire` result, call `knowledge_ingest` with the captured text, an intentional
  scope, and an optional `source_url`. Direct ingestion creates or reuses a non-refreshable inline
  source for that scope; `source_url` supplies document identity but does not attach the capture to
  a registered browser source. Registered `authenticated_web` refresh is not a working end-to-end
  Browser-to-Knowledge path in the current Knowledge MCP process. Use the
  [Knowledge operations guide](../share/skills/h-knowledge-ops/SKILL.md) for the current result
  and limitation contract.

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

## First successful workflow

After verification, prove the installation with one small outcome:

1. Run `/ideate` and describe the outcome.

   **Expected result:** the Designer records a refined outcome and asks the next bounded question
   when more detail is needed.
2. Continue with `/design`, review the proposed work, and approve admission. When it succeeds,
   note the returned lowercase, hyphenated Change ID, for example `improve-search`.

  **Expected result:** one approved Change is admitted, its verified package is backed up on the
  managed Change branch, its initial checkpoint is queued or published, and its ID is available
  for later commands. The remote recovery guarantee begins at this boundary; earlier drafts remain
  local.
3. Run `/orchestrate` after admission. It acquires currently eligible work across the portfolio;
  Planning and Build then proceed in order.

   **Expected result:** the Change advances through currently eligible Planning and Build work, or
   Cockpit shows a typed request or block that needs your action.
4. Launch Cockpit from the project root and confirm the Change is visible.

   ```shell
   uv run --project ../owlbear cockpit
   ```

   **Expected result:** Cockpit opens at `http://127.0.0.1:8420`, reads the current project, and
   shows the Change, its current stage, and the next available action.
5. Run `/finalize-change improve-search` after the Change is complete, then review and merge the
  pull request in GitHub.

   **Expected result:** Delivery prepares the exact reviewed Change for publication; GitHub remains
   the place where a person reviews and merges the pull request.

If a worker returns a request or block, answer the request or clear the requestless block in Cockpit
and then resume the named workflow. Do not edit `.owlbear` Delivery state by hand.

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
| Delivery reports that remote Delivery-state snapshots are unavailable | The configured `delivery_state_branch` cannot be read from the configured remote | Verify remote access and the tracked branch name, then retry from the project root; do not copy hidden refs or ignored runtime files |
| Delivery reports that local state differs from a remote snapshot | Local runtime, package, or Change coordination no longer matches the last published checkpoint | Preserve the local checkout and remote branches, inspect the typed Change attention in Cockpit, and resolve the exact divergence before acquisition |
| `uv run cockpit` says the command is missing | Command was run from the consumer project without `--project` | Use `uv run --project ../owlbear cockpit` from the project root |
| Cockpit shows the wrong workspace or cannot find `.owlbear/delivery/config.json` | Cockpit was launched from the wrong working directory | Run from the project root or add `--directory /path/to/project` |
| `ValueError` on setup | Cross-drive path resolution | Place owlbear and your project on the same Windows drive |
| Hook file not refreshed on rerun | Existing local `.owlbear/hooks/` file differs from seed | Re-run `init.py --replace-hooks` to overwrite, or choose `replace` when prompted interactively |
| Agent name conflict | Same-name agent in both owlbear and project locations | Give project agents unique names; see [Adding local agents](operating-owlbear.md#adding-local-agents) |

For deeper debugging, use **"Show Chat Debug View"** (Chat view ellipsis `…` menu) to inspect
raw LLM request/response payloads.

## Next

| You want to... | Go to |
| --- | --- |
| Know exactly what setup wrote, and how to undo it | [Operating OwlBear](operating-owlbear.md) |
| Run, correct, publish, and accept changes | [Delivery Workflow](operating-owlbear.md#delivery-workflow) |
| Add project-local agents, instructions, or MCP servers | [Project-Specific Customization](operating-owlbear.md#project-specific-customization) |
| Set a teammate up on the same installation | [Sharing guide](sharing-guide.md) |
