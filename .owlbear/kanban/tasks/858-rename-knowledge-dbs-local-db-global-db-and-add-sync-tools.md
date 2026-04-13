---
id: 858
title: Rename knowledge DBs (local.db/global.db) and add sync tools
status: in-progress
priority: important
created: '2026-04-12T22:04:00.060405+00:00'
updated: '2026-04-13T17:52:41.974641+00:00'
tags:
- scope:knowledge
- quality
parent: null
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Context

The knowledge system currently uses a single `knowledge.db` file at `store/knowledge/knowledge.db` relative to the consumer project CWD. This naming is ambiguous when working across multiple projects that need to share a global knowledge base.

The approved architecture (decision #616) uses scope-based import/export with a single running DB. This task adds clear naming and sync tools on top of that foundation.

## Desired state

- **Local DB**: `{consumer_project}/.owlbear/knowledge/local.db` — project-specific + imported global knowledge
- **Global DB**: `{owlbear_install}/store/knowledge/global.db` — shared cross-project knowledge
- Global DB location resolved via `owlbear_path` from `owlbear-project.json` (gives that field a real consumer)
- Two new MCP tools for syncing between local and global

## Acceptance Criteria

- [ ] Rename default KB path from `store/knowledge/knowledge.db` to `.owlbear/knowledge/local.db` in mcp-knowledge server (`_DEFAULT_KB_PATH`)
- [ ] Update `scope_transfer.py` auto-detect path (`_AUTO_DETECT_RELATIVE`) — the local DB IS now the running DB, so auto-detect no longer makes sense for import_scope; revisit
- [ ] Seed template: ensure `.owlbear/knowledge/` directory exists (`.gitkeep` already present)
- [ ] Global DB path: `{owlbear_path}/store/knowledge/global.db` — resolved by reading `owlbear_path` from `owlbear-project.json` in CWD
- [ ] New MCP tool `sync_from_global` — imports all entries from global DB into local DB under scope `"global"`, with content-hash dedup
- [ ] New MCP tool `sync_to_global` — exports global-scoped entries from local DB, imports them into the global DB with content-hash dedup (safe for concurrent projects)
- [ ] Env var overrides: `OWLBEAR_LOCAL_KB_PATH`, `OWLBEAR_GLOBAL_KB_PATH`
- [ ] Update all tests referencing `knowledge.db` or `store/knowledge/`
- [ ] Existing `import_scope`/`export_scope` tools still work (generic scope transfer)

## Technical notes

- `import_scope` already handles content-hash dedup and FK remapping — sync tools wrap it
- The global DB merge is safe for concurrent projects because dedup is additive (skip existing docs by hash)
- `owlbear_path` field in `owlbear-project.json` finally gets a real runtime consumer
- Memory DB (`store/memory/memory.db`) is NOT part of this task — separate concern
[[2026-04-13]]
## Architecture Review

### SPLIT: sync tools moved to #860

Original AC5 (sync_from_global) and AC6 (sync_to_global) split into #860 with depends_on: [858]. Task #858 now covers path rename + global path resolution infrastructure only. AC9 (existing import/export still work) moved to #860 as regression check.

### Refined Scope for #858

**Files in scope (builder must update all):**
- `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` — `_DEFAULT_KB_PATH`, env var name
- `serve/knowledge/src/owlbear_knowledge/loader.py` — default path (line 240), env var name
- `serve/knowledge/src/owlbear_knowledge/scope_transfer.py` — `_AUTO_DETECT_RELATIVE`, auto-detect semantics
- `serve/knowledge/src/owlbear_knowledge/benchmark.py` — hardcoded `knowledge.db` (line 51)
- `README.md` — path and env var references (lines 89, 92)
- `seed/.owlbear/knowledge/.gitkeep` — already exists, no change needed

**Tests to update:**
- `serve/mcp-knowledge/tests/test_server.py` — `OWLBEAR_KB_PATH` references
- `tests/test_scope_transfer_618.py` — `.owlbear/knowledge/knowledge.db` auto-detect tests

### AC Clarifications and Missing Items

**AC1 (rename _DEFAULT_KB_PATH):** Also update `loader.py` line 240 which has the same hardcoded `store/knowledge/knowledge.db`. Both must become `.owlbear/knowledge/local.db`.

**AC2 (scope_transfer.py auto-detect — "revisit"):** Concrete directive: update `_AUTO_DETECT_RELATIVE` from `knowledge.db` to `local.db`. However, the auto-detect fallback in `import_scope` when `src_path=None` now points to the running DB itself (local.db IS the running DB). When `src_path=None` and no env var set, return `"error: explicit source path required (local DB is the running DB)"` instead of auto-detecting. Auto-detect made sense when import went from project-local into a separate global DB; now the running DB IS the local DB.

**AC7 (env vars):** Unify env var naming across server.py and scope_transfer.py:
- Server.py: rename `OWLBEAR_KB_PATH` to `OWLBEAR_LOCAL_KB_PATH`. Add fallback: `os.environ.get("OWLBEAR_LOCAL_KB_PATH") or os.environ.get("OWLBEAR_KB_PATH", _DEFAULT_KB_PATH)` for backward compat.
- Loader.py: same fallback chain.
- scope_transfer.py: already uses `OWLBEAR_LOCAL_KB_PATH` — no change needed.
- `OWLBEAR_GLOBAL_KB_PATH`: new env var, overrides the owlbear-project.json resolution.

**AC4 (global DB path resolution — missing error handling):** Add a module-level function (e.g., `resolve_global_db_path(cwd: Path) -> Path | str`) in scope_transfer.py or a new `_paths` helper:
- Read `owlbear-project.json` from `cwd`
- Extract `owlbear_path` field
- Resolve to `{owlbear_path}/store/knowledge/global.db` relative to `cwd`
- Check `OWLBEAR_GLOBAL_KB_PATH` env var first (override)
- Return `error:` prefixed string if: file not found, JSON parse error, `owlbear_path` field missing

**MISSING from original AC (add before building):**
- Update `benchmark.py` hardcoded `knowledge.db` reference (line 51)
- Update `README.md` references to `store/knowledge/knowledge.db` and `OWLBEAR_KB_PATH`

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS (after split) | Sync tools moved to #860; #858 is path+env infrastructure only |
| Interface clarity | PASS (with clarifications) | Auto-detect, env var fallback, error handling now specified above |
| Dependency correctness | PASS | No upstream deps; #860 depends on this |
| Module layering | PASS | Changes within knowledge + mcp-knowledge packages, respects layer direction |
| TDD compliance | PASS | Test-writer will process before builder |
| KISS/YAGNI | PASS | Path rename is necessary for multi-project support |
| Premise challenge | PASS | Decision #616 approved scope-based architecture; this is the naming layer |
| Pattern consistency | PASS | Follows existing error: prefix convention, env var override pattern |
| Security surface | PASS | sandbox_path already guards scope_transfer paths; global path resolved from owlbear-project.json (trusted config) |
| Single domain | PASS | All within knowledge domain |

### Failure Mode Map

| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|-------------|-----------|----------|-------------|
| resolve_global_db_path | owlbear-project.json missing | FileNotFoundError | Yes (error: string) | Clear error message |
| resolve_global_db_path | owlbear_path field missing | KeyError | Yes (error: string) | Clear error message |
| resolve_global_db_path | owlbear_path points to nonexistent dir | N/A | Yes (error: string) | Clear error message |
| server.py lifespan | .owlbear/knowledge/ dir missing | sqlite3.OperationalError | Yes (mkdir parents=True) | Auto-created |

### Challenge Results
- Challenger: SKIP (SPLIT verdict — challenger not required)

### Verdict: SPLIT
### Action Taken: Sync tools (AC5, AC6, AC9) split to #860 (depends_on: [858]). Remaining AC tightened with clarifications above. Approved to todo.
[[2026-04-13]]
## Test-Writer Notes
- Test file: tests/test_rename_knowledge_dbs_858.py
- Classes: TestFromAC_DefaultKBPath, TestFromAC_AutoDetectBehavior, TestFromAC_ResolveGlobalDbPath, TestFromAC_EnvVarRenameServer, TestFromAC_LoaderEnvVarChain, TestFromAC_BenchmarkLocalDb
- Tests per category: happy 9, edge 3, error 6, boundary 3
- Total: 21 tests, all FAIL
- ruff: clean
- Commit: dde3b2b4

AC coverage:
| AC | Tests |
|----|-------|
| AC1 (_DEFAULT_KB_PATH in server.py → local.db) | test_server_default_kb_path_is_local_db, test_server_default_kb_path_not_old_store_path |
| AC2 (_AUTO_DETECT_RELATIVE → local.db; explicit error when src_path=None) | test_auto_detect_relative_ends_with_local_db, test_auto_detect_relative_not_knowledge_db, test_import_scope_none_no_env_no_root_returns_explicit_error, test_import_scope_none_no_env_with_root_returns_explicit_error |
| AC4 (resolve_global_db_path function) | test_function_is_importable, test_resolve_happy_path_returns_path_object, test_resolve_happy_path_points_to_global_db, test_resolve_env_var_override_returns_env_path, test_resolve_env_var_overrides_even_without_json, test_resolve_missing_json_returns_error_prefix, test_resolve_malformed_json_returns_error_prefix, test_resolve_missing_owlbear_path_field_returns_error_prefix, test_resolve_nonexistent_owlbear_dir_returns_error_prefix |
| AC7 (server.py OWLBEAR_LOCAL_KB_PATH primary, OWLBEAR_KB_PATH fallback) | test_server_lifespan_reads_owlbear_local_kb_path, test_server_lifespan_local_kb_takes_priority_over_kb_path, test_server_lifespan_no_env_uses_local_db_default |
| AC7 loader.py env var chain | test_loader_main_source_references_owlbear_local_kb_path, test_loader_main_default_path_is_local_db |
| benchmark.py local.db update | test_benchmark_uses_local_db_not_knowledge_db |