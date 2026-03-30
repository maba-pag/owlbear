---
id: 202
title: 'Test: CLI trigger commands'
status: backlog
priority: needed
created: 2026-03-30T07:54:24.5857587+02:00
updated: 2026-03-30T07:54:31.4617797+02:00
started: 2026-03-30T07:54:31.4617797+02:00
tags:
    - phase-2
    - ' scope:cli'
    - ' type:test'
    - ' test'
depends_on:
    - 20
class: standard
---

## Objective
Write failing tests for the owlbear CLI commands (dispatch, run, status) before implementation.

## Acceptance Criteria

### Test infrastructure
- [ ] Test file at `tests/test_cli.py`
- [ ] Uses `typer.testing.CliRunner` to invoke commands
- [ ] All planner and AcpClient dependencies mocked (no real subprocess/Copilot calls)

### `owlbear dispatch <task_id>` tests
- [ ] Test: valid task_id dispatches to correct agent, prints success message, exit 0
- [ ] Test: task not found returns exit 1 with error message on stderr
- [ ] Test: task already claimed returns exit 1 with error message on stderr
- [ ] Test: AcpClientError (transient) returns exit 1 with error message

### `owlbear run` tests
- [ ] Test: picks top-priority actionable task, dispatches, prints result, exit 0
- [ ] Test: no actionable tasks prints "No actionable tasks on the board.", exit 0
- [ ] Test: `--all` loops until no tasks remain, printing each dispatch result

### `owlbear status` tests
- [ ] Test: formats task counts by status column
- [ ] Test: shows blocked tasks with block reasons
- [ ] Test: exit 0

### Error handling tests
- [ ] Test: Copilot CLI not found (shutil.which mocked to None) prints install message, exit 1
- [ ] Test: all errors written to stderr via typer.echo(..., err=True)

### Constraints
- [ ] All tests must FAIL (RED phase) — no implementation exists yet
- [ ] Tests import from `owlbear.cli` (module path, not file path)
- [ ] Mock boundaries: mock `owlbear.planner` functions and `owlbear_orchestrator.AcpClient`

## Context
TDD RED phase for #22 (Build CLI trigger commands). See docs/research/cli-trigger-commands.md for command specs and testing strategy (section 3.6).
