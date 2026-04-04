---
name: h-kanban-md
description: "Handbook (DEPRECATED): kanban-md CLI reference — use h-mcp-kanban instead"
user-invocable: false
---

# kanban-md CLI Reference (Deprecated)

> **Deprecated.** Use MCP tools via `h-mcp-kanban` for all board operations. This skill is retained as a fallback reference for direct CLI troubleshooting only. If MCP tools fail, consult this for CLI equivalents, then record the MCP failure in repo memory.

Command synopsis, flag reference, and recipes for `kanban\kanban-md.exe`.
Each task is a `.md` file in `kanban/tasks/`.

## Command Synopsis

| Command | Purpose |
|---------|---------|
| `show ID` | Read task details (default format includes body) |
| `edit ID [flags]` | Modify fields, append body, claim/release |
| `create "TITLE" [flags]` | Create a new task |
| `list [filters]` | List tasks with filters |
| `move ID STATUS` | Change status (also `--next`/`--prev`) |
| `archive ID` | Move task to archived status |
| `delete ID --yes` | Delete a task (always pass `--yes`) |
| `board --compact` | Board overview |
| `agent-name` | Generate unique claim name for session |
| `handoff ID --claim <agent> --note "..." -t --release` | Park work for another agent |

Use `--compact` on `list`, `board`, `metrics`, `log`. Use `--json` only when piping to another tool.

## Claiming Commands

```powershell
kanban\kanban-md.exe edit {id} --claim <agent>                         # Phase 1: claim
kanban\kanban-md.exe edit {id} -a "..." -t --claim <agent>             # Phase 2: maintain
kanban\kanban-md.exe edit {id} --status <next> --release               # Phase 3: advance
```

**Dispatch rule:** Always claim by ID. Never use `pick` — it grabs the highest-priority unclaimed task, which may not be yours.

## List Filters

| Flag | Purpose |
|------|---------|
| `--status <col>` | Filter by status column |
| `--tag <tag1,tag2>` | Filter by tags (comma-separated) |
| `--blocked` | Only tasks with an explicit block flag |
| `--not-blocked` | Only tasks without an explicit block flag |
| `--unblocked` | Only tasks whose deps are all at terminal status (done/archived) |
| `--unclaimed` | Only tasks with no active claim (respects `claim_timeout`) |
| `--compact` | Compact output format |
| `--json` | JSON output (for piping to tools) |

## Edit Flags

| Flag | Purpose |
|------|---------|
| `-a "text"` / `--append "text"` | Append text to body |
| `-t` / `--timestamp` | Prepend timestamp to appended content |
| `--claim <name>` | Set claim |
| `--release` | Release claim |
| `--status <col>` | Move to status |
| `--block "reason"` | Block with reason |
| `--unblock` | Remove block |
| `--tags <t1,t2>` | Replace tags |
| `--priority <level>` | Set priority |
| `--add-dep <ID>` | Add dependency |
| `--remove-dep <ID>` | Remove dependency |
| `--title "new title"` | Change title |

## Create Flags

| Flag | Purpose |
|------|---------|
| `--status <col>` | Initial status |
| `--priority <level>` | Priority |
| `--tags <t1,t2>` | Tags |
| `--depends-on <IDs>` | Dependencies (comma-separated) |
| `--parent <ID>` | Parent task ID |
| `--claim <name>` | Claim immediately |
| `--body "text"` | Initial body content |

## Board Configuration

- **Config:** `kanban/config.yml`
- **Statuses:** ideation, backlog, todo, in-progress, review, docs, done
- **Priorities:** `someday` < `nice-to-have` < `important` (default) < `needed` < `critical`

## Recipes

### Read a task

```powershell
kanban\kanban-md.exe show 480
```

### Create a follow-up task at backlog

```powershell
kanban\kanban-md.exe create "Implement retry logic" --status backlog --priority important --tags "scope:core" --depends-on 479
```

### Append Channel B notes mid-task

