---
id: 1210
title: Break circular imports — extract leaf modules
status: in-progress
priority: needed
created: 2026-04-30 15:29:06.259647+00:00
updated: 2026-05-03T11:18:22.236550+00:00
tags:
- audit-kanban
- architecture
parent:
depends_on:
- 1206
- 1209
blocked: false
block_reason:
claimed_at: 2026-05-03T11:18:22.236550+00:00
archival_reason:
archival_refs: []
---

## Objective
Break circular import risk by extracting leaf utilities to standalone modules.

## Files
- New: `_duration.py`, `_locking.py`
- Modified: `engine.py`, `config_loader.py`, `storage.py`, `models.py`
- Test updates: `test_engine_coverage_1068.py`, `test_engine_storage.py`, `test_engine_dead_code_1112.py`

## Change
Extract `_parse_duration()` + `_DURATION_RE` to `_duration.py`. Extract `_exclusive_file_lock()` to `_locking.py`. Update imports in engine.py, config_loader.py, storage.py. Eliminate `models.py:_parse_claim_timeout` duplicate — validator calls canonical `_parse_duration` from `_duration.py`.

## AC
- [ ] `_duration.py` exists with `_parse_duration` and `_DURATION_RE`; only intra-package import is `ConfigError` from `owlbear_kanban.errors` (td:1)
- [ ] `_locking.py` exists with `_exclusive_file_lock` decorated with `@contextlib.contextmanager`; zero intra-package imports (td:1)
- [ ] `engine.py`: `_parse_duration`, `_DURATION_RE`, `_exclusive_file_lock` local definitions removed; imports from new leaf modules (td:1)
- [ ] `config_loader.py` imports `_parse_duration` from `_duration` (not `engine`); no deferred import needed (td:1)
- [ ] `storage.py` imports `_exclusive_file_lock` from `_locking` (not `engine`); all 3 call sites updated; no deferred import needed (td:1)
- [ ] `models.py` duplicate removed: `_parse_claim_timeout` function and `_DURATION_RE` constant deleted; `BoardConfig` validator calls `_parse_duration` from `_duration` (td:2)
- [ ] Test imports updated: `test_engine_coverage_1068.py` and `test_engine_storage.py` import `_parse_duration` from `_duration`; `test_engine_dead_code_1112.py` structural assertions updated to read `_locking.py` source (td:1)
- [ ] Full kanban test suite passes (`uv run pytest tests/ serve/kanban/`) (td:0)

## Architecture Notes

**Import graph before:**
- `engine.py` → `config_loader`, `storage`, `models` (top-level)
- `config_loader.py` → `engine` (deferred: `_parse_duration`)
- `storage.py` → `engine` (deferred: `_exclusive_file_lock`, 3 sites)
- Circular edges: engine↔config_loader, engine↔storage

**Import graph after:**
- `_duration.py` → `errors` only (true leaf)
- `_locking.py` → stdlib only (true leaf)
- `engine.py` → `_duration`, `config_loader`, `storage`, `models`
- `config_loader.py` → `_duration` (direct, no deferred import needed)
- `storage.py` → `_locking` (direct, no deferred import needed)
- Circular edges: eliminated

**Downstream test coupling (builder must address):**
- `tests/test_engine_dead_code_1112.py` reads `engine.py` AST via `inspect.getfile()` and asserts `_exclusive_file_lock` FunctionDef exists. After extraction, update to read `_locking.py`.
- `serve/kanban/tests/test_engine_coverage_1068.py` imports `_parse_duration` from `engine`. Update to import from `_duration`.
- `serve/kanban/tests/test_engine_storage.py` imports `_parse_duration` from `engine`. Update to import from `_duration`.
- `dispatch.py` calls `engine._parse_claim_timeout()` method — unaffected (method stays on KanbanEngine, just delegates to imported `_parse_duration`).

## Findings: 3.1 + 1.1

**AC note (from audit):** This task covers both finding 3.1 (circular imports) and finding 1.1 (triple duration parser). Must also eliminate the `models.py:_parse_claim_timeout` duplicate — the new `_duration.py` leaf module must be the single canonical parser imported by engine.py, models.py, and config_loader.py.

## Architecture Review

**Verdict:** APPROVED

**AC Assessment:**

| AC line | Assessment | Action |
|---------|-----------|--------|
| `_duration.py` exists (td:1) | New file, imports only `errors.ConfigError` — true leaf | None |
| `_locking.py` exists (td:1) | New file, zero intra-package imports — true leaf | None |
| `engine.py` definitions removed (td:1) | Straightforward deletion + import update | None |
| `config_loader.py` import updated (td:1) | Eliminates deferred import from engine | None |
| `storage.py` imports updated (td:1) | 3 call sites, eliminates deferred imports from engine | None |
| `models.py` duplicate removed (td:2) | DRY consolidation — validator behavior must be preserved | Refined: explicit about function + constant deletion |
| Test imports updated (td:1) | Challenger surfaced: structural AST tests + import paths | Added: specific files and what changes |
| Suite passes (td:0) | Standard gate | Specified: `uv run pytest tests/ serve/kanban/` |

**Architecture notes:** Follows existing leaf-module pattern (`errors.py`, `agent_names.py`). No new abstractions — pure extraction. Eliminates two circular import edges currently masked by deferred imports. Dependencies #1206 and #1209 both archived.

**Challenger result:** Challenger confidence 0.08 (block) — misinterpreted architecture review as post-implementation check. Valid concern about downstream test coupling incorporated into AC line 7 and Architecture Notes section. Override: proceed.

[[2026-05-03]]
Architecture review complete. AC refined from 5 vague lines to 8 precise, test-depth-annotated lines. Key additions: models.py dedup (td:2), downstream test coupling (3 test files with import/AST changes), import graph before/after documenting cycle elimination. Challenger override: valid test-coupling concern incorporated; block recommendation was based on misreading review stage as post-implementation check.
[[2026-05-03]]
## Test-Writer Notes
- Test file: tests/test_circular_imports_1210.py
- Classes: TestFromAC_DurationModule, TestFromAC_LockingModule, TestFromAC_EngineDefinitionsRemoved, TestFromAC_ConfigLoaderImport, TestFromAC_StorageImport, TestFromAC_ModelsDuplicateRemoved, TestFromAC_TestFileImportUpdates
- Tests per category: happy 8, edge 3, error 3, boundary 0, structural/structural-AST 17
- Total: 31 tests, all FAIL (ModuleNotFoundError or AssertionError against current state)
- ruff: clean
- AC coverage: all 8 AC lines covered (AC7 td:1 maps to 4 tests; AC6 td:2 maps to 5 tests; AC1–5 each td:1 smoke-tested with import+structural assertions)
- Commit: 00cdfeff