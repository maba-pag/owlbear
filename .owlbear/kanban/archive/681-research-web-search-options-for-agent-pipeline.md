---
id: 681
title: Research web search options for agent pipeline
status: archived
priority: medium
created: 2026-04-08T19:03:20.5804986+02:00
updated: 2026-04-09T00:58:34.7604341+02:00
started: 2026-04-09T00:58:34.7604341+02:00
completed: 2026-04-09T00:58:34.7604341+02:00
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

[[2026-04-08]] Wed 20:54
## Research
- Research doc: .owlbear/research/web-search-mcp-options.md
- Sources: 7 studied, 4 high-relevance (ddgs .95, v2 MCP pattern .90, researcher agent .90, v1 web_search .85)
- Recommendation: Use ddgs built-in MCP server (confidence: .85)
- Follow-up tasks created: #686 (implementation at research)
- Decision requests: T3 — needs DR via scribe (new capability addition)

## Challenge Results
- Challenger: FALLBACK — no challenger agent available in session
- Confidence in original: .85
- Key finding: ddgs v9.13 now ships its own MCP server (`ddgs mcp`), eliminating need to build a custom OwlBear MCP server. Zero API keys, 9 search backends with auto-fallback, built-in content extraction. Pure configuration integration — no new code in serve/.

## Key Findings
1. ddgs library evolved since v1 research — now includes built-in MCP server with 6 tools and 9 backends
2. Brave Search MCP is viable alternative but requires API key and Node.js runtime (stack mismatch)
3. Tavily MCP requires paid API key — eliminated on cost/KISS grounds
4. Custom OwlBear MCP server (v1-style approach) unnecessary — ddgs MCP provides better capability with zero maintenance
5. Integration is pure config: `.vscode/mcp.json` entry + agent tool allowlist updates

[[2026-04-08]] Wed 21:35
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Pure research task — single topic (web search options) |
| Interface clarity | PASS | AC defines 4 clear deliverables: research doc, matrix, recommendation, follow-ups |
| Dependency correctness | PASS | No dependencies listed, none needed for standalone research |
| Module layering | N/A | No code changes — research deliverable only |
| TDD compliance | N/A | `type:research` — no testable code |
| KISS/YAGNI | PASS | Scoped to 4 specific research questions, evaluated minimum viable set |
| Premise challenge | PASS | Confirmed v2 has no web search capability — researcher agent has `web` (fetch_webpage) and `markitdown/*` but no search tool. Gap is real |
| Pattern consistency | PASS | Research doc follows `.owlbear/research/` convention with standard structure (Context, Sources, Analysis, Recommendation, Follow-ups) |
| Security surface | PASS | No code changes. Research notes ddgs is MIT-licensed, no API keys, no new attack surface at research stage |
| Single domain | PASS | `scope:tools` only |

### Deliverable Verification

