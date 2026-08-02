---
id: 104
title: 'Test: FastMCP server and lifespan wiring for mcp-knowledge'
status: archived
priority: medium
created: 2026-03-28 14:01:13.729874+01:00
updated: 2026-03-29 08:27:24.430974+02:00
started: 2026-03-29 08:27:20.250700+02:00
completed: 2026-03-29 08:27:20.250700+02:00
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
Write failing tests (TDD RED) for the FastMCP server wiring and lifespan in mcp-knowledge, before the builder implements #54.

## Acceptance Criteria
- [ ] packages/mcp-knowledge/tests/test_server.py exists
- [ ] Test: app_lifespan yields AppContext with non-None query_service (mock all owlbear_knowledge imports: init_db, GraphStore, QdrantVectorStore, BgeM3EmbeddingProvider, KnowledgeQueryService)
- [ ] Test: app_lifespan closes sqlite3 connection in finally block (verify mock conn.close() called)
- [ ] Test: app_lifespan reads OWLBEAR_KB_PATH env var for DB path (mock os.environ, verify init_db called with expected path)
- [ ] Test: search_knowledge is registered as a tool on the FastMCP instance (inspect mcp._tool_manager or list_tools())
- [ ] Test: __main__ module is importable (import owlbear_mcp_knowledge.__main__)
- [ ] All tests FAIL (RED phase -- server.py not yet implemented)
- [ ] Tests mock all owlbear_knowledge imports (no real DB, Qdrant, or embeddings needed)
- [ ] Tests use pytest + pytest-asyncio

## Context
Preceding test task for #54 server/lifespan layer. Complements #72 (tool function tests, done).
See docs/research/mcp-python-sdk.md for FastMCP lifespan pattern.
See docs/research/search-knowledge-tool-impl.md section 3.6 for testing strategy.

[[2026-03-29]] Sun 06:18
## Builder Notes
- Non-implementation task (TDD RED test deliverable) pass-through
- AC verification: packages/mcp-knowledge/tests/test_server.py exists with 7 TestFromAC tests
- All tests FAIL as required: ModuleNotFoundError for owlbear_mcp_knowledge.server (correct RED state)
- Test classes: TestFromAC_ServerLifespan (5 tests), TestFromAC_ServerWiring (2 tests)
- Lint: ruff clean on test_server.py
- Implementation (server.py) is task #54 responsibility

[[2026-03-29]] Sun 06:26
## Review Evidence
See docs/scratch/104-reviewer.md for full evidence.

[[2026-03-29]] Sun 06:41
## Test-Writer Notes (retry)
- Retry reason: reviewer FAIL — test_app_lifespan_closes_connection_on_exception had patch context exiting before app_lifespan was invoked
- Fix: moved _raise definition, try/except block, and mock_conn.close.assert_called_once() inside the with-patch block
- Preserved: 7 existing tests, all still FAIL (ModuleNotFoundError for owlbear_mcp_knowledge.server)
- ruff: clean
- commit: 1aa9df2

[[2026-03-29]] Sun 07:47
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | TDD RED test task; no behavior, API, or convention change |
| 2 | Docstrings | No | N/A | Only test file added (test_server.py); no production modules created or modified |
| 3 | docs/sources/overview.md | No | N/A | No new external patterns adopted; research docs referenced were prior existing work |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc linked | No | N/A | No research doc produced by this task |
| 6 | Scratch files | No | N/A | No docs/scratch/104-* files found to clean |

### Files Updated
- None

### Scratch Files Cleaned
- None (docs/scratch/104-reviewer.md already absent)

[[2026-03-29]] Sun 08:27
## Audit
### AC Verification
| AC | Evidence | Status |
|---|---|---|
| test_server.py exists | read_file confirmed 207 lines | PASS |
| app_lifespan yields AppContext with query_service | 2 tests verify ctx and mock_qs identity | PASS |
| app_lifespan closes conn in finally | 2 tests: clean exit + exception path | PASS |
| OWLBEAR_KB_PATH env var | test with custom path + default path | PASS |
| search_knowledge registered as tool | test inspects mcp tool manager | PASS |
| __main__ importable | test uses importlib.import_module | PASS |
| All tests FAIL (RED) | ModuleNotFoundError at collection | PASS |
| Mock all owlbear_knowledge imports | All patches target server module | PASS |
| pytest + pytest-asyncio | asyncio markers present | PASS |

### Test Results
- pytest (task-specific): collection error as expected (RED phase)
- pytest (full suite): 628 passed, 106 failed (all pre-existing from other tasks)
- ruff: All checks passed

### AC Quality Score: 4/5
AC was specific and coverage-complete. Each line mapped directly to a testable behavior.

### Confidence: .97
### Action: archive
