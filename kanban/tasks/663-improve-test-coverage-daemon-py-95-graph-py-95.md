---
id: 663
title: 'Improve test coverage: daemon.py (95%) + graph.py (95%)'
status: todo
priority: nice-to-have
created: 2026-03-08T01:59:46.1349218+01:00
updated: 2026-03-10T04:16:24.3522915+01:00
started: 2026-03-08T05:24:18.1721271+01:00
tags:
    - coverage-sprint
    - scope:core
    - knowledge
    - test
blocked: true
block_reason: 'daemon.py < 97%: _apply_hydration (lines 612-637, ~13 stmts) has zero tests. Add tests or revise AC (file grew 255 to 338 stmts via #703/#704/#711)'
class: standard
---

## Coverage Gap
daemon.py: 95% (12 of 255 stmts uncovered)  lines 82-87, 522, 561-576
graph.py: 95% (8 of 155 stmts uncovered)  lines 54, 320-335

## Acceptance Criteria
- [ ] Coverage >= 97% for src/owlbear/daemon.py
- [ ] Coverage >= 97% for src/owlbear/memory/knowledge/graph.py
- [ ] Tests cover daemon.py uncovered startup/shutdown paths
- [ ] Tests cover graph.py uncovered query/edge-case paths
- [ ] All new tests pass, ruff clean

[[2026-03-10]] Tue 01:11
## Audit
### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| Coverage >= 97% daemon.py | No new daemon tests from #663. Original gaps (L82-87, L522, L561-576) covered by #621/#665 commits. Cannot verify actual %. | UNVERIFIABLE |
| Coverage >= 97% graph.py | 13 new tests added in test_knowledge_graph.py covering merge_entities, get_neighbors, list_entities_for_document, _load_meta. | LIKELY PASS |
| Tests cover daemon.py paths | No new daemon tests written for #663. Improvements from other tasks. | FAIL |
| Tests cover graph.py paths | TestMergeEntities(3), TestGetNeighbors(5), TestListEntitiesForDocument(4), test_load_meta(1) | PASS |
| All new tests pass, ruff clean | 1337 passed/0 failed. Ruff clean for #663 files. | PASS |

### Test Results
- pytest: 1337 passed, 2 skipped, 0 failed
- ruff: 3 errors in unrelated files (screenshot.py, test_bootstrap_structure.py)

### Issues
- No builder/reviewer/writer notes on task body
- daemon.py coverage improvements came from #621 and #665, not #663
- Cannot verify coverage percentage (terminal interrupt corrupts .coverage data)

### Confidence: .85
### Action: reject to review

[[2026-03-10]] Tue 02:12
## Review Evidence

### Test Results
- graph tests: 79 passed, 0 failed (test_knowledge_graph.py + test_graph_store_neighbors.py)
- daemon tests: 70 passed, 0 failed (test_daemon.py  KeyboardInterrupt during teardown from signal tests, not a test failure)

### Lint Results
- ruff: All checks passed (daemon.py, graph.py, all test files)

### Coverage
- graph.py: 155 stmts, 0 miss, **100%** (from test_knowledge_graph.py + test_graph_store_neighbors.py alone)
- daemon.py: **~94% estimated**  combined coverage unmeasurable due to signal handler tests propagating SIGINT through subprocess and coverage tooling. Estimated by intersecting two partial runs (daemon-only: 63%, non-daemon: 65%). Intersection of uncovered lines: ~21 stmts (537-538, 571-584, 698, 700, 956, 958-959).

### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | graph: exact IDs, counts, metadata dicts. daemon: exact True/False, specific log messages |
| Negative/error paths | ADEQUATE | graph: nonexistent entity, empty scopes, unknown doc. daemon: dead PID, channel.send failure |
| Mutation reasoning | STRONG | Swapping merge redirect, removing BFS, etc. would break multiple tests |
| Independence | STRONG | Unique entity IDs per test, no shared state |
| Naming | STRONG | Descriptive: test_merge_redirects_edges, test_bidirectional_traversal, etc. |

### Security Review
No issues found. graph.py uses parameterized SQL. No secrets, injection, or path traversal.

### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| Coverage >= 97% daemon.py | Estimated ~94% (21 stmts uncovered). Signal handler tests prevent reliable combined measurement. | **FAIL** |
| Coverage >= 97% graph.py | 100% (155/155 stmts) verified independently | PASS |
| Tests cover daemon.py startup/shutdown paths | TestIsProcessAlive(2 tests) covers _is_process_alive (lines 82-87). TestTransientExhaustedChannelSendFails(1) covers channel.send failure. Lines 537-538, 571-584 (retry/lint-gate paths in reconcile_tasks) still uncovered. | **PARTIAL** |
| Tests cover graph.py query/edge-case paths | TestMergeEntities(3), TestGetNeighbors(5), TestListEntitiesForDocument(4), _load_meta parametrized(1) = 13 tests. Lines 54, 320-335 all covered. | PASS |
| All new tests pass, ruff clean | 149 total pass, 0 fail, ruff clean | PASS |

### Rejection Details
| Gap | Required Fix |
|-----|-------------|
| daemon.py ~94% < 97% | Add tests for reconcile_tasks retry path (lines 537-538), lint gate retry path (lines 571-584), retry re-dispatch in poll_tick (lines 698, 700), and run_daemon finally block inflight cancellation (956, 958-959). |
| daemon.py partial coverage of original gaps | Lines 522, 561-576 identified in task body as uncovered need explicit tests. TestIsProcessAlive covers 82-87 only. |

### Verdict: FAIL
Confidence: .80

[[2026-03-10]] Tue 02:49
## Test-Writer Notes
- Test file: tests/test_daemon_coverage_gaps.py
- Classes: TestFromAC_ReconcileRetryExhaustedKanbanFailure, TestFromAC_PollTickRetryRedispatch, TestFromAC_RunDaemonInflightCancellation
- Tests per category: happy 5, edge 3, error 2, boundary 2
- Total: 12 tests, all PASS (coverage improvement task -- code exists, tests exercise uncovered paths)
- ruff: clean
- Note: graph.py already at 100% per prior review -- no new graph tests needed.
- AC coverage:
| AC Line | Test(s) | Category |
|---------|---------|----------|
| Coverage >= 97% daemon.py | All 12 tests target uncovered daemon.py lines | coverage |
| Coverage >= 97% graph.py | Already 100% per review -- no tests needed | n/a |
| daemon.py startup/shutdown paths | test_inflight_tasks_cancelled_on_exit, test_no_inflight_tasks_exits_cleanly | happy, edge |
| daemon.py uncovered paths | test_kanban_edit_failure_*, test_retries_exhausted_*, test_due_retry_* | happy, error, boundary |
| All new tests pass, ruff clean | 12 passed, 0 failed, ruff clean | verification |
