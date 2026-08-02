---
id: 96
title: 'Test: Port agents to agent-md v2 location'
status: archived
priority: medium
created: 2026-03-28 03:42:21.979229+01:00
updated: 2026-03-29 15:16:08.481771+02:00
started: 2026-03-29 15:16:08.184776+02:00
completed: 2026-03-29 15:16:08.184776+02:00
tags:
- phase-1
- scope:agents
- type:test
- test
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Write file-content assertion tests for the agent port (task #8).

## Acceptance Criteria
- [ ] Test all 11 .agent.md files exist in agents/ directory (architect, auditor, builder, curator, kanban-planner, orchestrator, planner, researcher, reviewer, test-writer, writer)
- [ ] Test each of the 11 agent files contains todos (not todo) in tools: list
- [ ] Test curator.agent.md does NOT contain resolveMemoryFileUri in tools: list
- [ ] Test researcher.agent.md contains microsoft/markitdown/* in tools: list
- [ ] Test orchestrator.agent.md agents: field includes Explore
- [ ] Test researcher.agent.md agents: field is [Explore]
- [ ] Test 9 leaf agents have agents: [] (empty list)
- [ ] Test .github/agents/ contains no .agent.md files (v1 cleanup complete)
- [ ] All tests FAIL in RED phase
- [ ] ruff clean

[[2026-03-29]] Sun 13:06
## Test-Writer Notes
- Test file: tests/test_agent_port_v2.py
- Classes: TestFromAC_AgentFilesExist, TestFromAC_AgentToolsTodos, TestFromAC_CuratorNoResolveMemoryFileUri, TestFromAC_ResearcherMarkitdown, TestFromAC_OrchestratorAgentsExplore, TestFromAC_ResearcherAgentsExploreOnly, TestFromAC_LeafAgentsEmptyList, TestFromAC_V1Cleanup
- Tests per category: happy 30, edge 3, error 2, boundary 6
- Total: 41 tests
- ruff: clean
- NOTE: Test file pre-existed from prior work cycle; all tests PASS (not FAIL) because task #8 (agent port) was completed before this RED phase. Implementation and tests are already aligned.
- AC coverage: all 8 implementation AC lines covered; AC line 9 (all tests FAIL) not achievable post-implementation.

[[2026-03-29]] Sun 13:07
## Test-Writer Notes
- Test file: tests/test_agent_port_v2.py
- Classes: TestFromAC_AgentFilesExist, TestFromAC_AgentToolsTodos, TestFromAC_CuratorNoResolveMemoryFileUri, TestFromAC_ResearcherMarkitdown, TestFromAC_OrchestratorAgentsExplore, TestFromAC_ResearcherAgentsExploreOnly, TestFromAC_LeafAgentsEmptyList, TestFromAC_V1Cleanup
- Tests per category: happy 30, edge 3, error 2, boundary 6
- Total: 41 tests
- ruff: clean
- NOTE: Test file pre-existed from prior work cycle; all tests PASS (not FAIL) because task #8 (agent port) was completed before this RED phase. Implementation and tests are already aligned.
- AC coverage: all 8 implementation AC lines covered; AC line 9 (all tests FAIL) not achievable post-implementation.

[[2026-03-29]] Sun 15:15
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| 11 agent files exist in agents/ | Get-ChildItem: 11 files; 11 tests pass | PASS |
| Each file contains todos (not todo) | 11 tests pass (TestFromAC_AgentToolsTodos) | PASS |
| curator no resolveMemoryFileUri | 2 tests pass | PASS |
| researcher has markitdown tool | 2 tests pass | PASS |
| orchestrator agents includes Explore | 2 tests pass | PASS |
| researcher agents is [Explore] | 3 tests pass | PASS |
| 9 leaf agents have agents: [] | 9 tests pass | PASS |
| .github/agents/ no agent.md files | Count=0; 1 test passes | PASS |
| All tests FAIL in RED | N/A - implementation preceded RED phase | N/A |
| ruff clean | All checks passed | PASS |

### Test Results
- pytest (task-specific): 41 passed in 0.10s
- pytest (full suite): 569 passed, 81 failed (pre-existing: stale test_rename_todo_to_todos.py + unrelated)
- ruff: All checks passed

### AC Quality: 4/5
AC was specific with concrete file names, tool names, and counts. Minor gap: AC9 (all tests FAIL) was unachievable given task ordering.

### Confidence: .97
### Action: archive

### Commits (upstream)
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| ec84b55 | feat | tests/test_agent_port_v2.py + agents/*.agent.md | #96 |

[[2026-03-29]] Sun 15:16
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| 11 agent files exist in agents/ | Get-ChildItem: 11 files; 11 tests pass | PASS |
| Each file contains todos (not todo) | 11 tests pass (TestFromAC_AgentToolsTodos) | PASS |
| curator no resolveMemoryFileUri | 2 tests pass | PASS |
| researcher has markitdown tool | 2 tests pass | PASS |
| orchestrator agents includes Explore | 2 tests pass | PASS |
| researcher agents is [Explore] | 3 tests pass | PASS |
| 9 leaf agents have agents: [] | 9 tests pass | PASS |
| .github/agents/ no agent.md files | Count=0; 1 test passes | PASS |
| All tests FAIL in RED | N/A - implementation preceded RED phase | N/A |
| ruff clean | All checks passed | PASS |

### Test Results
- pytest (task-specific): 41 passed in 0.10s
- pytest (full suite): 569 passed, 81 failed (pre-existing: stale test_rename_todo_to_todos.py + unrelated)
- ruff: All checks passed

### AC Quality: 4/5
AC was specific with concrete file names, tool names, and counts. Minor gap: AC9 (all tests FAIL) was unachievable given task ordering.

### Confidence: .97
### Action: archive

### Commits (upstream)
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| ec84b55 | feat | tests/test_agent_port_v2.py + agents/*.agent.md | #96 |
