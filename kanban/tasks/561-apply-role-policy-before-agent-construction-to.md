---
id: 561
title: Apply role policy before Agent construction to avoid double-build
status: ideation
priority: someday
created: 2026-03-04T07:39:04.0573106+01:00
updated: 2026-03-04T07:39:04.0573106+01:00
tags:
    - audit
    - code-quality
    - scope:core
class: standard
---

F-20: When role != BUILDER, code builds second Agent with filtered toolsets, discarding first. Apply apply_role_policy to toolsets before constructing Agent. AC: single Agent construction per role. See docs/code-quality-audit.md.
