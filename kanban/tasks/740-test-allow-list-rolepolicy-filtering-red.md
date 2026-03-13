---
id: 740
title: Test allow-list RolePolicy filtering (RED)
status: todo
priority: needed
created: 2026-03-11T10:43:08.8802354+01:00
updated: 2026-03-12T22:09:17.4958114+01:00
tags:
    - test
    - security
    - scope:core
class: standard
---

TDD RED phase for #524 split. See docs/validator-role-policy-research.md for context.

AC:
1. New tests in tests/test_roles.py cover RolePolicy.allowed_tools: frozenset[str] field
2. Test: apply_role_policy with non-empty allowed_tools only permits listed tools
3. Test: apply_role_policy with empty allowed_tools (default) permits all tools (backwards-compatible with builder)
4. Test: both allowed_tools and denied_tools set -> tool must be in allowed AND not in denied
5. Test: VALIDATOR_POLICY uses allow-list model, not 2-item deny-list
6. Test: tool not in allowed_tools is automatically rejected for validator (fail-safe default)
7. Test: AgentRegistry applies allow-list policy to agents with role=validator
8. Existing tests in test_roles.py updated to match new model where needed
9. All new tests FAIL (RED phase)
10. ruff check tests/test_roles.py clean

Files: tests/test_roles.py
Ref: docs/validator-role-policy-research.md
