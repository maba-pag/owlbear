---
id: 348
title: bearclaw project CLI commands — create, list, switch, archive
status: archived
priority: needed
created: 2026-03-01T11:20:09.5488666+01:00
updated: 2026-03-01T17:10:17.04382+01:00
started: 2026-03-01T11:22:00.6250972+01:00
completed: 2026-03-01T17:10:17.04382+01:00
tags:
    - phase-12
    - cli
    - daemon
depends_on:
    - 347
class: standard
---

## Acceptance Criteria
- [ ] Add 'project' Typer subcommand group to bearclaw CLI
- [ ] bearclaw project create --name NAME --workspace PATH (default: CWD) -> creates project via ProjectStore
- [ ] bearclaw project list -> table: name, workspace, last_active, status (active only by default, --all for archived)
- [ ] bearclaw project switch NAME -> writes project id to config_dir/active_project file
- [ ] bearclaw project archive NAME -> sets status to archived via ProjectStore
- [ ] Error handling: nonexistent project, duplicate name
- [ ] Unit tests: each subcommand with CliRunner and tmp_path ProjectStore

See docs/research/multi-project-session.md S3.9
