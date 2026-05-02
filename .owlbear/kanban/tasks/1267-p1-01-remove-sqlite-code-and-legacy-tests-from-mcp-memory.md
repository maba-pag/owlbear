---
id: 1267
title: 'P1-01: Remove SQLite code and legacy tests from mcp-memory'
status: todo
priority: needed
created: 2026-05-02T03:43:26.887977+00:00
updated: 2026-05-02T03:45:18.088483+00:00
tags:
- phase-1
- scope:mcp-memory
- cleanup
parent: 1266
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective

Remove all SQLite-based code from `serve/mcp-memory/` and its legacy tests. Clear the module for the new file-based engine.

Brief: see parent #1266

## Scope

**In scope:**
- Delete `server.py` (SQLite DDL, connection management)
- Delete `migrate.py` (migration utilities)
- Delete `approve.py` (SQLite approval logic)
- Delete `tools.py` (old SQLite-backed tool implementations)
- Delete `tests/test_server.py` and `tests/test_package.py`
- Clean `__init__.py` and `__main__.py` to empty stubs
- Remove any alembic/migration artifacts if present

**Out of scope:**
- Writing new code (handled by subsequent tasks)
- Modifying `pyproject.toml` deps (handled by engine task)
- Modifying `models.py` (replaced in #1269)

## Acceptance Criteria

- [ ] No SQLite imports remain in `serve/mcp-memory/src/`
- [ ] No `*.db` files or migration scripts in the package
- [ ] Old test files removed (`test_server.py`, `test_package.py`)
- [ ] Module still importable (empty `__init__.py` at minimum)
- [ ] `uv run pytest serve/mcp-memory/tests/` passes (no tests = pass)