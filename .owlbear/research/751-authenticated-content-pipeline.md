# Authenticated Content Pipeline — Research Validation

> **Owning task:** #751 — Authenticated Content Pipeline
> **Date:** 2026-04-10  **Status:** Complete

## 1. Context and Question

Task #751 proposes a Production-tier feature to bring corporate authenticated web content (behind SSO on SharePoint, Confluence, internal tools) into the OwlBear knowledge graph via Edge CDP. The brief (`.owlbear/briefs/draft-browser-knowledge-extraction/brief.md`) has full voice analysis (architect, security, data-person). This research validates the brief's technical approach, assesses HTML cleaning library options, and confirms architecture fit with the existing knowledge pipeline.

Key questions: (1) Is Playwright `connect_over_cdp` viable for Edge SSO reuse? (2) Which HTML→markdown cleaning approach for the pipeline? (3) Does the phased delivery plan hold up against the codebase?

## 2. Sources Studied

| Source | URL | Type | Relevance |
|--------|-----|------|-----------|
| Playwright `connect_over_cdp` docs | <https://playwright.dev/python/docs/api/class-browsertype#browser-type-connect-over-cdp> | Primary — API docs | .95 |
| trafilatura (PyPI) | <https://pypi.org/project/trafilatura/> | Primary — extraction lib | .85 |
| markdownify (PyPI) | <https://pypi.org/project/markdownify/> | Primary — HTML→MD lib | .80 |
| browser-use project | <https://github.com/browser-use/browser-use> | Prior art — CDP automation (80K stars) | .85 |
| Existing a11y-snapshot research (#726) | `.owlbear/research/a11y-snapshot.md` | Internal — CDP viability validation | .90 |
| Existing knowledge pipeline | `serve/knowledge/src/owlbear_knowledge/` | Internal — integration surface | .95 |
| Brief + voice analysis | `.owlbear/briefs/draft-browser-knowledge-extraction/` | Internal — design spec | .95 |

## 3. Analysis

### 3a. Edge CDP Viability

Playwright `connect_over_cdp` (stable since v1.9) connects to a running Chromium-based browser via Chrome DevTools Protocol. Usage:

```python
browser = await playwright.chromium.connect_over_cdp("http://localhost:9222", is_local=True)
```

**Confirmed**: Works with Edge (Chromium-based). The `is_local=True` flag (v1.58+) enables file system optimizations. CDP carries the user's full authenticated session — no isolation, which is required for SSO reuse. The a11y-snapshot research (#726) already validated CDP session management in this project.

**Corporate environment risk**: EDR/DLP may block `--remote-debugging-port`. This is an execution risk, not an architecture risk — hence Phase 0 spike.

### 3b. HTML→Markdown Cleaning — Trade-off Matrix

| Criterion | trafilatura | markdownify + custom strip | readability-lxml + markdownify |
|-----------|-------------|---------------------------|-------------------------------|
| License | Apache 2.0 ✅ | MIT ✅ | Apache 2.0 + MIT ✅ |
| Main content extraction | Built-in | Manual (fragile) | Built-in |
| Boilerplate removal | Built-in (nav, footer, ads) | Custom BS4 filtering (~40-80 LOC) | Built-in |
| Markdown output | Native | Native | HTML → markdownify (2-step) |
| Transitive deps | ~8 | 1 (bs4) | 2 (lxml) + 1 (bs4) |
| LOC for integration | ~10 | ~40-80 | ~20 |
| Corporate HTML quality | Best (benchmark-proven) | Fragile (site-specific patterns) | Good (article-biased) |
| KISS alignment | Medium (feature-rich) | Low (custom boilerplate code) | High |
| Risk | Over-extraction on web-part pages | Under-extraction, maintenance | Article-bias may strip web parts |

**html2text was evaluated and excluded** — GPL-3.0 license is incompatible.

### 3c. Architecture Fit with Existing Pipeline

The brief proposes protocol injection via `ContentFetcher = Callable[[str], Awaitable[IntakeResult]]`. This aligns with the existing pipeline:

| Pipeline component | Current state | Change needed |
|-------------------|---------------|---------------|
| `SourceType` enum | `URL_LIST`, `FILE_GLOB` | Add `AUTHENTICATED_WEB` |
| `RefreshOrchestrator` | Handlers per source type | New `_handle_authenticated_web()` + shared `_fetch_and_ingest_urls()` |
| `EntityType` enum | 6 code-centric types | Add 5 corporate types (REQUIREMENT, SOLUTION, PROCEDURE, POLICY, STANDARD) |
| `RelationType` enum | 7 types | Add GOVERNS, SUPERSEDES_VERSION |
| `IngestPipeline.ingest()` | Wraps URL content in `<untrusted_web_content>` | Invert predicate: wrap all except file/text (security voice rec) |
| Schema | v8, no source_id FK on docs | v9: `source_pages` table + `source_id` FK on `documents` |
| `LLM_EXTRACTION_PROMPT` | Code-centric guidance | Add corporate entity examples |

**Existing DI patterns**: `StructuredExtractor` protocol, `ContentFetcher`-style callable injection in evaluator/bookmark pipeline. The approach is consistent with established project conventions.

### 3d. Content Safety Gap

The ingest pipeline checks `metadata.get("source_type") == "url"` for untrusted content wrapping (`ingest.py` line ~154). Authenticated web content with `source_type="authenticated_web"` would bypass this. The architect voice already identified this: predicate should be inverted to wrap everything except known-safe types (`"file"`, `"text"`). This is a one-line fix but must ship in Phase 1.

### 3e. Phased Delivery Validation

| Phase | Dependencies | Validated |
|-------|-------------|-----------|
| 0: CDP spike | None — independent validation | ✅ Correct go/no-go gate |
| 1: Browser pkg + pipeline quality | Phase 0 passes | ✅ Clean boundary — browser decoupled from knowledge |
| 2: Source management agent | Phase 1 (browser tools + ingestion) | ✅ Agent uses 2 MCP tool sets |
| 3: Cross-source linking | Phase 2 (ingested corporate content) | ✅ InterDocGraphBuilder already has DI pattern |
| 4: SharePoint API (optional) | Protocol abstraction from Phase 1 | ✅ ContentFetcher protocol accommodates swap |

## 4. Recommendation

**Proceed with brief's approach as-is. Confidence: .82.**

The brief's architecture is sound, security analysis is thorough, and data quality gaps are correctly identified. Two specific recommendations:

1. **HTML cleaning**: Use trafilatura for Phase 1 (confidence: .75). Accept ~8 transitive deps for battle-tested content extraction. If trafilatura over-extracts on corporate web-part pages (validated during Phase 0 spike alongside CDP), fall back to readability-lxml + markdownify.

2. **Phase 0 scope addition**: Test trafilatura extraction quality on real corporate pages alongside CDP connectivity. The spike should validate both transport (CDP) and content quality (extraction) before Phase 1 investment.

**Challenge: FALLBACK — challenger subagent not available in agent list. Self-challenge applied: primary risk is trafilatura dep weight (~8 deps) vs KISS principle. Mitigation: dep count is in the browser package only — knowledge package unchanged. Secondary risk: corporate EDR blocking CDP — mitigated by Phase 0 gate.**

**Tier classification: T3** — new capability, architecture changes, new packages, schema migration, pipeline behavior change. Blocking DR required for the go/no-go decision after Phase 0 spike completes.

## 5. Follow-up Tasks

Created at `research` status as children of #751:

- **Phase 0: Edge CDP Technical Spike** — validate CDP connectivity on corporate laptop + trafilatura extraction quality on SharePoint/Confluence sample pages
- **Phase 1: Browser Package + Pipeline Quality + Schema** — needs decomposition (browser pkg, MCP server, content cleaner, schema v9 migration, entity types, content safety inversion, extraction prompt update)
