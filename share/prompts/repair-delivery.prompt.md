---
description: "Diagnose Delivery offline and apply supported fenced repairs"
agent: agent
tools: [execute/runInTerminal, vscode/askQuestions, read/readFile]
---

Change (optional): ${input:change:Native Change ID to scope the diagnosis, or leave empty}

Read and follow `../skills/w-delivery-repair/SKILL.md`.

Always start with the read-only bootstrap: run the fixed `delivery-diagnose inspect` operation for
the current project (optionally scoped with `--change-id`) through the uv-managed environment as
`PYTHONDONTWRITEBYTECODE=1 uv run --no-sync delivery-diagnose inspect`. If that entry is unavailable,
invoke the source fallback exactly as
`uv run --no-sync python -B serve/tools/src/owlbear_tools/delivery_diagnostics.py inspect`; do not run
`uv sync`, setup, initialization, or lifecycle commands. In a consumer project, run every command from
the project root through the OwlBear checkout (`uv --project ../owlbear run --no-sync delivery-diagnose`,
`delivery-repair` likewise) and prefix the fallback path with that checkout (`../owlbear/serve/...`).
If the terminal is unavailable, report unavailable;
do not substitute another tool. The tool declaration is not an automation-permission bypass and
does not claim to prevent arbitrary shell use. Treat the inspection as structural evidence only.

Then follow the skill: `delivery-repair classify`, one route per finding, and offline writes only
through `delivery-repair` proposals under their policy. Never edit, delete, copy, unlock, or
recover Delivery files by hand, never use Git, network, provider or process-control commands as a
repair, and never promise an automatic fix or ask the user to perform manual repair. Stopping and
restarting Delivery MCP and Cockpit is the user's step. Report bounded findings, routes, owners and
resume conditions without raw record values, absolute paths, exception text, or log lines.
