---
id: 897
title: Test role-filter simplification without core.roles
status: archived
priority: someday
created: 2026-03-21T13:50:03.1361348+01:00
updated: 2026-03-21T15:08:28.4848658+01:00
tags:
    - audit
    - yagni
    - scope:core
    - test
    - type:test
blocked: true
block_reason: 'Interface conflict: TestFromAC_BuilderFilterBypass (test_agent_registry_no_core_roles_import) requires removing the owlbear.core.roles import from agent_registry.py, and TestFromAC_ValidatorDirectFiltering (test_validator_does_not_call_apply_role_policy) requires apply_role_policy NOT be called. But existing passing TestFromAC_AllValidatorsAllowList and TestFromAC_AuditorKanbanAccess in tests/test_validator_role_assignment.py both (a) require patch(''owlbear.core.agent_registry.apply_role_policy'') to resolve (needs the import) and (b) assert call_count >= 1 (apply_role_policy MUST be called). These two contracts are mutually exclusive. Builder cannot proceed without either violating the no-modify-TestFromAC rule or creating test regressions. The test-writer must supersede the #742 TestFromAC_AllValidatorsAllowList and TestFromAC_AuditorKanbanAccess classes with new TestFromAC_ classes that test the new direct-filtering behavior before this task can proceed.'
class: standard
---

YAGNI-03 follow-up from #565. The current code already uses a validator allow-list and live builder/validator role assignments. This RED task locks in direct-filtering behavior before the roles abstraction is removed.

## AC

- [ ] In tests/test_agent_registry.py, add failing tests proving _build_agent() builds role: validator agents without calling apply_role_policy or consulting _ROLE_POLICIES, by applying AbstractToolset.filtered() directly and passing the filtered toolsets into the single Agent() call
- [ ] In tests/test_agent_registry.py, add a guard test proving role: builder agents bypass direct filtering and still construct Agent() exactly once
- [ ] Update role-metadata assertions in tests/test_agent_definitions.py, tests/test_pipeline_e2e.py, and tests/test_validator_role_assignment.py to compare defn.role strings (builder / validator) instead of importing AgentRole
- [ ] The new validator-filtering RED test fails before implementation because AgentRegistry still depends on owlbear.core.roles
- [ ] uv run ruff check is clean for the modified test files

Files: tests/test_agent_registry.py, tests/test_agent_definitions.py, tests/test_pipeline_e2e.py, tests/test_validator_role_assignment.py
Research: docs/research/role-system-complexity.md
Original task: #565

[[2026-03-21]] Sat 14:26

## Test-Writer Notes

- Test file: tests/test_agent_registry.py (2 new classes appended)
- Classes: TestFromAC_ValidatorDirectFiltering, TestFromAC_BuilderFilterBypass
- Total: 5 new tests, all FAIL
- ruff: clean
