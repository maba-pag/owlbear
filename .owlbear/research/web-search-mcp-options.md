# Web Search MCP Options for Agent Pipeline

> **Owning task:** #681 — Research web search options for agent pipeline
> **Date:** 2026-04-08 **Status:** Complete

## 1. Context and Question

v2 has no web search capability. The researcher agent has `web` (fetch_webpage for known URLs) and `microsoft/markitdown/*` but no search-the-internet tool. v1 used `duckduckgo-search` via a PydanticAI toolset — dropped in the v1→v2 MCP transition. The question: what's the best way to add web search to v2's MCP-based architecture?

Prior research (task #292, `.owlbear/research/web-search-tool.md`) evaluated search libraries for v1's toolset pattern. This research evaluates **MCP server options** for v2.

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| ddgs (deedy5/ddgs) v9.13 | github.com/deedy5/ddgs | .95 | Metasearch lib with **built-in MCP server** (`ddgs mcp`). 9 backends, extract(), 2.4k stars, MIT |
| Brave Search MCP (official) | github.com/brave/brave-search-mcp-server | .80 | Official Brave MCP server. Node.js/TS. 6 tools. API key required. 880 stars, 87 releases |
| Tavily MCP | github.com/tavily-ai/tavily-mcp | .70 | Node.js. Search+extract+map+crawl. API key required. 1.7k stars. Remote MCP option |
| MCP servers registry | github.com/modelcontextprotocol/servers | .60 | Lists official/community MCP servers. Brave archived → official repo. SearXNG community options |
| v1 web_search.py | v1/src/owlbear/tools/web_search.py | .85 | Prior v1 implementation using DDGS().text() via asyncio.to_thread(). Pattern reference |
| v2 MCP server pattern | serve/mcp-kanban/, serve/mcp-knowledge/ | .90 | FastMCP pattern: lifespan context, tool functions, pyproject.toml per server |
| Researcher agent config | share/agents/researcher.agent.md | .90 | Tool allowlist format: `'server-name/tool_name'`. Shows integration point |

## 3. Analysis

### 3.1 MCP Server Options

| Criterion | ddgs built-in MCP (.90) | Brave Search MCP (.65) | Tavily MCP (.55) | Custom OwlBear MCP (.50) |
|-----------|------------------------|----------------------|-------------------|--------------------------|
| API key required | **No** | Yes (free tier avail.) | Yes (paid) | No |
| Language | Python | Node.js/TS | Node.js/TS | Python |
| Search backends | **9** (auto-fallback) | 1 (Brave) | 1 (Tavily) | Wraps ddgs (9) |
| Tools provided | 6 (text/images/news/videos/books/extract) | 6 (web/local/video/image/news/summarizer) | 4 (search/extract/map/crawl) | Custom (1-2) |
| Content extraction | Built-in `extract_content` | No | Yes (`tavily-extract`) | DIY with httpx+trafilatura |
| Setup complexity | `pip install ddgs[mcp]` + config | `npx` + API key mgmt | `npx` + API key mgmt | New package + tests |
| Maintenance burden | **Zero** (upstream) | Zero (upstream) | Zero (upstream) | **High** (own code) |
| KISS score | **High** | Medium | Low | Medium |
| Stack alignment | **Python** (matches v2) | Node.js (new runtime) | Node.js (new runtime) | Python |
| Stars / maturity | 2.4k / 208 releases | 880 / 87 releases | 1.7k / no releases | N/A |

### 3.2 Integration Approach

Adding an external MCP server to the agent pipeline requires:

1. **VS Code MCP config** — add server entry in `.vscode/mcp.json` (or user settings)
2. **Agent tool allowlists** — add `'ddgs/*'` (or selected tool names) to researcher/ideator agent tools lists
3. **No code changes** to existing MCP servers or agent implementations

For ddgs specifically:
```json
{
  "servers": {
    "ddgs": {
      "command": "ddgs",
      "args": ["mcp"]
    }
  }
}
```

### 3.3 Which Agents Benefit?

| Agent | Use Case | Priority |
|-------|----------|----------|
| researcher | Prior art discovery, documentation lookup | **Primary** |
| ideator | Feature research, competitive analysis | High |
| architect (future) | Technology evaluation, API docs | Medium |
| builder | Library docs lookup (has codebase access already) | Low |

### 3.4 Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| ddgs scraping breaks | Medium | Medium | 9-backend auto-fallback; upstream actively maintained |
| Rate limiting | Low-Medium | Low | Agent usage is infrequent; built-in retry |
| ddgs abandoned | Very Low | High | Brave Search MCP as fallback (requires API key) |
| Tool proliferation (6 tools) | Low | Low | Can restrict to `ddgs/search_text` + `ddgs/extract_content` only |

## 4. Recommendation (.85 confidence)

**Use ddgs built-in MCP server.** No API key, Python-native, 9-backend metasearch with auto-fallback, built-in content extraction, zero maintenance. Integration is pure configuration — no new code in OwlBear's serve/ directory.

Start with 2 tools in agent allowlists: `ddgs/search_text` and `ddgs/extract_content`. Add image/news/video search later if needed (YAGNI).

**Tier classification: T3 (new capability)** — adds web search to agent pipeline, changes agent behavior. Requires DR via scribe.

Challenge: FALLBACK — no challenger agent available in this session.

## 5. Follow-up Tasks

1. **DR: Approve ddgs MCP server integration** — T3 decision: adding external web search capability to agent pipeline
2. **Add ddgs MCP server to VS Code config** — configure `.vscode/mcp.json`, add ddgs dependency
3. **Update researcher agent tool allowlist** — add `ddgs/search_text`, `ddgs/extract_content` to tools
4. **Update ideator agent tool allowlist** — add `ddgs/search_text` for feature research
5. **Integration test** — verify ddgs MCP server starts, researcher can invoke search
