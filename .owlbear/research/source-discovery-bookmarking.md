# Source Discovery and Bookmarking — Crawl, Evaluate, Ingest Pipeline

> **Owning task:** #304 — Source discovery and bookmarking — crawl, evaluate, ingest pipeline
> **Date:** 2026-03-01
> **Status:** Complete

## 1. Context and Question

During research, OwlBear encounters many URLs (docs, repos, articles). Currently, useful sources are either lost after the session or manually ingested via `ingest_document`. There is no systematic way to evaluate whether content is worth keeping, bookmark it with metadata, or auto-discover valuable pages.

**Core question:** How should OwlBear evaluate, bookmark, and ingest discovered sources — and what data model and agent tools support this workflow?

**Key dependency:** Task #254 (source registry) proposes a `KnowledgeSource` model and `knowledge_sources` SQLite table (schema v5). This task layers evaluation and bookmarking _on top_ of that registry.

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| Karakeep (fka Hoarder) | <https://github.com/karakeep-app/karakeep> | .90 | AI-based auto-tagging via LLM prompt; bookmark → extract → tag pipeline; 23.8k stars |
| Pinboard API v1 | <https://pinboard.in/api/> | .85 | Minimal bookmark model: url, title, description, tags, datetime, toread flag; `posts/suggest` for tag recommendations |
| Omnivore digest-score | <https://github.com/omnivore-app/omnivore/tree/main/ml/digest-score> | .75 | ML-based relevance scoring (random forest); user interaction features; too complex for OwlBear's needs |
| Linkwarden | <https://github.com/linkwarden/linkwarden> | .70 | Collaborative bookmarks with auto-screenshot, PDF archive, AI tagging; heavy TypeScript stack |
| OwlBear source-registry-research | docs/research/source-registry.md | 1.0 | `KnowledgeSource` data model, `knowledge_sources` SQLite table, `RefreshOrchestrator` for crawl/ingest dispatch |
| OwlBear content-hashing-research | docs/research/content-hashing.md | .95 | SHA-256 content hash dedup, `check_content_changed()`, `document_status` table |
| OwlBear IngestPipeline | src/owlbear/memory/knowledge/ingest.py | 1.0 | Existing pipeline: intake → chunk → embed+extract → store, with delta detection |
| OwlBear WebSearchToolset | src/owlbear/tools/web_search.py | 1.0 | Existing `web_read()` tool: httpx + trafilatura content extraction |

## 3. Analysis

### 3.1 Evaluation Approach — LLM vs ML vs Heuristic

| Criterion | LLM prompt (.85) | ML model (.40) | Keyword heuristic (.55) |
|-----------|-------------------|----------------|------------------------|
| Accuracy | High — understands context and nuance | High (if trained) | Low — brittle, keyword-dependent |
| Training data needed | None | Yes — interaction logs | None |
| Complexity | Low — one prompt call | High — feature eng + training pipeline | Low |
| Dependency | Already have LLM via Copilot OAuth | Needs sklearn/lightgbm, feature store | None |
| Project-awareness | Reads project description for relevance scoring | Must encode project as features | Can't understand project context |
| KISS score | **High** | Low | Medium |
| YAGNI risk | None — LLM is already present | High — building ML infra for a laptop daemon | None |

**Recommendation (.85): LLM-based evaluation.** Karakeep proves LLM auto-tagging works well for bookmarks. Omnivore's ML approach requires interaction data we don't have. A single structured-output prompt asking the LLM to score relevance (0.0–1.0) and suggest tags is simple, accurate, and project-aware.

### 3.2 Bookmark Data Model — Extend Source Registry vs Separate Table

