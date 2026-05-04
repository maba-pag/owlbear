---
id: 1340
title: 'Audit Python 3.14.4 requirement: revert to 3.12 if no 3.14-only features used'
status: in-progress
priority: needed
created: 2026-05-04T15:00:05.846058+00:00
updated: 2026-05-04T15:27:54.529987+00:00
tags:
- sync-blocker
- config
parent:
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Context

Both kanban and mcp-kanban pyproject.toml require >=3.14.4 but consumer branch (main) specifies >=3.12. No 3.14-only features found during audit. Syncing raises consumer runtime floor without justification.

## Acceptance Criteria

1. Grep/audit serve/kanban/ and serve/mcp-kanban/ source for Python 3.13+ or 3.14+ only syntax/features (e.g., TypeIs, type statement, PEP 728 TypedDict extras, exception groups without exceptiongroup backport)
2. If none found: revert requires-python to ">=3.12" in both pyproject.toml files
3. If found: document which feature and why, update setup-guide.md and README.md to note requirement
4. CI/tests pass with the chosen floor

## Key Files

- `serve/kanban/pyproject.toml`
- `serve/mcp-kanban/pyproject.toml`

## Source

Finding 6 in `.owlbear/research/kanban-mcp-deployment-audit.md`
[[2026-05-04]]
## Test-Writer Notes
- Test file: tests/test_python_version_floor_1340.py
- Classes: TestFromAC_RequiresPythonFloor, TestFromAC_NoUnjustifiedVersionBump
- Tests per category: happy 0, edge 0, error 0, boundary 2 (both packages, both floor and pin checks)
- Total: 6 tests, all FAIL
- ruff: clean

AC coverage:
| AC | Test(s) |
|----|---------|
| AC1: Audit source for 3.13+ features | `test_kanban_floor_justified_by_source_syntax`, `test_mcp_kanban_floor_justified_by_source_syntax` (scans source, asserts floor matches reality) |
| AC2: Revert requires-python to ">=3.12" | `test_kanban_requires_python_is_3_12`, `test_mcp_kanban_requires_python_is_3_12`, `test_kanban_does_not_pin_to_3_14`, `test_mcp_kanban_does_not_pin_to_3_14` |

All 6 tests fail with AssertionError (current: ">=3.14.4", expected: ">=3.12").