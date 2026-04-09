# Dead SourceType.CRAWL Stubs — Remove vs Document

> **Owning task:** #696 — Document or remove dead SourceType.CRAWL stubs in knowledge engine
> **Date:** 2026-04-08  **Status:** Complete

## 1. Context and Question

The knowledge engine carries `SourceType.CRAWL` stubs from v1 design. No crawl handler implementation exists in v2. Research #684 recommends deferring browser integration (YAGNI). Should we remove or document these stubs?

## 2. Sources Studied

| Source | Location | Relevance | What |
|--------|----------|-----------|------|
| v2 knowledge `models.py` | `serve/knowledge/src/owlbear_knowledge/models.py:39` | 1.0 | `SourceType.CRAWL = "crawl"` enum member |
| v2 `refresh.py` | `serve/knowledge/src/owlbear_knowledge/refresh.py:29,69,100,179-203` | 1.0 | `CrawlHandler` type alias, constructor param, dispatch branch, `_handle_crawl` method |
| v2 `loader.py` | `serve/knowledge/src/owlbear_knowledge/loader.py:39` | 1.0 | `"crawl"` in `_SOURCE_SCHEMA` YAML enum |
| Research #684 doc | `.owlbear/research/playwright-browser-integration-v2.md` | .95 | Recommends Option B MCP server (`serve/mcp-browser/`) when demand emerges |
| crawl4ai evaluation | `.owlbear/research/crawl4ai-evaluation.md` | .80 | YAGNI conclusion — crawling is supporting feature, not core mission |
| web-crawling research | `.owlbear/research/web-crawling.md` | .80 | v1 architecture: custom `WebCrawler` on `BrowserManager` — completely different from v2's handler injection pattern |

## 3. Analysis

### 3.1 Dead Code Inventory

| Component | File | Lines | Purpose |
|-----------|------|-------|---------|
| `SourceType.CRAWL` | models.py | 39 | Enum member |
| `CrawlHandler` type alias | refresh.py | 29 | Callable type for injection |
| `crawl_handler` constructor param | refresh.py | 69 | Optional DI slot |
| `_crawl_handler` storage | refresh.py | 74 | Instance variable |
| Dispatch branch | refresh.py | 100-101 | Routes CRAWL to `_handle_crawl` |
| `_handle_crawl` method | refresh.py | 179-203 | Raises ValueError if no handler |
| `"crawl"` in schema | loader.py | 39 | YAML manifest validation |
| 6+ test cases | test_bookmark_pipeline_136.py, test_refresh_555.py, test_refresh_orchestrator.py | Various | Test coverage for dead paths |
| 2 MCP test refs | test_ingest_graph_tools.py:174, test_list_sources.py:177 | — | Crawl type in test fixtures |

### 3.2 Trade-off Matrix

| Criterion | Option 1: Remove (.85) | Option 2: Document (.45) |
|-----------|------------------------|--------------------------|
| KISS | **High** — less code, less cognitive load | Low — dead code with comments is still dead code |
| YAGNI | **Aligned** — no demand exists (#684) | Violates — preserving unneeded extension points |
| Future re-add cost | **Trivial** — git history preserves everything; ~25 LOC to restore | N/A |
| Architecture fit | **High** — v2 would use MCP server, not handler injection (#684 Option B) | Low — stubs model the wrong integration pattern for v2 |
| Test maintenance | **Better** — removes ~80 LOC of tests for dead paths | Worse — tests remain for untestable-in-production code |
| Risk | **Negligible** — no production consumer exists | None |
| Churn | ~10 files touched | ~3 files touched (add comments) |

### 3.3 Key Insight

The v2 architecture uses MCP servers as integration points. If crawling is implemented, it would be `serve/mcp-browser/` (#684), not a callable injected into `RefreshOrchestrator`. The existing stubs model the wrong pattern — keeping them as "future integration points" is misleading because they won't be used as-is.

## 4. Recommendation

**Remove all CRAWL stubs.** Confidence: .85.

Rationale: (1) Dead code with no consumer. (2) Wrong architectural pattern for v2. (3) Trivial to restore from git history. (4) Aligns with KISS/YAGNI principles the project follows. (5) Reduces test surface for unreachable code.

Challenge: FALLBACK — trivial T1 dead-code cleanup; recommendation is uncontroversial.

## 5. Follow-up Tasks

- **Follow-up #1:** Remove `SourceType.CRAWL` enum member, `CrawlHandler` type alias, `crawl_handler` constructor param, `_handle_crawl` method, `"crawl"` from loader schema, and all crawl-specific tests. Update any test fixtures using crawl type.

Tier: **T1 — Autonomous.** Dead code removal is a refactor, not a capability change.
