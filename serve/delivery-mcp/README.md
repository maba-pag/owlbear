# owlbear-delivery-mcp — Delivery MCP Server

MCP server for authored Design, sequential Delivery planning and execution, provider-observed
publication and acceptance, and completed Change history. It is registered in VS Code as
`owlbear-delivery` and composes the Delivery portfolio from
explicit startup configuration.

**Use this guide when:** you need to configure the seeded `owlbear-delivery` server or understand
the agent-facing Design, Planning, Build, publication, and acceptance tools.

Package map: [serve/README.md](../README.md) · Project README: [README.md](../../README.md)

---

## Launch / Usage

```bash
uv run python -m owlbear_delivery_mcp
```

Typically launched as a stdio MCP server via VS Code's `mcp.json`/`settings.json` — not invoked directly.

### Tools

The server exposes these operation groups:

| Area | Tools |
| --- | --- |
| Design | `create_design_session`, `read_design_session`, `revise_design_session`, `publish_design_checkpoint`, `derive_delivery_contract`, `validate_delivery_contract`, `admit_delivery_change` |
| Portfolio | `list_work_items`, `list_retained_change_worktrees`, `show_work_item`, `acquire_frontier_work`, `show_plan_context`, `show_build_context`, `show_finalization_context` |
| Delivery | `publish_delivery_plan`, `publish_delivery_result`, `finalize_change`, `mark_change_ready`, `reconcile_finalization_head`, `reconcile_change_checkpoint`, `sync_change_with_target`, `adopt_external_head`, `promote_external_head`, `abort_target_sync_conflict`, `resolve_target_sync_conflict`, `observe_acceptance`, `resolve_change_disposition`, `defer_change`, `resume_change`, `abandon_change`, `cleanup_abandoned_change_worktree`, `cleanup_completed_change_worktree`, `recover_change_worktree`, `recover_publication_baseline`, `transition_delivery`, `recover_claim` |
| Publication | `observe_change_publication_checks`, `supersede_publication` |
| Legacy compatibility | `show_integration_attention`, `recover_integration_repair_claim` |
| Completed changes | `list_completed_changes`, `search_completed_changes`, `show_completed_change` |

The server exposes no Assembly stage or new Integration repair admission, candidate, or authority
attention operation. The compatibility tools only make persisted legacy state visible or recoverable;
current work uses sequential Change outcomes and user-owned pull-request acceptance.

## Configuration

`setup/init.py` creates the tracked project policy `.owlbear/delivery/config.json` in the consuming
workspace and preserves project edits on later setup runs. Normal VS Code MCP launch uses the workspace folder as its working
directory, so no Delivery environment variable is required.

```json
{
 "schema_version": 2,
 "remote": "origin",
 "target_branch": "main",
 "github_repository": "your-org/your-project",
 "delivery_state_branch": "owlbear/delivery-state"
}
```

The workspace root determines the repository and the canonical `.owlbear/delivery/packages`,
`.owlbear/delivery/runtime`, and `.owlbear/delivery/worktrees` locations. Delivery admits active
Planner and Builder outcome claims against one shared `execution_capacity` budget, defaulting to `3`.
Each Change retains exact Build writer custody; `writer_capacity` is rejected and is never an active
admission limit. See the [core Delivery configuration reference](../delivery/README.md#configuration).
`CapacityLedger` and `capacity.json` data are historical migration exports, not current runtime authority.
Agent frontmatter owns model selection; Delivery owns the fixed Planner, Builder, and reviewer routing.
Startup validates the configured remote, the exact
`refs/remotes/<remote>/<target_branch>` commit, and the GitHub `owner/name` identity parsed from that
remote URL. It does not require or inspect a local target branch.

The tracked `.owlbear/delivery/config.json` is required for canonical startup and contains schema
version `2` plus `remote`, `target_branch`, `github_repository`, and `delivery_state_branch`; setup
defaults the remote to `origin`, uses `main` for non-interactive target selection, writes
`owlbear/delivery-state` as the state-branch default, and infers the GitHub repository from the
remote. The ignored `.owlbear/delivery/runtime/host.json` is optional: its schema version is `1`, and
`execution_capacity` defaults to `3` when the file or field is absent. The historical
`.owlbear/delivery/runtime/capacity.json` is not current runtime state or configuration and must not
be edited manually. The Delivery server reads no environment variables.

At admission, Delivery commits the verified four-file Design package to the managed Change branch
before opening its first draft pull request. Sparse checkpoints on `delivery_state_branch` retain
frontier, publication, finalization, and completion authority without active claims, locks, process
identifiers, or local paths. A fresh clone restores the last published checkpoint and requeues
incomplete work; local `refs/owlbear/packages/*` refs are not a remote backup.

`sync_change_with_target` is an allowed Change-worktree operation. It fetches the configured
remote-tracking target and merges the exact target head into the managed Change worktree, preserving
conflicts there for review. It never updates a local or remote target ref, touches the user checkout,
or merges a pull request.

Finalization is bound to the exact current Change head in its managed worktree. The finalizer records
typed observations for the relevant maintained checks and obtains an independent exact-commit review;
Delivery does not resolve or execute a target-bound verification profile. This evidence does not claim
that GitHub can merge the Change or that the merged result passes.

`adopt_external_head` fetches one exact remote Change descendant into a fixed remote-tracking ref and
fast-forwards only the managed Change worktree. Adoption proves provenance but does not grant review
authority: it preserves the prior reviewed boundary, and Builder acquisition remains blocked until
`promote_external_head(change_id, expected_head, operation_id)` records explicit review admission for
the exact adopted head. Finalization may perform its own exact-head promotion for a completed adopted
Change after independent review. Durable adoption and promotion receipts make both operations
replayable after a process interruption.

Legacy coordination records without publication-baseline provenance fail closed during publication
summary generation. After confirming the exact Change head, baseline commit, and a clean idle managed
worktree, `recover_publication_baseline` records one replayable recovery receipt. It does not resolve
existing publication attention; use `resolve_change_disposition` separately after reviewing the repair.

Delivery has no environment configuration. The server must be launched with the consuming workspace
as its current directory. Startup fails closed when nonempty retired `.owlbear/target` or
`.owlbear/worktrees` roots remain, so live state cannot be silently orphaned before migration.

## Dependencies

| Package | Purpose |
| --- | --- |
| `mcp` | MCPServer framework |
| `owlbear-delivery` | Design authority, sequential execution, publication, acceptance observation, legacy compatibility, and completed history |
| `owlbear-delivery-github` | Fixed GitHub API adapter for draft pull-request publication |
