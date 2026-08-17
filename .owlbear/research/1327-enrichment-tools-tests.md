# Phase 1 Enrichment Tool Tests — Research

> **Owning task:** #1327 — P2-11: Tests — Phase 1 enrichment tools (get_next_batch, store_enrichment)
> **Date:** 2026-05-05 **Status:** Complete

## 1. Context and Question

Task #1327 is a TDD RED phase: write failing tests for `get_next_batch` and `store_enrichment` MCP tools defined in Brief §4.4. Tests must FAIL (ImportError or assertion) until #1328 implements the tools.

**Key questions:**
1. How to verify atomic IMMEDIATE transactions in tests?
2. How to test WAL-mode concurrent write safety?
3. What test patterns fit the existing mcp-knowledge test suite?

## 2. Sources Studied

| # | Source | Relevance | What was taken |
|---|--------|-----------|----------------|
| 1 | `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` | 1.0 | MCP tool patterns: async, `asyncio.to_thread`, `AppContext` access |
| 2 | Brief §4.4 (`draft-knowledge-activation/brief.md`) | 1.0 | Exact specs: get_next_batch SELECT+IMMEDIATE, store_enrichment UPSERT/IGNORE |
| 3 | `serve/knowledge/src/owlbear_knowledge/schema.py` | 1.0 | Schema v11: enrichment_state, claimed_at, edge UNIQUE index, WAL |
| 4 | `tests/test_enrichment_schema_1323.py` | 0.9 | Sibling test pattern: in-memory SQLite + `init_db()` |
| 5 | `serve/mcp-knowledge/tests/test_ingest_graph_tools.py` | 0.9 | MCP tool test pattern: `_make_mcp_ctx()`, mock AppContext |
| 6 | Python `sqlite3.Connection.set_trace_callback` docs | 0.8 | Mechanism to intercept SQL and verify BEGIN IMMEDIATE |
| 7 | SQLite WAL concurrency docs + SO answers | 0.7 | WAL requires file-backed DB; multiple connections test pattern |
| 8 | `serve/kanban/tests/test_storage_io.py` L265-290 | 0.8 | Threading concurrency test pattern (50 threads + lock) |

## 3. Analysis

### Test Architecture Decision

| Approach | Pros | Cons | Fit |
|----------|------|------|-----|
| A) Pure mock (mock conn, verify SQL strings) | Fast, no DB | Doesn't prove correctness; fragile to SQL rewording | Low |
| B) Real in-memory SQLite + schema | Proves SQL works, fast | WAL is no-op on :memory: | High for AC1-7 |
| C) File-backed SQLite for WAL test | Proves WAL concurrency | Slightly slower (tmp_path) | Required for AC8 |
| **D) Hybrid: B for most + C for WAL** | Best coverage, pragmatic | Two fixture types | **Selected** |

### Per-AC Test Strategy

| AC | Test approach | Key technique |
|----|--------------|---------------|
| AC1: atomic SELECT+UPDATE IMMEDIATE | `set_trace_callback` captures SQL → assert "BEGIN IMMEDIATE" in trace | Trace callback |
| AC2: returns chunk metadata | Insert chunks with known data → call tool → assert fields in result | Real DB |
| AC3: claimed not re-returned | Call get_next_batch twice → assert no overlap in returned chunk_ids | Real DB |
| AC4: lease expiry (>10 min) | Insert chunk with old claimed_at → call get_next_batch → assert it's returned | Time manipulation |
| AC5: UPSERT entities | Insert entity → store_enrichment same entity → verify single row, updated | INSERT OR REPLACE |
| AC6: INSERT OR IGNORE edges | Insert edge → store_enrichment duplicate edge → verify single row, no error | UNIQUE constraint |
| AC7: updates enrichment_state | Call store_enrichment → SELECT chunk → assert state='enriched' | Real DB |
| AC8: WAL concurrent writes | File-backed DB + threading (2 writers) → no OperationalError | `tmp_path` + threads |

### Import Strategy (TDD RED)

Tests import `get_next_batch` and `store_enrichment` from `owlbear_mcp_knowledge.server`. These don't exist yet → ImportError makes all tests fail (RED). Once #1328 implements them, tests turn GREEN.

### Fixture Pattern

```python
# Real DB fixture (in-memory, fast)
@pytest.fixture()
def db_conn():
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    return conn


# File-backed DB fixture (WAL-capable)
@pytest.fixture()
def wal_db(tmp_path):
    path = str(tmp_path / "test.db")
    conn = sqlite3.connect(path)
    init_db(conn)
    return conn, path
```

### IMMEDIATE Transaction Verification

`sqlite3.Connection.set_trace_callback(fn)` invokes `fn(sql_statement)` for every SQL statement executed. Test captures traces into a list and asserts `"BEGIN IMMEDIATE"` appears.

### Lease Expiry Testing

Insert a chunk with `enrichment_state='claimed'` and `claimed_at` set 11 minutes in the past. Call `get_next_batch` → the stale chunk should be returned (reset to pending, re-claimed).

## 4. Recommendation

**Approach D (Hybrid):** Real in-memory SQLite for AC1–AC7, file-backed for AC8 (WAL). Uses existing patterns from sibling test suites.

**Confidence:** 0.90 — all AC items map cleanly to testable behaviors with established patterns in this codebase.

**Challenge:** SKIPPED — trivial test-strategy research for a TDD RED task. All specs come directly from Brief §4.4; no design decisions to challenge.

## 5. Follow-up Tasks

None needed — #1328 (GREEN implementation) already exists as the TDD pair.
