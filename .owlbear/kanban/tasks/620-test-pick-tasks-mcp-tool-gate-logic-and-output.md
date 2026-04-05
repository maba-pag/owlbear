---
id: 620
title: 'Test: pick_tasks MCP tool gate logic and output format'
status: backlog
priority: needed
created: 2026-04-05T01:30:52.3984607+02:00
updated: 2026-04-05T10:33:45.378526+02:00
tags:
    - scope:mcp
    - phase-2
    - test
parent: 619
class: standard
---

## Acceptance Criteria

- Tests cover `pick_tasks` MCP tool in owlbear-kanban server
- Test cases validate:
  - Basic pick: tasks in various statuses returned with task_id and status
  - Gate filtering: tasks failing atomicity/TDD/clarity gates are excluded
  - Limit: `limit=5` caps output at 5 entries
  - Default limit is 25
  - Sort order: critical+done-adjacent tasks appear before someday+ideation tasks
  - Empty board: returns empty dispatch list
  - Archived tasks excluded
  - Blocked/claimed tasks excluded (unblocked + unclaimed board read)
- Tests use the existing test patterns for MCP kanban tools (mock _run_kanban or use subprocess fixtures)
- Tests live in tests/test_pick_tasks_{task_id}.py

[[2026-04-05]] Sun 10:33
## Research
- Research doc: .owlbear/research/pick-tasks-test-design.md
- Sources: 8 studied, 6 high-relevance
- Recommendation: Mock _run_kanban pattern with 7 test classes covering all AC items (confidence: .90)
- Follow-up tasks created: none (all subtasks exist under #619)
- Decision requests: none

## Challenge Results
- Challenger: N/A — trivial T1 test task, no recommendation to challenge
- Tier: T1 (autonomous) — standard TDD RED test writing

## Key Findings for Test-Writer
- Mock pattern: `patch("owlbear_mcp_kanban.server._run_kanban", AsyncMock(return_value=(json_str, "", 0)))`
- pick_tasks calls _run_kanban once with: list --json --unblocked --not-blocked --unclaimed
- Gate logic migrated from planner/gates.py: atomicity (word-boundary "and"), TDD (## Test-Writer Notes), clarity (bullet AC for active statuses)
- Sort: (PRIORITY_RANK, STATUS_RANK) ascending — critical+done first, someday+ideation last
- Output: {"dispatch": [{"task_id": int, "status": str}]}
- 7 test classes: Signature, BasicPick, GateFiltering, Limit, SortOrder, EdgeCases, BoardFlags
