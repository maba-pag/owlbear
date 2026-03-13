# Break memory-to-tools Upward Dependency

> **Owning task:** #502 — Break memory to tools upward dependency
> **Date:** 2026-03-06  **Status:** Complete

## 1. Context and Question

`memory/knowledge/refresh.py` imports three symbols from `tools.browser`:

| Import | Type | Usage |
|--------|------|-------|
| `CrawlConfig` (runtime) | Frozen Pydantic model | `_build_crawl_config()` constructs it from dict; uses `.model_fields` |
| `crawl_and_ingest` (runtime) | Async function | Called in `_handle_crawl()` with crawler + pipeline + config |
| `WebCrawler` (TYPE_CHECKING) | Class | Type hint for `__init__` crawler param |

This violates layering: `memory` (lower layer) depends on `tools` (upper layer).
The AC requires: **memory package has zero tools imports**.

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| Cosmic Python Ch.3 — Coupling & Abstractions | cosmicpython.com/book/chapter_03_abstractions.html | 0.95 |
| Python typing.Protocol (PEP 544) | docs.python.org/3/library/typing.html#typing.Protocol | 0.85 |
| OwlBear `EmbeddingProvider` Protocol | `src/owlbear/memory/knowledge/embeddings.py` | 0.90 |
| OwlBear `VectorStoreProtocol` | `src/owlbear/memory/knowledge/protocol.py` | 0.85 |
| OwlBear `NotificationBackend` Protocol + DI | `src/owlbear/core/notification_hook.py` | 0.80 |
| OwlBear bootstrap assembly | `src/owlbear/bootstrap.py` L478-524 | 0.90 |

## 3. Analysis

### Option comparison

| Criterion | A: Callback (`Callable`) | B: Protocol class | C: Move `CrawlConfig` to shared |
|-----------|--------------------------|--------------------|---------------------------------|
| Symbols removed from memory | 3/3 | 3/3 | 1/3 (still needs `crawl_and_ingest`) |
| New abstractions | 1 type alias | 1 Protocol class + 1 impl | 0 new, but model relocation |
| Lines changed in refresh.py | ~20 | ~25 | ~10 (partial fix only) |
| Lines changed in bootstrap.py | ~10 (closure factory) | ~15 (adapter class) | ~5 |
| Test impact | Crawl tests simplify (no `mock.patch`) | Similar simplification | Crawl tests unchanged |
| KISS alignment | High | Medium | Low (doesn't solve the problem) |
| YAGNI alignment | High (single call site) | Lower (Protocol for 1 impl) | N/A |
| Existing codebase precedent | None (but idiomatic Python) | Strong (`EmbeddingProvider`, `VectorStoreProtocol`) | None |

### Option A detail — Callback injection

Replace `crawl_and_ingest` + `CrawlConfig` + `WebCrawler` with a single callback:

```python
# In refresh.py — type alias only, no tools imports
CrawlHandler = Callable[[dict[str, object]], Awaitable[list[IngestResult]]]
```

Constructor changes: `crawler: WebCrawler | None` becomes `crawl_handler: CrawlHandler | None`.
The handler encapsulates CrawlConfig construction, crawler reference, and the
`crawl_and_ingest` call. Bootstrap creates a closure binding those together.

### Option B detail — Protocol class

```python
class CrawlService(Protocol):
    async def crawl_and_ingest(self, config: dict[str, object]) -> list[IngestResult]: ...
```

Clean, but adds a Protocol for a single method with a single implementation.
YAGNI says: don't create abstractions until the third repetition.

### Option C detail — Relocate CrawlConfig

Moving `CrawlConfig` to `memory/knowledge/models.py` or `core/models.py` fixes
only 1 of 3 imports. `crawl_and_ingest` and `WebCrawler` remain. Incomplete.

## 4. Recommendation (.85 confidence)

**Option A: Callback injection.** Simplest change, removes all 3 imports, aligns
with KISS/YAGNI, and simplifies tests (no more `mock.patch` on `crawl_and_ingest`).

Risks:
- Callback type alias is slightly less discoverable than a Protocol — mitigated
  by clear docstring on the type alias and constructor parameter.
- Tests for the crawl handler must verify the callback is called with the right
  dict — straightforward with `AsyncMock`.

Implementation sketch:
1. In `refresh.py`: define `CrawlHandler` type alias, replace constructor param,
   call `self._crawl_handler(source.config)` in `_handle_crawl`.
2. In `bootstrap.py`: create closure `_make_crawl_handler(crawler, pipeline)` that
   imports `CrawlConfig` and `crawl_and_ingest` locally and returns a bound async fn.
3. Update tests: replace `mock.patch("...crawl_and_ingest")` with passing an
   `AsyncMock` as `crawl_handler`.
4. Verify: `grep -r "from owlbear.tools" src/owlbear/memory/` returns zero hits.

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Implement callback injection in RefreshOrchestrator" --priority needed --tags "audit,architecture,scope:core" --status todo --body "Implement Option A from docs/research/memory-tools-dependency-inversion.md. Steps: (1) Define CrawlHandler type alias in refresh.py. (2) Replace crawler param with crawl_handler param. (3) Update _handle_crawl to call self._crawl_handler(source.config). (4) Remove all tools.browser imports. (5) In bootstrap.py, create _make_crawl_handler closure. (6) Update tests. AC: grep -r 'from owlbear.tools' src/owlbear/memory/ returns 0 hits. All tests pass."

kanban\kanban-md.exe create "Verify memory package has no tools imports (INT-07 acceptance)" --priority important --tags "audit,test,scope:core" --status todo --body "After callback injection is implemented, run: grep -r 'from owlbear.tools' src/owlbear/memory/ and confirm zero results. Run full test suite. Update docs/integration-audit.md to mark INT-07 resolved."
```
