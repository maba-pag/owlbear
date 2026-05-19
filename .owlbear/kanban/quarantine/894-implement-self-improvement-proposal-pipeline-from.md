---
id: 894
title: Implement self-improvement proposal pipeline from observability metrics
status: archived
priority: someday
created: 2026-03-21T13:19:26.8073909+01:00
updated: 2026-03-26T14:59:51.9779723+01:00
tags:
    - phase-14
    - agent
    - analytics
    - type:build
    - scope:core
depends_on:
    - 893
class: standard
---

Split from #146. Owns GREEN implementation for proposal generation from observability data. Scope is limited to analytics-to-proposal evaluation; no scheduling and no file mutation.

AC:

- Add a typed proposal-generation service that reads existing observability aggregates from EventStore; no parallel analytics persistence is introduced.
- The service returns structured proposal objects with target agent name, change category (prompt/tools/skills), evidence summary, and suggested agent-definition change content.
- Empty or insufficient metrics return an empty result or neutral no-op summary instead of raising.
- The implementation never applies changes or prompts the user.
- Unit tests from #893 pass.

[[2026-03-26]] Thu 14:59

## Test-Writer Notes

- Test file: tests/test_894_improvement_proposals_impl.py
- Classes: TestFromAC_ChangeCategorySpec, TestFromAC_AgentDefinitionSuggestedChange
- Tests per category: happy 0, edge 2, error 5, boundary 0
- Total: 7 tests, all FAIL (AssertionError - current impl uses 'reliability'/'performance')
- ruff: clean
- AC coverage:
  AC1 (no second store): covered by #893 tests (48 pass)
  AC2 (change_category in prompt/tools/skills): TestFromAC_ChangeCategorySpec x5
  AC2 (agent-definition suggested_change): TestFromAC_AgentDefinitionSuggestedChange x2
  AC3 (empty/low-signal): covered by #893 tests
  AC4 (no side effects): covered by #893 tests
  AC5 (unit tests from #893 pass): 48 tests passing
