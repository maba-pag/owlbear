---
id: 681
title: Research web search options for agent pipeline
status: research
priority: important
created: 2026-04-08T19:03:20.5804986+02:00
updated: 2026-04-08T19:03:20.5804986+02:00
tags:
    - scope:tools
    - ' type:research'
    - ' source:analysis'
class: standard
---

## Context

Analysis confirmed that v2 has no web search capability. The researcher agent has the `web` tool category (which provides `fetch_webpage` for known URLs) and `microsoft/markitdown/*` (document conversion), but no search-the-internet tool.

v1 had `tools/web_search.py` with DuckDuckGo integration. This was dropped in the v1→v2 transition. The researcher agent cannot discover new URLs or resources through search — it can only fetch URLs it already knows about.

## Research Questions

1. **What web search MCP servers exist?** Evaluate: Tavily MCP, Brave Search MCP, SerpAPI MCP, DuckDuckGo packages. Assess: API key requirements, rate limits, cost, quality.
2. **Is a custom MCP server needed?** Could a thin wrapper around `duckduckgo-search` (v1's approach) be packaged as a 5th OwlBear MCP server?
3. **How would it integrate?** The researcher agent's `tools:` list would need the new MCP server's tool references. Would other agents benefit (ideator for research, architect for prior art)?
4. **What's the minimal viable version?** A single `web_search(query, limit)` tool returning title+URL+snippet is probably sufficient.

## Acceptance Criteria

- [ ] AC1: Research doc in `.owlbear/research/` evaluating ≥3 web search options
- [ ] AC2: Trade-off matrix: API key required?, free tier?, rate limits, result quality, MCP ecosystem availability
- [ ] AC3: Recommendation with confidence score
- [ ] AC4: Follow-up implementation task(s) created if recommendation is favorable
