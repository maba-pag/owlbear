---
id: 778
title: Tests for bearclaw decisions commands
status: backlog
priority: nice-to-have
created: 2026-03-13T11:32:08.6438877+01:00
updated: 2026-03-13T12:33:42.3291318+01:00
started: 2026-03-13T12:28:36.4671799+01:00
tags:
    - cli
    - process
    - test
claimed_by: researcher
claimed_at: 2026-03-13T12:33:42.3291318+01:00
class: standard
---

## Context
TDD tests for the decisions CLI subcommands.
See docs/research/bearclaw-decision-commands.md for research.

## Acceptance Criteria
- [ ] tests/test_cli_decisions.py using CliRunner + tmp_path fixtures
- [ ] Test list with 0, 1, 2+ pending decisions
- [ ] Test show by task_id (found + not found)
- [ ] Test resolve interactive flow with CliRunner input= mocking
- [ ] Test resolve moves file from pending/ to resolved/
- [ ] Test malformed frontmatter graceful error
- [ ] Coverage >= 90%% for decisions.py

[[2026-03-13]] Fri 12:33
## Research
See docs/research/bearclaw-decision-tests.md for full findings.

Key testing decisions:
- Fixture strategy: tmp_path + _make_decision_file() helper (matches test_cli_project.py)
- Interactive resolve: prefer typer.prompt() over Rich Prompt.ask() for CliRunner input= compat
- Monkeypatch DECISIONS_DIR constant to redirect to tmp_path
- 7 test classes mapping 1:1 to AC items

Recommendation for #777 builder: use typer.prompt(choices=...) not Rich Prompt.ask() for testability.
