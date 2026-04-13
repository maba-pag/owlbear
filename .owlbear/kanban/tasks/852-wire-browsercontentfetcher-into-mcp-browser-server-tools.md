---
id: 852
title: Wire BrowserContentFetcher into MCP browser server tools
status: todo
priority: important
created: '2026-04-12T14:03:06.606752+00:00'
updated: '2026-04-12T15:48:07.764729+00:00'
tags:
- phase-1
- scope:browser
- type:feature
parent: 751
depends_on:
- 842
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Context

The MCP browser server (`serve/mcp-browser/src/owlbear_mcp_browser/server.py`) has 6 stub tool definitions (navigate, click, type, select, read_text, snapshot). None delegate to actual browser code. Once #842 delivers `BrowserContentFetcher`, the MCP tools need to use it.

Extracted from #838 AC3 — the SSO redirect detection (AC1/AC2/AC4 of #838) is covered by #830/#842.

See `.owlbear/research/838-wire-check-sso-redirect.md` for analysis.

## Acceptance Criteria

1. `AppContext` in `server.py` holds a `BrowserContentFetcher` instance, initialized in `app_lifespan()`.
2. `navigate(url)` tool calls `fetcher.fetch(url)` and stores the result. Returns the fetched markdown content.
3. If `AuthenticationRequired` is raised during `navigate()`, it is caught and converted to a `ToolError` with a descriptive message (e.g. "SSO session expired").
4. `read_text()` returns the content from the most recent `navigate()` call (or empty string if none).
5. Integration test: stub BrowserContentFetcher, call navigate via MCP tool, verify delegation and error handling for both success and AuthenticationRequired cases.

## Notes

- Depends on #842 (BrowserContentFetcher implementation).
- `ToolError` is already imported in server.py (used for domain allowlist violations).
- Consider whether `BrowserContentFetcher` should be created in lifespan or lazily on first navigate call (CDPConnectionManager may not be connected at startup).
[[2026-04-12]]
## Research
- Research doc: .owlbear/research/852-wire-browserfetcher-mcp-tools.md
- Sources: 11 studied, 7 high-relevance (≥.85)
- Recommendation: Eager creation with Optional fallback — `AppContext.fetcher: BrowserContentFetcher | None`, `AppContext.last_content: str`. Lifespan creates+connects CDPConnectionManager, builds fetcher. navigate() delegates to fetcher.fetch(), catches AuthenticationRequired → ToolError. read_text() returns last_content. (confidence: .85)
- Follow-up tasks created: #856 (RED: tests for fetcher wiring), #857 (GREEN: implement wiring)
- Decision requests: none
- Tier: T1 — autonomous wiring of approved components

## Challenge Results
- Challenger: FALLBACK — no challenger agent available
- Confidence in original: .85
- Key challenges (self): "Should MCP server own CDPConnectionManager lifecycle?" — Yes, lifespan is the standard ownership point (mcp-knowledge precedent).
- Researcher response: accepted — no alternative owner in current architecture

## Critical Finding
**Dependency correction needed:** #852 depends_on must include #850 (ctx: Context refactor). Without ctx in tool signatures, tools cannot access AppContext.fetcher. Both follow-up tasks (#856, #857) include correct dependency chains.
[[2026-04-12]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: wire BrowserContentFetcher into MCP browser navigate/read_text tools |
| Interface clarity | PASS | AC1-4 specify exact AppContext fields, delegation flow, exception mapping, and state semantics. Children #856/#857 refine with Optional typing and None-guard details |
| Dependency correctness | PASS (with correction) | #842 declared, **#850 missing** — tools need ctx: Context to access AppContext.fetcher. See DEPENDS_ON-CORRECTION below |
| Module layering | PASS | owlbear_mcp_browser imports from owlbear_browser (already declared workspace dep in pyproject.toml). No upward imports |
| TDD compliance | PASS | #856 (RED) precedes #857 (GREEN), both children of #852. Dependency chains correctly ordered |
| KISS/YAGNI | PASS | Minimal scope — wiring only, no new abstractions. Optional fallback for fetcher matches mcp-knowledge pattern |
| Premise challenge | PASS | Tools are stubs returning raw strings/empty. Wiring is necessary for any browser functionality |
| Pattern consistency | PASS | Follows established MCP server patterns: ctx: Context first param, lifespan_context access, PermissionError→ToolError catch (server.py L73-76), AppContext dataclass |
| Security surface | PASS | No new boundaries. DomainAllowlist check preserved before fetch. AuthenticationRequired surfaced as ToolError (no credential leakage) |
| Single domain | PASS | scope:mcp-browser only |

### Failure Mode Map

| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|-------------|-----------|----------|-------------|
| navigate() → fetcher.fetch(url) | SSO redirect detected | AuthenticationRequired | Yes → ToolError | "SSO session expired" message |
| navigate() → fetcher is None | Browser not initialized at startup | N/A | Yes → ToolError (per #857 AC5) | "Browser not available" message |
| app_lifespan() → CDPConnectionManager | Edge not running / CDP fails | Exception | Yes → fetcher stays None | Graceful degradation, navigate returns ToolError |

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| AC1: AppContext holds BrowserContentFetcher, initialized in app_lifespan() | Verifiable. Children refine to `BrowserContentFetcher \| None = None` + `last_content: str = ""` (#857 AC1) | None — parent-level AC is acceptable; children carry precise type spec |
| AC2: navigate(url) calls fetcher.fetch(url), stores result, returns markdown | Verifiable. Delegation, state update, return value all testable | None |
| AC3: AuthenticationRequired → ToolError | Verifiable. Exact exception types named. Follows existing PermissionError→ToolError pattern at server.py L73-76 | None |
| AC4: read_text() returns most recent navigate content | Verifiable. State stored in AppContext.last_content (per #857 AC6) | None |
| AC5: Integration test for success + AuthenticationRequired | Verifiable. Covered by child #856 with 5 test cases (success, auth error, fetcher-None, read_text after navigate, read_text without navigate) | None — parent AC aligns with child scope |

### Challenge Results

- Challenger: FALLBACK — no challenger agent available in session
- Self-challenge: "Should parent #852 be approved when children already carry the detailed work?" — Yes. Parent tracks feature-level AC; children decompose into TDD pair. Standard parent/subtask pattern.
- Self-challenge: "Is AC precise enough without Optional typing in AC1?" — Yes. Children #856/#857 carry the refined typing. Parent AC captures intent without over-specifying.
- Confidence: .90

### DEPENDS_ON-CORRECTION

DEPENDS_ON-CORRECTION: task #852 should have depends_on [842, 850]. Without ctx: Context in tool signatures (#850), tools cannot access AppContext.fetcher. Research §3c confirms this. Children #856/#857 already include #850 in their depends_on chains.

### Codebase Evidence

- server.py L22-26: AppContext(allowlist: DomainAllowlist) — needs fetcher + last_content fields added
- server.py L56-61: app_lifespan() yields AppContext — CDPConnectionManager + BrowserContentFetcher creation goes here
- server.py L69-76: navigate() duplicates env read + allowlist — will be replaced by ctx.lifespan_context access (after #850)
- server.py L14: ToolError already imported
- fetcher.py: BrowserContentFetcher.__init__(cdp) stores ref, fetch(url) → str via CDP page
- _errors.py L14-15: AuthenticationRequired(Exception) defined
- mcp-browser pyproject.toml: owlbear-browser already declared as workspace dep

### Verdict: APPROVE
### Action Taken: Advanced to todo. DEPENDS_ON-CORRECTION flagged: #852 should have depends_on [842, 850] — orchestrator should correct before dispatch.