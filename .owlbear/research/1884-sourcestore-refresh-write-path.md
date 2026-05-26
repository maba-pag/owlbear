# SourceStore — last_refreshed_at Write Path

> **Owning task:** #1884 — Knowledge: SourceStore protocol — add last_refreshed_at write path
> **Date:** 2026-05-26  **Status:** Complete

## 1. Context and Question

IngestCoordinator.refresh() (#1886) needs to persist a refresh timestamp through the protocol boundary. Currently `SourceUpdate` has no `last_refreshed_at` field and `record_health` only sets `last_checked_at`. The legacy `refresh.py` L430-455 bypasses the protocol entirely via direct `model_copy` + store mutation.

**Question:** What's the minimal protocol extension to unblock refresh timestamp writes?

## 2. Sources Studied

| # | Source | Relevance |
|---|--------|-----------|
| S1 | `protocols/sources.py` — SourceUpdate, record_health, SourceStore protocol | 1.0 |
| S2 | `stores/sources.py` — SqliteSourceStore.update_source impl (L200-273) | 1.0 |
| S3 | `stores/sources.py` — SqliteSourceStore.record_health impl (L274-296) | .90 |
| S4 | `refresh.py` L430-455 — legacy `_update_source_record` | .90 |
| S5 | `protocols/ingest.py` — RefreshRequest, RefreshResult contracts | .85 |
| S6 | `.owlbear/research/1877-ingest-coordinator.md` — §3.7 challenger findings | .80 |
| S7 | `.owlbear/research/refresh-honesty-two-field-timestamps.md` — truth table | .75 |

## 3. Analysis

### 3.1 Current State

- `_SourceRecordBase` has `last_refreshed_at: datetime | None` (readable)
- `update_source` impl writes `last_refreshed_at` to DB from existing row value (never from input)
- `SourceUpdate` lacks `last_refreshed_at` field (write path missing)
- `record_health` sets `last_checked_at` + `health` + `last_error` (different concern)

### 3.2 Trade-Off Matrix

| Criterion | A: Add field to SourceUpdate | B: Dedicated record_refresh() | C: Extend record_health |
|-----------|------------------------------|-------------------------------|-------------------------|
| LOC added | ~5 (1 field + 1 if-check) | ~30 (model + method + impl) | ~10 (optional field + logic) |
| KISS | ✓ Minimal | ✗ Over-designs before need proven | ✗ Conflates concerns |
| Pattern fit | Matches partial-update model | Matches record_health pattern | Breaks record_health semantics |
| Truth table encapsulation | Caller decides when to set | Protocol impl decides | Mixed responsibility |
| Unblocks #1886 | Yes | Yes | Yes |
| Reversibility | Add method later if needed | Cannot easily downgrade to field | Hard to separate |
| Risk | Low — one nullable field | Low — more code, proven pattern | Moderate — semantic overload |
| Confidence | .82 | .70 | .50 |

### 3.3 Key Observations

1. **update_source already owns the full-row write** — the SQL already includes `last_refreshed_at` in SET.
2. **Refresh caller has the data** — IngestCoordinator knows whether content arrived (from `IngestResult` counters); it can set the field conditionally.
3. **Truth table lives in coordinator, not store** — the legacy truth table (checked vs refreshed vs failed) depends on ingest outcomes that the store doesn't own. Putting decision logic in the store would violate single-responsibility.
4. **YAGNI on dedicated method** — #1886 may reveal that a dedicated method IS warranted once the full refresh flow is designed. Adding a field now doesn't preclude adding a method later.

## 4. Recommendation

**Option A: Add `last_refreshed_at: datetime | None = None` to `SourceUpdate`** (confidence: .82)

The minimal change that unblocks #1886 while preserving future flexibility. The coordinator sets `last_refreshed_at` only when content arrived, mirrors how it already uses `record_health` for health concerns.

Challenge: reconsider — confidence in original (Option B): .47 (challenger)
Researcher response: revised — accepted challenger's "smallest unblocker" argument. Option B remains valid as a future refinement if #1886 reveals complex refresh recording semantics.

## 5. Follow-up Tasks

1. #1884 itself advances to backlog — implement the field addition
2. No additional follow-ups needed — #1885 and #1886 already cover downstream work
