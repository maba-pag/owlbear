---
id: 10
title: 'P1-10: Create tests/ skeleton with basic tests'
status: done
priority: high
created: 2026-02-24T15:05:08.5357734+01:00
updated: 2026-02-26T18:15:02.1872802+01:00
started: 2026-02-24T15:16:56.6196723+01:00
completed: 2026-02-26T18:15:02.1872802+01:00
tags:
    - phase-1
    - test
depends_on:
    - 7
    - 8
class: standard
---

## Acceptance Criteria
- Create tests/__init__.py (empty)
- Create tests/conftest.py with:
  - from __future__ import annotations
  - Common fixtures: tmp_path-based fixtures for config files, mock settings fixture
  - pytest marker registration if needed
- Create tests/test_config.py with:
  - Test that OwlBearSettings() instantiates with defaults
  - Test that provider defaults to 'copilot'
  - Test that copilot_token_path is a Path object
  - Test that env vars with OWLBEAR_ prefix override settings (use monkeypatch)
  - At least 4 test cases
- All tests must PASS (this is testing existing code from P1-08, not TDD)

## Files to Create
- tests/__init__.py
- tests/conftest.py
- tests/test_config.py

## Verification
- uv run pytest tests/test_config.py -v passes all tests
- ruff check tests/ passes
- At least 4 test cases exist and pass
