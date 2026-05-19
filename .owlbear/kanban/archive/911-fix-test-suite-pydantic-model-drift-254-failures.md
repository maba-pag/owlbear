---
id: 911
title: Fix test suite Pydantic model drift (254 failures)
status: archived
priority: important
created: 2026-04-17T10:47:30.452675+00:00
updated: 2026-04-17T20:04:08.487577+00:00
tags:
- scope:test
- type:test
- debt
parent:
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Context

`uv run pytest tests/ -n 0 -q --tb=no` shows 254 failed / 4307 passed / 189 skipped.

Representative failure: tests construct `AnalysisProposal` (and likely other models) without newly-added required fields (`category`, `pattern`, `rationale`, `suggested_action`), causing Pydantic validation errors.

## Acceptance Criteria

- [ ] `uv run pytest tests/ -q --tb=no` reports 0 failures
- [ ] No test fixes rely on removing or weakening model validation

## Resolution

**Closed as superseded by #912** (Test Lifecycle Management). Analysis showed all 254 failures are `TestFromAC_` RED-phase TDD tests across 6 categories: cdp-spike script not found (70), kanban AppContext model drift (48+46), AnalysisProposal model drift (22), .ps1→.py hook references (17), and misc (51). Fixing would patch tests about to be deleted in #913 (nuclear reset).
