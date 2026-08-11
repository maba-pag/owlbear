# owlbear-delivery-mcp — Target Delivery MCP Server

MCP server for authored Design, Delivery planning and execution, reviewed Integration, and completed
change history. It is registered in VS Code as `owlbear-delivery` and composes the Delivery portfolio from
explicit startup configuration.

→ Parent: [README.md](../../README.md)

---

## Launch / Usage

```bash
uv run python -m owlbear_delivery_mcp
```

Typically launched as a stdio MCP server via VS Code's `mcp.json`/`settings.json` — not invoked directly.

### Tools

The server exposes 33 tools:

| Area | Tools |
|------|-------|
| Design | `create_design_session`, `read_design_session`, `revise_design_session`, `publish_design_checkpoint`, `derive_delivery_contract`, `validate_delivery_contract`, `admit_delivery_change` |
| Portfolio | `list_work_items`, `show_work_item`, `acquire_frontier_work`, `show_plan_context`, `show_build_context`, `show_integration_repair_context`, `create_integration_repair_candidate` |
| Delivery | `publish_delivery_plan`, `publish_delivery_result`, `finalize_change`, `mark_change_ready`, `reconcile_finalization_head`, `reconcile_change_checkpoint`, `transition_delivery`, `recover_claim`, `recover_integration_repair_claim` |
| Publication | `observe_change_publication_checks` |
| Integration | `list_integration_ready_changes`, `show_integration_attention`, `integrate_ready_change`, `prepare_external_completion`, `admit_reviewed_integration_repair`, `publish_integration_repair_authority_attention` |
| Completed changes | `list_completed_changes`, `search_completed_changes`, `show_completed_change` |

## Configuration

`setup/init.py` creates the tracked project policy `.owlbear/delivery/config.json` in the consuming
workspace and preserves project edits on later setup runs. Normal VS Code MCP launch uses the workspace folder as its working
directory, so no Delivery environment variable is required.

```json
{
 "schema_version": 2,
 "remote": "origin",
 "target_branch": "main",
 "github_repository": "your-org/your-project"
}
```

The workspace root determines the repository and the canonical `.owlbear/delivery/packages`,
`.owlbear/delivery/runtime`, and `.owlbear/delivery/worktrees` locations. Delivery admits one active
claim and one Build writer at a time. Agent frontmatter owns model selection; Delivery owns the fixed
Planner, Builder, and reviewer routing. Startup validates the configured remote, the exact
`refs/remotes/<remote>/<target_branch>` commit, and the GitHub `owner/name` identity parsed from that
remote URL. It does not require or inspect a local target branch.

The tracked `.owlbear/delivery/verification.json` profile declares ordered argv, working directory,
timeout, and environment-name allowlist for exact-candidate verification. `integrate_ready_change`
anchors the merged candidate, runs that profile in a disposable detached worktree outside the MCP
event loop, persists bounded request and receipt evidence, then revalidates package, source, target,
and candidate identities before compare-and-swap publication. A passing receipt is replayed after an
interruption. Missing, invalid, changed, timed-out, or failing verification is reported as typed
Integration attention without moving the target. See [setup-guide.md](../../setup/setup-guide.md) for
profile scaffolding and ownership.

Delivery has no environment configuration. The server must be launched with the consuming workspace
as its current directory. Startup fails closed when nonempty retired `.owlbear/target` or
`.owlbear/worktrees` roots remain, so live state cannot be silently orphaned before migration.

## Dependencies

| Package | Purpose |
|---------|---------|
| `mcp[cli]` | MCPServer framework and CLI |
| `owlbear-delivery` | Design authority, execution, Integration evidence, and completed history |
| `owlbear-delivery-github` | Fixed GitHub API adapter for draft pull-request publication |
