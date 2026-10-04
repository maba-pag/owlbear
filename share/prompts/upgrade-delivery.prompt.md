---
description: "Upgrade this workspace's pinned Delivery controller through the rehearsed procedure"
agent: agent
tools:
  - execute/runInTerminal
  - owlbear-delivery/delivery_health
  - owlbear-delivery/list_changes
  - owlbear-delivery/get_change
  - vscode/askQuestions
---
Upgrade the pinned Delivery controller of this workspace to ${input:revision:Release commit or ref}.

The workspace is the primary checkout that Delivery manages; run every command from its root and pass
`--project-root` with its absolute path. Read `.owlbear/controller/pin.json` once: `commit` is the current
release, `previous` its rollback release. `NEW` below is
`.owlbear/controller/releases/<new commit>/.venv/bin`. Stop at the first refusal, blocker or failed check
and report it unchanged; never retry a mutating step blindly.

1. **Install** while Delivery may still run: `delivery-controller install <revision>` from the current
   release (`.owlbear/controller/releases/<current>/.venv/bin/delivery-controller`) or, on a workspace
   that is not pinned yet, `uv run delivery-controller install <revision>` from a checkout that contains
   the tool. It refuses a modified release and reuses an intact one. Report the resolved commit.
2. **Online preflight:** call `delivery_health`, `list_changes` and `get_change` for every Change. Report
   running claims, started or interrupted engine actions, pending checkpoints and pending publications.
   If any exists, ask the user to let the work finish or settle it; do not settle, release or repair
   anything yourself.
3. **Stop:** with `vscode/askQuestions`, ask the user to stop `owlbear-delivery` (*MCP: List Servers* →
   *Stop*) and Cockpit, and wait for the confirmation. Do not stop or kill processes yourself.
4. **Offline preflight:** `NEW/delivery-controller --project-root <root> preflight`. Continue only when
   `ready` is true; `controller-running` means a controller still runs.
5. **Backup:** `NEW/delivery-controller --project-root <root> backup --destination <directory outside the
   repository>` (for example `~/owlbear-delivery-backups/<UTC timestamp>`). Report the file and ref counts.
6. **Migrate:** `NEW/delivery-migrate --project-root <root> propose`. On `migration-not-required` continue;
   otherwise show the entries, then run `apply <migration_id>` and `verify <migration_id>`, which must
   reach `verified`. Never run `abort` or `resume` without the user's decision.
7. **Switch:** ask the user to confirm the switch from the current to the new release, then run
   `NEW/delivery-controller --project-root <root> switch <new commit>` (`pin` when the workspace is not
   pinned yet). Report the recorded `previous`.
8. **Restart and verify:** ask the user to start `owlbear-delivery` from *MCP: List Servers* and Cockpit
   with `.owlbear/controller/bin/cockpit`. Then run `NEW/delivery-controller --project-root <root> verify`,
   call `delivery_health` and `list_changes`, and call `get_change` for every Change: each must be
   available and match its step-2 state. Only then run `NEW/delivery-controller --project-root <root>
   prune`, which keeps the current and previous releases.
9. **Failure after the switch:** ask the user to stop both controllers, copy the state with another
   `backup` to a second directory, and report. Offer `switch <previous>`; it succeeds only when the
   previous release's own gate accepts the migrated state. Restoring the step-5 backup is the user's
   decision; never restore, edit or delete Delivery state yourself.

Never edit `pin.json`, launchers or release directories by hand, never run checkout code
(`uv run python -m owlbear_delivery_mcp`, `uv run cockpit`) against a pinned workspace, and never call
Delivery tools that change state.
