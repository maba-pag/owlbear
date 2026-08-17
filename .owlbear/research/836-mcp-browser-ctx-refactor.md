# Refactor mcp-browser tools to ctx: Context + AppContext

> **Owning task:** #836 — Refactor mcp-browser tools to use ctx: Context + AppContext pattern
> **Date:** 2026-04-12  **Status:** Complete

## 1. Context and Question

Task #836 is a follow-up from research doc 771-mcp-browser-server.md §3c (F2 tension). The mcp-browser server has `AppContext` and `app_lifespan` already wired, but its 6 tools omit the `ctx: Context` parameter. `navigate()` re-reads `BROWSER_ALLOWED_DOMAINS` and creates a new `DomainAllowlist` per call instead of using the one created in `app_lifespan`. All 3 other MCP servers (kanban, knowledge, memory) use the `ctx: Context` → `ctx.request_context.lifespan_context` pattern.

Question: What is the implementation approach for adding `ctx: Context` to all 6 tools and updating tests to match?

## 2. Sources Studied

| # | Source | Location | Relevance |
|---|--------|----------|-----------|
| 1 | mcp-browser server.py | `serve/mcp-browser/src/owlbear_mcp_browser/server.py` | 1.0 |
| 2 | mcp-kanban server.py (reference) | `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` | .95 |
| 3 | mcp-knowledge server.py (reference) | `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` | .90 |
| 4 | mcp-memory tools.py (reference) | `serve/mcp-memory/src/owlbear_mcp_memory/tools.py` | .85 |
| 5 | Existing tests | `tests/test_mcp_browser_775.py` | 1.0 |
| 6 | Kanban test ctx mocking pattern | `tests/test_mcp_kanban_create_task_475.py` L68-75 | .90 |
| 7 | FastMCP dependency injection docs | `gofastmcp.com/servers/dependency-injection` | .85 |
| 8 | Prior research doc | `.owlbear/research/771-mcp-browser-server.md` §3c | .95 |

## 3. Analysis

### 3a. Server-Side Changes (trivial)

| Change | File | LOC | Risk |
|--------|------|-----|------|
| Add `Context` to import | server.py L13 | 1 | None |
| Add `ctx: Context` to all 6 tool signatures | server.py | 6 | None — FastMCP auto-injects, excluded from schema |
| Replace env read in navigate() with `ctx.request_context.lifespan_context.allowlist` | server.py L71-74 | -4/+2 | None — allowlist already built in app_lifespan |
| Other 5 tools: add param, no body change | server.py | 5 | None — unused param now, ready for Phase 2 |

### 3b. Test Impact

| Test Class | Test Count | Impact | Action |
|------------|-----------|--------|--------|
| TestFromAC_MCPServerLifespan (AC1) | 3 | None — tests registration, not invocation | No change |
| TestFromAC_DomainAllowlistEnvVar (AC2) | 5 | None — tests app_lifespan directly | No change |
| TestFromAC_NavigateToolError (AC3) | 5 | **Breaks** — calls `navigate(url=...)` without ctx | Add mock ctx with allowlist |
| TestFromAC_ApplyToolExclusions (AC4) | 9 | None — tests _apply_tool_exclusions, not tools | No change |

Only 5 of 22 tests need updating. The established mock pattern from kanban tests:

```python
def _make_app_ctx(domains: list[str]) -> AppContext:
    return AppContext(allowlist=DomainAllowlist(domains=domains))


def _make_mcp_ctx(app_ctx: AppContext) -> MagicMock:
    ctx = MagicMock()
    ctx.request_context.lifespan_context = app_ctx
    return ctx
```

### 3c. Pattern Comparison

| Criterion | Current (per-call env read) | Target (ctx + lifespan) |
|-----------|-----------------------------|-------------------------|
| Convention-compliant | No | Yes — matches kanban/knowledge/memory |
| Performance | New DomainAllowlist per navigate() call | Single instance shared for session |
| Testability | Must patch os.environ | Mock ctx with test allowlist |
| Phase 2 readiness | Tools can't access AppContext | Tools ready for browser Page/session |

## 4. Recommendation (confidence: .90)

Straightforward refactor. The `AppContext` and `app_lifespan` infrastructure already exists. Adding `ctx: Context` follows the exact pattern used by 3 other MCP servers in this workspace. Only 5 of 22 tests need updating, and the mock pattern is well-established.

**Implementation is two tasks:** RED (update tests first) + GREEN (update server code).

Challenge: FALLBACK — no controversial recommendation. Pattern is dictated by established convention. Single viable approach.

**Tier: T1 — Autonomous.** Internal refactor to match existing convention. No new capability, no architecture change, no user-facing behavior change.

## 5. Follow-up Tasks

1. RED: Write/update tests expecting `navigate(ctx, url=...)` signature
2. GREEN: Add `ctx: Context` to all 6 tools, replace env read in navigate()
