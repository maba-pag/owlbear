---
description: "Upgrade this workspace's Delivery controller and migrate its Delivery state through the rehearsed procedure"
agent: agent
tools:
  - execute/runInTerminal
  - owlbear-delivery/delivery_health
  - owlbear-delivery/list_changes
  - owlbear-delivery/get_change
  - owlbear-delivery/list_work_items
  - vscode/askQuestions
---
Upgrade the Delivery controller of this workspace to ${input:revision:OwlBear commit or ref; empty for the latest commit of the checkout's branch}.

The workspace is the primary checkout that Delivery manages; run every command from its root and pass
`--project-root` with its absolute path. Stop at the first refusal, blocker or failed check and report it
unchanged; never retry a mutating step blindly.

Determine the mode once. **Pinned:** `.owlbear/controller/pin.json` exists. Read it once: `commit` is the
current release, `previous` its rollback release, and `NEW/<tool>` is
`.owlbear/controller/releases/<new commit>/.venv/bin/<tool>`. **Unpinned** (the default for consumer
projects): Delivery runs from the OwlBear checkout that the `owlbear-delivery` entry of `.vscode/mcp.json`
names with `--project` (`<owlbear>`), and `NEW/<tool>` is `uv --project <owlbear> run <tool>` once step 4
has moved that checkout.

1. **Install (pinned only)** while Delivery may still run: `delivery-controller install <revision>` from the
   current release (`.owlbear/controller/releases/<current>/.venv/bin/delivery-controller`). In a consumer
   project, add `--source <owlbear>` and the Cockpit bundle of the same commit. With no revision given,
   run `git -C <owlbear> pull --ff-only`, install `HEAD` and add
   `--bundle-source <owlbear>/serve/cockpit/dist`. With a named revision, run `git -C <owlbear> fetch`,
   extract that commit's bundle into an empty directory outside the repository with
   `git -C <owlbear> archive <revision> serve/cockpit/dist | tar -x -C <that directory>`, and install
   `<revision>` with `--bundle-source <that directory>/serve/cockpit/dist`; the checkout's `HEAD` stays
   where it is. It refuses a modified release and reuses an intact one. Report the resolved commit.
2. **Online check:** call `delivery_health`, `list_changes` and `get_change` for every Change. Report
   running claims, started or interrupted engine actions, pending checkpoints and pending publications.
   If any exists, ask the user to let the work finish or settle it; do not settle, release or repair
   anything yourself. An older running controller may lack `list_changes` and `get_change`: then report
   what `delivery_health` and, where offered, `list_work_items` show, tell the user that no per-Change
   baseline exists, and continue; steps 3 and 5 still apply. If `owlbear-delivery` does not start because
   it refuses `state-migration-required` (the checkout was already moved), skip this step and step 4 and
   rely on step 5.
3. **Stop:** with `vscode/askQuestions`, ask the user to stop `owlbear-delivery` (*MCP: List Servers* →
   *Stop*) and Cockpit, and wait for the confirmation. Do not stop or kill processes yourself.
4. **Move the checkout (unpinned only):** require an empty `git -C <owlbear> status --porcelain`, record
   `git -C <owlbear> rev-parse HEAD` as the old commit, then run `git -C <owlbear> pull --ff-only` (or
   `git -C <owlbear> checkout <revision>` when one is given) and report the old and new commits. Every
   project that uses this checkout now runs the new code; tell the user to run `/upgrade-delivery` in each
   of them before starting its Delivery again.
5. **Offline preflight:** `NEW/delivery-controller --project-root <root> preflight`. Continue only when
   `ready` is true; `controller-running` means a controller still runs.
6. **Backup:** `NEW/delivery-controller --project-root <root> backup --destination <directory outside the
   repository>` (for example `~/owlbear-delivery-backups/<UTC timestamp>`). Report the file and ref counts.
7. **Migrate:** `NEW/delivery-migrate --project-root <root> propose`. On `migration-not-required` continue;
   otherwise show the entries, then run `apply <migration_id>` and `verify <migration_id>`, which must
   reach `verified`. Never run `abort` or `resume` without the user's decision.
8. **Switch (pinned only):** ask the user to confirm the switch from the current to the new release, then
   run `NEW/delivery-controller --project-root <root> switch <new commit>`. Report the recorded `previous`.
9. **Verify and prune (pinned only) while stopped:** run `NEW/delivery-controller --project-root <root>
   verify`, which must report `verified` true for the release, its interpreter, the pin and the launchers.
   Then run `NEW/delivery-controller --project-root <root> prune`, which keeps the current and previous
   releases and refuses while a controller runs, so it belongs here, before the restart.
10. **Restart and verify:** ask the user to start `owlbear-delivery` from *MCP: List Servers* and Cockpit
    (pinned: `.owlbear/controller/bin/cockpit`; unpinned: `uv run --project <owlbear> cockpit`). Then call
    `delivery_health`, which must be `healthy`, and `list_changes`, and call `get_change` for every Change:
    each must be available and match the state step 2 recorded for it, where step 2 recorded one. In an
    unpinned workspace, remind the user to rerun OwlBear setup from the project root to refresh copied
    files.
11. **Failure after migration or switch:** ask the user to stop both controllers, copy the state with
    another `backup` to a second directory, and report. Pinned: offer `switch <previous>`; it succeeds only
    when the previous release's own gate accepts the migrated state. Unpinned: moving the checkout back to
    the old commit is safe only when step 7 reported `migration-not-required`. Restoring the step-6 backup
    is the user's decision; never restore, edit or delete Delivery state yourself.

Never edit `pin.json`, launchers or release directories by hand, never run checkout code
(`uv run python -m owlbear_delivery_mcp`, `uv run cockpit`) against a pinned workspace, and never call
Delivery tools that change state.