- AC1: Research doc at `.owlbear/research/web-search-mcp-options.md` — **MET** (evaluates 4 options: ddgs, Brave, Tavily, Custom)
- AC2: Trade-off matrix — **MET** (10-criterion comparison table in §3.1 covering API key, free tier, rate limits, quality, MCP availability)
- AC3: Recommendation with confidence — **MET** (ddgs built-in MCP server, .85 confidence)
- AC4: Follow-up task created — **MET** (#686 at `research` status, depends_on #681)

### T3 DR Note

Research correctly identifies T3 tier classification and flags DR requirement for implementation. The DR enforcement belongs at #686's architect review, not at this research task. The researcher fulfilled their obligation by documenting the DR need.

### Challenge Results
- Challenger: FALLBACK — no challenger agent available in session
- Architect assessment: Research is thorough (7 sources, 4 high-relevance), recommendation is well-supported by evidence, risk assessment is reasonable. No architectural concerns with the research deliverables themselves.

### Verdict: APPROVE
### Action Taken: Advanced #681 to todo. All 4 AC deliverables verified. T3 DR enforcement deferred to follow-up task #686 architect review.

[[2026-04-08]] Wed 22:23
## Test-Writer Notes
- Non-implementation task (tagged type:research) — no tests applicable.
- Passing through to builder.

[[2026-04-08]] Wed 22:44
## Builder Notes
- Non-implementation task — no code changes needed.
- Passing through to review.

[[2026-04-08]] Wed 23:23
## Review Evidence

### Source Control
No files changed for #681. All git diff entries are unrelated tasks (#685, #688 test infrastructure, kanban task files, research docs for other tasks, voice package, brief files). Type:research — no code changes expected or present.

### Test Results
N/A — `type:research`, no tests applicable. No TestFromAC modifications detected.

### Lint
N/A — no code changes.

### AC Compliance Table

| AC | Evidence | Status |
|----|----------|--------|
| AC1: Research doc in `.owlbear/research/` evaluating ≥3 web search options | `.owlbear/research/web-search-mcp-options.md` exists; §3.1 matrix covers 4 options: ddgs, Brave, Tavily, Custom | PASS |
| AC2: Trade-off matrix — API key, free tier, rate limits, result quality, MCP ecosystem | §3.1: 10-criterion matrix covers all required dimensions (API key row, free tier inline, rate limits in §3.4 risk table, result quality via stars/maturity, MCP ecosystem via maturity) | PASS |
| AC3: Recommendation with confidence score | §4: "Use ddgs built-in MCP server. Confidence: .85" — explicit and located | PASS |
| AC4: Follow-up task(s) if recommendation favorable | #686 at `research` status with `depends_on: [681]`; §5 of research doc enumerates 5 follow-up items | PASS |

### Research Quality
7 sources studied, 4 high-relevance. Integration approach detailed with JSON config snippet. Agent benefit analysis included. Risk matrix complete. T3 classification flagged; DR deferral to #686 endorsed by architect review.

### Deductions
None. AC2 coverage is distributed across §3.1 and §3.4 rather than all in matrix rows — acceptable for a research deliverable.

### Verdict
Confidence: 0.98 → PASS → docs

[[2026-04-08]] Wed 23:44
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | `type:research` — no code changes, no behavior or API change |
| 2 | Module docstrings | No | N/A | No Python modules created or modified |
| 3 | External attribution | Yes | Verified | `.owlbear/sources/overview.md` §"Web Search MCP Options (Task #681)" already present — 4 sources (ddgs, Brave Search MCP, Tavily MCP, MCP servers registry) attributed with URLs, license, and research doc link |
| 4 | CLI changes | No | N/A | No CLI changes |
| 5 | Research doc | Yes | Verified | `.owlbear/research/web-search-mcp-options.md` exists, linked from task body; follow-up #686 created at `research` status with `depends_on: [681]` |

### Files Updated
- None — all documentation already present and accurate

### Scratch Files Cleaned
- None — no `.owlbear/scratch/681-*` files found

[[2026-04-09]] Thu 00:58
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: Research doc in `.owlbear/research/` evaluating ≥3 options | `.owlbear/research/web-search-mcp-options.md` exists; §3.1 matrix covers 4 options (ddgs, Brave, Tavily, Custom) | PASS |
| AC2: Trade-off matrix (API key, free tier, rate limits, quality, MCP) | §3.1: 10-criterion comparison table covers all required dimensions | PASS |
| AC3: Recommendation with confidence score | §4: "Use ddgs built-in MCP server. Confidence: .85" | PASS |
| AC4: Follow-up task(s) if recommendation favorable | #686 at `research` status, `depends_on: [681]`, `source:research-681` tag | PASS |

### Research Task Verification (Step 1a)
- Research doc exists at `.owlbear/research/web-search-mcp-options.md` ✓
- Follow-up #686 created at `research` status ✓
- Follow-up references research doc in body ✓

### Test Results
- pytest: 3664 passed, 382 failed, 18 skipped — no failures in task scope (type:research, no code changes)
- ruff: 5 errors — none in task scope (all in mcp-kanban server.py and test_server.py)

### Architect Quality: 5/5
AC lines are specific, verifiable, and complete. All 4 deliverables map directly to observable artifacts. Conditional AC4 is well-structured.

### Deduction Breakdown
- No AC evidence gaps: 0
- No lint violations in scope: 0
- AC quality 5/5: 0
- Reviewer evidence present and detailed (.98 PASS): 0
- No full-suite failures in scope: 0
- Note: research doc was uncommitted by upstream — committed in audit Step 4

### Confidence: .99
### Action: archive

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| ccd3f31 | docs(research) | web-search-mcp-options.md, #681 task, #686 task | #681 |
