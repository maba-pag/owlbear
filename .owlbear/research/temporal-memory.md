# Temporal Memory — Time-Aware Retrieval with Relevance Decay

> **Owning task:** #136 — Temporal memory — time-aware retrieval with relevance decay
> **Date:** 2026-02-28
> **Status:** Complete

## 1. Context and Question

OwlBear's knowledge graph retrieves by embedding similarity only. A function documented yesterday and a pattern documented three months ago get equal ranking if their embeddings match equally well. This research investigates adding a time dimension so more recent knowledge ranks higher — without losing valuable long-term knowledge.

**Key constraints:** KISS, no background jobs, no time-series infrastructure, single SQLite file. All tables already have `created_at TEXT` columns.

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| Generative Agents (Park et al., 2023) | arxiv.org/abs/2304.03442 + github.com/joonspk-research/generative_agents | .95 | Three-component retrieval: `recency × w₁ + relevance × w₂ + importance × w₃`. Recency = `decay_rate ^ rank`. Importance = LLM-assigned "poignancy" (1-10). All normalized [0,1]. Weights `[0.5, 3, 2]`. |
| LangChain TimeWeightedVectorStoreRetriever | github.com/langchain-ai/langchain (retrievers/time_weighted_retriever.py) | .90 | Formula: `combined = (1 - decay_rate) ^ hours_passed + similarity`. Default `decay_rate = 0.01` → half-life ≈ 69 hours (3 days). Uses `last_accessed_at` — updates on each retrieval. Additive score, no normalization. |
| Mem0 (mem0ai) | github.com/mem0ai/mem0 | .60 | Stores `created_at`/`updated_at` timestamps on all memories. Scoping via `user_id`/`agent_id`. No temporal decay in retrieval — pure vector similarity + metadata filters. |

## 3. Analysis

### 3.1 Decay Strategy Comparison

| Criterion | Query-time freshness boost (.90) | Staleness markers (.50) | Sliding time window (.40) |
|-----------|----------------------------------|-------------------------|---------------------------|
| Schema change | None (use existing `created_at`) | `stale BOOL` + cron job | None (WHERE filter) |
| Implementation | ~30 LOC in `search_similar` | ~50 LOC + scheduler | ~5 LOC WHERE clause |
| Adapts to query context | Yes (recency blended per-query) | No (binary stale/fresh) | No (hard cutoff) |
| Preserves old knowledge | Yes (decayed, not deleted) | Partially (stale = deprioritized) | No (dropped entirely) |
| Background job needed | No | Yes (periodic update) | No |
| KISS score | **High** | Low | High but lossy |
| Prior art | LangChain, Generative Agents | Elasticsearch TTL | RAG sliding window |

**Verdict:** Query-time freshness boost. Zero schema required, fits the existing two-stage retrieval pattern, preserves all knowledge.

### 3.2 Decay Function Comparison

| Function | Formula | Half-life control | Complexity | Prior art |
|----------|---------|-------------------|------------|-----------|
| Exponential (time-based) | `(1 - r) ^ hours` | `half_life = ln(2) / ln(1/(1-r))` | Low | LangChain |
| Exponential (rank-based) | `r ^ rank_position` | Implicit (position-dependent) | Low | Generative Agents |
| Linear | `max(0, 1 - hours / max_age)` | `max_age` directly | Lowest | — |
| Hyperbolic | `1 / (1 + α × hours)` | Slower tail, no hard zero | Low | Academic |

**Verdict:** Exponential time-based decay (LangChain pattern). Smooth, configurable via a single `decay_rate` parameter, well-proven. Rank-based decay requires sorting all memories first — unnecessary overhead when we already have timestamps.

### 3.3 Where the Temporal Boost Applies

```
vec0 query → candidates (rowid, distance) → resolve IDs via bridge table
                                                    ↓
                                        look up created_at from source table
                                                    ↓
                                        compute recency_score per candidate
                                                    ↓
                                        adjusted_score = f(distance, recency)
                                                    ↓
                                        re-sort → return top_k
```

Two integration points in `VectorStore`:

| Path | Current behavior | Temporal integration |
|------|-----------------|---------------------|
| `search_similar` (no reranker) | Sort by vec0 distance | `score = distance - recency_weight × recency_score` (lower = better) |
| `_search_with_reranker` | Over-fetch → rerank by cross-encoder score | `score = reranker_score + recency_weight × recency_score` (higher = better) |

