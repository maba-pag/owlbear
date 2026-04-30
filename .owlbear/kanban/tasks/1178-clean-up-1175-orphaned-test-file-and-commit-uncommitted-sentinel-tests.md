---
id: 1178
title: 'Clean up #1175 orphaned test file and commit uncommitted sentinel tests'
status: in-progress
priority: nice-to-have
created: 2026-04-30T00:39:02.728003+00:00
updated: 2026-04-30T00:55:40.831064+00:00
tags:
- scope:kanban
- type:chore
parent:
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---

## Context

Follow-up from #1175 (config loader sentinel-value handling).

## Work Items

1. **Commit `tests/test_support_migration_1175.py`** — 260 lines of sentinel-value tests (AC1–AC5 cycle). Currently uncommitted. Verify they pass, then commit.
2. **Delete `tests/test_storage_1175.py`** — orphaned RED test file (8 failing tests) from a superseded task definition (save_config hardening). No active save_config task exists on the board.

## AC

- [ ] `tests/test_support_migration_1175.py` is committed and all tests in it pass
- [ ] `tests/test_storage_1175.py` is deleted from the working tree and the deletion is committed
- [ ] No other orphaned test files matching `test_*_1175.py` remain
[[2026-04-30]]
## Architecture Review

**Verdict:** APPROVED → todo

### AC Assessment

| AC line | Assessment | Action |
|---------|-----------|--------|
| `test_support_migration_1175.py` committed and passing | Verifiable — binary check (file in git + pytest green) | Tightened: "all tests in it pass" |
| `test_storage_1175.py` deleted | Was conditional (delete OR reassign). Searched board: no `save_config` task exists → resolved to deterministic "deleted" | Rewrote to remove ambiguity |
| No other orphaned `test_*_1175.py` files | Verifiable — glob scan | Minor wording tweak for precision |

### Architecture Notes

- Both files exist on disk. `test_support_migration_1175.py` tests the actual #1175 AC (Phase 3 migration). `test_storage_1175.py` tests a superseded `save_config` hardening scope with no current board task.
- No dependency on other tasks. Pure cleanup chore.
- No codebase conflicts — neither file imports anything that would break on deletion.

### Dependency Analysis

None. Task is self-contained.
[[2026-04-30]]
## Test-Writer Notes
- Non-impl pass-through: `type:chore` with no testable Python interfaces.
- AC describes only git commit and file-deletion operations (`test_support_migration_1175.py` committed, `test_storage_1175.py` deleted).
- Scanned AC for implementation intent keywords (`implement`, `function`, `class`, `module`, `src/`, `serve/`, `endpoint`, `API`): none found.
- No new RED tests applicable. Passing through to builder.