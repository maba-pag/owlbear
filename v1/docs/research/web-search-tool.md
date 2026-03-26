# Web Search Tool Research

> **Owning task:** #292 — Web search tool — enable agents to search the internet
> **Date:** 2026-03-01
> **Status:** Complete

## 1. Context and Question

Agents need a web search primitive for research, prior art discovery, and documentation lookup. The existing `BrowserToolset` provides navigate/click/read but no search capability. The content extractor (`trafilatura`) and URL safety guard already exist. Key questions: (1) what search backend? (2) dedicated toolset or extend browser? (3) how to handle content extraction for `web_read`?

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| ddgs (deedy5/ddgs) | github.com/deedy5/ddgs | .90 | Metasearch library: DuckDuckGo, Google, Bing, Brave, Yahoo backends. No API key. Returns `{title, href, body}`. MIT, 2.2k stars, 761 dependents |
| SearXNG | github.com/searxng/searxng | .60 | Self-hosted metasearch engine. JSON API. Requires Docker/server. 25.5k stars |
| Brave Search API | search.brave.com/api | .50 | REST API, requires paid API key ($3/1k queries after free tier) |
| LangChain DuckDuckGoSearchRun | python.langchain.com/docs/integrations/tools/ddg | .75 | Thin wrapper over `duckduckgo-search`; formats concatenated snippets for LLM consumption |
| Existing content_extractor.py | src/owlbear/tools/browser/content_extractor.py | .95 | trafilatura-based extraction already in codebase — Markdown output, metadata |
| Existing URLSafetyGuard | src/owlbear/tools/browser/safety.py | .90 | Regex blocklist/allowlist pattern reusable for search result filtering |
| MCP servers research | docs/research/mcp-servers.md | .70 | Previously deferred Brave Search MCP server due to API key requirement |

## 3. Analysis

### 3.1 Search Backend

| Criterion | ddgs (.85) | SearXNG (.45) | Brave Search API (.40) | Raw httpx scraping (.25) |
|-----------|------------|---------------|------------------------|--------------------------|
| API key required | No | No | Yes ($3/1k) | No |
| Setup complexity | `pip install ddgs` | Docker container | Account + key mgmt | DIY HTML parsing |
| Multi-engine fallback | Yes (9 engines) | Yes (hundreds) | Single engine | Single engine |
| Structured output | `{title, href, body}` | JSON API | JSON API | Fragile HTML parsing |
| Rate limit handling | Built-in retry + `RatelimitException` | Self-hosted (no limits) | 2000 free/mo | Manual |
| Dependency cost | 1 pkg (`primp` Rust HTTP) | Full server | httpx (already have) | 0 |
| Maintenance burden | Low (library maintained) | High (server ops) | Low | High (scraper breaks) |
| KISS score | **High** | Low | Medium | Low |

### 3.2 Dedicated Toolset vs Extend BrowserToolset

| Criterion | Dedicated WebSearchToolset (.90) | Extend BrowserToolset (.35) |
|-----------|----------------------------------|----------------------------|
| Separation of concerns | Clean — search is stateless HTTP | Mixes browser lifecycle with search |
| Playwright dependency | Not needed | Forces Playwright for search |
| Startup cost | None (lazy init) | Browser launch overhead |
| Agent flexibility | Agents can use search without browser | All-or-nothing |
| Follows existing patterns | Yes — matches FileToolset, TerminalToolset | Violates single-responsibility |
| `web_read` implementation | httpx + trafilatura (lightweight) | Playwright overkill for static pages |

### 3.3 Content Extraction for `web_read`

| Criterion | httpx + trafilatura (.85) | Playwright + trafilatura (.60) | httpx + BeautifulSoup (.40) |
|-----------|--------------------------|-------------------------------|----------------------------|
| JS rendering | No | Yes | No |
| Speed | Fast (~200ms) | Slow (~2s) | Fast (~200ms) |
| Dependencies | httpx (have) + trafilatura (have) | playwright (optional) | new dep |
| Coverage | 90% of pages | 99% of pages | 60% of pages |
| KISS score | **High** | Medium | Medium |

For the 10% JS-rendered pages, the agent can fall back to `browser_navigate` + `browser_read_text`.

### 3.4 Result Formatting for LLM

LangChain's pattern: concatenate snippets into a single string. Better approach — numbered markdown list with title, URL, and snippet separated. This gives the LLM structured info to decide which links to follow with `web_read`:

```markdown
## Search results for "pydantic-ai toolsets"

1. **PydanticAI Toolsets Documentation** — Toolsets let you register…
   https://ai.pydantic.dev/toolsets/

2. **GitHub: pydantic/pydantic-ai** — PydanticAI is a Python agent framework…
   https://github.com/pydantic/pydantic-ai
```

### 3.5 URL Safety Integration

The existing `URLSafetyGuard.check_url()` method is reusable. For web search:

- **Search results**: Filter results through blocklist before returning to agent
- **web_read**: Check URL before fetching (same as `browser_navigate`)
- Share `blocked_urls`/`allowed_urls` patterns from a common config, or accept them as `WebSearchToolset.__init__` params with sensible defaults

### 3.6 Dependency Strategy

`ddgs` uses `primp` (Rust-based HTTP client with TLS fingerprinting). This is a new dependency chain but justified — it's what makes API-key-free search work reliably. Add as optional:

```toml
search = ["ddgs>=9.0.0"]
```

`web_read` reuses existing `trafilatura` from `crawl` extra. Combined extra:

```toml
search = ["ddgs>=9.0.0", "trafilatura>=2.0.0"]
```

## 4. Recommendation (.85 confidence)

**Use `ddgs` library for search, httpx + trafilatura for content extraction, as a dedicated `WebSearchToolset`.**

- `ddgs` is the KISS choice: no API key, multi-engine fallback, structured output, actively maintained. Its sync API is trivially wrapped with `asyncio.to_thread()`.
- `web_read` uses httpx (already a dependency) + trafilatura (already an optional dep) — no new packages needed for content extraction.
- Dedicated toolset follows existing patterns and avoids coupling with Playwright.
- URL safety guard reuses existing `URLSafetyGuard.check_url()` or equivalent blocklist check.

**Risk:** `ddgs` scrapes search engines, which may break if engines change HTML. **Mitigation:** `ddgs` has 9 backend engines and an `auto` mode that falls back across them. Library is actively maintained (203 releases as of Dec 2025).

**Risk:** Rate limiting under heavy agent use. **Mitigation:** Add configurable delay between searches (default 2s). Catch `RatelimitException` and return informative error.

## 5. Follow-up Tasks

1. **Add `ddgs` optional dependency** — Add `search = ["ddgs>=9.0.0", "trafilatura>=2.0.0"]` to `pyproject.toml`.

2. **Implement `WebSearchToolset`** — `src/owlbear/tools/web_search.py`, subclass `FunctionToolset`, register `web_search` and `web_read` tools. Use `DDGS().text()` via `asyncio.to_thread()`. Format results as numbered markdown. Apply URL blocklist to results and to `web_read` targets.

3. **Wire into bootstrap** — Add `WebSearchToolset` to `build_toolsets()` in `bootstrap.py`.

4. **Unit tests** — Mock `DDGS().text()`, mock httpx responses, test result formatting, test URL safety filtering, test error handling. Target >= 90% coverage.
