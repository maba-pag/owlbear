# OwlBear

**A guided workflow that turns a plain-language idea into a reviewed pull request, using GitHub
Copilot inside VS Code.**

Copilot is good at writing code and bad at holding on to what it agreed to. OwlBear adds the
structure around it: one approved scope per change, ordered execution, an independent review of
every step, evidence that survives a crashed session, and a human decision before anything is
published. You stay in VS Code, and you still review and merge the pull request yourself.

OwlBear installs alongside an existing project. It does not replace your source code, your build
tools, or your GitHub workflow.

## What it looks like

You work in Copilot Chat. Four commands cover the normal loop:

```text
/ideate                       Refine a rough idea, one question at a time.
/design                       Turn it into an approved work package. You approve it.
/orchestrate                  Run the work that is currently eligible: plan, build, review, repeat.
/finalize-change my-change    Collect evidence and open the pull request.
```

```mermaid
flowchart LR
    A[Rough idea] -->|/ideate| B[Refined outcome]
    B -->|/design| C[Approved change]
    C -->|/orchestrate| D[Plan, build, review]
    D -->|/finalize-change| E[Pull request]
    E -->|you merge| F[Completed history]
```

Between those commands, a browser view called Cockpit shows what is in flight, what is waiting on
you, and what already completed. When a step needs a decision or gets stuck, it stops and asks
there instead of guessing.

![Cockpit delivery portfolio: one change in Design, portfolio counters for work that needs you, is
blocked, running, or ready, and the exact next command to run](share/diagrams/cockpit-delivery.png)

## Is this for you?

A good fit when:

- You already use VS Code and GitHub Copilot on a Git project hosted on GitHub.
- Your changes are large enough that scope, ordering, and review actually matter.
- You want a pull request and a human merge at the end, not an agent that pushes to your branch.
- You are willing to let agents write files and run commands in your working copy.

Probably not a fit when:

- You want an autonomous agent that ships without you in the loop.
- You want a hosted service or a CI-side bot; OwlBear runs on your laptop, in your editor.
- You need a stable, versioned dependency. OwlBear ships from a rolling branch with no releases.
- You are not using GitHub Copilot in VS Code. The agent format, prompts, and tools are specific
  to that product.

## Before you start

