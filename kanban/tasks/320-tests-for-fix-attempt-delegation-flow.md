---
id: 320
title: Tests for fix-attempt delegation flow
status: review
priority: needed
created: 2026-03-30T20:38:27.954547+02:00
updated: 2026-04-04T23:09:56.1814758+02:00
tags:
    - scope:agents
    - test
    - phase-2
depends_on:
    - 318
class: standard
---

AC:
1. Unit tests verify retry_hint construction from error output
2. Test fix-attempt input contract validation
3. Test builder delegates after exactly 2 failures (not 1, not 3)
4. Test FIXED result triggers final verify + continue
5. Test FAILED result triggers BLOCK
6. Test fix-attempt never receives kanban tools
See docs/research/fresh-context-retry-builder.md

[[2026-04-04]] Sat 23:09
## Builder Notes
- **File changed:** `.github/skills/w-tdd-green/SKILL.md` (Step 6.3 only)
- **Tests:** 9 passed, 0 failed (`tests/test_fix_attempt_delegation_320.py`)
- **Lint:** ruff clean
- **Coverage:** N/A — contract test on Markdown files, no Python module coverage target

### Changes Applied
1. **AC1** — `retry_hint` description now explicitly references "error output" extraction and "failing tests" identification
2. **AC2** — Added cross-reference to `fix-attempt.agent.md` Input Contract by name
3. **AC3** — Added "exactly 2 failures (not 1, not 3)" threshold with mandatory sequence statement
4. **AC4** — FIXED row now names `pytest` and `ruff` explicitly; re-verify failure uses `end_work(outcome="reject")` directly
5. **AC5** — FAILED row now names "same-context retry (Step 6.2) diagnosis" and "fix-attempt diagnosis" separately
6. **AC6** — Added prerequisite blockquote: `fix-attempt` must be in builder's `agents:` array

### Builder-Discovered Issue
The word "fixed" in "The sequence is fixed" triggered the `re.IGNORECASE` regex before reaching the table row. Changed to "mandatory" to avoid false capture.
