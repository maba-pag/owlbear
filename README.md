# OwlBear

**A guided workflow that turns a plain-language idea into a reviewed pull request, using GitHub
Copilot on your Mac.**

Copilot is good at writing code and bad at holding on to what it agreed to. OwlBear adds the
structure around it: one approved scope per change, ordered execution, an independent review of
every step, evidence that survives a crashed session, and a human decision before any work starts.

OwlBear runs once on your Mac and serves every project you add to it. It does not replace your
source code, your build tools, or your GitHub workflow, and the local files its Delivery setup
writes into a project are kept out of Git.

## What it looks like

You work on OwlBear's Changes page in your browser and in Copilot Chat. **New Change** on that page
opens a shaping chat in VS Code that turns your idea into a brief; you approve the brief on the
page, and OwlBear plans, builds, reviews and publishes it:

```mermaid
flowchart LR
    A[Rough idea] -->|New Change: shaping chat| B[Approved brief]
    B -->|plan, build, review| C[Pull request]
    C -->|you approve the merge| D[Done]
```

When a step needs a decision or gets stuck, OwlBear asks on the Changes page instead of guessing.
Once the pull request's checks and your branch rules pass, OwlBear merges it; when it needs your
consent, it asks on the Changes page and you can also merge in GitHub.

## Is this for you?

A good fit when:

- You use VS Code and GitHub Copilot on a Mac, on Git projects hosted on GitHub.
- Your changes are large enough that scope, ordering, and review actually matter.
- You want every change to arrive as a reviewed pull request, not as an agent's push to your branch.
- You are willing to let agents write files and run commands in OwlBear's own worktrees of your
  project.

Probably not a fit when:

- You work on Linux or Windows. OwlBear supports macOS only; Linux and Windows are not supported
  yet.
- You want an autonomous agent that ships without you in the loop.
- You want a hosted service or a CI-side bot; OwlBear runs on your Mac.
- You are not using GitHub Copilot. The agents, chats and tools are specific to that product.

## Before you start

