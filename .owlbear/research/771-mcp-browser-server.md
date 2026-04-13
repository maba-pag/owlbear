# MCP Browser Server — Implementation Research

> **Owning task:** #771 — P1-18: Impl — MCP browser server + URL domain allowlist
> **Date:** 2026-04-11  **Status:** Complete

## 1. Context and Question

Task #771 is a GREEN phase task: make all P1-17 tests (#770) in `test_mcp_browser_775.py` pass. The tests cover 4 ACs: server lifespan + 6 tools registered (AC1), BROWSER_ALLOWED_DOMAINS configures allowlist (AC2), navigate raises ToolError for blocked domains (AC3), and BROWSER_TOOLS_EXCLUDE removes tools (AC4).

The skeleton implementation already exists in `serve/mcp-browser/src/owlbear_mcp_browser/server.py` with stub tool bodies. Key question: what gaps remain, and what implementation approach follows MCP server conventions?

## 2. Sources Studied

| # | Source | Location | Relevance |
|---|--------|----------|-----------|
| 1 | mcp-kanban reference server | `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` | .95 |
| 2 | mcp-knowledge server | `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` | .90 |
| 3 | mcp-memory server | `serve/mcp-memory/src/owlbear_mcp_memory/` | .85 |
| 4 | Architecture standards skill | `share/skills/r-architecture-standards/SKILL.md` | .95 |
| 5 | FastMCP tools documentation | gofastmcp.com/servers/tools | .85 |
| 6 | Existing tests (#770) | `tests/test_mcp_browser_775.py` | .95 |
| 7 | Current mcp-browser skeleton | `serve/mcp-browser/src/owlbear_mcp_browser/server.py` | 1.0 |
| 8 | Browser research #264 | `.owlbear/research/browser-automation.md` | .70 |
| 9 | Phase 1 research #775 | `.owlbear/research/775-phase1-browser-pipeline-schema.md` | .80 |
| 10 | Playwright v2 research #684 | `.owlbear/research/playwright-browser-integration-v2.md` | .75 |

## 3. Analysis

### 3a. Current State vs Test Requirements

| AC | Test Count | Current Stub Status | Gap |
|----|-----------|-------------------|-----|
| AC1: lifespan + 6 tools | 3 | app_lifespan exists, 6 tools registered | **PASS** — no gap |
| AC2: BROWSER_ALLOWED_DOMAINS | 5 | Lifespan reads env, creates DomainAllowlist | **PASS** — no gap |
| AC3: navigate ToolError | 5 | navigate reads env, raises ToolError | **PASS** — no gap |
| AC4: BROWSER_TOOLS_EXCLUDE | 9 | _apply_tool_exclusions reads env, calls remove_tool | **PASS** — no gap |

**Finding F1:** The skeleton implementation should already pass all 22 tests. The builder's primary work is convention compliance (annotations, `__main__.py`, `__all__`).

### 3b. Convention Compliance Gaps

| Convention | Required By | Current State | Action |
|------------|------------|---------------|--------|
| ToolAnnotations (3 fields) | r-architecture-standards | Missing on all 6 tools | **ADD** |
| `__main__.py` entry point | All 3 reference MCP servers | Missing | **ADD** |
| `ctx: Context` parameter | All 3 reference servers (S1-S3) | Missing on all tools | **DEFER** (F2) |
| `__all__` exports | r-architecture-standards | `["mcp_app"]` only | **EXPAND** |
| Server name consistency | Reference pattern | `_mcp` (underscore prefix) | OK — matches kanban's `mcp` module-level pattern |

### 3c. Context Parameter Tension (F2)

| Approach | Tests Pass? | Convention-Compliant? | Confidence |
|----------|------------|----------------------|------------|
| A: No ctx (current) | Yes | No — tools can't access AppContext | .80 |
| B: Add ctx: Context | No — tests call navigate(url=...) without ctx | Yes | .40 |
| C: Add ctx with default=None | Maybe — depends on FastMCP signature handling | Partial | .50 |

Tests in `test_mcp_browser_775.py` call `navigate(url=...)` directly (no ctx). Adding `ctx: Context` as a required parameter breaks all AC3 tests. This is a test-design choice: mock-free testing at the cost of pattern compliance.

**Recommendation:** Keep Option A for GREEN phase. The tests were written before convention formalization. Refactoring to ctx-based access should be a follow-up task paired with test updates.

### 3d. ToolAnnotation Assignments

| Tool | readOnlyHint | idempotentHint | destructiveHint | Rationale |
|------|-------------|---------------|----------------|-----------|
| navigate | False | True | False | Changes page state, but repeating same URL = same result |
| click | False | False | False | Mutates page state, not idempotent (click toggles, submits) |
| type | False | False | False | Mutates input field, appends vs overwrites depends on impl |
| select | False | True | False | Mutates select element, same value = same result |
| read_text | True | True | False | Read-only extraction |
| snapshot | True | True | False | Read-only a11y tree |

Sources: r-architecture-standards (S4), FastMCP docs (S5), mcp-kanban annotations (S1).

### 3e. Allowlist Enforcement Pattern (F3)

| Approach | Correctness | Performance | Pattern-Compliant |
|----------|------------|-------------|-------------------|
| A: Per-call env read (current) | Correct | New DomainAllowlist per call | No — bypasses AppContext |
| B: AppContext via lifespan_context | Correct | Single DomainAllowlist shared | Yes — follows kanban/knowledge |

Current approach creates a new `DomainAllowlist` on every `navigate()` call. All 3 reference servers use `ctx.request_context.lifespan_context` for shared state. However, changing to B requires adding `ctx: Context` (see F2 tension). Current approach is functional and test-compatible.

### 3f. Non-Navigate Tool Bodies

Tests only verify tool registration (AC1) and navigate behavior (AC3). Tools `click`, `type`, `select`, `read_text`, `snapshot` have no behavioral tests. Current stub returns (selector echo, empty string) are sufficient for this GREEN phase. Full browser interaction requires a Playwright Page object in AppContext — a Phase 2 concern.

## 4. Recommendation (confidence: .85)

**Proceed with minimal GREEN implementation.** The skeleton already passes behavioral tests. Add convention-required items:

1. **Add ToolAnnotations** to all 6 tools per §3d table
2. **Add `__main__.py`** — `from .server import _mcp; _mcp.run()` (note: `_mcp` not `mcp`)
3. **Expand `__all__`** — add `app_lifespan`, `AppContext`, tool names
4. **Keep current allowlist pattern** — per-call env read matches test expectations
5. **Keep stub tool bodies** — no behavioral tests for non-navigate tools

**Do NOT** add `ctx: Context` to tool signatures (breaks tests). **Do NOT** implement full browser interaction (deferred to Phase 2).

Challenge: FALLBACK — no controversial recommendation to challenge. Implementation approach is dictated by existing test expectations and established conventions.

**Tier: T1 — Autonomous.** GREEN phase implementation within approved architecture. No new capabilities or architectural changes.

## 5. Follow-up Tasks

1. Refactor navigate + tools to use `ctx: Context` + AppContext (requires test updates)
2. Implement browser session management in AppContext (CDPConnectionManager, Page lifecycle)
3. Implement full tool bodies (navigate with Playwright, click/type/select with Page, read_text with extractor, snapshot with a11y tree)