Both paths already iterate candidates and resolve IDs via the bridge table — adding a `created_at` lookup is a single extra JOIN, ~5 lines.

### 3.4 Decay Rate Calibration

| Context | decay_rate | Half-life | Rationale |
|---------|-----------|-----------|-----------|
| Chat agents (Generative Agents) | 0.01 | ~3 days | Conversations stale quickly |
| General RAG (LangChain default) | 0.01 | ~3 days | Documents refresh often |
| **Dev tool (OwlBear)** | **0.001** | **~29 days** | Code patterns persist weeks. Decisions age slower than chat. |
| Archival knowledge | 0.0001 | ~289 days | Near-permanent, minimal decay |

**Recommendation:** Default `decay_rate = 0.001` (29-day half-life), configurable via settings. A developer's codebase knowledge decays slower than conversational memory but faster than archived documentation.

### 3.5 Importance / Decay Resistance

The task mentions preventing critical long-term knowledge from decaying. Three options:

| Approach | Cost | KISS score | Accuracy |
|----------|------|------------|----------|
| LLM-assigned importance at ingest | LLM call per entity | Low | High |
| Rule-based by entity_type | Zero (lookup table) | **High** | Medium |
| Access-count (frequently retrieved = important) | Counter column | Medium | Medium |

**Recommended (phase 1):** Rule-based importance. Map `entity_type` → importance weight:

```python
IMPORTANCE_BY_TYPE = {
    "decision": 0.9,  # Decisions persist — decay very slowly
    "pattern": 0.8,  # Patterns are reusable
    "concept": 0.7,  # Conceptual knowledge ages slowly
    "class_": 0.5,  # Code structures change moderately
    "function": 0.4,  # Functions change often
    "file": 0.3,  # Files change most frequently
}
```

Adjusted decay: `recency_score = (1 - decay_rate × (1 - importance)) ^ hours`. Higher importance → slower effective decay. A `decision` with importance 0.9 has effective `decay_rate = 0.0001` (289-day half-life) vs a `file` at `0.0007` (41-day half-life).

### 3.6 Schema Impact

**None required for phase 1.** All tables already have `created_at TEXT`. The temporal boost is computed at query time by joining to the source table.

Optional future additions:

- `updated_at TEXT` — track when knowledge was refreshed (useful if entities are updated in place)
- `last_accessed_at TEXT` — track retrieval recency (LangChain pattern), requires write-on-read
- `importance REAL` — explicit importance override (for LLM-assigned scores later)

These are **not needed** for the initial implementation. YAGNI.

## 4. Recommendation (.85 confidence)

**Query-time exponential decay with rule-based importance resistance.**

- **Decay function:** `recency_score = (1 - decay_rate × (1 - importance)) ^ hours_passed`
- **Default decay_rate:** 0.001 (configurable via `OwlBearSettings`)
- **Default recency_weight:** 0.1 (similarity still dominates; recency is a tiebreaker)
- **Importance:** Rule-based by `entity_type`, zero-cost lookup
- **Integration point:** `VectorStore.search_similar()`, post vec0 retrieval
- **Schema changes:** None (uses existing `created_at`)

**Risk:** The `created_at` field stores ISO-8601 strings. Parsing them per candidate adds ~microseconds. For OwlBear's scale (<50K vectors), this is negligible.

**Risk:** Documents don't have an `entity_type` for importance mapping. Mitigation: default importance 0.5 for documents, allow override via metadata.

## 5. Follow-up Tasks

1. **Temporal freshness boost in VectorStore** — Add `recency_weight` and `decay_rate` params to `search_similar()`. Compute per-candidate recency from `created_at`. Blend with distance/reranker scores. TDD: write decay function tests first, then integration tests with old/new entries. Priority: nice-to-have (matches parent task).

2. **Importance-based decay resistance** — Add `IMPORTANCE_BY_TYPE` lookup. Modify decay formula to attenuate by importance. Default 0.5 for documents. TDD: test that high-importance old entries outrank low-importance new entries. Priority: nice-to-have. Depends on task 1.

3. **Temporal decay settings** — Add `temporal_decay_rate` and `temporal_recency_weight` to `OwlBearSettings`. Priority: nice-to-have. Depends on task 1.
