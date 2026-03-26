---
id: 22
title: Build CLI trigger commands
status: ideation
priority: needed
created: 2026-03-26T17:22:48.6175218+01:00
updated: 2026-03-26T17:22:48.6175218+01:00
tags:
    - phase-2
    - scope:cli
    - type:build
depends_on:
    - 20
class: standard
---

## Objective
Build the owlbear CLI commands that trigger orchestrator dispatch.

## Acceptance Criteria
- [ ] owlbear dispatch <id> - dispatch a specific task to the appropriate agent
- [ ] owlbear run - dispatch the next actionable task from the board
- [ ] owlbear run --all - dispatch tasks in a loop until no actionable tasks remain
- [ ] owlbear status - show current board summary
- [ ] CLI uses Typer or click for argument parsing
- [ ] CLI entry point configured in pyproject.toml
- [ ] Clear output: what was dispatched, what agent, outcome
- [ ] Error handling: no Copilot CLI available, no actionable tasks, task already claimed
- [ ] Unit tests for CLI argument parsing

## Context
Depends on O2 (dispatch planner). These CLI commands are the on-demand triggers that replace v1's always-on daemon.
