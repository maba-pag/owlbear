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
| Check that setup worked | [Verify the setup](#verify-the-setup) |
| Run one small change | [Try the first workflow](#try-the-first-workflow) |
| Launch the human work view | [Open Cockpit](#open-cockpit) |
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
extension, and Git. Your project and OwlBear checkout must be on the same drive on Windows.

The project should already be a Git checkout with a GitHub `origin`. If it has no GitHub remote,
pass its `OWNER/NAME` explicitly to `setup/init.py` as shown below.

## Fast path

Replace `/path/to/owlbear`, `/path/to/project`, and `OWNER/PROJECT` with your paths and repository
identity. Keep the OwlBear checkout available; multiple projects can share it.

```shell
# Clone the rolling consumer branch once.
git clone https://github.com/OWNER/owlbear.git /path/to/owlbear

# Run setup from the project root.
cd /path/to/project
uv run --project /path/to/owlbear python /path/to/owlbear/setup/init.py \
  --github-repository OWNER/PROJECT

# Open the configured project.
code .
```

Expected result: `.vscode/settings.json`, `.vscode/mcp.json`, and tracked
`.owlbear/delivery/config.json` exist in the project. Existing project settings are merged, not
replaced. If the project already has a GitHub `origin`, you may omit `--github-repository`.

Windows PowerShell uses the same steps with PowerShell paths. The [setup guide](setup/setup-guide.md)
has a copy-paste example and the same-drive limitation in full.

## Verify the setup

In the project window:

1. Open Copilot Chat and **Chat: Open Customizations**. OwlBear agents, skills, instructions, and
    prompts should be listed.
2. Run **MCP: List Servers**. These five servers should show `running`:
    `owlbear-delivery`, `owlbear-knowledge`, `owlbear-memory`, `owlbear-browser`, and `markitdown`.
3. If a server or customization is missing, check the paths in `.vscode/settings.json`, then rerun
    `setup/init.py` from the project root. See [troubleshooting](#troubleshooting) for the common
    failures.

Expected result: VS Code can see the shared OwlBear customization and all five seeded tool
connections.

## Try the first workflow

Use a small, real outcome so the result is easy to recognize:

1. Run `/ideate` and describe the outcome you want.
2. Run `/design`, review the proposed work, and approve it. This creates the tracked Change that
    Delivery will execute.
3. Run `/orchestrate <change-id>` after approval. Planning and Build work then proceed in order.
4. Launch [Cockpit](#open-cockpit) from the project root and confirm the Change is visible.

Expected result: one Change appears in Cockpit with its current work and next human action. Use the
[Delivery Workflow](setup/setup-guide.md#delivery-workflow) when you need correction, publication,
acceptance, or recovery details.

## Open Cockpit

Run this from the consumer project root:

```shell
uv run --project /path/to/owlbear cockpit
```

Cockpit opens `http://127.0.0.1:8420` and reads this project's Delivery and Memory state. Set
`COCKPIT_NO_OPEN=1` to suppress the browser or `COCKPIT_PORT` to choose another port. Consumers use
the prebuilt bundle and do not need Node/npm.

## Keep it current

Pull the shared OwlBear checkout when you want newer agents, skills, instructions, prompts, or
runtime fixes:

```shell
git -C /path/to/owlbear pull
```

Rerun `setup/init.py` from each project when copied hooks or seed-managed runtime files need
refreshing. Ordinary reruns preserve project settings and existing Delivery policy. Use the
[configuration refresh](setup/setup-guide.md#refreshing-consumer-configs) procedure when you
intentionally want to replace the five seeded editor and lint configuration files.

## Troubleshooting

| Symptom | First action |
| --- | --- |
| Agents, skills, or prompts are missing | Check the shared paths in `.vscode/settings.json`; rerun setup from the project root |
| An MCP server is missing or stopped | Open **MCP: List Servers**, check the OwlBear path, and run `uv sync --all-extras` in the OwlBear checkout |
| Setup cannot determine the repository | Add `--github-repository OWNER/PROJECT` or configure a GitHub `origin` in the project |
| Cockpit cannot find the workspace or `dist/` | Launch it from the project root with `--project /path/to/owlbear`; pull the current `main` checkout |
| Knowledge or Browser behaves unexpectedly | Treat it as Alpha, check its [package guide](serve/README.md), and record a reproducible gap |

For optional profile settings, browser-backed tests, customization, sharing, and complete recovery
procedures, continue to the [setup guide](setup/setup-guide.md).
