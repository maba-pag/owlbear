# EnrichmentStore — Queue State Machine Research

> **Owning task:** #1875 — Knowledge: EnrichmentStore — queue state machine
> **Date:** 2026-05-25 **Status:** Complete

## 1. Context and Question

Implement the EnrichmentStore queue state machine as a new `stores/enrichment.py` module. The protocol is defined; the implementation is greenfield. Key questions:
1. What table schema supports the AC and protocol?
2. How do AC and protocol discrepancies resolve?
3. What patterns from existing stores and prior art apply?

## 2. Sources Studied

| # | Source | Relevance | What was taken |
|---|--------|-----------|----------------|
| 1 | `protocols/enrichment.py` — EnrichmentStore protocol | 1.0 | Authoritative interface: enqueue_chunks, discard_chunks, claim_batch, mark_failed, stats |
| 2 | `protocols/ARCHITECTURE.md` — Spec Amendment Process | 1.0 | "Method signature changes require a new CP entry" — protocol is authoritative |
| 3 | `protocols/DESIGN_DECISIONS.md` CP10, CP22 | 1.0 | CP10: state machine only, no LLM; CP22: claim_ttl is internal invariant |
| 4 | `schema.py` — existing enrichment columns on chunks | 0.9 | Legacy: enrichment_state, claimed_at, claimed_by, claim_token on chunks table |
| 5 | `graph_store.py`, `source_store.py` — store patterns | 0.9 | Patterns: __init__(conn), parameterized SQL, commit after writes, static helpers |
| 6 | litements/litequeue (GitHub) | 0.8 | SQLite queue: IMMEDIATE transactions for claiming, UPDATE...RETURNING, WAL mode |
| 7 | rails/solid_queue (GitHub) | 0.7 | Batch claiming: separate claimed_executions table, semaphore-based claiming |
| 8 | Task #1876 AC (sibling task) | 0.8 | submit_extractions uses batch_id; confirms batch_id as ownership primitive |

## 3. Analysis

### 3.1 Protocol vs AC Discrepancy Matrix

| Aspect | Protocol (authoritative) | AC (#1875) | Resolution |
|--------|--------------------------|------------|------------|
| State enum | `IN_PROGRESS` | `CLAIMED` | Protocol wins; enum value is "in_progress" |
| Failure method | `mark_failed(chunk_id, error)` with retry logic | `fail_chunk(batch_id, chunk_id, error)` always→FAILED | Protocol wins (retry is superior design) |
| Release | Not defined | `release_claim(batch_id)` | Implementation adds it (crash recovery, non-breaking addition) |
| Stats fields | `EnrichmentStats(pending, in_progress, completed, failed)` | "pending, claimed, completed, failed" | Protocol wins (field named `in_progress`) |

**Governance**: Per ARCHITECTURE.md Spec Amendment Process, the protocol is authoritative. The implementation MUST conform to it. AC discrepancies need architect resolution.

### 3.2 Table Design

Two tables per AC7, conforming to `enrich_*` ownership prefix:

**`enrich_queue`** — individual queue items:
```sql
CREATE TABLE IF NOT EXISTS enrich_queue (
    id          TEXT PRIMARY KEY,
    chunk_id    TEXT NOT NULL,
    source_id   TEXT NOT NULL,
    state       TEXT NOT NULL DEFAULT 'pending',
    batch_id    TEXT,
    attempts    INTEGER NOT NULL DEFAULT 0,
    last_error  TEXT,
    enqueued_at TEXT NOT NULL,
    started_at  TEXT,
    completed_at TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_enrich_queue_chunk ON enrich_queue(chunk_id);
CREATE INDEX IF NOT EXISTS idx_enrich_queue_state ON enrich_queue(state);
CREATE INDEX IF NOT EXISTS idx_enrich_queue_batch ON enrich_queue(batch_id);
```

**`enrich_batches`** — batch-level tracking:
```sql
CREATE TABLE IF NOT EXISTS enrich_batches (
    batch_id    TEXT PRIMARY KEY,
    claimed_at  TEXT NOT NULL,
    batch_size  INTEGER NOT NULL,
    max_retries INTEGER NOT NULL DEFAULT 3
);
```

### 3.3 Implementation Patterns (from codebase)

| Pattern | Source | Apply to EnrichmentStore |
|---------|--------|--------------------------|
| `__init__(self, conn)` | GraphStore, KnowledgeSourceStore | Yes — receive pre-initialized connection |
| Parameterized SQL (no f-strings) | All stores | Yes — prevents SQL injection |
| `self._conn.commit()` after writes | All stores | Yes |
| Static helpers for serialization | GraphStore._load_meta | Minimal — states are plain strings |
| `ensure_tables()` as class/static method | New pattern (AC7) | Yes — idempotent DDL in a classmethod |

### 3.4 Claim Expiry (CP22)

Per CP22, `claim_ttl` is a system invariant (not caller-tunable). Implementation should:
- Store `claimed_at` (started_at) in enrich_queue
- On `claim_batch`, optionally auto-release stale claims (started_at > TTL) before selecting new items
- TTL value is a module-level constant (e.g. 600s matching existing MCP behavior)

### 3.5 Migration from Legacy Chunks-Based State

The legacy system stores enrichment state on the chunks table. The new enrich_* tables provide clean separation. Migration path:
- New module owns only enrich_* tables
- Legacy MCP code continues using chunks columns until replaced
- No migration of existing data needed (greenfield implementation)

### 3.6 Prior Art Summary

| Library | Pattern | Applicable Insight |
|---------|---------|-------------------|
| litequeue | IMMEDIATE txn for atomic claim, UPDATE...RETURNING | Atomic claim via transaction, WAL mode |
| Solid Queue | Separate claimed_executions table | Batch table justifies enrich_batches |
| honker | claim_batch(worker_id, n) + ack_batch | Batch as first-class entity |

## 4. Recommendation

**Implement following the protocol as-is**, adding `release_claim` as a non-protocol extension for crash recovery. Create an advisory DR for the architect to resolve AC/protocol naming discrepancies.

**Confidence: 0.78** — Protocol is clear for 5 of 7 AC items; the 2 discrepancies (release_claim, fail_chunk naming) need architect input but don't block queue table implementation.

**Challenge: reconsider** — Challenger correctly identified governance issues with treating AC as authority over protocol (confidence in original: 0.37). Revised to protocol-first approach. Key insight: ARCHITECTURE.md's Spec Amendment Process makes protocol authoritative; AC conflicts are resolution items, not implementation guidance.

## 5. Follow-up Tasks

1. Advisory DR: Resolve AC/protocol discrepancies (state naming, release_claim, fail_chunk vs mark_failed)
2. Implementation task remains at research→backlog with refined guidance
