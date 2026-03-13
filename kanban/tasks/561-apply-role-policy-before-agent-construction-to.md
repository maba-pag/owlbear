---
id: 561
title: Apply role policy before Agent construction to avoid double-build
status: backlog
priority: someday
created: 2026-03-04T07:39:04.0573106+01:00
updated: 2026-03-07T04:23:48.8847296+01:00
started: 2026-03-07T02:20:43.1600761+01:00
tags:
    - audit
    - code-quality
    - scope:core
class: standard
---

F-20: Double Agent construction in _build_agent() when role != BUILDER. See docs/research/role-policy-before-agent-construction.md for analysis.

## AC

- [ ] _build_agent constructs exactly one Agent per call regardless of role
- [ ] apply_role_policy applied to toolsets before Agent()
- [ ] Existing tests pass
- [ ] New test asserts single Agent construction for validator role
