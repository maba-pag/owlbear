# owlbear-mcp-kanban — Target Delivery MCP Server

MCP server for authored Design, Delivery planning and execution, reviewed Integration, and completed
change history. It is registered in VS Code as `ob-kanban` and composes the Delivery portfolio from
explicit startup configuration.

→ Parent: [README.md](../../README.md)

---

## Launch / Usage

```bash
uv run python -m owlbear_mcp_kanban
```

Typically launched as a stdio MCP server via VS Code's `mcp.json`/`settings.json` — not invoked directly.

### Tools

The server exposes 23 tools:

| Area | Tools |
|------|-------|
| Design | `create_design_session`, `read_design_session`, `revise_design_session`, `publish_design_checkpoint`, `derive_delivery_contract`, `validate_delivery_contract`, `admit_delivery_change` |
| Portfolio | `list_work_items`, `show_work_item`, `acquire_frontier_work`, `show_plan_context`, `show_build_context` |
| Delivery | `publish_delivery_plan`, `publish_delivery_result`, `transition_delivery`, `recover_claim` |
| Integration | `list_integration_ready_changes`, `show_integration_attention`, `integrate_ready_change`, `admit_reviewed_integration_repair` |
| Completed changes | `list_completed_changes`, `search_completed_changes`, `show_completed_change` |

## Configuration

`setup/init.py` creates `.owlbear/delivery/config.json` in the consuming workspace and preserves
local edits on later setup runs. Normal VS Code MCP launch uses the workspace folder as its working
directory, so no Delivery environment variable is required.

```json
{
 "schema_version": 1,
 "integration_target": "main"
}
```

The workspace root determines the repository and the canonical `.owlbear/delivery/packages`,
`.owlbear/target`, and `.owlbear/worktrees` locations. Delivery admits one active claim and one Build
writer at a time. Agent frontmatter owns model selection; Kanban owns the fixed Planner, Builder,
and reviewer routing. `integration_target` names the branch from which change worktrees start and
into which reviewed changes are integrated.

| Variable | Default | Description |
|----------|---------|-------------|
| `OWLBEAR_WORKSPACE_ROOT` | Current working directory | Workspace used to verify the existing target-cutover receipt. |
| `OWLBEAR_TARGET_CUTOVER_REQUEST` | `.owlbear/target-cutover-request.json` | Absolute or workspace-relative cutover request used only for receipt authorization. |

The canonical `.owlbear/target` path must match the receipt-authorized target path. Use
`OWLBEAR_WORKSPACE_ROOT` only when launching outside the consuming workspace.

## Dependencies

| Package | Purpose |
|---------|---------|
| `mcp[cli]` | FastMCP server framework |
| `owlbear-kanban` | Target authority, execution, evidence, and cutover engine |
