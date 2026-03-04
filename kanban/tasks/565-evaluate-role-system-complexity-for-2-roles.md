---
id: 565
title: Evaluate role system complexity for 2 roles
status: ideation
priority: someday
created: 2026-03-04T07:39:07.9665052+01:00
updated: 2026-03-04T07:39:07.9665052+01:00
tags:
    - audit
    - yagni
    - scope:core
class: standard
---

YAGNI-03: Full infrastructure (AgentRole enum, RolePolicy, apply_role_policy, 2 policies) to express: validators cant use write_file and create_file. 100 lines for a 2-element frozenset. Keep if more roles planned, otherwise simplify. AC: decision documented. See docs/software-design-audit.md.
