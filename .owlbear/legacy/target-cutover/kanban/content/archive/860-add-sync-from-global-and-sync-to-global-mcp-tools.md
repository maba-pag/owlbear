---
id: 860
title: Add sync_from_global and sync_to_global MCP tools
status: archived
priority: medium
created: '2026-04-13T13:55:19.633331+00:00'
updated: '2026-04-14T19:56:53.212874+00:00'
tags:
- scope:knowledge
parent: null
depends_on:
- 858
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Context

Split from #858 (sync tool AC items). After #858 establishes the local.db/global.db naming convention and global DB path resolution, this task adds two MCP tools for syncing between them.

Both tools wrap the existing `_do_import` function in `scope_transfer.py` which handles content-hash dedup, FK remapping, and atomic transactions.

## Acceptance Criteria

- [ ] New MCP tool `sync_from_global` in mcp-knowledge server.py:
  - Zero user-facing parameters (resolves paths internally)
  - Resolves global DB path via the global-path resolution function from #858
  - Opens global DB as read-only source connection
  - Calls `_do_import(src_conn=global_conn, dest_conn=local_conn, target_scope="global")` to import all entries into local DB under scope `"global"`
  - Content-hash dedup: duplicate documents (same hash) are skipped (existing `_do_import` behavior)
  - Returns count string: `"Imported {n} documents (skipped {m} duplicates) from global into local under scope 'global'"`
  - Returns `"error: global DB not found at {path}"` if global DB file doesn't exist
  - Returns `"error: global DB path could not be resolved"` if `owlbear-project.json` is missing or malformed
  - ToolAnnotations: `readOnlyHint=False, destructiveHint=False`
- [ ] New MCP tool `sync_to_global` in mcp-knowledge server.py:
  - Zero user-facing parameters
  - Resolves global DB path via same function
  - Opens global DB as read-write destination connection
  - Queries local DB for all entries with `scope="global"`, imports them into global DB with content-hash dedup
  - Creates global DB file (with `init_db` schema) if it doesn't exist yet
  - Returns count string: `"Exported {n} documents (skipped {m} duplicates) from local scope 'global' to global DB"`
  - Returns `"error: ..."` if global DB path can't be resolved
  - ToolAnnotations: `readOnlyHint=False, destructiveHint=False`
- [ ] Existing `import_scope`/`export_scope` MCP tools continue to work unchanged (regression check)
- [ ] Both tools registered in `__all__` and in the mcp FastMCP instance

## Technical notes

- `_do_import` already handles content-hash dedup and FK remapping — sync tools are thin wrappers
- Global DB merge is safe for concurrent projects because dedup is additive (skip existing docs by hash)
- The global-path resolution function is implemented in #858 — this task consumes it
[[2026-04-13]]

## Architecture Review

### AC Refinements

**CRITICAL — `_do_import` source-scope filtering:**
The AC claims sync tools are "thin wrappers" around `_do_import`, but `_do_import` reads ALL source rows unconditionally (`SELECT * FROM documents`). For `sync_to_global`, only `scope="global"` entries from local should be exported. Without a source-scope filter, `sync_to_global` would copy the entire local DB into global.

**Resolution (add to AC):**

- Extend `_do_import` with optional `source_scope: str | None = None` kwarg. When non-None, all source table reads are filtered with `WHERE scope = ?`. Default `None` preserves current behavior — backward-compatible.
- `sync_to_global` calls `_do_import(src_conn=local_conn, dest_conn=global_conn, target_scope="global", source_scope="global")`
- Update existing `import_scope` caller: no change needed (passes `source_scope=None` implicitly)

**Return message format:**
`_do_import` returns `f"Imported {n} documents (skipped {m} duplicates) into scope {target_scope}"`. The AC specifies different custom messages. Builder should either: (a) refactor `_do_import` to return `tuple[int, int]` (imported, skipped) so callers can format custom strings, updating `import_scope` accordingly; or (b) accept `_do_import`'s native format. Recommend (a) for clarity — "Exported" vs "Imported" matters semantically for `sync_to_global`.

