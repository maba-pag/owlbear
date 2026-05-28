# SourceFetcher Adapter Design — Phase B2b

> **Owning task:** #1904 — Knowledge: Implement SourceFetcher adapter and migrate refresh to IngestCoordinator (Phase B2b)
> **Date:** 2026-05-28 **Status:** Complete

## 1. Context and Question

`IngestCoordinator.refresh()` requires a `SourceFetcher` implementation but none exists. The MCP handler `knowledge_sources_refresh` currently returns "error: refresh orchestrator not available" because `refresh_orchestrator=None` since task #1900. This task must create a concrete `SourceFetcher`, wire it to the coordinator, and replace the MCP handler.

**Question:** What is the right design for the `SourceFetcher` adapter, and what secondary changes are needed for correct end-to-end behavior?

## 2. Sources Studied

| Source | Location | Relevance |
|--------|----------|-----------|
| SourceFetcher protocol | `protocols/fetcher.py` | Contract definition (0.95) |
| IngestCoordinator.refresh() | `ingest_coordinator.py:283-340` | Consumer of adapter (0.95) |
| RefreshOrchestrator handlers | `refresh.py:193-365` | Logic to wrap (0.90) |
| MCP server lifespan/handler | `server.py:422-462, 873-905` | Integration point (0.90) |
| Typed SourceConfig models | `protocols/sources.py:60-101` | Input shape (0.85) |
| Prior research B2 | `.owlbear/research/mcp-knowledge-legacy-removal-b2.md` | Context (0.80) |
| IngestCoordinator tests | `test_ingest_coordinator_1886.py` | Validation patterns (0.75) |

## 3. Analysis

### 3.1 Adapter Design Options

| Criterion | A: Single Class (dispatch) | B: Strategy per-kind | C: Wrap RefreshOrch |
|-----------|---------------------------|---------------------|---------------------|
| LOC | ~120 | ~200 (4 classes) | ~80 adapter + keep legacy |
| KISS | ✓ | Over-engineered for 3 kinds | Conversion layers add complexity |
| Testability | Mock intake fns | Each strategy isolated | Need both old+new mocks |
| Enables removal | Full RefreshOrch removal | Full removal | Keeps legacy alive |
| New kinds | Add case branch | Add class | N/A (won't add to legacy) |
| Risk | Low (direct mapping) | Low but YAGNI | Medium (dual worlds) |

### 3.2 Critical Implementation Details (from Challenger)

| Issue | Severity | Resolution |
|-------|----------|------------|
| Coordinator ignores `FetchResult.errors` | Critical | Fix coordinator to propagate fetch errors into RefreshResult.errors (separate sub-task) |
| Transport selection per-source | Moderate | Adapter accepts `Callable[[FetchTransport], ContentFetcher]` or similar dispatch; NOT a single injected fetcher |
| MCP return contract changes | Moderate | Document new shape: `{sources_checked, sources_refreshed, errors}` replaces `{refreshed, partial, skipped, failed, errors, warnings}` |
| INLINE refresh = false positive | Moderate | Adapter returns `FetchResult()` for INLINE; coordinator already skips zero-doc sources for ingest. Source should have `refreshable=False` |
| Multi-pattern glob overlap | Moderate | Deduplicate resolved paths before mapping to FetchedDocuments |
| Cancellation support | Moderate | Check `cancel.is_set()` between items in URL/file iteration loops |
| `follow_symlinks` in FileGlobConfig | Low | Pass to `Path.glob()` or `rglob()` |
| `auth_profile` / `page_limit` | Low | Future fields — log warning if auth_profile set (no auth system yet); page_limit caps doc count |
| Local-path fallback in auth URLs | Low | Detect `file://` scheme, delegate to `intake.read_file()` |

### 3.3 Config Mapping (old → new)

| Old untyped | New typed | Notes |
|-------------|-----------|-------|
| `config["urls"]` (list) | `UrlListConfig.urls` (tuple) | Direct mapping |
| `config["pattern"]` / `config["glob"]` | `FileGlobConfig.patterns` (tuple) | Multi-pattern now |
| `config["base_dir"]` | `FileGlobConfig.base_path` (str) | Same semantics |
| `config["urls"]` for authenticated | `AuthenticatedWebConfig.base_url` (str) | Single URL; multi-URL = multi-source |
| `source.fetch_method` (str) | `source.fetch_method` (FetchTransport enum) | Select ContentFetcher per-source |

### 3.4 Wiring in MCP Server Lifespan

```
CompositeSourceFetcher(workspace_root=Path.cwd(), content_fetcher_factory=select_content_fetcher)
  → passed to IngestCoordinator(fetcher=..., sources=..., content=..., enrichment=..., graph=...)
  → knowledge_sources_refresh calls ingest_coordinator.refresh(RefreshRequest(source_ids=(id,)))
```

## 4. Recommendation (confidence: 0.72)

**Proceed with Option A** (single `CompositeSourceFetcher` class) with these mandatory additions:

1. **Sub-task for coordinator error propagation** — IngestCoordinator.refresh() must propagate `fetch_result.errors` into `RefreshResult.errors` (currently silently drops them).
2. **Per-source transport selection** — constructor takes a factory/mapping, not a single ContentFetcher.
3. **Path deduplication** for multi-pattern FILE_GLOB.
4. **Cancel signal** checked between iteration items.

Challenge: reconsider (0.34) → revised to proceed (0.72) after addressing error-propagation gap as a scoped sub-task rather than a design blocker. The adapter itself correctly returns FetchResult.errors per protocol; the consumer (coordinator) needs a 5-line fix.

## 5. Follow-up Tasks

1. **Implement CompositeSourceFetcher** — ~120 LOC adapter in `serve/knowledge/src/owlbear_knowledge/source_fetcher.py` (at `todo` after architect writes AC)
2. **Fix coordinator error propagation** — propagate `fetch_result.errors` into RefreshResult.errors (~5 LOC fix in ingest_coordinator.py)
3. **Wire fetcher in MCP server + replace handler** — lifespan creates fetcher, passes to coordinator; handler calls coordinator.refresh()
4. **Remove legacy** — delete RefreshOrchestrator import, `source_store` field, `refresh_orchestrator` field from AppContext, dead imports
