# owlbear — Orchestrator

Orchestrator and command-line interface for the OwlBear pipeline. Reads the kanban board, selects the highest-priority actionable task, and dispatches it to the appropriate pipeline agent via the Agent Communication Protocol (ACP).

→ Parent: [README.md](../../README.md)

---

## Launch / Usage

```bash
# Dispatch the top-priority task
uv run owlbear run

# Loop until the board is empty
uv run owlbear run --all

# Dispatch a specific task by ID
uv run owlbear dispatch <task_id>

# Print task counts per status column (and any blocked tasks)
uv run owlbear status
```

Requires `gh` (GitHub CLI with the Copilot extension) installed and on `$PATH`.

## Configuration

No environment variables. Board directory and binary path are resolved relative to the working directory:

| Path | Value |
|------|-------|
| Kanban dir | `kanban/` |
| Kanban binary | `kanban/kanban-md` |

## Dependencies

| Package | Purpose |
|---------|---------|
| `agent-client-protocol` | ACP client for dispatching tasks to agents |
| `pydantic` | Data validation for board and dispatch models |
| `typer` | CLI framework |
