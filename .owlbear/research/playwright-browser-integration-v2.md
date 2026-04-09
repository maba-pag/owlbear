# Playwright Browser Integration for v2 Agents

> **Owning task:** #684 — Research: Playwright browser integration for agents
> **Date:** 2026-04-08  **Status:** Complete

## 1. Context and Question

v1 has a full Playwright browser subsystem (~1200 LOC, 12 files) under
`v1/src/owlbear/tools/browser/`: BrowserManager (CDP/launch), BrowserToolset
(7 tools), WebCrawler (BFS), content extraction (trafilatura), URL safety
guard, content injection guard, Edge CDP launcher, HTML cache, and CLI
commands. Prior research #264 (2026-02-28) evaluated OSS alternatives and
concluded: keep custom (.90 confidence).

v2 has zero browser capability. The knowledge engine has dead `SourceType.CRAWL`
stubs in `RefreshOrchestrator` (raises `ValueError` when `crawl_handler=None`),
but no handler implementation. The `fetch_webpage` tool available in Copilot
Chat provides basic HTTP GET — no JS rendering, no screenshots, no auth.

**Question:** What scope of browser integration should v2 adopt, and how?

## 2. Sources Studied

| Source | Location | Relevance |
|--------|----------|-----------|
| v1 browser module | `v1/src/owlbear/tools/browser/` (12 files) | .95 |
| Prior research #264 | `.owlbear/research/browser-automation.md` | .90 |
| v2 knowledge engine | `serve/knowledge/src/owlbear_knowledge/` | .85 |
| v2 MCP server pattern | `serve/mcp-kanban/` (reference architecture) | .80 |
| v2 pyproject.toml | Root + `serve/knowledge/pyproject.toml` | .75 |
| Playwright PyPI | pypi.org/project/playwright/ (v1.58.0) | .70 |

## 3. Analysis

### 3.1 Use Case Inventory

| Use Case | Priority | `fetch_webpage` covers? | Needs Playwright? |
|----------|----------|------------------------|-------------------|
| Knowledge ingestion from static pages | High | Yes — httpx GET sufficient | No |
| JS-rendered SPA content extraction | Medium | No — no JS execution | Yes |
| Screenshot capture for visual debug | Low | No | Yes |
| Interactive web app testing | Low | No | Yes |
| Authenticated intranet access | Low | No — needs cookie/session | Yes |
| Crawling (BFS with depth/page limits) | Medium | No | Yes |

**Finding:** The high-priority use case (static page ingestion) is already
served by the URL intake handler (`owlbear_knowledge.intake.read_url`). The
Playwright-dependent use cases are medium-to-low priority.

### 3.2 Scope Options vs Use Cases

| Criterion | A: Minimal | B: Read-only | C: Full v1 | D: MCP Server |
|-----------|-----------|-------------|-----------|---------------|
| Screenshot | Yes | Yes | Yes | Yes |
| Navigate + read | No | Yes | Yes | Yes |
| Click/type/select | No | No | Yes | Yes |
| Crawler | No | No | Yes | Optional |
| AX tree snapshot | No | Yes | Yes | Yes |
| Knowledge engine wire-up | No | Partial | Full | Via tool call |
| Complexity (est. LOC) | ~100 | ~400 | ~1200+ | ~600 + MCP |
| New dependencies | playwright | playwright | playwright + trafilatura | playwright + mcp |
| Architecture fit | Tool func | Tool funcs | FunctionToolset? | MCP server |
| v2 pattern alignment | Low | Medium | Low (no FunctionToolset) | High |

### 3.3 Dependency Impact

| Item | Detail |
|------|--------|
| Package | `playwright>=1.40.0` |
| Python install | ~5 MB (pip package) |
| Browser binaries | ~300-500 MB (`playwright install chromium`) |
| v2 dependency tree | Not present — must add as optional extra |
| Transitive deps | greenlet, pyee (~2 additional) |
| Corporate constraint | No admin needed — Playwright self-installs browsers |

### 3.4 Architecture Fit Assessment

v2 uses MCP servers (`serve/mcp-*`), not PydanticAI FunctionToolsets. v1's
`BrowserToolset` is a `FunctionToolset` subclass — this pattern doesn't
exist in v2. The natural v2 integration point is a new MCP server
(`serve/mcp-browser/`) following the established pattern:

- `serve/mcp-kanban/` — 1 dependency (`mcp[cli]`), FastMCP-based
- `serve/mcp-knowledge/` — thin MCP wrapper around knowledge engine
- `serve/mcp-memory/` — thin MCP wrapper around memory store

A `serve/mcp-browser/` would expose tools like `browser_navigate`,
`browser_screenshot`, `browser_read_text`, `browser_snapshot` as MCP
tools — consumable by any agent via the standard MCP client.

### 3.5 CrawlHandler Integration Path

The knowledge engine's `RefreshOrchestrator` already accepts a
`crawl_handler: CrawlHandler` injection point. A browser MCP server
could provide the crawl_handler implementation, or it could be wired
as a library dependency (not via MCP). The cleanest path:

1. Create `serve/mcp-browser/` with Playwright browser tools
2. Separately create a `crawl_handler` adapter in `serve/knowledge/`
   that calls the browser MCP tools or directly uses Playwright

### 3.6 Priority vs KISS/YAGNI

| Principle | Assessment |
|-----------|------------|
| KISS | Browser integration adds significant complexity (browser lifecycle, CDP, cleanup). Only justified when JS-rendering or screenshots are actively needed. |
| YAGNI | No current v2 agent workflow requires browser automation. The dead CRAWL stubs suggest it was planned but never needed. |
| Priority | Task is `nice-to-have`. No blocking downstream work identified. |

## 4. Recommendation — Option B (Read-Only MCP) when needed (.75 confidence)

**Defer implementation.** No current v2 workflow requires browser integration.
The `nice-to-have` priority and YAGNI principle both argue against building
this now.

**When demand materializes,** implement Option B (read-only) as a new MCP
server `serve/mcp-browser/`:

- Tools: `browser_navigate`, `browser_read_text`, `browser_screenshot`,
  `browser_snapshot` (accessibility tree)
- Port from v1: `BrowserManager`, `BrowserConfig`, `URLSafetyGuard`,
  `ContentInjectionGuard`, Edge launcher
- Skip: click/type/select (interactive), WebCrawler (separate concern)
- Optional extra: `playwright>=1.40.0` in `pyproject.toml`
- Wire crawl handler separately if/when crawl use case emerges

**Why not Option C/D full:**
- v1 interactive tools (click/type/select) were rarely used by agents
- Crawler is a separate concern — port independently if needed
- Full v1 port would be ~1200 LOC for low-priority capability

**Why not Option A minimal:**
- Screenshot-only doesn't justify the Playwright dependency — a headless
  Chromium for one function is wasteful. If we install Playwright, get
  navigate + read_text + snapshot too

Challenge: FALLBACK — subagent invocation not attempted (defer recommendation
has no controversy requiring challenge)

## 5. Follow-up Tasks

1. Remove dead `SourceType.CRAWL` stubs or document them as future
   integration point (backlog, low priority)
2. When browser demand emerges: create `serve/mcp-browser/` MCP server
   with read-only Playwright tools ported from v1