| Requirement | Why |
| --- | --- |
| **macOS** | The only supported system; Linux and Windows are not supported yet |
| **Python 3.14.8 or later in the 3.14 series** | Runs OwlBear |
| [uv](https://docs.astral.sh/uv/) | Installs OwlBear's dependencies |
| Git, with `user.name` and `user.email` set | OwlBear commits each Change's work |
| [GitHub CLI](https://cli.github.com/), signed in with push access to your project | Opens, updates and merges pull requests |
| GitHub Copilot CLI (`brew install --cask copilot-cli`) | Runs OwlBear's agent sessions |
| VS Code + GitHub Copilot extension | New Change opens its shaping chat there |
| A Git project with a GitHub `origin` | Each Change is published to that repository |

Run `gh auth login` once. OwlBear checks these before it works on a project and names the fix for
anything missing.

Expect agent-scale Copilot usage. A single change runs many agent sessions across planning,
building, and review.

## Quick Start

OwlBear installs once per Mac, into `~/.owlbear/runtime`; cloning it is the installation. Your
projects stay where they are.

```shell
# 1. Clone OwlBear into its runtime folder and install its dependencies.
git clone https://github.com/maba-pag/owlbear.git ~/.owlbear/runtime
cd ~/.owlbear/runtime
uv sync --locked

# 2. Install the command; it asks before each change outside ~/.owlbear.
.venv/bin/owlbear install

# 3. Start OwlBear; it prints the address of its pages.
owlbear start
```

`owlbear install` asks separately before it links `~/.local/bin/owlbear`, links the shaping agent
and its skill into `~/.copilot`, and adds a login item. Say yes to the shaping agent: **New Change**
needs it. Without the command link, run `~/.owlbear/runtime/.venv/bin/owlbear` instead of `owlbear`.
If the login item already started OwlBear, it runs paused: press **Resume** in the bar at the top.

Open the printed address, choose **Add project** in the bar at the top and enter your project's
folder. If the page then shows **Setup required**, run the command it names from any terminal:

```shell
owlbear setup --repo ~/work/my-project
```

**Expected result:** setup checks readiness, asks you to confirm the project's profile, and asks
before writing the two local chat files listed under [What setup changes](#what-setup-changes).
Reload the project's VS Code window afterwards.

See the [setup guide](setup/setup-guide.md#quick-start) for every step's expected output.

## Verify

1. Run `owlbear status` and confirm your project is listed as `loaded`.
2. Run `owlbear doctor` and confirm it ends with `all checks passed`.
3. Confirm the project's Changes page shows no **Setup required** note.

If something is missing, go to [Verify the installation](setup/setup-guide.md#verify-the-installation)
and [Troubleshooting](setup/setup-guide.md#troubleshooting).

## Your first change

Prove the installation with one small outcome on the Changes page:

1. Press **New Change** and describe what you want in the shaping chat it opens in VS Code.
2. Approve the brief on the Changes page. OwlBear plans, builds, reviews and publishes it as a
   pull request, and asks on the page when it needs you.
3. When the page asks you to approve the merge, review the pull request and approve it there, or
   merge it in GitHub yourself.

The full walkthrough with expected output at each step is in
[First successful workflow](setup/setup-guide.md#first-successful-workflow).

## What setup changes

OwlBear keeps its runtime, versions, logs and each project's Delivery state under `~/.owlbear/`.
Only with your yes does it add:

- `~/.local/bin/owlbear`, a link to the command, and the zsh completion in `~/.owlbear/`.
- Links to the shaping agent and its skill in `~/.copilot/agents/` and `~/.copilot/skills/`.
- A login item that starts OwlBear paused at login.
- In each project: the Delivery chat server and, once the shared data repository holds the project, the
  memory server for New Change's shaping chat in `.mcp.json`, and `chat.defaultToCopilotHarness` in `.vscode/settings.json`, each with its own yes.
  Both files are listed in `.git/info/exclude`. Setup never writes a file Git tracks; for a tracked
  `.mcp.json` it prints the Delivery entry to add to your user-level MCP configuration.

To undo it, run `owlbear uninstall`: it removes the links, the completion and the login item, and
keeps the runtime and your projects. **Remove project** on the page stops OwlBear serving a project.
See [Uninstalling](setup/operating-owlbear.md#uninstalling) for removing everything.

## Status and expectations

OwlBear's versions are Git tags such as `v1.0`. It updates itself to the newest version of its
channel after 15 minutes without use while nothing runs, announced on open pages first, and never
moves to an older version. **Run updates now** on a paused page, or `owlbear update`, updates at
once; `owlbear versions` shows the version it runs and the next one. See
[Upgrading OwlBear](setup/operating-owlbear.md#upgrading-owlbear).

| Surface | Status | What it does |
| --- | --- | --- |
| Delivery | Core | Shapes, plans, builds, reviews, publishes, and recovers one change; pages for Changes, Backlog, Memory, Settings, and Maintenance |
| Memory | Available | Durable, scoped agent knowledge that carries across sessions and projects |
| Knowledge | Alpha | Searchable documents and knowledge graphs; needs field validation |
| Browser | Alpha | Authenticated web acquisition; needs field validation |

## Learn more

| You want to... | Go to |
| --- | --- |
| Every setup option, verification detail, and fix | [Setup guide](setup/setup-guide.md) |
| Daily operation, upgrades, recovery, uninstall, and customization | [Operating OwlBear](setup/operating-owlbear.md) |
| Share one installation with teammates | [Sharing guide](setup/sharing-guide.md) |
| Understand the packages and tool servers | [Package map](serve/README.md) |
| Configure the Browser capability | [Browser MCP guide](serve/browser-mcp/README.md) |
| Change agents, skills, instructions, or prompts | [Agent ecosystem guide](share/README.md) |
| Develop OwlBear itself | [Contributing](CONTRIBUTING.md) |

## Security

Report vulnerabilities privately. See [SECURITY.md](SECURITY.md).
