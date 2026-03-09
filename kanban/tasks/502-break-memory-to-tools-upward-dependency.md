---
id: 502
title: Break memory to tools upward dependency
status: done
priority: important
created: 2026-03-04T07:38:15.2330855+01:00
updated: 2026-03-08T15:41:31.3998922+01:00
started: 2026-03-06T23:31:40.1597395+01:00
completed: 2026-03-08T15:41:31.3998922+01:00
tags:
    - audit
    - architecture
    - scope:core
class: standard
---

INT-07: memory/knowledge/refresh.py imports tools.browser.crawl_config and tools.browser.integration. Violates layering (memory depends on tools). Option A from research: inject crawl function as callback parameter. See docs/memory-tools-dependency-inversion-research.md.

## Acceptance Criteria

1. **CrawlHandler type alias defined in refresh.py**
   - `CrawlHandler = Callable[[dict[str, object]], Awaitable[list[IngestResult]]]`
   - Uses only `typing` stdlib + memory-local `IngestResult` (no `owlbear.tools` imports)
   - Docstring on the alias explains the contract: receives raw source config dict, returns ingest results

2. **RefreshOrchestrator constructor updated**
   - `crawler: WebCrawler | None` param replaced with `crawl_handler: CrawlHandler | None = None`
   - `self._crawler` attr replaced with `self._crawl_handler`

3. **_handle_crawl simplified**
   - Calls `await self._crawl_handler(source.config)` (raw dict in, results out)
   - `_build_crawl_config` static method removed (responsibility moves to bootstrap closure)
   - Raises `ValueError` when `self._crawl_handler is None` (same guard as today)

4. **Bootstrap closure wires the callback**
   - `bootstrap.py` defines a factory/closure that locally imports `CrawlConfig`, `crawl_and_ingest`, `WebCrawler`
   - Closure binds crawler + pipeline + CrawlConfig construction
   - Passes bound callback as `crawl_handler=` to `RefreshOrchestrator`
   - Note: bootstrap currently does NOT pass a crawler (line ~633), so the immediate wiring is `crawl_handler=None` unless a crawler is available from browser toolset setup

5. **Tests updated (not a separate task -- refactoring, existing suite is the safety net)**
   - `test_refresh_orchestrator.py` crawl tests pass `AsyncMock` as `crawl_handler` (no `mock.patch` on `crawl_and_ingest`)
   - `test_refresh_orchestrator.py` removes all imports from `owlbear.tools.browser`
   - All existing test behaviors and assertions preserved (url_list, file_glob, crawl, refresh_all)

6. **Verification (all must pass)**
   - `grep -r 'from owlbear.tools' src/owlbear/memory/` returns 0 hits
   - `grep -r 'import owlbear.tools' src/owlbear/memory/` returns 0 hits
   - `uv run pytest tests/test_refresh_orchestrator.py -q --tb=short` all pass
   - `uv run ruff check src/owlbear/memory/knowledge/refresh.py src/owlbear/bootstrap.py tests/test_refresh_orchestrator.py` clean

## Architecture Notes

- **Pattern:** Callback injection (Callable type alias), not Protocol -- single-function, single-implementation, KISS/YAGNI
- **Precedent:** Codebase uses Protocols for multi-method interfaces (EmbeddingProvider, VectorStoreProtocol); callback is appropriate for this simpler case
- **Module layering:** After change, refresh.py depends only on memory-local types + owlbear.paths (leaf). bootstrap.py remains the sole cross-layer wiring point
- **Files touched:** src/owlbear/memory/knowledge/refresh.py, src/owlbear/bootstrap.py, tests/test_refresh_orchestrator.py
