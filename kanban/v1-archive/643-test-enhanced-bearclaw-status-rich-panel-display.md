---
id: 643
title: 'Test: enhanced bearclaw status rich.Panel display'
status: archived
priority: important
created: 2026-03-07T07:56:36.4417669+01:00
updated: 2026-03-07T18:08:31.6404844+01:00
started: 2026-03-07T18:08:31.6404844+01:00
completed: 2026-03-07T18:08:31.6404844+01:00
tags:
    - phase-cli
    - scope:cli
    - cli
    - test
class: standard
---

Test-first companion for #631. Write failing tests for the enhanced bearclaw status display before implementation.

Existing tests in test_cli_daemon.py::TestDaemonStatus cover the current 3-state typer.echo() output. These tests must be replaced/updated to verify the new rich.Panel output.

## AC

- [ ] Test: no PID file -> output contains 'Stopped', border would be red
- [ ] Test: PID alive -> output contains 'Running', PID number, uptime value
- [ ] Test: PID stale -> output contains 'Stale', PID number, no uptime
- [ ] Test: --detail flag -> output contains 'Model', 'Autonomous', 'Heartbeat' labels
- [ ] Test: active project set -> output contains project name
- [ ] Test: no active project -> output contains 'None' for project field
- [ ] Test: CliRunner invocation of 'bearclaw status' returns exit code 0
- [ ] All tests fail initially (no implementation yet -- tests describe the target interface)
- [ ] ruff clean

## Implementation Notes

- Use capsys or CliRunner to capture rich Console output
- Mock OwlBearSettings, _is_process_alive, PID file, active_project file
- Follow existing test_cli_daemon.py patterns
- rich Console(force_terminal=True) may be needed in test to get styled output, or force_terminal=False for plain text assertions
