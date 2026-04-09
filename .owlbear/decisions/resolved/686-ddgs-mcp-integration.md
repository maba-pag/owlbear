---
# >> Your action: set response to approved, needs-info, or rejected
response: approved
decision: "A: Approve ddgs integration as proposed"
notes: ""
# >> Agent metadata
task_id: 686
agent: researcher
created: 2026-04-09
urgency: blocking
decision_type: feature-gate
impact_tier: 3
---

# Decision: Add ddgs MCP server for web search in agent pipeline?

## Context

v2 has no web search capability. The researcher agent has `fetch_webpage` for known URLs but no search-the-internet tool. v1 used `duckduckgo-search` via PydanticAI toolset — dropped in the v1→v2 MCP transition.

Research #681 evaluated 4 MCP server options (ddgs built-in, Brave Search, Tavily, custom OwlBear MCP) and recommended ddgs with .85 confidence. Follow-up implementation research on #686 validated the approach at .82 confidence, addressing dependency placement, MCP config format, agent tool selection, and compatibility.

This is a **T3 new capability** — adds external web search to the agent pipeline, changing what researcher and ideator agents can do. Task #686 is blocked pending this decision.

## Options

### A: Approve ddgs integration as proposed — (rec:) recommended
- Effort: ~1 hour (pure configuration: dependency + MCP config + agent tool allowlists)
- Trade-off: Adds external runtime dependency (ddgs v9.13, MIT, 2.4k stars, 208 releases). Scraping-based — no API key needed but could break if search engines change anti-scraping measures. 9-backend auto-fallback mitigates.
- Risk: Low. `ddgs[mcp]>=9.13,<10` version pin limits blast radius. mcp SDK compatibility unverified (needs `uv add --dry-run` check before implementation). Agents degrade gracefully if search fails.
- Details: Add `ddgs[mcp]>=9.13,<10` to dev dependencies. Configure `uv run ddgs mcp` in seed/.vscode/mcp.json. Grant researcher `ddgs/search_text` + `ddgs/extract_content`; ideator `ddgs/search_text` only. See `.owlbear/research/ddgs-mcp-integration.md`.

### B: Require additional evaluation of alternatives
- Effort: 2–4 hours research + implementation
- Trade-off: Delays web search capability. Brave Search MCP (Node.js, API key required) and Tavily (Node.js, paid API key) are the main alternatives — both require a different runtime and credential management.
- Risk: Analysis paralysis. Research already evaluated 4 options systematically.

### C: Defer — web search not needed yet
- Effort: Zero
- Trade-off: Researcher and ideator remain limited to fetching known URLs. No competitive analysis, no prior art discovery, no documentation search outside the workspace.
- Risk: Low immediate risk, but agents lack a capability that was available in v1.
