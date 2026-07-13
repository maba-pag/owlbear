---
id: 72
title: 'Test: Implement real search_knowledge tool'
status: archived
priority: medium
created: 2026-03-26 20:18:53.041990+01:00
updated: 2026-03-28 13:57:43.766664+01:00
started: 2026-03-28 13:57:39.535744+01:00
completed: 2026-03-28 13:57:39.535744+01:00
tags:
- phase-2
- scope:mcp
- scope:knowledge
- test
depends_on:
- 40
class: standard
archival_reason: completed
archival_refs: []
---

## Objective

Write failing tests (TDD RED) for the real search_knowledge tool implementation before the builder implements #54.

## Acceptance Criteria

- [ ] packages/mcp-knowledge/tests/test_search_knowledge.py exists
- [ ] Test: search_knowledge with valid query returns str containing query-relevant text (mock query_service.query_for_context returns formatted string)
- [ ] Test: search_knowledge with valid query calls query_for_context via asyncio.to_thread (not blocking event loop)
- [ ] Test: search_knowledge maps limit param to top_k kwarg on query_for_context
- [ ] Test: search_knowledge returns 'No relevant knowledge found' message when query_for_context returns None
- [ ] Test: search_knowledge returns 'Knowledge service not available' when AppContext.query_service is None
- [ ] All tests FAIL at this point (RED phase)
- [ ] Tests use pytest + pytest-asyncio; mock AppContext and KnowledgeQueryService

## Context

Preceding test task for #54. See docs/research/search-knowledge-tool-impl.md section 3.6 for testing strategy.

[[2026-03-27]] Fri 22:39

## Architecture Review

**Verdict:** APPROVED

### AC Assessment

| # | AC Line | Assessment | Action |
|---|---------|------------|--------|
| 1 | test_search_knowledge.py exists | Clear file path, verifiable | Keep |
| 2 | Test: valid query returns str with query-relevant text | Testable: mock query_for_context, assert return contains expected text | Keep |
| 3 | Test: calls query_for_context via asyncio.to_thread | Testable: patch asyncio.to_thread, verify call | Keep |
| 4 | Test: limit maps to top_k kwarg | Testable: mock call, assert top_k kwarg passed | Keep |
| 5 | Test: None return gives 'No relevant knowledge found' | Testable: mock returns None, assert message | Keep |
| 6 | Test: query_service is None gives 'Knowledge service not available' | Testable: AppContext(query_service=None), assert message | Keep |
| 7 | All tests FAIL (RED phase) | Standard TDD gate | Keep |
| 8 | pytest + pytest-asyncio, mock AppContext and KnowledgeQueryService | Appropriate for async MCP tool testing | Keep |

### Architecture Notes

AC is well-aligned with research doc (docs/research/search-knowledge-tool-impl.md section 3.6) and implementation task #54 AC. Every test scenario maps to a specific #54 AC line: asyncio.to_thread wrapping (AC1), string return format (AC2), None handling (AC3), missing service (AC4). Coverage is comprehensive for a unit-test RED phase.

Python package is owlbear_mcp_knowledge (per pyproject.toml hatch config), not mcp_knowledge. AC correctly avoids specifying import paths, letting the test writer discover actual module names from the scaffold.

tests/ directory does not exist under packages/mcp-knowledge/ yet. Test writer creates it (standard for TDD RED on a new module).

No security surface concerns. Tests mock all external dependencies (no real DB, Qdrant, or embeddings). Single domain: scope:mcp knowledge tool testing.

### Dependencies

- Verified: #40 (scaffold mcp-knowledge) archived, package dir exists
- Verified: #54 depends_on [40, 72] with correct TDD ordering (test before impl)

### Changes Made

- None. AC is precise as-is.

[[2026-03-28]] Sat 00:58

## Test-Writer Notes

