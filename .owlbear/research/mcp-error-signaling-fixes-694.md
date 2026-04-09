# Fix 3 MCP Tool Error Signaling Bugs

> **Owning task:** #694 — Fix 3 MCP tool error signaling bugs and tighten convention docs
> **Date:** 2026-04-09 **Status:** Complete

## 1. Context and Question

Task #680 audited all 28 MCP tools and identified 3 error-signaling bugs. This research validates the bugs, maps the full blast radius (code + tests + docs + runtime consumers), and confirms the fix approach.

## 2. Sources Studied

| # | Source | Path / URL | Relevance |
|---|--------|-----------|-----------|
| S1 | MCP Spec §6 (2025-11-25) | modelcontextprotocol.io/specification/2025-11-25/server/tools | 1.0 |
| S2 | Research doc #680 | `.owlbear/research/mcp-tool-error-signaling-680.md` | 1.0 |
| S3 | r-architecture-standards | `share/skills/r-architecture-standards/SKILL.md` | 1.0 |
| S4 | mcp-knowledge server.py | `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` | 1.0 |
| S5 | mcp-memory tools.py | `serve/mcp-memory/src/owlbear_mcp_memory/tools.py` | 1.0 |
| S6 | approve.py runtime consumer | `serve/mcp-memory/src/owlbear_mcp_memory/approve.py` | 0.9 |

## 3. Analysis

### 3a. Bug Verification (all 3 confirmed)

| Bug | File | Line | Current code | Fix |
|-----|------|------|-------------|-----|
| Double-prefix | server.py | ~237 | `raise ToolError("error: source store not available")` | Remove `"error: "` prefix |
| Double-prefix | server.py | ~305 | `raise ToolError("error: graph store not available")` | Remove `"error: "` prefix |
| Mixed pattern | tools.py | ~265 | `return "error: transition from..."` | Change to `raise ToolError(...)` |

### 3b. Test Blast Radius

| File | Tests affected | Change needed |
|------|---------------|---------------|
| `serve/mcp-knowledge/tests/test_null_safety_539.py` | 2 | Assert ToolError (not return value); no "error:" in msg |
| `tests/test_set_approval_state_569.py` | 8 (T4-T10, E2) | `pytest.raises(ToolError)` instead of `result.startswith("error:")` |
| `serve/mcp-memory/tests/test_server.py` | 3 | Same — 3 invalid-transition tests need ToolError assert |

**Total: 13 test assertions across 3 files.**

Note: `test_null_safety_539.py` tests for list_sources/get_stats currently expect error string RETURNS but the code already raises ToolError — these tests are likely already failing. The fix corrects both the production code (remove prefix) and the tests (assert ToolError).

### 3c. Runtime Consumer Impact

`approve.py` calls `set_approval_state` via MCP transport (`client.call_tool`). Its error check:
```python
if result.isError or text_r.startswith("error:"):
```
After change: ToolError → `result.isError = True` (caught by first condition). The `startswith("error:")` check becomes dead code for this path but does not break. **No approve.py code changes needed.**

### 3d. AC Gap: Missing Affected File

AC4 lists `test_null_safety_539.py` and `test_set_approval_state_569.py`, but `serve/mcp-memory/tests/test_server.py` also has 3 tests asserting `result.startswith("error:")` for invalid transitions. This file MUST be updated too.

### 3e. Convention Doc Changes

| Doc | Update needed |
|-----|--------------|
| r-architecture-standards SKILL.md | Add anti-pattern: "Never prefix ToolError messages with `error:` — redundant with `isError: true`" |
| h-mcp-memory SKILL.md | Change set_approval_state: "Raises ToolError for disallowed transitions" (not "returns error: string") |

## 4. Recommendation (.90 confidence)

Proceed with all 6 AC items as specified. This is a clean T1 bug fix with well-defined blast radius.

Key risks:
- **Low:** test_server.py not in AC's affected files list — builder must be told
- **Low:** test_null_safety_539.py tests may already be failing — fix addresses both issues

Challenge: FALLBACK — trivial bug fix with clear scope; challenger not necessary per w-research Step 3.5 ("skip for info-only or trivial research").

## 5. Follow-up Tasks

No additional follow-up tasks needed. Task #694 itself covers all required work. The only gap (missing test file) is noted in the research doc and will be included in the task body update.
