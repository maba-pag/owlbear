# SQLite Connection Lifecycle Management in Bootstrap

> **Owning task:** #459 — Add SQLite connection lifecycle management to bootstrap
> **Date:** 2026-03-06 **Status:** Complete

## 1. Context and Question

Bootstrap creates a SQLite connection at `_build_knowledge_infra()` (line ~300) via
`sqlite3.connect()`. This connection is stored in `_KnowledgeInfra.conn` and shared with
`GraphStore`, `BookmarkStore`, `IngestPipeline`, and knowledge query services. However,
`conn.close()` is never called. `BootstrapResult.cleanup` exists and is iterated in the
CLI's `finally` block (`cli.py` ~L1179) but only contains `progress_reporter.stop`. The
connection leaks for the daemon's entire lifetime. On Python 3.13+, this emits
`ResourceWarning` when GC collects the connection object.

**Question:** What is the simplest, correct way to register `conn.close()` in cleanup?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | Python docs — `sqlite3.Connection.close()` | <https://docs.python.org/3/library/sqlite3.html#sqlite3.Connection.close> | 1.0 — Official API. Confirms `close()` is sync, rolls back pending txn if autocommit=False. Python 3.13 emits `ResourceWarning` if not called. |
| 2 | Datasette `database.py` | <https://github.com/simonw/datasette/blob/main/datasette/database.py> | .90 — Long-running Python daemon managing SQLite. Tracks all connections in `_all_file_connections` list, has explicit `close()` method that iterates and closes each. |
| 3 | OwlBear `architecture-audit.md` §ARC-04 | Local: `docs/architecture-audit.md` L45–55 | .95 — Internal finding confirming the bug and recommending cleanup list registration. |
| 4 | OwlBear `resilience-audit.md` §C-1 | Local: `docs/resilience-audit.md` L50 | .95 — Internal finding rating this CRITICAL. Notes FD accumulation over daemon lifetime. |
| 5 | Flask `ctx.py` teardown | <https://github.com/pallets/flask/blob/main/src/flask/ctx.py> | .70 — Shows cleanup-list pattern: `pop()` iterates through teardown callbacks with error suppression. Same pattern as OwlBear's `for cb in result.cleanup`. |

## 3. Analysis

### Option Comparison

| Criterion | A: Append `conn.close` to cleanup list | B: Context manager wrapper | C: `atexit.register` |
|-----------|----------------------------------------|---------------------------|----------------------|
| Simplicity | High — 1 line change in `bootstrap()` | Medium — new class or `contextlib.closing` | Medium |
| Fits existing pattern | Yes — matches `progress_reporter.stop` | No — requires refactoring call site | No — bypasses `BootstrapResult` |
| Testable | Easy — assert `conn.close` in cleanup | Easy | Hard — atexit hard to test |
| Daemon-safe | Yes — cleanup runs in `finally` block | Yes | Risky — atexit order undefined |
| KISS/YAGNI | Best — minimal change | Over-engineered for 1 connection | Adding parallel cleanup mechanism |

### Key Design Facts

1. **Single connection:** After the C-2 fix, only one `sqlite3.connect()` exists in
   bootstrap — in `_build_knowledge_infra()`. The bookmark toolset reuses `infra.conn`.
2. **Cleanup is sync:** The CLI iterates `result.cleanup` calling `cb()` (not `await`).
   `sqlite3.Connection.close()` is synchronous — perfect fit.
3. **`build_toolsets` doesn't surface `conn`:** It returns `(toolsets, knowledge_service)`.
   The connection must be threaded back to `bootstrap()` somehow.
4. **Failure tolerance:** Cleanup uses `contextlib.suppress(Exception)` — a failed
   `conn.close()` won't crash shutdown.

### Implementation Path

The cleanest approach: modify `build_toolsets` to also return the `_KnowledgeInfra`
(or just the `conn`), then append `conn.close` to `cleanup` in `bootstrap()`.

**Option A1 — Return conn from `build_toolsets`:**
Change return type to `tuple[list[AbstractToolset], KnowledgeQueryService | None, sqlite3.Connection | None]`.
In `bootstrap()`: `if conn is not None: cleanup.append(conn.close)`.

**Option A2 — Accept cleanup list as parameter:**
Pass `cleanup` list into `build_toolsets`, let it append `infra.conn.close` internally.
Avoids changing the return type but couples the function to cleanup semantics.

**Recommendation (.90 confidence): Option A2.** Passing the cleanup list is the smallest
diff — one parameter added, one `cleanup.append(infra.conn.close)` line inside
`build_toolsets`. No return type change, no new abstractions. Matches KISS.

## 4. Recommendation (.90 confidence)

**Use Option A2:** Pass the `cleanup` list from `bootstrap()` into `build_toolsets()`.
Inside `build_toolsets`, after `_build_knowledge_infra()` succeeds, append
`infra.conn.close` to the cleanup list. This is:

- **1 new parameter** on `build_toolsets` (already has 7)
- **1 line** appending `cleanup.append(infra.conn.close)`
- **0 new abstractions**
- **Consistent** with how `progress_reporter.stop` is already registered

Risk: `conn.close()` on an already-closed connection raises `ProgrammingError`, but
`contextlib.suppress(Exception)` in the CLI handles this.

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Implement SQLite connection cleanup in bootstrap" --priority critical --status todo --tags "resilience,scope:core" --body "Register infra.conn.close in BootstrapResult.cleanup. Implementation: (1) Add cleanup param to build_toolsets, (2) append infra.conn.close after _build_knowledge_infra succeeds, (3) test that conn.close appears in cleanup list, (4) test that calling cleanup closes the connection. See docs/sqlite-connection-lifecycle-research.md."
```

## 6. Testing Strategy

1. **Unit test:** After `build_toolsets()`, verify `conn.close` is in the cleanup list.
2. **Integration test:** After calling all cleanup callbacks, verify
   `conn.execute("SELECT 1")` raises `ProgrammingError` (connection is closed).
3. **Existing test pattern:** Follow `test_bootstrap_progress_stop_in_cleanup` in
   `tests/test_bootstrap.py` — same assertion style.
