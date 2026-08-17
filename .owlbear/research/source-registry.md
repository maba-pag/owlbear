# Source Registry and Crawl Scheduling

> **Owning task:** #254 — Research: Source registry and crawl scheduling
> **Date:** 2026-03-01
> **Status:** Complete

## 1. Context and Question

OwlBear's knowledge ingestion is currently one-shot: an agent or user calls `ingest_document` with a specific URL, file path, or text blob. There is no way to define a persistent "source" (e.g., "the PydanticAI docs site") and refresh it periodically. The `document_status` table tracks content hashes for delta detection, but there is no registry of *what* to refresh or *when*.

**Core question:** What data model and mechanism should OwlBear use to register knowledge sources and optionally schedule their refresh?

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| LlamaIndex Data Connectors | <https://developers.llamaindex.ai/python/framework/module_guides/loading/connector/> | .85 | Reader → Document pattern, LlamaHub connector registry, type-specific loaders |
| LlamaIndex IngestionPipeline | <https://developers.llamaindex.ai/python/framework/module_guides/loading/ingestion_pipeline/> | .90 | doc_id → hash dedup, IngestionCache, document management, upsert-on-change |
| Haystack Pipelines | <https://docs.haystack.deepset.ai/docs/pipelines> | .60 | Component protocol, typed I/O, no built-in source registry or scheduling |
| APScheduler (v4 pre-release) | <https://github.com/agronholm/apscheduler> | .70 | Cron/interval/calendar triggers, SQLite data store, async-native v4 |
| LangChain indexing API | (cited in content-hashing.md) | .80 | RecordManager, content+metadata hashing, cleanup modes (incremental/full) |
| Cognee (task pipeline) | (cited in knowledge-pipeline.md) | .75 | Source provenance tracking (source_pipeline, source_task fields) |
| OwlBear IngestPipeline | src/owlbear/memory/knowledge/ingest.py | 1.0 | Existing delta detection via content_hash in document_status |
| OwlBear CrawlConfig | src/owlbear/tools/browser/crawl_config.py | 1.0 | Existing crawl configuration model (seeds, depth, patterns, politeness) |
| OwlBear crawl_and_ingest | src/owlbear/tools/browser/integration.py | 1.0 | Existing crawl → ingest bridge |
| Task #147 | kanban/tasks/147-*.md | .90 | Existing "cron job scheduler" task (phase-14, someday priority) |

## 3. Analysis

### 3.1 Source Type Assessment

| Source type | Complexity | Value | MVP? | Notes |
|------------|-----------|-------|------|-------|
| URL list | Low | High | Yes | Simplest: list of URLs → `ingest(url)` per URL |
| Crawl site | Medium | High | Yes | Already have `CrawlConfig` + `WebCrawler` + `crawl_and_ingest` |
| File glob | Low | Medium | Yes | `pathlib.Path.glob()` → `ingest(path)` per file |
| Sitemap | Low | Medium | No | XML parse → URL list; trivial add-on later |
| RSS feed | Medium | Low | No | Niche use case, YAGNI |
| Confluence API | High | Low | No | Requires auth, pagination, API client; YAGNI |
| Git repo | High | Low | No | Complex (clone, diff, parse); YAGNI |

**MVP source types: `url_list`, `crawl`, `file_glob`.**

### 3.2 Storage: Config File vs Database

| Criterion | TOML/YAML config (.85) | SQLite table (.70) |
|-----------|----------------------|-------------------|
| KISS | Higher — flat file, human-readable | Lower — requires schema migration |
| Multi-project scoping | Manual — separate config per project | Built-in — scope column |
| CRUD via CLI | Edit file or parse/rewrite | SQL INSERT/UPDATE/DELETE |
| Query (sort by last_refreshed) | Parse file, sort in Python | `ORDER BY last_refreshed_at` |
| Atomicity | No (file write races) | Yes (SQLite transactions) |
| Dependency | None | Already using SQLite for knowledge DB |
| Agent tool integration | Must read/write files | Reuses existing DB connection |

**Recommendation (.85): SQLite table** in the existing knowledge DB. Reasons: already using SQLite for `document_status`, agent tools need CRUD, multi-project scoping is free. The schema migration pattern is already established (v1→v2→v3→v4).

### 3.3 Scheduling Approach

| Criterion | APScheduler (.50) | asyncio interval loop (.70) | Manual refresh only (.85) |
|-----------|-------------------|---------------------------|--------------------------|
| Dependency count | +1 heavy dep (APScheduler) | 0 (stdlib) | 0 |
| Cron expressions | Full cron syntax | Simple interval (seconds) | N/A |
| KISS | Low — full scheduler framework | Medium — custom loop | High — no scheduling code |
| Existing task overlap | Conflicts with #147 | Partially overlaps #147 | Orthogonal to #147 |
| MVP scope | Over-engineered | Reasonable | Minimal |
| YAGNI risk | High | Medium | None |
| Upgrade path | N/A | Add cron via APScheduler later | Add interval loop later |

