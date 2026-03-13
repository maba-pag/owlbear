# Enhanced bearclaw status with rich.Panel

> **Owning task:** #631 — Enhanced bearclaw status with rich.panel
> **Date:** 2026-03-07 **Status:** Complete

## 1. Context and Question

`bearclaw status` currently outputs plain text via `typer.echo()` — three possible states
("running (PID X)", "stale PID file", "not running"). Task #631 asks: should we use
`rich.Panel` to display structured daemon info (PID, uptime, active project, channel),
and how should `--detail` work?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | rich.Panel API docs | <https://rich.readthedocs.io/en/stable/reference/panel.html> | .95 |
| 2 | rich-cli — Panel wrapping Table | <https://github.com/Textualize/rich-cli/blob/main/src/rich_cli/__main__.py> | .85 |
| 3 | Prefect server CLI / _server_utils.py | <https://github.com/PrefectHQ/prefect/blob/main/src/prefect/cli/_server_utils.py> | .75 |
| 4 | rich Console auto-detection | <https://rich.readthedocs.io/en/stable/console.html> | .70 |

## 3. Analysis

### 3.1 Display Approach

| Criterion | rich.Panel + Table (.85) | rich.Panel + Text (.70) | Plain typer.echo (.40) |
|-----------|--------------------------|------------------------|----------------------|
| Structured layout | Table rows = key-value pairs | Manual string formatting | No structure |
| Color support | Built-in style/border_style | Built-in style | Manual ANSI codes |
| Pipe safety | Console auto-detects | Console auto-detects | Needs manual check |
| Composability | Table nests inside Panel | Text nests inside Panel | N/A |
| Existing pattern | project_list() uses Table | N/A | _daemon_status() |
| KISS | Medium (2 imports) | Simple (1 import) | Simplest |

**Prior art confirms**: rich-cli wraps a `Table` inside `Panel(table, border_style="dim",
title="Options")`. Prefect uses plain text for status but `Table` for service listing.

### 3.2 Data Sources

| Field | Source | Availability | Notes |
|-------|--------|--------------|-------|
| PID | `config_dir/owlbear.pid` | Always | Read and parse int |
| Running state | `_is_process_alive(pid)` | Always | os.kill(pid, 0) |
| Uptime | `owlbear.pid` mtime | When running | `time.time() - pid_path.stat().st_mtime` |
| Active project | `config_dir/active_project` | When set | File contains project ID |
| Chat model | `OwlBearSettings().chat_model` | Always | Config value |
| Autonomous mode | `OwlBearSettings().autonomous_mode` | Always | Bool |
| Heartbeat | `OwlBearSettings().heartbeat_enabled` | Always | Bool + interval |
| Slack channel | `OwlBearSettings().slack_channel_id` | When configured | --detail only |

### 3.3 `_is_process_alive()` Duplication

Both `cli.py` (line ~1016) and `daemon.py` (line ~69) define `_is_process_alive()`.
This is a DRY violation. Recommend extracting to a shared location during implementation.

### 3.4 Pipe Detection

`rich.Console` auto-detects terminal vs pipe via `Console.is_terminal`. When piped,
`Console.print()` emits plain text without ANSI codes. No manual handling needed —
this satisfies the AC item "Piped output auto-disables color" for free.

## 4. Recommendation (.85 confidence)

**Panel + Table composition** — matches existing `project_list()` pattern and rich-cli
prior art. Implementation approach:

```
# Pseudocode — NOT to be used verbatim
console = Console()
table = Table(show_header=False, box=None, padding=(0, 1))
table.add_row("Status", "[green]Running[/]")
table.add_row("PID", str(pid))
table.add_row("Uptime", "2h 34m")
table.add_row("Project", "owlbear")

border_style = "green" if running else "red"
panel = Panel(table, title="OwlBear Status", border_style=border_style)
console.print(panel)
```

**`--detail` flag**: Add a second section with heartbeat, autonomous mode, model, slack
channel. Use `Panel.fit()` to avoid full-width expansion.

**Risk**: Minimal — rich is already a dependency; Panel + Table are stable APIs.

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Implement rich.Panel status display for bearclaw status" --priority needed --status todo --tags "phase-cli,scope:cli,cli" --body "Implement enhanced bearclaw status per docs/research/enhanced-bearclaw-status.md.\n\nAC from #631:\n- [ ] bearclaw status shows PID, uptime, active project name\n- [ ] bearclaw status --detail adds session info, channel, last activity\n- [ ] Output uses rich.Panel with colored status indicators (green/red)\n- [ ] Piped output auto-disables color (Console auto-detection)\n- [ ] Tests verify status output contains expected fields\n- [ ] ruff clean\n\nImplementation notes:\n- Use Panel(Table(...), title='OwlBear Status', border_style=color)\n- Extract _is_process_alive() to shared module (DRY fix)\n- Uptime from pid file mtime\n- --detail flag via typer.Option"
```

```
kanban\kanban-md.exe create "Extract _is_process_alive to shared utility" --priority nice-to-have --status backlog --tags "scope:core,cli" --body "DRY violation: _is_process_alive() is duplicated in cli.py (~line 1016) and daemon.py (~line 69). Extract to owlbear.core.process or similar.\n\nAC:\n- [ ] Single _is_process_alive() in shared module\n- [ ] cli.py and daemon.py import from shared\n- [ ] Tests pass, ruff clean"
```
