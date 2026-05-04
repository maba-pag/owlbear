# Browser Fetcher Wiring + RefreshOrchestrator Fix — Test Research

> **Owning task:** #1325 — P1-09: Tests — Browser fetcher wiring + RefreshOrchestrator fix
> **Date:** 2026-05-04 **Status:** Complete

## 1. Context and Question

Task #1325 requires RED-phase tests for the browser fetcher wiring and RefreshOrchestrator fix (impl: #1326). The brief (§4.5, §4.7) specifies that:

- `RefreshOrchestrator` must be wired with `content_fetcher` (selected by `fetch_method`) and `graph_store`
- The `fetch_method` field on `KnowledgeSource` determines whether HTTP or browser fetcher is used on re-ingest
- `inter_doc_builder` is intentionally omitted (enrichment handled by agent workers per D7)

**Question:** What test structure and assertions are needed to verify the five ACs?

## 2. Sources Studied

| # | Source | Relevance |
|---|--------|-----------|
| 1 | `serve/knowledge/src/owlbear_knowledge/refresh.py` — full RefreshOrchestrator | 1.0 |
| 2 | `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` L308-313 — current (incomplete) wiring | 1.0 |
| 3 | `serve/knowledge/src/owlbear_knowledge/protocol.py` — ContentFetcher Protocol | 0.9 |
| 4 | `serve/knowledge/src/owlbear_knowledge/models.py` — KnowledgeSource.fetch_method | 0.9 |
| 5 | `serve/knowledge/src/owlbear_knowledge/fetcher.py` — HttpxContentFetcher | 0.8 |
| 6 | `serve/browser/src/owlbear_browser/fetcher.py` — BrowserContentFetcher | 0.8 |
| 7 | `tests/test_persistence_source_wiring_1320.py` — sibling task test patterns | 0.9 |
| 8 | `.owlbear/briefs/draft-knowledge-activation/brief.md` §4.5, §4.7 | 1.0 |

## 3. Analysis

### Current State

| Component | Status | Gap |
|-----------|--------|-----|
| `RefreshOrchestrator.__init__` | Accepts `content_fetcher`, `graph_store`, `inter_doc_builder` as optional kwargs | None — interface ready |
| `app_lifespan` server.py L308 | Instantiates without `content_fetcher`, `graph_store`, `inter_doc_builder` | **Missing wiring** |
| `fetch_method` field | Exists on model + schema, persisted via SourceStore | **Not consumed** by any fetcher selection logic |
| `_handle_authenticated_web()` | Returns no-op RefreshResult when `content_fetcher is None` | Works correctly once wired |
| `_schedule_inter_doc_build()` | Returns early when `graph_store is None` or `inter_doc_builder is None` | Safe no-op |
| `ContentFetcher` Protocol | `@runtime_checkable` with `async fetch(url) -> str` | Clean protocol |

### Test Strategy

Tests should verify at two levels:

1. **Unit level (RefreshOrchestrator):** Inject mock fetchers and verify correct dispatch based on `fetch_method`
2. **Integration level (MCP server lifespan):** Verify wiring passes `content_fetcher` and `graph_store`

### AC → Test Mapping

| AC | Test Focus | Assert Pattern |
|----|-----------|----------------|
| AC1: ContentFetcher injection | `app_lifespan` passes fetcher to RefreshOrchestrator; AUTHENTICATED_WEB sources call `fetcher.fetch()` | Mock fetcher, assert `fetch()` called |
| AC2: GraphStore injection | `app_lifespan` passes `graph_store` to RefreshOrchestrator | Inspect constructor args or assert entity operations possible |
| AC3: fetch_method → fetcher type | Source with `fetch_method="browser"` gets BrowserContentFetcher; `"http"` gets HttpxContentFetcher | Selection logic tested via mock factory |
| AC4: Works without inter_doc_builder | `_schedule_inter_doc_build()` returns early, no crash | Construct without `inter_doc_builder`, refresh succeeds |
| AC5: refresh_source uses saved fetch_method | `refresh_source` MCP tool reads source record's `fetch_method` and uses correct fetcher | End-to-end mock: source fixture + assert fetcher selection |

### Mocking Approach

- **Heavy I/O patches** (same as #1320 pattern): Qdrant, BgeM3, LLMExtractor, GraphStore
- **ContentFetcher mock**: `AsyncMock(spec=ContentFetcher)` with `fetch` returning fixture content
- **Pipeline mock**: `MagicMock` with `ingest` returning `IngestResult(status="ok", document_id="doc-1")`
- **SourceStore mock**: Returns `KnowledgeSource` fixtures with various `fetch_method` values

### Risk: Fetcher Selection Logic Doesn't Exist Yet

The current `refresh()` method dispatches by `source.source_type` (enum), not by `fetch_method` (string). The fix in #1326 must add logic that:

1. Reads `source.fetch_method` from the source record
2. Selects `HttpxContentFetcher` or `BrowserContentFetcher` accordingly
3. Falls back to HTTP when `fetch_method` is empty/unset

Tests should assert this selection happens in the server lifespan or at refresh-time dispatch.

## 4. Recommendation

**Approach:** Single test file `tests/test_browser_fetcher_wiring_1325.py` with 5 test classes (one per AC), following the `test_persistence_source_wiring_1320.py` pattern.

**Key design decisions for tests:**

1. **Fetcher selection** should be tested as a factory/selection function (not embedded in lifespan) — tests call the selection logic directly with `fetch_method` values
2. **GraphStore injection** verified by inspecting RefreshOrchestrator constructor args in patched lifespan
3. **inter_doc_builder omission** tested via unit test on RefreshOrchestrator — construct without it, verify refresh completes without error
4. **refresh_source integration** tested by patching the MCP server's AppContext and calling the tool function

Confidence: 0.85

Challenge: SKIPPED — test-writing research, no architecture alternatives to evaluate.

## 5. Follow-up Tasks

None needed — this is a leaf test-writing task. Implementation is #1326 (already exists).