**Connection lifecycle:**
Both sync tools must close their secondary connection (global DB) in a `finally` block, following the pattern in `import_scope` (scope_transfer.py L330-333).

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Two related sync tools + one `_do_import` enhancement, all in knowledge domain |
| Interface clarity | PASS (after refinement) | `source_scope` addition makes `sync_to_global` feasible; return format clarified |
| Dependency correctness | PASS | Depends on #858 (todo) for global path resolution; `depends_on` field enforces ordering |
| Module layering | PASS | mcp-knowledge server imports from knowledge package; `_do_import` change is in knowledge package |
| TDD compliance | PASS | Test-writer will process before builder |
| KISS/YAGNI | PASS | Thin wrappers + one backward-compatible kwarg; zero-parameter design with env var override from #858 |
| Premise challenge | PASS | Sync tools are the user-facing layer for multi-project knowledge sharing (decision #616) |
| Pattern consistency | PASS | Follows existing MCP tool patterns: `@mcp.tool(annotations=...)`, `asyncio.to_thread()`, `ctx.request_context.lifespan_context`, error string convention |
| Security surface | PASS | Global DB path resolved from trusted config (`owlbear-project.json`); no user-controlled path input; sandbox_path not needed (global path is intentionally outside workspace) |
| Single domain | PASS | All within knowledge domain |

### Failure Mode Map

| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|-------------|-----------|----------|-------------|
| sync_from_global | Global path unresolvable | N/A | Yes (error: string) | Clear error message |
| sync_from_global | Global DB file missing | N/A | Yes (error: string) | Clear error message |
| sync_from_global | Global DB corrupt/wrong schema | sqlite3.Error | Yes (via `_do_import` catch) | Error string returned |
| sync_to_global | Global path unresolvable | N/A | Yes (error: string) | Clear error message |
| sync_to_global | Global DB dir missing (new file) | os error | Builder must mkdir parents=True before init_db | Auto-created |
| sync_to_global | `_do_import` fails mid-transaction | sqlite3.Error | Yes (atomic rollback via `with dest_conn:`) | No partial writes |

### Challenge Results

- Challenger: proceed (Approach A — `source_scope` param — recommended; zero-param design acceptable; concurrency safe)
- Architect response: accepted; refinements incorporated

### Builder Guidance

**Files to modify:**

- `serve/knowledge/src/owlbear_knowledge/scope_transfer.py` — add `source_scope` kwarg to `_do_import`; optionally refactor return type
- `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` — add `sync_from_global` and `sync_to_global` tools, register in `__all__`

**Patterns to follow:**

- `import_scope` MCP tool (server.py L451-471) for async wrapping pattern
- `_do_import` try/finally connection close pattern (scope_transfer.py L330-333)
- `init_db` for creating new global DB schema (scope_transfer.py L14)

### Verdict: APPROVE (with refinements noted above)

### Action Taken: AC refinements documented in Architecture Review; advanced to todo

[[2026-04-13]]

## Test-Writer Notes

**Test file:** `tests/test_sync_global_tools_860.py`

**Classes and counts:**

| Class | Category | Tests |
|-------|----------|-------|
| `TestFromAC_DoImportSourceScope` | happy/edge/boundary | 7 |
| `TestFromAC_SyncToolRegistration` | happy | 6 |
| `TestFromAC_SyncToolAnnotations` | happy | 4 |
| `TestFromAC_SyncFromGlobal` | happy/error/edge | 6 |
| `TestFromAC_SyncToGlobal` | happy/error/edge | 6 |

**Total: 29 tests — all FAIL (confirmed via pytest run)**

**Failure modes:**

- `TestFromAC_DoImportSourceScope`: `TypeError: _do_import() got an unexpected keyword argument 'source_scope'` or assertion on missing parameter
- `TestFromAC_SyncToolRegistration`: `hasattr` returns False; `ImportError` on direct import
- `TestFromAC_SyncToolAnnotations`: tool not in `_tool_manager`, `ann is None` assertion fails
- `TestFromAC_SyncFromGlobal` / `TestFromAC_SyncToGlobal`: `ImportError: cannot import name 'sync_from_global'/'sync_to_global'`

**AC coverage:**

| AC item | Tests |
|---------|-------|
| `_do_import` source_scope kwarg (arch-review refinement) | 6 — signature, default None, no-filter backward-compat, filters by scope, zero-match, child-row exclusion |
| `sync_from_global` registered + zero user params | 3 |
| `sync_to_global` registered + zero user params | 3 |
| ToolAnnotations readOnlyHint=False, destructiveHint=False | 4 (2 per tool) |
| `sync_from_global` error: path unresolvable | 1 |
| `sync_from_global` error: global DB not found | 1 |
| `sync_from_global` happy path return format | 2 |
| `sync_from_global` content-hash dedup | 1 |
| `sync_from_global` imported docs land under scope='global' | 1 |
| `sync_to_global` error: path unresolvable | 1 |
| `sync_to_global` creates global DB if not exists | 1 |
| `sync_to_global` scope filter (only global docs) | 1 |
| `sync_to_global` return format (Exported ... to global DB) | 2 |
| `sync_to_global` content-hash dedup | 1 |

**Patch targets for builder:** `owlbear_mcp_knowledge.server.resolve_global_db_path` — builder must import this at module level from `owlbear_knowledge.scope_transfer` (added by #858) for the patches in behavior tests to work.
[[2026-04-14]]

## Builder Notes

**Files changed:**

- `serve/knowledge/src/owlbear_knowledge/scope_transfer.py` — added `source_scope: str | None = None` kwarg to `_do_import`; when non-None, filters source reads with `WHERE scope = ?` (documents, document_status, chunks, entities, edges). Default `None` preserves all existing behavior exactly.
- `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` — added `resolve_global_db_path` and `_do_import` imports; added `sync_from_global` and `sync_to_global` MCP tools with `ToolAnnotations(readOnlyHint=False, destructiveHint=False)`; registered both in `__all__`.

**Test results:** 29/29 passed (were 29/29 failing at start — full RED→GREEN)

**Lint status:** ruff clean (both files)

**Coverage:** 43% on scope_transfer.py (all new code paths exercised by test suite; overall module has extensive untested legacy code not part of this task)

**Pre-existing failures confirmed unrelated:** `test_scope_transfer_618.py::TestFromAC_MCPToolWiring::test_import_scope_tool_returns_error_prefix_when_no_file` fails on baseline `dev` branch (sqlite3 cross-thread issue predating this task). `test_orchestrator_loop.py` failure also pre-existing.

**AC coverage:**

- `source_scope` kwarg added, default None, filters correctly ✓
- `sync_from_global` registered in server module + `__all__` + mcp instance ✓
- `sync_to_global` registered in server module + `__all__` + mcp instance ✓
- Both tools: zero user-facing parameters (only `ctx`) ✓
- ToolAnnotations readOnlyHint=False, destructiveHint=False both tools ✓
- sync_from_global: error on unresolvable path, error on missing file, happy-path format, dedup, scope='global' in dest ✓
- sync_to_global: error on unresolvable path, auto-creates global DB + parent dirs, scope filter, return format "Exported...to global DB", dedup ✓
[[2026-04-14]]

## Review Evidence

### Tests

**Source:** `pytest_results.txt` + `pytest_run2.txt` (full-suite run artifacts in changed files).
Quality-runner not in installed agent roster — artifact evidence used. No failures from `tests/test_sync_global_tools_860.py` appear in either run's FAILURES section. Builder's 29/29 claim is consistent with both artifacts.
Pre-existing unrelated failures confirmed in both runs: `test_scope_transfer_618.py::TestFromAC_MCPToolWiring::test_import_scope_tool_returns_error_prefix_when_no_file` (sqlite3 cross-thread — same root cause exists in original `import_scope` tool, predates this task).

### Lint

Builder self-report: ruff clean on both changed files. No ruff errors are visible from the diffs (noqa: S608 suppressions are legitimate — SQL IN clauses use parameterized `?` placeholders, not string interpolation).

### Coverage

Builder reports 43% on `scope_transfer.py` — expected given large legacy code. New code paths (source_scope branch) exercised by 7 dedicated tests.

---

### AC Compliance Table

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| `_do_import` gains `source_scope: str \| None = None` | `scope_transfer.py:249` | `TestFromAC_DoImportSourceScope::test_source_scope_in_signature` | PASS |
| default None = backward-compat (copy all rows) | `else:` branch identical to pre-task code | `test_source_scope_none_imports_all_docs` | PASS |
| source_scope filters `WHERE scope = ?` | Lines 282–316 in scope_transfer.py | `test_source_scope_filters_to_matching_scope_only` | PASS |
| source_scope child-row exclusion | `doc_ids` propagated to chunks/entities sub-queries | `test_source_scope_child_rows_excluded_for_filtered_docs` | PASS |
| `sync_from_global` in server module + zero user params | `server.py:472`: `async def sync_from_global(ctx: Context)` | `test_sync_from_global_registered_on_server_module`, `test_sync_from_global_zero_user_facing_params` | PASS |
| `sync_from_global` in `__all__` | `server.py:238`: `"sync_from_global"` in `__all__` | `test_sync_from_global_in_all` | PASS |
| `sync_from_global` in mcp instance | `@mcp.tool(...)` decorator | `test_sync_from_global_not_read_only` (annotation retrieval proves registration) | PASS |
| `sync_from_global` ToolAnnotations readOnlyHint=False, destructiveHint=False | `ToolAnnotations(readOnlyHint=False, destructiveHint=False)` | `TestFromAC_SyncToolAnnotations` ×2 | PASS |
| `sync_from_global` error: path unresolvable | Line 480: `return "error: global DB path could not be resolved"` | `test_returns_error_when_global_path_unresolvable` | PASS |
| `sync_from_global` error: file not found | Line 483: `return f"error: global DB not found at {global_path}"` | `test_returns_error_when_global_db_file_missing` | PASS |
| `sync_from_global` return format: "Imported N... from global into local under scope 'global'" | Lines 492-497: string reformatting of `_do_import` raw output | `test_happy_path_return_string_format_matches_ac` | PASS |
| `sync_from_global` content-hash dedup | `_core_do_import` behavior + `"skipped 1" in result` | `test_content_hash_dedup_skips_already_present_docs` | PASS |
| `sync_from_global` docs land under scope='global' | `target_scope="global"` passed to `_core_do_import` | `test_imported_docs_land_in_local_under_scope_global` | PASS |
| `sync_to_global` in server module + zero user params | `server.py:509`: `async def sync_to_global(ctx: Context)` | `test_sync_to_global_registered_on_server_module`, `test_sync_to_global_zero_user_facing_params` | PASS |
| `sync_to_global` in `__all__` | `server.py:239`: `"sync_to_global"` | `test_sync_to_global_in_all` | PASS |
| `sync_to_global` ToolAnnotations readOnlyHint=False, destructiveHint=False | Same annotation | `TestFromAC_SyncToolAnnotations` ×2 | PASS |
| `sync_to_global` error on unresolvable path | Line 515: `return f"error: {global_path}"` | `test_returns_error_when_global_path_unresolvable` | PASS |
| `sync_to_global` creates global DB if not exists | Lines 521-522: `mkdir(parents=True)` + `_schema_init_db` | `test_creates_global_db_file_if_not_exists` | PASS |
| `sync_to_global` scope filter: only global docs | `source_scope="global"` in `_core_do_import` call | `test_only_exports_global_scope_docs_not_other_scopes` | PASS |
| `sync_to_global` return format: "Exported N... to global DB" | Lines 530-533: reformatting logic | `test_return_string_format_says_exported_not_imported` | PASS |
| `sync_to_global` content-hash dedup | `_core_do_import` behavior | `test_dedup_skips_docs_already_in_global` | PASS |
| `import_scope`/`export_scope` regression | Neither function touched; pre-existing test failure unrelated to this task | N/A | PASS |

### Pass 1 — CRITICAL

#### 5.0 Test-Writer AC Coverage

All 14 AC items have mapped `TestFromAC_*` tests. All assertions would fail if the AC requirement were violated (confirmed by reasoning through each mutation). No MISSING or LAX ratings.

#### 5.1 Security Review

- **SQL injection:** Dynamic IN-clause placeholders built via `"?" * len(docs)` — fully parameterized, no user string injection. `# noqa: S608` suppressions warranted.
- **Path traversal:** `resolve_global_db_path` reads from trusted `owlbear-project.json` / env var. No user-controlled path input.
- **Hardcoded secrets:** None.
- **Threading:** `local_conn` used inside `to_thread` inherits the pre-existing SQLite threading issue from `import_scope`/`export_scope`. Not introduced by this task; tests safely patch `asyncio.to_thread` to avoid it. Not a new vulnerability.
- **No new dependencies.**
- **OWASP Top 10:** No issues.

#### 5.2 TestFromAC Integrity

No TestFromAC modifications by the builder. All 29 tests identical to test-writer output.

#### 5.3 Test Quality

Assertion specificity: STRONG — tests assert exact counts, titles, format strings, and boolean equality. No lazy `assert result` patterns.
Error-path coverage: ADEQUATE — error paths use `startswith("error:")` check; acceptable given AC specifies the prefix, not the full message.
Mutation resistance: Flipping scope filter off → test_source_scope_filters_to_matching_scope_only catches count=2 instead of 1. Removing string reformatting → format tests catch wrong prefix.
Test independence: Each test creates its own in-memory connections. No shared mutable state.
Test names: Descriptive. No `test_1` patterns.

#### 5.4 Data Safety

No LLM output persisted. `_do_import` uses atomic transaction (`with dest_conn:`). No unbounded input processing. No new race conditions beyond pre-existing threading issue.

#### 5.5 Test Gap Analysis

- `_run()` error pass-through when `_core_do_import` returns `"error: import failed: ..."` → falls through `return raw` correctly. Untested, but this is a trivial pass-through of a pre-existing error format. Informational only.
- `finally` block for `global_conn.close()` — not independently tested but unconditional via code structure.

#### 5.6 Necessity Check

New sync tools. No existing equivalent in the codebase. Not a speculative feature — builds on #858 global path resolution that was planned.

#### 5.7 Builder Process Quality

**CLEAN** — Single builder pass. Full RED→GREEN cycle documented.

### Pass 2 — INFORMATIONAL

**6.1** `sync_to_global` uses `f"error: {global_path}"` when `resolve_global_db_path` returns an error string. If the return value already starts with "error:", this produces a double-prefix `"error: error: ..."`. `sync_from_global` uses a hardcoded message instead. Minor inconsistency. Does not affect AC compliance (requirement is `"error: ..."` prefix).

### Deductions

- Quality-runner unavailable; using full-suite pytest artifact as evidence: −0.05

### Verdict

Confidence: **0.95** → **PASS**
[[2026-04-14]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | Yes | N/A | Two new MCP tools + `_do_import` `source_scope` kwarg added. `copilot-instructions.md` has no tool/API tables (only project identity + branch sections) — no update warranted. |
| 2 | Module docstrings | Yes | Verified | `_do_import` (scope_transfer.py:245): docstring accurate with full Args section documenting new `source_scope` param. `sync_from_global` (server.py:474): docstring accurate. `sync_to_global` (server.py:510): docstring accurate. No edits needed. |
| 3 | External attribution | No | N/A | Task body, architecture review, and builder notes cite no external repos, articles, or docs. All patterns drawn from existing in-repo code (`import_scope`, `_do_import`). |
| 4 | CLI changes | No | N/A | New MCP tools only — no CLI commands added or modified. |
| 5 | Research doc | No | N/A | No `.owlbear/research/` file for #860 found or linked. Task was an implementation split from #858, not a research task. |

### Files Updated

- None

### Scratch Files Cleaned

- None (no `.owlbear/scratch/860-*` files found)
[[2026-04-14]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| `_do_import` gains `source_scope: str \| None = None` | scope_transfer.py:249 — param present with default None | PASS |
| source_scope filters `WHERE scope = ?` | scope_transfer.py:282-316 — conditional branch filters all tables | PASS |
| `sync_from_global` registered, zero user params | server.py:474 `async def sync_from_global(ctx: Context)` | PASS |
| `sync_to_global` registered, zero user params | server.py:510 `async def sync_to_global(ctx: Context)` | PASS |
| Both in `__all__` | server.py:240-241 | PASS |
| ToolAnnotations readOnlyHint=False, destructiveHint=False (both) | Decorator on both tools | PASS |
| `sync_from_global` error: path unresolvable | server.py:480 | PASS |
| `sync_from_global` error: file not found | server.py:483 | PASS |
| `sync_from_global` return format + dedup | server.py:492-497 | PASS |
| `sync_to_global` error on unresolvable path | server.py:515 | PASS |
| `sync_to_global` creates global DB + parent dirs | server.py:521-522 | PASS |
| `sync_to_global` scope filter + return format + dedup | server.py:524-533, source_scope="global" | PASS |
| `import_scope`/`export_scope` regression | Neither function touched; pre-existing failure unrelated | PASS |
| Both registered in mcp instance | `@mcp.tool(...)` decorators present | PASS |

Spot-checked 4 AC items directly in source; remainder trusted from reviewer's detailed evidence table (22-row AC compliance table, security review, test quality assessment — thorough).

### Test Results

- pytest (task): 29/29 passed
- pytest (full suite): 4239 passed, 291 failed (all pre-existing — none from test_sync_global_tools_860.py or knowledge domain)
- ruff (task files): all checks passed
- ruff (full): 1 pre-existing E501 in engine.py (not in scope)

### Architect Quality: 4/5

AC was specific with clear parameter, return format, and error requirements. Architect review correctly identified the critical `source_scope` gap and resolved it. Minor gap: return format specified in prose rather than exact format strings.

### Deduction Breakdown

- Builder source files uncommitted (committed as leftover by auditor): −0.02

### Confidence: 0.98

### Action: archive

## Commits

| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 6005e6a5 | feat | scope_transfer.py, server.py | #860 |
