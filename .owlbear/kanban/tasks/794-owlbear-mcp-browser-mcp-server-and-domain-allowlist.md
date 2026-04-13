---
id: 794
title: owlbear_mcp_browser MCP server and domain allowlist
status: review
priority: important
created: '2026-04-10T12:31:51.889527+00:00'
updated: '2026-04-12T16:54:31.004720+00:00'
tags:
- phase-1
- scope:mcp-browser
parent: 775
depends_on:
- 790
- 788
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- `serve/mcp-browser/` package created: `pyproject.toml`, `src/owlbear_mcp_browser/__init__.py`, `server.py`
- 6 MCP tools registered: `navigate`, `click`, `type`, `select`, `read_text`, `snapshot` — each with `ToolAnnotations` (readOnlyHint, idempotentHint, destructiveHint)
- AppContext + lifespan pattern per architecture standards
- Domain allowlist enforcement: `BROWSER_ALLOWED_DOMAINS` comma-separated env var; requests to non-allowlisted domains rejected with `ToolError`
- `BROWSER_TOOLS_EXCLUDE` env var removes specified tools from registration
- `ALLOWED_IMPORTS` updated: `owlbear_mcp_browser: {"owlbear_browser"}`
- All #790 tests pass
- Files: `serve/mcp-browser/`, `tests/test_package_boundary.py`

## Context
- WS-C: Browser Packages
- Scope item 2 from #775

