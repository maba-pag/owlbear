---
id: 614
title: Move skills-ref to optional dependency group
status: backlog
priority: needed
created: 2026-04-04T21:55:37.0586851+02:00
updated: 2026-04-04T21:55:37.0586851+02:00
tags:
    - scope:infra
    - type:build
    - phase-2
parent: 610
class: standard
---

## Summary

Move skills-ref from the main dev dependency group to a separate optional group so uv sync on main (which lacks .owlbear/scripts/skills_ref/) does not fail.

## Acceptance Criteria

- [ ] AC1: pyproject.toml has skills-ref in a separate dependency group (e.g., [dependency-groups] ci = ["skills-ref==0.1.1"])
- [ ] AC2: Dev workflow uses uv sync --group ci (or similar) to install skills-ref
- [ ] AC3: uv sync without --group ci succeeds on a clean clone of main (no skills_ref/ present)
- [ ] AC4: .owlbear/scripts/validate_skills.py still works on dev (skills-ref found)
- [ ] AC5: pre-commit hooks or CI scripts updated to install the ci group
