---
id: 502
title: Break memory to tools upward dependency
status: backlog
priority: important
created: 2026-03-04T07:38:15.2330855+01:00
updated: 2026-03-06T23:37:52.8508377+01:00
started: 2026-03-06T23:31:40.1597395+01:00
tags:
    - audit
    - architecture
    - scope:core
class: standard
---

INT-07: memory/knowledge/refresh.py imports tools.browser.crawl_config and tools.browser.integration. Violates layering (memory depends on tools). Inject crawl function as callback parameter instead. AC: memory package has no tools imports. See docs/integration-audit.md.

## Research Complete

See docs/memory-tools-dependency-inversion-research.md for full analysis.

### Research Checklist
1. **Theoretical validity** - Dependency inversion via callback injection is sound. Lower layer defines the contract (type alias), upper layer provides the implementation.
2. **Prior art** - Cosmic Python Ch.3 (Functional Core / Imperative Shell + DI), Python typing.Protocol (PEP 544). Both validate the callback approach for single-function injection.
3. **Technical feasibility** - Confirmed: all 3 tools imports are isolated to refresh.py. CrawlHandler type alias uses only stdlib typing + memory-local IngestResult. No blockers.
4. **Architecture fit** - Codebase already uses Protocol DI (EmbeddingProvider, VectorStoreProtocol). Callback is simpler than Protocol for single-function case. Bootstrap already assembles the orchestrator.
5. **Implementation approach** - Option A (Callback injection, .85 confidence): Define CrawlHandler Callable type alias in refresh.py, replace crawler param, create closure factory in bootstrap.py.

### Recommendation
Option A: Callback injection. Simplest, removes all 3 imports, KISS/YAGNI-aligned. See research doc for trade-off matrix.
