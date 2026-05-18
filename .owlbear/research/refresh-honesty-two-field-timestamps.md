# Refresh Honesty — Two-Field Timestamp Model

> **Owning task:** #1651 — P1-01: Refresh honesty — two-field timestamp model
> **Date:** 2026-05-18 **Status:** Complete

## 1. Context and Question

`_update_source_record` (refresh.py L435–452) unconditionally bumps `last_refreshed_at` to `now` after every refresh attempt, regardless of outcome. This makes `last_refreshed_at` meaningless as a health signal — a source that fails every refresh still appears "recently refreshed."

**Question:** Is the two-field timestamp model (`last_checked_at` + `last_refreshed_at`) the right fix, and what are the implementation constraints?

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| S1 | Brief `.owlbear/briefs/draft-knowledge-source-lifecycle/brief.md` | Internal | 1.0 |
| S2 | Brief data stance (`stances/data.md`) | Internal | 0.9 |
| S3 | `refresh.py` L435–452 — current `_update_source_record` | Codebase | 1.0 |
| S4 | `source_store.py` — KnowledgeSourceStore CRUD | Codebase | 1.0 |
| S5 | `schema.py` L413–440 — migration system (13 prior migrations) | Codebase | 0.9 |
| S6 | `models.py` L111–131 — KnowledgeSource model | Codebase | 1.0 |
| S7 | HTTP `Last-Modified` vs `Date` header semantics (RFC 9110 §8.8.2) | Prior art | 0.7 |

## 3. Analysis

### 3.1 Current Bug (S3)

```python
def _update_source_record(self, source, result):
    now = datetime.now(tz=UTC).isoformat()
    messages = [*result.errors, *result.warnings]
    last_error = "; ".join(messages) if messages else None
    updated = source.model_copy(update={
        "last_refreshed_at": now,  # ← always bumped
        "last_error": last_error,
        "updated_at": now,
    })
    self._store.update(updated)
```

No conditional logic — `last_refreshed_at` bumped even when all URLs fail.

### 3.2 Implementation Change Map

| File | Change | Complexity |
|------|--------|------------|
| `models.py` | Add `last_checked_at: str \| None = None` after `last_refreshed_at` | Trivial |
| `schema.py` | Add `_migrate_v13_to_v14`: `ALTER TABLE knowledge_sources ADD COLUMN last_checked_at TEXT`; register in `_apply_migrations` | Low |
| `source_store.py` | Add `last_checked_at` to `_SELECT_COLS` (idx 13), `_row_to_model` (row[13]), `create` INSERT, `update` SET | Low — 4 mechanical edits |
| `refresh.py` | Rewrite `_update_source_record` with conditional logic per truth table | Medium — 4-branch conditional |

### 3.3 Column Ordering Risk

`_row_to_model` uses positional indexing (row[0]–row[12]). Adding `last_checked_at` to `_SELECT_COLS` shifts `created_at` and `updated_at` indices unless inserted at the end. **Safest approach:** append `last_checked_at` after `updated_at` in SELECT, making it row[13]. This avoids shifting existing indices.

### 3.4 Migration Pattern (S5)

13 prior migrations exist, all following the same pattern:
1. Execute DDL in a function `_migrate_vN_to_vM(conn)`
2. Update `schema_version` row
3. Register in `_apply_migrations` tuple

`ALTER TABLE ADD COLUMN` is SQLite-safe for nullable columns (no default needed).

### 3.5 Upstream Contamination (S2)

`_record_ingest_outcome` aliases unknown statuses to `"ok"` (refresh.py L189–190). Cancelled ingest outcomes inflate `refreshed` counter. **Assessment:** Pre-existing bug, explicitly out of scope per brief. O2 fix operates on the counters as received — correct behavior given available data.

### 3.6 Truth Table Validation

| Condition | `last_checked_at` | `last_refreshed_at` | `last_error` | Rationale |
|-----------|-------------------|---------------------|--------------|-----------|
| `refreshed > 0 or partial > 0` | Bump | Bump | errors+warnings joined, or clear | Content arrived |
| `skipped > 0` only | Bump | Preserve | Clear | System checked, content unchanged |
| `failed > 0`, no success | Bump | Preserve | Set from errors | System checked, content failed |
| All zero | Preserve | Preserve | Preserve | Misconfigured source, no-op |

The "all zero" row correctly handles misconfigured sources (empty URL lists, no glob matches) — the system didn't meaningfully check anything.

## 4. Recommendation

**Proceed with implementation as designed in the brief.** Confidence: 0.92.

The two-field model is well-established (HTTP `Last-Modified`/`Date`, RSS `lastBuildDate`/`pubDate`). The implementation touches 4 files with mechanical changes. No architectural risk.

**Risk:** Column ordering in `source_store.py` — must append `last_checked_at` after existing columns to avoid index shift. Mitigated by placing it at position 13 in SELECT.

Challenge: FALLBACK — no multi-option recommendation to challenge; brief decisions already settled design.

## 5. Follow-up Tasks

No follow-up tasks needed — this task IS the implementation task. It has full AC and proceeds to `backlog` for architecture review and TDD implementation.
