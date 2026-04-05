---
id: 292
title: Web search tool — enable agents to search the internet
status: archived
priority: critical
created: 2026-03-01T02:52:02.8223556+01:00
updated: 2026-03-22T18:59:18.2235207+01:00
started: 2026-03-01T03:25:30.329278+01:00
completed: 2026-03-01T17:08:16.4303051+01:00
tags:
    - phase-11
    - tools
depends_on:
    - 309
class: standard
---

Implement WebSearchToolset — a dedicated FunctionToolset for web search and content retrieval. See docs/research/web-search-tool.md for research findings. Uses `ddgs` library for search, `httpx` + `trafilatura` for content extraction.

## Acceptance Criteria

### Dependency: pyproject.toml

- [ ] Add optional extra: `search = ["ddgs>=9.0.0", "trafilatura>=2.0.0"]`
- [ ] `ddgs` import guarded with try/except ImportError at module level (same pattern as trafilatura in content_extractor.py)

### WebSearchToolset class (`src/owlbear/tools/web_search.py`)

- [ ] `WebSearchToolset(FunctionToolset)` subclass
- [ ] Constructor: `__init__(self, *, blocked_urls: list[str] = [], allowed_urls: list[str] = [])`
- [ ] Stores compiled regex patterns for blocked/allowed URLs
- [ ] `_register_tools()` registers 2 tools: `web_search`, `web_read`
- [ ] Private `_check_url(url: str) -> None` — raises ValueError if URL is blocked or not in allowlist (evaluation order: blocklist first, then allowlist — same as URLSafetyGuard)
- [ ] `__all__ = ["WebSearchToolset"]`

### web_search tool

- [ ] Registered name: `web_search`
- [ ] Signature: `_web_search(self, query: str, num_results: int = 5) -> str`
- [ ] Uses `DDGS().text(query, max_results=num_results)` wrapped in `asyncio.to_thread()`
- [ ] Returns numbered markdown list: `1. **{title}** — {snippet}\n   {url}`
- [ ] Filters each result URL through `_check_url()` — excluded results silently dropped
- [ ] Catches `ddgs.exceptions.RatelimitException` → returns `"Rate limited. Try again in a few seconds."`
- [ ] Returns `"No results found for: {query}"` for empty result sets

### web_read tool

- [ ] Registered name: `web_read`
- [ ] Signature: `_web_read(self, url: str, max_length: int = 50_000) -> str`
- [ ] Calls `_check_url(url)` before fetching — raises ValueError for blocked URLs
- [ ] Fetches via `httpx.AsyncClient.get(url, timeout=30, follow_redirects=True)`
- [ ] Extracts content via `trafilatura.extract(html, output_format="markdown", include_links=True, url=url)`
- [ ] Falls back to raw HTML text (stripped tags) truncated to max_length if trafilatura returns None
- [ ] Truncates final output to max_length characters
- [ ] Handles `httpx.TimeoutException` → returns `"Timeout fetching {url}"`
- [ ] Handles `httpx.HTTPStatusError` → returns `"HTTP {status}: {url}"`

### Bootstrap wiring (`src/owlbear/bootstrap.py`)

- [ ] Import WebSearchToolset (guarded try/except like other optional toolsets)
- [ ] Add to `build_toolsets()` after BrowserToolset — conditional on ddgs being installed
- [ ] Wrapped in HookedToolset (same as other raw toolsets)
- [ ] blocked_urls/allowed_urls sourced from BrowserConfig defaults (share the same safety patterns)

### Architecture constraints

- Follow FileToolset/TerminalToolset pattern: subclass FunctionToolset, `_register_tools()`, private tool methods
- No Playwright dependency — httpx only for web_read
- `ddgs` sync API wrapped with `asyncio.to_thread()` (it does network I/O)
- Module-level docstring with Usage example (following filesystem.py pattern)
- Logging via `logging.getLogger(__name__)`
- >= 90% coverage (test task #309)
