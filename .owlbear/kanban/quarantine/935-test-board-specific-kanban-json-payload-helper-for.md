---
id: 935
title: Test board-specific kanban JSON payload helper for BearClaw board CLI tests (RED)
status: archived
priority: nice-to-have
created: 2026-03-22T04:41:07.5881815+01:00
updated: 2026-03-24T01:14:57.721927+01:00
started: 2026-03-24T01:14:57.721927+01:00
completed: 2026-03-24T01:14:57.721927+01:00
tags:
    - cli
    - test
    - tooling
    - phase-14
    - type:test
    - scope:cli
depends_on:
    - 910
class: standard
---

Research follow-up from docs/research/bearclaw-board-kanban-json-fixtures.md. Add failing tests for an importable tests/cli_board_fixtures.py helper. AC: (1) tests/test_cli_board_fixtures.py defines the executable contract for board_task(), board_move(), and board_payloads() helpers that return paired kanban-md list/log JSON from shared semantic inputs; (2) tests cover assignee precedence and latest-move age fixtures, including created fallback and wrong-destination ignore cases; (3) tests/test_cli_board.py updates at least two existing happy-path cases to consume the helper while keeping subprocess routing local to that file; (4) scope stays under tests/ only and does not touch tests/conftest.py, src/, or the generic subprocess helper lane covered by #926; (5) all new assertions fail before the paired implementation task lands. See docs/research/bearclaw-board-kanban-json-fixtures.md §Follow-up Tasks.

[[2026-03-24]] Tue 00:08

## Research

Doc: docs/research/board-fixture-helper-red-gate.md

Gate validation of parent research (docs/research/bearclaw-board-kanban-json-fixtures.md, task #923):

- Theoretical validity: PASS â€” factory extraction of paired list/log payloads is standard pytest pattern
- Prior art: PASS â€” pytest factory fixtures + existing _task/_move pattern (2 sources)
- Technical feasibility: PASS â€” standard Python module import, no new deps
- Architecture fit: PASS â€” tests/ only, clear boundary with archived #926
- Dependencies satisfied: #910 (archived), #926 (archived)
- YAGNI: helpers used only in test_cli_board.py today; priority nice-to-have is correct
- DUPLICATE: #935 and #936 are near-identical tasks; created follow-up #973 to consolidate
- Confidence: .90
