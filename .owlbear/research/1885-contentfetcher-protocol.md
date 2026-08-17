# ContentFetcher Protocol — Fetch Abstraction for Refresh

> **Owning task:** #1885 — Knowledge: ContentFetcher protocol — fetch abstraction for refresh
> **Date:** 2026-05-26  **Status:** Complete

## 1. Context and Question

IngestCoordinator.refresh() needs a protocol to fetch content from registered sources across three transport types: filesystem, HTTP, and browser (Playwright). The legacy `RefreshOrchestrator` mixes transport logic inline. The new design requires a clean abstraction that separates fetch concerns from coordination.

Key questions: (1) What shape should the protocol take? (2) How to preserve per-item cancel/error accounting? (3) How to avoid colliding with the legacy `ContentFetcher` in `protocol.py`?

## 2. Sources Studied

| Source | Location | Relevance |
|--------|----------|-----------|
| Legacy RefreshOrchestrator | `serve/knowledge/src/owlbear_knowledge/refresh.py` | 1.0 |
| Legacy ContentFetcher protocol | `serve/knowledge/src/owlbear_knowledge/protocol.py:98` | .95 |
| BrowserContentFetcher impl | `serve/browser/src/owlbear_browser/fetcher.py` | .90 |
| HttpxContentFetcher impl | `serve/knowledge/src/owlbear_knowledge/fetcher.py` | .90 |
| FetchTransport enum + SourceConfig | `protocols/sources.py` | .95 |
| IngestCoordinator protocol | `protocols/ingest.py` (RefreshRequest/Result) | .95 |
| select_content_fetcher call site | `serve/mcp-knowledge/.../server.py:838` | .85 |
| Prior research #751 | `.owlbear/research/751-authenticated-content-pipeline.md` | .80 |
| httpx AsyncBaseTransport pattern | github.com/encode/httpx `_transports/base.py` | .75 |
| Multi-transport abstraction article | dev.to/tosin2013 (Strategy + Registry pattern) | .70 |

## 3. Analysis

### 3.1 Design Options

| Option | Description | Cancel granularity | Error accounting | Coupling |
|--------|-------------|-------------------|-----------------|----------|
| A. Source-level batch | `fetch_source(source) -> tuple[Doc]` | Source-only | Lost | Low |
| B. Source-level + FetchResult | `fetch_source(source, cancel) -> FetchResult` | Per-item (internal) | Per-item via errors | Low |
| C. Per-URI protocol (legacy-style) | `fetch(url) -> str` | Coordinator loops | Coordinator counts | Coordinator bloat |
| D. Async generator | `fetch_source(source) -> AsyncIterator[Doc]` | Yield boundary | Complex | Medium |

### 3.2 Evaluation Criteria

| Criterion | Weight | B (recommended) | C (legacy) | D (generator) |
|-----------|--------|-----------------|------------|---------------|
| KISS | .30 | .85 | .70 | .60 |
| Cancel fidelity | .20 | .80 | .90 | .95 |
| Error accounting | .20 | .85 | .90 | .70 |
| Testability | .15 | .90 | .85 | .70 |
| Architecture fit | .15 | .90 | .60 | .75 |
| **Weighted** | | **.85** | **.77** | **.72** |

### 3.3 Key Design Decisions

**Name: `SourceFetcher`** — avoids collision with legacy `ContentFetcher(Protocol)` in `protocol.py` which still has active call sites in `serve/mcp-knowledge/`.

**`FetchedDocument.uri` is required** — establishes replacement identity for Content.ingest dedup. Legacy IntakeResult has `source: str` serving same purpose.

**`FetchResult` wrapper** — carries per-item errors, preserving skipped/failed accounting lost by raw tuple return.

**`CancelSignal` parameter** — fetcher checks between items internally, returns partial result on cancel. Coordinator checks between sources.

**INLINE/NONE handling** — coordinator handles directly (text already stored). No fetcher invoked.

### 3.4 Legacy Migration Path

- Legacy `ContentFetcher` (`protocol.py`): `async def fetch(url: str) -> str` — active in MCP server
- New `SourceFetcher` (`protocols/fetcher.py`): source-aware, richer return type
- Coexistence: both live until #1886 migrates MCP server to use IngestCoordinator.refresh()
- Existing `HttpxContentFetcher` and `BrowserContentFetcher` become internal adapters within the new transport implementations

## 4. Recommendation

**Protocol shape** (confidence: .80):

```python
# protocols/fetcher.py


class FetchedDocument(BoundaryModel):
    title: str
    text: str
    uri: str  # Required — replacement identity
    external_id: str | None = None
    metadata: Metadata = Field(default_factory=dict)


class FetchError(BoundaryModel):
    uri: str
    error: str


class FetchResult(BoundaryModel):
    documents: tuple[FetchedDocument, ...] = Field(default_factory=tuple)
    errors: tuple[FetchError, ...] = Field(default_factory=tuple)


@runtime_checkable
class SourceFetcher(Protocol):
    async def fetch_source(
        self,
        source: ConfiguredSourceRecord,
        *,
        cancel: CancelSignal | None = None,
    ) -> FetchResult: ...
```

**Coordinator injection**: `fetchers: Mapping[FetchTransport, SourceFetcher] | None = None`

**Three implementations** (created in #1886):
- `FilesystemFetcher`: expand `FileGlobConfig.patterns`, sandbox, read files
- `HttpFetcher`: iterate `UrlListConfig.urls`, fetch via httpx (wraps existing `HttpxContentFetcher`)
- `BrowserFetcher`: navigate `AuthenticatedWebConfig` pages via Playwright (wraps existing `BrowserContentFetcher`)

Challenge: reconsider — confidence in original: .34 (challenger)
Researcher response: revised — renamed to `SourceFetcher` (collision fix), added `CancelSignal` param (granularity), made `uri` required (identity), added `FetchResult` wrapper with `FetchError` (accounting), documented NONE handling.

## 5. Follow-up Tasks

Implementation tasks to create via planner:
1. Protocol file: `protocols/fetcher.py` with types and protocol definition
2. Re-export from `protocols/__init__.py`
3. Implementation in #1886 (already exists — depends on this task)