| Criterion | Extend `knowledge_sources` (.60) | Separate `bookmarks` table (.85) |
|-----------|----------------------------------|----------------------------------|
| Separation of concerns | Conflates "sources to refresh" with "pages I found useful" | Clean: bookmarks = evaluated URLs, sources = refresh configs |
| Schema fit | `knowledge_sources` has `source_type`, `config` JSON — wrong shape for a single-URL bookmark | `bookmarks` has URL, title, relevance_score, tags, reason — right shape |
| Query patterns | Filter bookmarks requires `WHERE source_type = 'bookmark'` — awkward | Direct `SELECT * FROM bookmarks` |
| Relationship | A bookmark _may become_ a source if the user wants periodic refresh | FK optional: `bookmarks.source_id → knowledge_sources.id` |
| KISS | Overloading one table for two concerns | Two simple tables, each with clear purpose |

**Recommendation (.85): Separate `bookmarks` table** in the knowledge DB. A bookmark is a evaluated-and-saved URL with relevance metadata. A source is a refresh configuration. They can link when a bookmark graduates to a monitored source.

### 3.3 Bookmark Model

Inspired by Pinboard's simplicity + Karakeep's AI enrichment:

```python
class Bookmark(BaseModel, frozen=True):
    id: str  # UUID hex
    url: str  # Source URL
    title: str  # Extracted or user-provided
    description: str  # LLM-generated summary or user reason
    tags: list[str]  # LLM-suggested + user-provided tags
    relevance_score: float  # LLM evaluation: 0.0–1.0
    reason: str  # Why this was bookmarked
    scope: str = "global"  # "global" or "project:{id}"
    document_id: str | None = None  # Link to ingested document (if ingested)
    content_hash: str | None  # For dedup
    created_at: str  # ISO timestamp
```

### 3.4 Evaluation Pipeline

```
URL → web_read(url) → extracted_text
                          ↓
                   SourceEvaluator.evaluate(text, project_context)
                          ↓
                   EvaluationResult(score, tags, summary)
                          ↓
              score >= threshold? → Yes → ingest + create bookmark
                                   No  → create bookmark (no ingest)
```

The `SourceEvaluator` is a thin wrapper around a PydanticAI agent with structured output:

```python
class EvaluationResult(BaseModel, frozen=True):
    relevance_score: float  # 0.0–1.0
    tags: list[str]  # Suggested tags
    summary: str  # 2-3 sentence summary
    worth_ingesting: bool  # Does it contain reusable knowledge?
```

**Prompt inputs:** page title, first 2000 chars of content, project name + description + goals (from `ProjectDefinition` or `Project` model). The LLM scores relevance _to the current project_.

### 3.5 Auto-Discovery — Hook vs Explicit

| Criterion | PostToolUse hook on web_read (.55) | Explicit bookmark_source tool only (.80) |
|-----------|-----------------------------------|-----------------------------------------|
| UX | Agent automatically suggests bookmarking after every web_read | Agent consciously decides to bookmark |
| Noise | High — every page triggers evaluation | Low — only pages the agent finds useful |
| LLM cost | Extra LLM call per web_read (even for irrelevant pages) | LLM call only when agent calls bookmark_source |
| KISS | Medium — hook wiring, suggestion flow | **High** — one tool, one pipeline |
| YAGNI | Premature optimization of discovery | Build explicit first, add hooks later |

**Recommendation (.80): Explicit `bookmark_source` tool first.** The agent already reads pages during research and can decide which are valuable. Auto-discovery via hooks is a future enhancement — get the basic pipeline working first.

### 3.6 Dedup Strategy

Existing `IngestPipeline.check_content_changed()` handles dedup at the ingest level. For bookmarks:

1. Before creating a bookmark, check `bookmarks` table for matching URL + scope.
2. If URL already bookmarked in same scope → update (merge tags, update score).
3. Before ingesting, existing content-hash dedup in `IngestPipeline` prevents re-embedding.

No new dedup mechanism needed — compose existing capabilities.

### 3.7 Schema Addition — `bookmarks` Table (schema v5)

