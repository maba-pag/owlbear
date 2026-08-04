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

`OWLBEAR_DELIVERY_CONFIG` is required and names a strict JSON document:
`setup/init.py` creates `.owlbear/delivery-config.json`, wires its absolute path into the seeded
`ob-kanban` environment, and preserves local edits on later setup runs.

```json
{
 "package_root": "/absolute/path/to/packages",
 "target_root": "/absolute/path/to/target",
 "repository_root": "/absolute/path/to/repository",
 "worktree_root": "/absolute/path/to/worktrees",
 "execution_capacity": 3,
 "writer_capacity": 1,
 "integration_target": "main",
 "role_policies": {
  "planner": {
   "worker_agent": "planner",
   "worker_model": "planning-model",
   "reviewer_agent": "planner-challenger",
   "reviewer_model": "review-model"
  },
  "builder": {
   "worker_agent": "builder",
   "worker_model": "build-model",
   "reviewer_agent": "build-reviewer",
   "reviewer_model": "review-model"
  },
  "assembly-reviewer": {
   "worker_agent": "build-reviewer",
   "worker_model": "review-model",
    "reviewer_agent": "build-reviewer",
   "reviewer_model": "review-model"
  }
 }
}
```

All roots must be absolute directory paths. Capacities must be positive integers. Every listed role
and identity is required; startup does not infer policy from agent files, environment model identity,
runtime inventory, or target state.

| Variable | Default | Description |
|----------|---------|-------------|
| `OWLBEAR_DELIVERY_CONFIG` | None | Path to the required Delivery startup JSON document. |
| `OWLBEAR_WORKSPACE_ROOT` | Current working directory | Workspace used to verify the existing target-cutover receipt. |
| `OWLBEAR_TARGET_CUTOVER_REQUEST` | `.owlbear/target-cutover-request.json` | Absolute or workspace-relative cutover request used only for receipt authorization. |

The configured `target_root` must match the receipt-authorized target path.

## Dependencies

| Package | Purpose |
|---------|---------|
| `mcp[cli]` | FastMCP server framework |
| `owlbear-kanban` | Target authority, execution, evidence, and cutover engine |
