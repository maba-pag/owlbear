# owlbear-mcp-kanban — Target Delivery MCP Server

MCP server for querying the global semantic work portfolio and operating reviewed plan, build, and
assembly transformations. It is registered in VS Code as `ob-kanban` and loads receipt-authorized
target stores through `owlbear-kanban`.

→ Parent: [README.md](../../README.md)

---

## Launch / Usage

```bash
uv run python -m owlbear_mcp_kanban
```

Typically launched as a stdio MCP server via VS Code's `mcp.json`/`settings.json` — not invoked directly.

### Tools

The server exposes 22 tools:

| Area | Tools |
|------|-------|
| Design authority | `list_changes`, `show_change`, `validate_change`, `admit_change` |
| Portfolio | `list_work_items`, `show_work_item`, `list_work_item_activity`, `list_semantic_updates`, `show_completion_summary` |
| Execution trace | `list_frontier`, `show_job`, `show_attempt`, `show_receipt` |
| Requests | `create_request`, `resolve_request` |
| Transformations | `start_job`, `finish_plan`, `finish_build`, `finish_assembly` |
| Review correction | `respond_to_review`, `arbitrate_attempt` |
| Recovery | `recover_interrupted_task` |

Portfolio queries can span every loaded change and return stable cursor pages bound to the current
authority identity. Mutation calls require exact change, job, attempt, claim, owner, and reviewer
identities as appropriate. The server exposes no Priority, Cancel, owner Release, accept-completion,
or audit-completion operation.

`validate_change` accepts one complete target authority plus per-identity challenge and baseline
evidence, then derives the exact initial plan frontier. `admit_change` additionally requires explicit
approval for that authority digest and atomically publishes authority, runtime state, and an immutable
admission receipt. An inactive admitted change may be revised; the prior revision is retained by
digest. Active work blocks revision.

An acceptable `finish_plan` carries the independently reviewed `planned_tasks` and atomically
publishes their build jobs. The plan receipt retains that exact task payload; build receipts then
advance task progress, and a declared composition claim adds an assembly job after its builds.

At process startup the server validates the configured cutover request and receipt, confirms the
bootstrap source remains retired, loads every authority and runtime from `.owlbear/target/changes/`,
and refuses startup if that boundary is absent or stale.

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `OWLBEAR_WORKSPACE_ROOT` | Current working directory | Workspace containing `.owlbear/target` and the cutover receipt. |
| `OWLBEAR_TARGET_CUTOVER_REQUEST` | `.owlbear/target-cutover-request.json` | Absolute path or workspace-relative path to the exact request used for cutover. |

The cutover request is runtime configuration and must remain byte-valid for the published receipt.
Use `setup/finalize.py` to perform the activation transaction; do not create target stores or receipts
manually.

## Dependencies

| Package | Purpose |
|---------|---------|
| `mcp[cli]` | FastMCP server framework |
| `owlbear-kanban` | Target authority, execution, evidence, and cutover engine |