```sql
CREATE TABLE IF NOT EXISTS bookmarks (
    id              TEXT PRIMARY KEY,
    url             TEXT NOT NULL,
    title           TEXT,
    description     TEXT,
    tags            TEXT,          -- JSON array
    relevance_score REAL,
    reason          TEXT,
    scope           TEXT DEFAULT 'global',
    document_id     TEXT,          -- FK to documents.id (NULL if not ingested)
    content_hash    TEXT,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_bookmarks_url_scope ON bookmarks(url, scope);
CREATE INDEX IF NOT EXISTS idx_bookmarks_scope ON bookmarks(scope);
```

**Note:** If #254 also adds schema v5 for `knowledge_sources`, combine both migrations into one v5 step.

## 4. Recommendation (.80 confidence)

**LLM-evaluated bookmarking with explicit `bookmark_source` tool, separate `bookmarks` table, and optional ingest for high-relevance pages.**

Architecture:

```
Agent calls bookmark_source(url, reason)
    ↓
BookmarkPipeline:
  1. web_read(url) → extracted text
  2. Check dedup: URL already bookmarked?
  3. SourceEvaluator.evaluate(text, project_context) → score, tags, summary
  4. If score >= ingest_threshold (default 0.7):
       IngestPipeline.ingest(url) → document_id
  5. INSERT INTO bookmarks
  6. Return summary to agent
```

Components:

| Component | Location | Responsibility |
|-----------|----------|---------------|
| `Bookmark` model | `src/owlbear/memory/knowledge/models.py` | Pydantic data model |
| `BookmarkStore` | `src/owlbear/memory/knowledge/bookmarks.py` | SQLite CRUD for bookmarks |
| `SourceEvaluator` | `src/owlbear/memory/knowledge/evaluator.py` | LLM-based relevance scoring |
| `BookmarkPipeline` | `src/owlbear/memory/knowledge/bookmark_pipeline.py` | Orchestrates extract → evaluate → ingest → store |
| `BookmarkToolset` | `src/owlbear/tools/bookmarks.py` | Agent tools: `bookmark_source`, `list_bookmarks` |
| Schema v5 migration | `src/owlbear/memory/knowledge/schema.py` | Add `bookmarks` table |

**Risks and mitigations:**

- **LLM latency per bookmark:** Acceptable — bookmarking is infrequent (research sessions), not high-throughput.
- **Relevance depends on project context:** When no active project, skip relevance scoring and use `score=0.5` (neutral).
- **Combined schema v5 with #254:** Coordinate — whoever lands first defines v5, the other adds v5→v6.

## 5. Follow-up Tasks

1. **Bookmark model + BookmarkStore** — Pydantic `Bookmark` model, SQLite CRUD (`create`, `get_by_url`, `list`, `update_tags`, `delete`). Schema v5 migration for `bookmarks` table.
2. **SourceEvaluator** — PydanticAI agent with `EvaluationResult` structured output. Prompt takes content excerpt + project context, returns score/tags/summary.
3. **BookmarkPipeline** — Orchestrator: `web_read` → dedup check → evaluate → conditional ingest → store bookmark. Wires evaluator, ingest pipeline, bookmark store.
4. **BookmarkToolset** — `bookmark_source(url, reason)` and `list_bookmarks(tag, min_score)` agent tools. Follow `FunctionToolset` pattern. Wire in `bootstrap.py`.
5. **Tests: Bookmark model + store** — TDD for Bookmark model, BookmarkStore CRUD, schema v5 migration. Mock SQLite.
6. **Tests: SourceEvaluator** — TDD with mocked PydanticAI agent. Test prompt construction, score thresholds, graceful failure.
7. **Tests: BookmarkPipeline** — TDD with mocked web_read, evaluator, ingest pipeline. Test full pipeline flow, dedup, ingest threshold.
8. **Tests: BookmarkToolset** — TDD for agent tool wrappers with mocked pipeline. Test output formatting.
