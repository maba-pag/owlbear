---
id: 1340
title: 'Audit Python 3.14.4 requirement: revert to 3.12 if no 3.14-only features used'
status: todo
priority: needed
created: 2026-05-04T15:00:05.846058+00:00
updated: 2026-05-04T15:01:06.370015+00:00
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