```powershell
kanban\kanban-md.exe edit 480 -a "## Builder Notes`nFiles changed: src/retry.py" -t --claim cedar-cloud
```

### Handoff with block

```powershell
kanban\kanban-md.exe handoff 480 --claim cedar-cloud --block "Waiting on user: credential setup" --note "## Handoff`n- Current state: tests pass`n- Open questions: need API key" -t --release
```

### Full board overview

```powershell
kanban\kanban-md.exe board --compact
```

## PowerShell Escaping Gotchas

kanban-md is a CLI binary called from PowerShell 5.1. Several PS escaping issues cause silent data corruption or parse errors.

### Pipe characters need backtick-escaping

Pipe (`|`) in markdown tables embedded in body text must be backtick-escaped in PS string arguments:

```powershell
# WRONG — PS interprets | as pipeline
kanban\kanban-md.exe edit 480 -a "| Col1 | Col2 |"

# CORRECT — backtick-escape pipes
kanban\kanban-md.exe edit 480 -a "| Col1 `| Col2 `|"
```

### `->` arrows parsed as CLI flag fragments

Body text containing `->` is parsed by kanban-md as shorthand flag fragments. Replace with prose:

```powershell
# WRONG — kanban-md misparses
kanban\kanban-md.exe edit 480 -a "builder -> reviewer"

# CORRECT — use prose
kanban\kanban-md.exe edit 480 -a "builder hands off to reviewer"
```

### `--token` patterns parsed as flags

CLI output or text containing double-dash patterns (`--cov`, `--tb`) are interpreted as kanban-md flags. Keep evidence in prose, never paste raw CLI output:

```powershell
# WRONG — --tb interpreted as a flag
kanban\kanban-md.exe edit 480 -a "Ran pytest --tb=short"

# CORRECT — describe in prose
kanban\kanban-md.exe edit 480 -a "Ran pytest with short traceback output"
```

### PS 5.1 here-strings split in ArgumentList

`@"..."@` here-strings passed via `Start-Process -ArgumentList` are split into separate args by the shell. Always use the temp-file pattern for multiline content:

```powershell
$body = @"
## Review Evidence
- Tests: 12/12 passed
- Coverage: 95%
"@
[IO.File]::WriteAllText("docs/scratch/$id-notes.tmp", $body, [Text.UTF8Encoding]::new($false))
$content = Get-Content "docs/scratch/$id-notes.tmp" -Raw
kanban\kanban-md.exe edit $id -a $content -t
Remove-Item "docs/scratch/$id-notes.tmp"
```

### Body-append with `--body` writes literal `\n`

`--body` on `create` writes literal `\n` instead of newlines. For multi-line body content at creation, write to a temp file and pass via `Get-Content -Raw`, or use `edit -a` after creation.

## Known Gotchas

- **`--unblocked` and `--not-blocked` are orthogonal.** `--unblocked` = all deps at terminal status (done/archived). `--not-blocked` = no explicit block flag. They do NOT imply each other.
- **`--unclaimed` respects `claim_timeout`** from `kanban/config.yml`. Never manually inspect `claimed_by`/`claimed_at` — the flag handles expiry server-side.
- **`--depends-on` is create-only.** Use `--add-dep`/`--remove-dep` on `edit`. `--depends-on` on `edit` silently fails.
- **Always `--yes` on delete.** Without it, the command hangs waiting for stdin.
- **`--claim` and `--release` must be separate calls.** Combining them in one `edit` command errors or silently ignores one flag. Always issue a separate `edit --release` call after the status-move.
- **Body-append requires `--claim <agent>` when task is claimed by you.** Omitting `--claim` on `edit -a` while the task is yours produces a "claimed by another agent" conflict error.
- **Task files must have LF line endings.** Python `write_text()` on Windows writes CRLF, causing "file does not start with YAML frontmatter" errors. Use `write_bytes(content.encode("utf-8").replace(b"\r\n", b"\n"))`.