**Recommendation (.85): Manual refresh first** (CLI + agent tool). Scheduling is a phase-14 concern (task #147). The source registry is valuable even without scheduling — users can `bearclaw knowledge source refresh --all` on demand.

### 3.4 Query Conflict Analysis

When a refresh deletes old document data and re-ingests, there's a brief window where queries return incomplete results. Three approaches:

| Approach | Complexity | Data integrity | Recommendation |
|----------|-----------|---------------|----------------|
| Accept brief gap | None | Brief stale/missing window | **Yes** (.85) — laptop-resident, acceptable |
| Shadow ingest (new ID, swap after) | High | Zero downtime | No — KISS violation |
| Read lock during refresh | Medium | Blocks queries | No — latency spike |

For a single-user laptop tool, the brief inconsistency during refresh is acceptable.

## 4. Recommendation (.85 confidence)

### Data Model: `KnowledgeSource`

```python
class SourceType(StrEnum):
    URL_LIST = "url_list"
    CRAWL = "crawl"
    FILE_GLOB = "file_glob"


class KnowledgeSource(BaseModel, frozen=True):
    id: str  # UUID hex
    name: str  # Human label, unique per scope
    source_type: SourceType
    config: dict[str, Any]  # Type-specific: urls, crawl_config, glob_pattern
    scope: str = "global"  # "global" or "project:{id}"
    enabled: bool = True
    priority: int = 0  # Higher = refresh first
    last_refreshed_at: str | None  # ISO timestamp
    created_at: str
    updated_at: str
```

**Type-specific `config` schema:**

- `url_list`: `{"urls": ["https://...", ...]}`
- `crawl`: `{"seed_urls": [...], "max_depth": 2, "max_pages": 50, "same_domain_only": true, ...}` (matches CrawlConfig fields)
- `file_glob`: `{"pattern": "docs/**/*.md", "base_dir": "."}`

### Architecture

```
KnowledgeSourceStore (SQLite CRUD)
    ↕
KnowledgeSourceToolset (agent tools: add, list, refresh, remove)
    ↕
bearclaw knowledge source (CLI commands)
    ↕
RefreshOrchestrator (reads source config → dispatches to IngestPipeline or crawl_and_ingest)
```

### Schema: `knowledge_sources` table (schema v5)

```sql
CREATE TABLE IF NOT EXISTS knowledge_sources (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    source_type     TEXT NOT NULL,
    config          TEXT NOT NULL,    -- JSON
    scope           TEXT DEFAULT 'global',
    enabled         INTEGER DEFAULT 1,
    priority        INTEGER DEFAULT 0,
    last_refreshed_at TEXT,
    last_error      TEXT,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_knowledge_sources_name_scope
    ON knowledge_sources(name, scope);
```

### CLI Commands

```
bearclaw knowledge source add --name "PydanticAI Docs" --type crawl \
    --seeds "https://ai.pydantic.dev/" --max-depth 2 --max-pages 100
bearclaw knowledge source add --name "Project Specs" --type file_glob \
    --pattern "docs/**/*.md"
bearclaw knowledge source add --name "Key References" --type url_list \
    --urls "https://example.com/a,https://example.com/b"
bearclaw knowledge source list [--scope global]
bearclaw knowledge source show <name>
bearclaw knowledge source refresh [--name <name> | --all]
bearclaw knowledge source remove <name>
```

### Refresh Flow

1. Load `KnowledgeSource` from registry
2. For `url_list`: `ingest(url)` per URL (delta check built in)
3. For `crawl`: build `CrawlConfig` from source config → `crawl_and_ingest()`
4. For `file_glob`: resolve glob → `ingest(path)` per file
5. Update `last_refreshed_at` / `last_error` on source record
6. Return summary (pages refreshed, skipped, failed)

The existing `IngestPipeline.check_content_changed()` handles dedup — unchanged pages are skipped automatically.

## 5. Follow-up Tasks

1. **KnowledgeSource data model** — Pydantic models (`KnowledgeSource`, `SourceType`) + `KnowledgeSourceStore` (SQLite CRUD)
2. **Schema v5 migration** — add `knowledge_sources` table to `schema.py`
3. **Refresh orchestrator** — dispatches refresh by source type using existing IngestPipeline + crawl_and_ingest
4. **CLI: bearclaw knowledge source** — add/list/show/refresh/remove subcommands
5. **KnowledgeToolset: source management tools** — expose add/list/refresh to agents
6. **File glob source type** — resolve workspace-relative globs for local file ingestion
