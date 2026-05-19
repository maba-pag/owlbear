---
id: 928
title: Implement shared CompletedProcess factory for BearClaw CLI tests
status: archived
priority: nice-to-have
created: 2026-03-21T23:37:10.4516472+01:00
updated: 2026-03-26T15:56:26.7946183+01:00
tags:
    - cli
    - test
    - tooling
    - phase-14
    - type:test
    - scope:cli
depends_on:
    - 920
    - 924
blocked: true
block_reason: 'Duplicate of #927 — identical title, AC, deps. #927 already at backlog with research gate passed.'
class: standard
---

Research follow-up from docs/research/bearclaw-cli-subprocess-result-helper.md. AC: (1) Add an importable tests/conftest.py helper that returns real text-mode subprocess.CompletedProcess values for success, non-zero exit, and malformed stdout/stderr cases. (2) Keep board-specific subprocess argument routing local to tests/test_cli_board.py, but have it compose the shared result helper. (3) Add an explicit missing-binary seam as a named OSError fixture/helper in the BearClaw CLI tests that need it. (4) Reuse the shared helper in tests/test_cli_chat.py and in board failure-path tests after #924 and #920 land. (5) Extend tests/test_conftest_helpers.py with contract coverage and duplicate-guard checks for the new helper. (6) Scope stays under tests/ only and adds no new dependency or production abstraction.

[[2026-03-24]] Tue 03:01

## Research

DUPLICATE of #927. Identical title, AC, dependencies, and research origin (docs/research/bearclaw-cli-subprocess-result-helper.md).

# 927 already passed the research gate (now at backlog) with research doc: docs/research/completedprocess-factory-implementation-gate.md

Follow-up #975 was created from #927. No additional work needed on this task.

Recommend closing or archiving #928 as duplicate.