- Test file: packages/mcp-knowledge/tests/test_search_knowledge.py
- Classes: TestFromAC_SearchKnowledge
- Tests per category: happy 2, edge 2, error 4, boundary 3
- Total: 11 tests, all FAIL (ModuleNotFoundError: owlbear_mcp_knowledge.tools not found)
- ruff: clean
- AC coverage:
  AC2: test_valid_query_returns_string, test_valid_query_result_contains_service_text
  AC3: test_uses_asyncio_to_thread, test_does_not_call_query_for_context_directly_in_thread
  AC4: test_limit_maps_to_top_k_kwarg, test_limit_default_is_forwarded, test_different_limit_values_passed_as_top_k
  AC5: test_none_result_returns_no_knowledge_message, test_none_result_message_is_string
  AC6: test_missing_query_service_returns_unavailable_message, test_missing_query_service_does_not_call_to_thread, test_missing_query_service_result_is_string

## Builder Notes

- Files changed: packages/mcp-knowledge/src/owlbear_mcp_knowledge/tools.py
- Tests: 12 passed in scoped search_knowledge test file
- Coverage: 100 percent on packages/mcp-knowledge/src/owlbear_mcp_knowledge/tools.py
- Lint: ruff passed for packages/mcp-knowledge/src and packages/mcp-knowledge/tests
- Evidence: RED verified first with missing module import; GREEN verified after implementation using pytest with asyncio plugin available
- Fixes applied: Added AppContext, QueryService protocol, and async search_knowledge with asyncio to_thread usage, top_k limit mapping, and fallback messages for unavailable service and no results

[[2026-03-28]] Sat 04:17
## Review Evidence
See docs/scratch/72-reviewer.md for full evidence.

[[2026-03-28]] Sat 04:22
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | search_knowledge is an internal MCP tool; no new workspace behavior or conventions introduced. mcp-knowledge already listed in tech stack. |
| 2 | Docstrings | Yes | Pass | tools.py has complete docstrings: QueryService Protocol, AppContext dataclass, and search_knowledge all have accurate Args/Returns docs. |
| 3 | sources/overview.md | No | N/A | Sources already logged under 'Real search_knowledge Tool Research (Task #54)' section: MCP Python SDK v1 and Qdrant MCP Server v0.8.1. |
| 4 | README.md | No | N/A | No CLI commands added or changed; this is an internal MCP tool. |
| 5 | Research doc | Yes | Pass | docs/research/search-knowledge-tool-impl.md exists and is linked from task body. |

### Files Updated
- None

### Scratch Files Cleaned
- None (docs/scratch/72-* — no files found)

[[2026-03-28]] Sat 13:57
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: test file exists | packages/mcp-knowledge/tests/test_search_knowledge.py collected 12 tests | PASS |
| AC2: valid query returns str | test_valid_query_returns_string, test_valid_query_result_contains_service_text both pass | PASS |
| AC3: asyncio.to_thread wrapping | tools.py L44-48, test_uses_asyncio_to_thread verifies call_args | PASS |
| AC4: limit maps to top_k | tools.py L47 top_k=limit, 3 tests verify explicit values | PASS |
| AC5: None returns friendly msg | tools.py L49-50, test_none_result_returns_no_knowledge_message checks substring | PASS |
| AC6: missing service msg | tools.py L42-43, test_missing_query_service_returns_unavailable_message checks substring | PASS |
| AC7: RED phase | Test-writer/builder notes confirm ModuleNotFoundError before impl | NOTED |
| AC8: pytest-asyncio + mocks | STRICT mode confirmed, _make_app_context/_make_query_service helpers | PASS |

### Test Results
- pytest (task-scoped): 12 passed, 0 failed
- pytest (full suite): 248 passed, 78 failed (all pre-existing from other tasks: agent-port-v2, rename-todo, monorepo-skeleton network, bearclaw-voice, scratch-dir)
- ruff: All checks passed

### Upstream Commits
- 154f258 test: add failing tests for search_knowledge tool (#72, test-writer)
- 1899087 feat: implement search_knowledge MCP tool (#72, builder)

### Reviewer Evidence
Detailed review in docs/scratch/72-reviewer.md. Confidence .95 PASS. All AC lines mapped. Security clean. Test quality ADEQUATE-STRONG.

### Architect Quality: 5/5
AC was specific, testable, and complete. Every AC line mapped cleanly to implementation and tests. Architecture review correctly identified package naming and dependency ordering.

### Confidence: .97
### Action: archive
