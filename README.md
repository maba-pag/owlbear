# Use OwlBear in a project

## What OwlBear is

OwlBear is a guided development workflow for using GitHub Copilot on an existing software project.
It takes work from a plain-language idea through design, ordered execution, evidence, and a pull
request that a person reviews and merges. Use it when Copilot work needs a clear scope, visible
progress, recovery when something goes wrong, and a human decision before publication.

OwlBear is not a new application framework and it does not replace your project's source code,
build tools, or GitHub workflow. Setup connects your project to a separate OwlBear checkout and
adds shared Copilot roles, reusable instructions, and tool servers for Delivery, Memory, Knowledge,
Browser, and document conversion. Your project keeps its code and project-specific configuration;
OwlBear supplies the workflow and tools around that code.

In practical terms: you describe an outcome, Copilot helps refine and design it, Delivery keeps the
approved work ordered and reviewed, and Cockpit gives you a human view of requests, recovery, and
publication. Setup writes the project-local VS Code and Delivery configuration; the shared agents,
skills, instructions, and prompts stay in your OwlBear checkout and update when that checkout is
pulled.

The supported consumer surface is the rolling `main` branch. OwlBear has no numbered product
releases. Browser and Knowledge are available but remain Alpha until field use validates them.

## Choose your next step

| You want to... | Go to |
| --- | --- |
| Install OwlBear now | [Fast path](#fast-path) |
| Check that setup worked | [Verify the installation](setup/setup-guide.md#verify-the-installation) |
| Run one small change | [First successful workflow](setup/setup-guide.md#first-successful-workflow) |
| Launch the human work view | [Cockpit details](setup/setup-guide.md#cockpit-details) |
| Share the setup with a teammate | [Sharing guide](setup/sharing-guide.md) |
| Find a package or server | [Package map](serve/README.md) |
| Read every setup option and recovery path | [Setup guide](setup/setup-guide.md) |

## What you get

| Part | What it does |
| --- | --- |
| Agents | Copilot roles for refining ideas, designing work, planning, building, and reviewing |
| Skills | Reusable instructions that give those roles domain knowledge |
| MCP servers | Tool connections for Delivery, Knowledge, Memory, Browser, and document conversion |
| Delivery | Keeps one approved change ordered, reviewed, publishable, and recoverable |
| Cockpit | Shows work, requests, attention, recovery controls, and completed history |

## A few terms

| Term | Meaning |
| --- | --- |
| Agent | A Copilot role with a focused job, such as design, planning, building, or review |
| Skill | Reusable instructions that give an agent domain or workflow knowledge |
| MCP server | A tool connection that exposes one OwlBear capability inside VS Code |
| Change | One approved piece of work tracked from design through review and publication |
| Cockpit | The browser UI for viewing work and taking human-owned actions |

## Before you start

Install Python 3.14.6+, [uv](https://docs.astral.sh/uv/), VS Code with the GitHub Copilot
extension, [GitHub CLI](https://cli.github.com/), and Git. Your project and OwlBear checkout must
be on the same drive on Windows. Authenticate the CLI with `gh auth login`; publication requires
`gh auth status` to report an active account.

The project should already be a Git checkout with a GitHub `origin`. If it has no GitHub remote,
pass its `OWNER/NAME` explicitly to `setup/init.py` as shown below.

## Fast path

Use sibling directories so the setup and Cockpit commands stay the same throughout the guide. Run
these commands from a parent directory such as `~/work`. If your project already exists, skip its
clone command.

```shell
# Clone the rolling consumer branch once.
git clone -b main https://github.com/maba-pag/owlbear.git owlbear

# Only if the project is not already checked out.
git clone https://github.com/OWNER/PROJECT.git my-project

# Run setup from the project root.
cd my-project
uv run --project ../owlbear python ../owlbear/setup/init.py

# Open the configured project.
code .
```

Expected result: `.vscode/settings.json`, `.vscode/mcp.json`, and tracked
`.owlbear/delivery/config.json` exist in the project. Existing project settings are merged, not
replaced. Setup infers the GitHub repository identity from `origin` and, in an interactive run,
suggests the currently checked-out branch as the Delivery target.

If the project has no GitHub `origin`, or you want a different identity, rerun setup with the
explicit override:

```shell
uv run --project ../owlbear python ../owlbear/setup/init.py \
  --github-repository OWNER/PROJECT
```

Setup writes or merges project-local `.vscode/settings.json` and `.vscode/mcp.json`, creates
tracked Delivery configuration and copied runtime hooks, and creates a starter
`.github/copilot-instructions.md` only when that file is absent. Review the generated settings and
customize the project instructions with your own architecture, commands, and conventions; the
project file is the place for rules that should override the shared OwlBear baseline. On macOS,
interactive setup may also ask before changing selected user-local Copilot profile model settings;
noninteractive setup skips that profile change. The seeded Browser MCP entry uses `*` to make local
testing work immediately; replace it with exact hostnames before using Browser against production
or sensitive sites.

Windows PowerShell uses the same steps with PowerShell paths. The [setup guide](setup/setup-guide.md)
has a copy-paste example and the same-drive limitation in full.

## After setup

The setup guide owns the exact checks and recovery steps. Continue there when you are ready to:

| Next action | Canonical procedure |
| --- | --- |
| Confirm agents and MCP servers loaded | [Verify the installation](setup/setup-guide.md#verify-the-installation) |
| Run the first admitted Change | [First successful workflow](setup/setup-guide.md#first-successful-workflow) |
| Launch Cockpit or understand its workspace | [Cockpit details](setup/setup-guide.md#cockpit-details) |
| Configure the Browser capability | [Browser MCP guide](serve/browser-mcp/README.md) |
| Diagnose a missing server, customization, or workspace | [Troubleshooting](setup/setup-guide.md#troubleshooting) |
| Remove OwlBear from a project | [Uninstalling](setup/setup-guide.md#uninstalling) |

## Keep it current

Pull the shared OwlBear checkout and rerun setup when you want newer agents, skills, instructions,
prompts, runtime fixes, or refreshed copied hooks. Use the [refresh procedures](setup/setup-guide.md#refreshing-consumer-configs)
when you intentionally want to replace seeded configuration files.

The `main` branch is a rolling consumer surface rather than a numbered release. For reproducible
workspaces, pin the OwlBear checkout to a reviewed commit and record that commit with the project;
shared customization files follow that checkout, while copied project files change only when setup
or a refresh command updates them.

For optional profile settings, sharing, and complete recovery procedures, continue to the
[setup guide](setup/setup-guide.md).
