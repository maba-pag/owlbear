# owlbear-mcp-kanban — Delivery MCP Server

MCP server for admitting delivery changes and operating their native job, request, evidence, and health records. It is registered in VS Code as `ob-kanban` and uses the filesystem-backed OwlBear delivery stores.

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
| Change admission | `list_changes`, `show_change`, `validate_change`, `change_health`, `admit_change` |
| Dispatch and claims | `pick_jobs`, `start_job`, `release_job`, `recover_expired_claims` |
| Completion | `finish_plan`, `finish_build`, `finish_accept`, `finish_audit` |
| Work inspection | `list_jobs`, `show_job`, `list_attempts`, `list_activity`, `show_receipt`, `work_health` |
| Requests | `create_request`, `list_requests`, `show_request` |

Change operations use a `change_id` and immutable delivery digest. Work operations additionally validate the candidate revision and claim or attempt identity appropriate to the operation. Completion tools persist immutable receipt evidence through the native runtime transaction boundary.

`admit_change` validates a change revision before atomically publishing its admission receipt, generation, native jobs, and reserved job-ID sequence. `pick_jobs` returns dependency-eligible dispatch waves; `start_job` creates a claimed attempt; the four `finish_*` tools enforce phase-specific evidence and state transitions.

The request tools create and inspect structured decision or action requests for an admitted revision. Text bodies normalize literal `\n` sequences at ingress; send `\\n` in JSON to preserve a literal sequence.

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `KANBAN_TOOLS_EXCLUDE` | _(none)_ | Comma-separated native tool names to remove from the live registry at startup. |
| `OWLBEAR_WORK_ROOT` | `.owlbear/kanban` | Optional native work-root override. Relative values resolve from process working directory, then normalize to absolute paths. |

If `OWLBEAR_WORK_ROOT` is unset or empty, the server uses `.owlbear/kanban` relative to the current working directory.

## Dependencies

| Package | Purpose |
|---------|---------|
| `mcp[cli]` | FastMCP server framework |
| `owlbear-kanban` | Kanban engine (workspace package) |