| Requirement | Why |
| --- | --- |
| **Python 3.14.6+** | Runs the OwlBear tool servers. Older 3.x will not work. |
| [uv](https://docs.astral.sh/uv/) | Installs dependencies and launches the tool servers |
| VS Code + GitHub Copilot extension | The editor and the agents |
| [GitHub CLI](https://cli.github.com/) | Opens and updates pull requests |
| Git, and a project with a GitHub `origin` | The change is published to that repository |

Run `gh auth login` once, and check `gh auth status` before your first change. On Windows, the
OwlBear checkout and your project must be on the same drive.

Expect agent-scale Copilot usage. A single change runs many chat requests across design, planning,
building, and review.

## Quick Start

OwlBear is cloned next to your project, not into it. Setup writes relative paths between the two,
so keep them as siblings:

```text
~/work/
├── owlbear/      <- the OwlBear checkout
└── my-project/   <- your project, where you run setup and open VS Code
```

Run these from the parent directory. Skip the first clone if your project is already checked out.

```shell
# 1. Clone your project.
git clone https://github.com/OWNER/PROJECT.git my-project

# 2. Clone OwlBear beside it. Its default branch is the rolling consumer surface.
git clone https://github.com/maba-pag/owlbear.git owlbear

# 3. Run setup from the project root.
cd my-project
uv run --project ../owlbear python ../owlbear/setup/init.py

# 4. Open the configured project.
code .
```

**Expected result:** `.vscode/settings.json`, `.vscode/mcp.json`, and a tracked
`.owlbear/delivery/config.json` exist in your project. Existing project settings are merged, not
replaced. Setup reads the GitHub identity from `origin` and, in an interactive run, suggests the
checked-out branch as the pull-request target.

If the project has no GitHub `origin`, or you want a different identity, name it explicitly:

```shell
uv run --project ../owlbear python ../owlbear/setup/init.py \
  --github-repository OWNER/PROJECT
```

Windows PowerShell uses the same steps with backslash paths. The
[setup guide](setup/setup-guide.md#quick-start) has the copy-paste variant and every option.

## Verify

1. Run **Chat: Open Customizations** and confirm OwlBear agents, skills, instructions, and prompts
   are listed.
2. Run **MCP: List Servers** and confirm five servers are running: `owlbear-delivery`,
   `owlbear-knowledge`, `owlbear-memory`, `owlbear-browser`, and `markitdown`.
3. Run `gh auth status` and confirm an active account.

If something is missing, go to [Verify the installation](setup/setup-guide.md#verify-the-installation)
and [Troubleshooting](setup/setup-guide.md#troubleshooting).

## Your first change

Prove the installation with one small outcome:

1. `/ideate` — describe what you want. Answer the questions it asks.
2. `/design` — review the proposed work and approve it. Note the Change ID it returns, for example
   `improve-search`.
3. `/orchestrate` — the work is planned, built, and reviewed in order. Repeat until it stops.
4. Open Cockpit from the project root to watch progress, or to answer whatever it is waiting for:

   ```shell
   uv run --project ../owlbear cockpit
   ```

   It opens at `http://127.0.0.1:8420` and reads the project you launched it from.
5. `/finalize-change improve-search` — OwlBear opens the pull request. You review and merge it on
   GitHub.

The full walkthrough with expected output at each step is in
[First successful workflow](setup/setup-guide.md#first-successful-workflow).

## What setup changes in your project

Setup writes project-local configuration and copied runtime files. It never touches your source
code.

- `.vscode/settings.json` and `.vscode/mcp.json` — merged, with your existing keys preserved.
- `.owlbear/` — tracked Delivery configuration, copied hooks, and local runtime state.
- `.github/copilot-instructions.md` — a starter file, only when none exists. Replace its
  placeholders with your project's own conventions.
- Editor and lint config (`.editorconfig`, markdownlint, yamllint) — only when absent.

Three seeded settings are deliberately permissive so the agent workflow is usable, and are worth a
look before you trust the workspace: an auto-approve list for common `uv run` commands,
`chat.tools.terminal.blockDetectedFileWrites: "never"`, and a `BROWSER_ALLOWED_DOMAINS: "*"`
wildcard on the Browser server. Narrow them to your own policy, and replace the browser wildcard
with exact hostnames before using it against anything sensitive.

To undo everything, run `--uninstall` from the project root. It removes only what it installed and
you left unmodified, and `--dry-run` shows the plan first:

```shell
uv run --project ../owlbear python ../owlbear/setup/init.py --uninstall --dry-run
```

See [Uninstalling](setup/operating-owlbear.md#uninstalling) for exactly what is kept.

## Status and expectations

OwlBear has no numbered releases. The rolling `main` branch is the supported consumer surface.
`git pull` in the OwlBear checkout updates the shared agents, skills, instructions, and prompts
immediately; rerun setup when you also want refreshed copied files. For a reproducible workspace,
pin the checkout to a reviewed commit and record that commit with your project.

| Surface | Status | What it does |
| --- | --- | --- |
| Delivery | Core | Plans, executes, reviews, publishes, and recovers one change |
| Cockpit | Core | The browser view for work, requests, recovery, and history |
| Memory | Available | Durable, scoped knowledge that carries across sessions |
| Knowledge | Alpha | Searchable documents and knowledge graphs; needs field validation |
| Browser | Alpha | Authenticated web acquisition; needs field validation |

## Learn more

| You want to... | Go to |
| --- | --- |
| Every setup option, verification detail, and fix | [Setup guide](setup/setup-guide.md) |
| Daily operation, recovery, uninstall, and customization | [Operating OwlBear](setup/operating-owlbear.md) |
| Share one installation with teammates | [Sharing guide](setup/sharing-guide.md) |
| Understand the packages and tool servers | [Package map](serve/README.md) |
| Configure the Browser capability | [Browser MCP guide](serve/browser-mcp/README.md) |
| Change agents, skills, instructions, or prompts | [Agent ecosystem guide](share/README.md) |

## Security

Report vulnerabilities privately. See [SECURITY.md](SECURITY.md).
