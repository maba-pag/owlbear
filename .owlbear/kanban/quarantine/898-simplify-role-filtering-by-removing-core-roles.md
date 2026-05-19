---
id: 898
title: Simplify role filtering by removing core.roles
status: archived
priority: someday
created: 2026-03-21T13:50:03.9551599+01:00
updated: 2026-03-21T13:50:03.9551599+01:00
tags:
    - audit
    - yagni
    - scope:core
    - refactor
    - type:build
depends_on:
    - 897
class: standard
---

YAGNI-03 follow-up from #565. Remove the dedicated role-policy module while preserving the current validator allow-list behavior and shipped agent role metadata.

## AC

- [ ] Delete src/owlbear/core/roles.py and remove owlbear.core.roles imports and _ROLE_POLICIES indirection from src/owlbear/core/agent_registry.py
- [ ] In AgentRegistry._build_agent(), apply the validator tool filter directly with AbstractToolset.filtered() before the single Agent() call; role: builder keeps raw toolsets unchanged
- [ ] Preserve current validator capabilities from the live codebase: the direct filter still allows the existing read-only validator tools (including run_command, kanban_create, kanban_edit, and kanban_move) and continues denying write_file and create_file
- [ ] Keep AgentDefinition.role and the role: frontmatter in src/owlbear/agents/*.md unchanged as string metadata; do not reintroduce AgentRole, RolePolicy, or apply_role_policy elsewhere
- [ ] Remove or replace obsolete owlbear.core.roles test imports and expectations in tests/test_roles.py, tests/test_agent_definitions.py, tests/test_pipeline_e2e.py, and tests/test_validator_role_assignment.py
- [ ] Scoped pytest passes for tests/test_agent_registry.py, tests/test_agent_definitions.py, tests/test_pipeline_e2e.py, and tests/test_validator_role_assignment.py
- [ ] uv run ruff check is clean for modified source and test files

Test task: #897
Files: src/owlbear/core/agent_registry.py, src/owlbear/core/roles.py, tests/test_agent_registry.py, tests/test_agent_definitions.py, tests/test_pipeline_e2e.py, tests/test_validator_role_assignment.py, tests/test_roles.py
Research: docs/research/role-system-complexity.md
Original task: #565
