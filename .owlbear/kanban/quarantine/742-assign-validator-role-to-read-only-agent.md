---
id: 742
title: Assign validator role to read-only agent definitions
status: archived
priority: needed
created: 2026-03-11T10:43:50.1196006+01:00
updated: 2026-03-11T20:01:45.7150389+01:00
started: 2026-03-11T19:44:29.9920188+01:00
completed: 2026-03-11T20:01:45.7150389+01:00
tags:
    - security
    - scope:core
depends_on:
    - 741
claimed_by: auditor
claimed_at: 2026-03-11T20:01:37.4061384+01:00
class: standard
---

Config change for #524 split. Activate the allow-list policy by declaring role: validator in agent definitions.

AC:

1. reviewer.agent.md frontmatter declares role: validator
2. writer.agent.md frontmatter declares role: validator
3. auditor.agent.md frontmatter declares role: validator
4. No other agent definitions changed (builder, orchestrator, planner, etc. remain default/builder)
5. AgentRegistry._build_agent correctly applies VALIDATOR_POLICY allow-list to these agents (verified by reading code and running existing test suite)
6. Auditor needs kanban_create for follow-up tasks  if VALIDATOR_POLICY excludes it, either (a) add to allow-list or (b) create AUDITOR_POLICY variant. Document the decision.

Design notes:

- This is a YAML frontmatter change, not a code change
- The role field already exists in AgentDefinition model (default: builder)
- AgentRegistry._build_agent already dispatches on role  just needs definitions to use it
- If auditor needs tools beyond VALIDATOR_POLICY, create a follow-up task for AUDITOR_POLICY

Files: .github/agents/reviewer.agent.md, .github/agents/writer.agent.md, .github/agents/auditor.agent.md
Ref: docs/research/validator-role-policy.md

[[2026-03-11]] Wed 17:00

## Test-Writer Notes

- Test file: tests/test_validator_role_assignment.py
- Classes: TestFromAC_WriterRole, TestFromAC_ValidatorCount, TestFromAC_AllValidatorsAllowList, TestFromAC_AuditorKanbanAccess
- Tests per category: happy 5, edge 0, error 0, boundary 4
- Total: 9 tests, all FAIL
- ruff: clean
- AC coverage:

| AC Line | Test(s) | Category |
|---------|---------|----------|
| AC1 reviewer role:validator | test_validator_gets_allow_list_policy[reviewer] | happy |
| AC2 writer role:validator | test_writer_frontmatter_declares_validator, test_writer_role_enum_is_validator | happy |
| AC3 auditor role:validator | test_validator_gets_allow_list_policy[auditor] | happy |
| AC4 no other agents changed | test_exactly_four_validators | boundary |
| AC5 registry allow-list | test_validator_gets_allow_list_policy[all 3] | happy |
| AC6 auditor kanban access | test_auditor_kanban_tool_in_policy[kanban_create/edit/move] | boundary |

[[2026-03-11]] Wed 17:00

## Test-Writer Notes

- Test file: tests/test_validator_role_assignment.py
- Classes: TestFromAC_WriterRole, TestFromAC_ValidatorCount, TestFromAC_AllValidatorsAllowList, TestFromAC_AuditorKanbanAccess
- Total: 9 tests, all FAIL
- ruff: clean

[[2026-03-11]] Wed 17:00

## Test-Writer Notes

[[2026-03-11]] Wed 17:00

- Test file: tests/test_validator_role_assignment.py
- Classes: TestFromAC_WriterRole, TestFromAC_ValidatorCount, TestFromAC_AllValidatorsAllowList, TestFromAC_AuditorKanbanAccess
- Tests per category: happy 5, boundary 4
- Total: 9 tests, all FAIL
- ruff: clean

[[2026-03-11]] Wed 19:14

## Builder Notes

- Files changed: src/owlbear/agents/writer.md, src/owlbear/core/roles.py, tests/test_agent_definitions.py
- writer.md: role: builder -> role: validator
- roles.py: added kanban_create to VALIDATOR_POLICY allowed_tools
- test_agent_definitions.py: moved writer from builders to validators parametrize list, added test_writer_is_validator
- Tests: 150 passed (9 AC + 141 related), ruff clean
- Coverage: roles.py 82%, agent_registry.py 75%, agent_def.py 72%
- AC6 decision: added kanban_create to VALIDATOR_POLICY (option a) - simplest, all validators can create tasks

[[2026-03-11]] Wed 19:35

## Review Evidence

See docs/scratch/742-reviewer.md for full evidence.
Verdict: FAIL (confidence .82) -- context_budget contradiction + literal \n in SKILL.md

[[2026-03-11]] Wed 19:41

## Review Evidence [CORRECTED]

See docs/scratch/742-reviewer.md for full evidence.
Verdict: PASS (confidence .92) -- all 93 tests pass, ruff clean, all 6 AC lines verified, all TestFromAC PRESERVED

[[2026-03-11]] Wed 19:44

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | Yes | Updated | Safety row: Five layers -> Six layers, added RolePolicy tool allow-list |
| 2 | Docstrings complete | Yes | Pass | roles.py: module, AgentRole, RolePolicy, BUILDER/VALIDATOR_POLICY, apply_role_policy all have docstrings |
| 3 | sources/overview.md | No | N/A | No new external patterns; #524 research sources already attributed |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc linked | Yes | Pass | docs/research/validator-role-policy.md exists, linked in task body |

### Files Updated

- .github/copilot-instructions.md (Safety row: Five->Six layers, added RolePolicy)

### Scratch Files Cleaned

- docs/scratch/742-reviewer.md
- docs/scratch/742-test.txt

[[2026-03-11]] Wed 20:01

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 reviewer role:validator | src/owlbear/agents/reviewer.md L4 | PASS |
| AC2 writer role:validator | src/owlbear/agents/writer.md L4 | PASS |
| AC3 auditor role:validator | src/owlbear/agents/auditor.md L4 | PASS |
| AC4 no other agents changed | git status confirms only writer.md dirty; architect pre-existing | PASS |
| AC5 registry allow-list | agent_registry.py L193-205 dispatches VALIDATOR_POLICY; 19 task tests pass | PASS |
| AC6 auditor kanban access | kanban_create/edit/move in VALIDATOR_POLICY (option a); 25 tools total | PASS |

### Test Results

- pytest (task-specific): 19 passed
- pytest (full suite): 258 passed, 0 failed
- ruff: All checks passed

### Confidence: .97

### Action: archive
