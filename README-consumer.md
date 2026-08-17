# Use OwlBear in a project

OwlBear adds GitHub Copilot agents and tools to an existing project. Setup writes the project-local
VS Code and Delivery configuration; the agents, skills, instructions, and prompts stay shared in
your OwlBear checkout and update when that checkout is pulled.

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
uv run --project ../owlbear python ../owlbear/setup/init.py \
  --github-repository OWNER/PROJECT

# Open the configured project.
code .
```

Expected result: `.vscode/settings.json`, `.vscode/mcp.json`, and tracked
`.owlbear/delivery/config.json` exist in the project. Existing project settings are merged, not
replaced. If the project already has a GitHub `origin`, omit `--github-repository OWNER/PROJECT`.

Windows PowerShell uses the same steps with PowerShell paths. The [setup guide](setup/setup-guide.md)
has a copy-paste example and the same-drive limitation in full.

## After setup

The setup guide owns the exact checks and recovery steps. Continue there when you are ready to:

| Next action | Canonical procedure |
| --- | --- |
| Confirm agents and MCP servers loaded | [Verify the installation](setup/setup-guide.md#verify-the-installation) |
| Run the first admitted Change | [First successful workflow](setup/setup-guide.md#first-successful-workflow) |
| Launch Cockpit or understand its workspace | [Cockpit details](setup/setup-guide.md#cockpit-details) |
| Diagnose a missing server, customization, or workspace | [Troubleshooting](setup/setup-guide.md#troubleshooting) |

## Keep it current

Pull the shared OwlBear checkout and rerun setup when you want newer agents, skills, instructions,
prompts, runtime fixes, or refreshed copied hooks. Use the [refresh procedures](setup/setup-guide.md#refreshing-consumer-configs)
when you intentionally want to replace seeded configuration files.

For optional profile settings, sharing, and complete recovery procedures, continue to the
[setup guide](setup/setup-guide.md).