[[2026-04-12]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | MCP server package + domain allowlist = one cohesive domain (mcp-browser) |
| Interface clarity | PASS | 6 tools named, env vars specified, error type (ToolError) explicit, AppContext+lifespan via arch-standards reference |
| Dependency correctness | PASS-with-note | #790 (tests) = done ✓. #788 (owlbear_browser extractor) = review/blocked ✗ — valid design dependency but not yet satisfied. Task should wait in todo until #788 completes. No action needed; orchestrator enforces depends_on. |
| Module layering | PASS | `ALLOWED_IMPORTS["owlbear_mcp_browser"] = {"owlbear_browser"}` already in test_package_boundary.py. server.py currently imports only from own package (allowlist.py). No upward imports. |
| TDD compliance | PASS | #790 (done) provides 3 test files: `test_mcp_browser_775.py` (AC1–AC4, ~20 tests), `test_mcp_browser_server_771.py` (AC5–AC7), `test_mcp_browser_tool_annotations_770.py` (annotation contract) |
| KISS/YAGNI | PASS | Stub tools returning trivial values. Real CDP wiring deferred to later tasks. Minimal scope. |
| Premise challenge | PASS-with-note | Implementation already exists. `serve/mcp-browser/` has server.py (108 lines), allowlist.py (33 lines), pyproject.toml, __init__.py, __main__.py. Builder should verify all #790 tests pass and fast-track. |
| Pattern consistency | PASS-with-advisory | Lifespan, AppContext, _apply_tool_exclusions, ToolAnnotations all follow mcp-kanban/mcp-knowledge patterns. **Advisory:** navigate() reads BROWSER_ALLOWED_DOMAINS directly via os.environ per-call instead of using AppContext.allowlist from lifespan. Tests (#790) are written around this approach (call navigate() without ctx). Not blocking for stub phase — future tasks wiring real CDP will refactor to use AppContext. |
| Security surface | PASS | Domain allowlist enforces deny-by-default when BROWSER_ALLOWED_DOMAINS unset/empty. PermissionError → ToolError chain correct. No injection surface (tools return strings). No file I/O, no deserialization. |
| Single domain | PASS | mcp-browser domain only |

### Failure Mode Map

| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|-------------|-----------|----------|-------------|
| navigate URL check | Domain not in allowlist | ToolError | Yes | Tool error: "Domain not in allowlist: {hostname}" |
| _apply_tool_exclusions | Unknown tool name | Exception (caught, silenced) | Yes | Silently ignored per convention |
| app_lifespan | BROWSER_ALLOWED_DOMAINS unset | N/A | Yes | Empty allowlist = deny-by-default (all navigate calls rejected) |

### Challenge Results
- Challenger: FALLBACK — challenger agent not in available agent roster
- Self-challenge:
  1. Can builder implement without interpretation? YES — 3 test files with ~40+ tests define exact imports, signatures, and behaviors
  2. Architecture risk? LOW — pre-existing stub implementation, follows established MCP server patterns
  3. Missing deps? #788 not done but orchestrator enforces depends_on before dispatch
  4. Security gap? NO — domain allowlist with deny-by-default, ToolError on violation

### Builder Guidance
- Implementation pre-exists in `serve/mcp-browser/`. Verify all tests pass in:
  - `tests/test_mcp_browser_775.py` (AC1–AC4: lifespan, env-var allowlist, navigate ToolError, tool exclusions)
  - `tests/test_mcp_browser_server_771.py` (AC5–AC7: annotations, __main__, __all__)
  - `tests/test_mcp_browser_tool_annotations_770.py` (annotation contract per tool)
- Confirm all 6 tools have all 3 ToolAnnotation hints (readOnlyHint, idempotentHint, destructiveHint) per AC
- `test_package_boundary.py` ALLOWED_IMPORTS entry already in place

### Verdict: APPROVE
### Action Taken: Advanced to todo. #788 dependency not yet done (review/blocked) — orchestrator will hold dispatch until satisfied.
[[2026-04-12]]
## Test-Writer Notes
- Test file: tests/test_mcp_browser_794.py
- Classes: TestFromAC_ToolAnnotationsComplete
- Tests per category: happy 0, edge 0, error 0, boundary 6
- Total: 6 tests, all FAIL (confirmed via pytest)
- ruff: clean

### AC Coverage

| AC Item | Coverage |
|---------|----------|
| 6 tools with ToolAnnotations (readOnlyHint, idempotentHint, destructiveHint) — all 3 per tool | Tests check the 6 untested hint combinations from prior tasks (#770, #771) |
| navigate → readOnlyHint=False | test_navigate_read_only_hint_is_false — FAIL (None≠False) |
| click → idempotentHint=False | test_click_idempotent_hint_is_false — FAIL (None≠False) |
| type → idempotentHint=False | test_type_idempotent_hint_is_false — FAIL (None≠False) |
| select → readOnlyHint=False | test_select_read_only_hint_is_false — FAIL (None≠False) |
| read_text → destructiveHint=False | test_read_text_destructive_hint_is_false — FAIL (None≠False) |
| snapshot → destructiveHint=False | test_snapshot_destructive_hint_is_false — FAIL (None≠False) |

### Notes
- AC items for lifespan, allowlist, BROWSER_TOOLS_EXCLUDE, __main__, __all__, and package boundary are already fully covered by tests from prior tasks (#790: test_mcp_browser_775.py AC1-AC4; #771: test_mcp_browser_server_771.py AC5-AC7; #770: test_mcp_browser_tool_annotations_770.py).
- server.py leaves readOnlyHint/idempotentHint/destructiveHint as None on 6 tool-hint combinations. Builder must set all three hints explicitly on every tool.
- Commit: test: add failing tests for complete ToolAnnotations hints (#794, test-writer)
[[2026-04-12]]
## Builder Notes\n\n### Files Changed\n- `serve/mcp-browser/src/owlbear_mcp_browser/server.py` — added missing hints to 6 tool `ToolAnnotations`\n\n### Root Cause\nEach of the 6 tools had only 2 of the 3 required ToolAnnotation hints set. The missing hint for each was `None` instead of an explicit boolean:\n- `navigate`: missing `readOnlyHint=False`\n- `click`: missing `idempotentHint=False`\n- `type`: missing `idempotentHint=False`\n- `select`: missing `readOnlyHint=False`\n- `read_text`: missing `destructiveHint=False`\n- `snapshot`: missing `destructiveHint=False`\n\n### Fix\nAdded all three hints explicitly to each `ToolAnnotations(...)` call — 6 one-line annotation replacements, no logic changed.\n\n### Test Results\n- `test_mcp_browser_794.py`: 6/6 passed (was 0/6)\n- `test_mcp_browser_tool_annotations_770.py` + `test_mcp_browser_server_771.py` + `test_mcp_browser_775.py`: 53/53 passed (no regressions)\n\n### Lint\n- ruff: clean\n\n### Coverage\n- `serve/mcp-browser/src/owlbear_mcp_browser/server.py` — all annotation lines exercised by existing test suite