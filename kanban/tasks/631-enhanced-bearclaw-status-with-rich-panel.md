---
id: 631
title: Enhanced bearclaw status with rich.panel
status: archived
priority: important
created: 2026-03-07T05:27:00.1282469+01:00
updated: 2026-03-07T18:08:27.3550449+01:00
started: 2026-03-07T07:52:11.0212845+01:00
completed: 2026-03-07T18:08:27.3550449+01:00
tags:
    - phase-cli
    - scope:cli
    - cli
depends_on:
    - 643
class: standard
---

Replace `_daemon_status()` in `src/bearclaw/cli.py` with a rich.Panel + Table display.
See `docs/enhanced-bearclaw-status-research.md` for research.

## AC

### Default display (`bearclaw status`)

- [ ] `_daemon_status()` uses `rich.Console` + `rich.Panel` + `rich.Table` (lazy imports, matching `project_list()` pattern)
- [ ] Panel title is `"OwlBear Status"`
- [ ] Table is headerless (`show_header=False, box=None`) with key-value rows
- [ ] Default rows: **Status** ("Running" / "Stopped" / "Stale"), **PID** (int or "—"), **Uptime** (humanized or "—"), **Project** (name or "None")
- [ ] Uptime computed from `owlbear.pid` file mtime: format `Xd Xh` when >= 1 day, `Xh Xm` otherwise; shown only when running
- [ ] Active project read from `config_dir/active_project` file; show `"None"` when file missing or empty
- [ ] Panel `border_style="green"` when running, `border_style="red"` when stopped or stale
- [ ] Panel rendered with `Panel.fit()` to avoid full-terminal-width expansion

### Detail display (`bearclaw status --detail`)

- [ ] `--detail` is a `typer.Option(bool)` flag on `status_cmd()`
- [ ] When `--detail`, additional rows appended: **Model** (`settings.chat_model`), **Autonomous** ("on"/"off"), **Heartbeat** ("enabled (Xs)" / "disabled"), **Slack Channel** (ID or "—")
- [ ] Settings read from `OwlBearSettings()` — single instantiation

### Pipe safety

- [ ] Use `Console()` with no manual terminal detection — rich auto-detects pipe and strips ANSI (no code needed, just don't override)

### Quality

- [ ] Existing `test_cli_daemon.py::TestDaemonStatus` tests updated to assert new Panel output (tests written in #643)
- [ ] `status_cmd` signature updated to accept `--detail` parameter
- [ ] `bearclaw status` and `bearclaw status --detail` both exit 0
- [ ] ruff clean

## Architecture Notes

- `rich` is a transitive dependency via `typer` — already used in `project_list()`, no new deps needed
- Follow `project_list()` pattern: lazy import `Console`, `Table` inside function body
- Additionally import `Panel` from `rich.panel`
- Uses local `_is_process_alive()` in cli.py (DRY extraction tracked separately in #642)
- Three states: not-running (no PID file), running (PID alive), stale (PID file exists but process dead)
