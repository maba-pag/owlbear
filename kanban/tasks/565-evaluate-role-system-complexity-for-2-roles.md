---
id: 565
title: Evaluate role system complexity for 2 roles
status: backlog
priority: someday
created: 2026-03-04T07:39:07.9665052+01:00
updated: 2026-03-07T04:28:05.1725947+01:00
started: 2026-03-07T04:28:05.1725947+01:00
tags:
    - audit
    - yagni
    - scope:core
class: standard
---

YAGNI-03: Full infrastructure (AgentRole enum, RolePolicy, apply_role_policy, 2 policies) to express: validators cant use write_file and create_file. 277 LOC for a 2-element frozenset. Research complete: recommend SIMPLIFY (.80 confidence). Replace with inline toolset.filtered() per PydanticAI idiom. See docs/role-system-complexity-research.md. AC: decision documented.
