---
name: kanban-md
description: "Claiming protocol and pitfalls reference for kanban-md. Per-agent command recipes live in each agent's skill file."
user-invocable: false
---

# kanban-md

Claiming protocol, command synopsis, and pitfalls for `kanban\kanban-md.exe`.
Each task is a `.md` file in `kanban/tasks/`.

## Claiming Protocol

See agent-common → **Task coordination** for the full three-phase claiming lifecycle
(claim → maintain → advance+release), dispatched vs self-selected rules, and crash safety.

Key commands:

```powershell
kanban\kanban-md.exe edit {id} --claim <agent>     # Phase 1: claim
kanban\kanban-md.exe edit {id} -a "..." -t --claim <agent>  # Phase 2: maintain
kanban\kanban-md.exe edit {id} --status <next> --release     # Phase 3: advance
```

**Dispatch rule:** Always claim by ID. Never use `pick` — it grabs the highest-priority unclaimed task, which may not be yours.

## Command Synopsis

| Command | Purpose |
|---------|---------|
| `show ID` | Read task details (default format includes body) |
| `edit ID [flags]` | Modify fields, append body, claim/release |
| `create "TITLE" [flags]` | Create a new task |
| `list [filters]` | List tasks with filters (`--status`, `--tag`, `--blocked`, `--not-blocked`, `--unblocked`, `--unclaimed`) |
| `move ID STATUS` | Change status (also `--next`/`--prev`) |
| `archive ID` | Move task to archived status |
| `delete ID --yes` | Delete a task (always pass `--yes`) |
| `board --compact` | Board overview |
| `agent-name` | Generate unique claim name for session |
| `handoff ID --claim <agent> --note "..." -t --release` | Park work for another agent |

Use `--compact` on `list`, `board`, `metrics`, `log`. Use `--json` only when piping to another tool.

## Pitfalls

- **`--unblocked` and `--not-blocked` are orthogonal.** `--unblocked` = all deps at terminal status (done/archived). `--not-blocked` = no explicit block flag. They do NOT imply each other.
- **`--unclaimed` respects `claim_timeout`** from `kanban/config.yml`. Never manually inspect `claimed_by`/`claimed_at` — the flag handles expiry server-side.
- **`--body` writes literal `\n`** instead of newlines. For multi-line content, write to a temp file and pass via `Get-Content -Raw`.
- **`--depends-on` is create-only.** Use `--add-dep`/`--remove-dep` on `edit`. `--depends-on` on `edit` silently fails.
- **Always `--yes` on delete.** Without it, the command hangs waiting for stdin.
