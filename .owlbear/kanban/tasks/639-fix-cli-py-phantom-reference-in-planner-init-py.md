---
id: 639
title: Fix cli.py phantom reference in planner/__init__.py docstring
status: backlog
priority: nice-to-have
created: 2026-04-06T02:35:22.7621528+02:00
updated: 2026-04-06T02:35:22.7621528+02:00
tags:
    - scope:orchestrator
    - phase-2
    - type:fix
    - docs
parent: 619
class: standard
---

## Acceptance Criteria

- Remove "and cli.py" from the docstring in serve/orchestrator/src/owlbear/planner/__init__.py L5
- Docstring should reference only loop.py (the actual caller with planner imports)
- waves.py also imports from planner (models only) — include if warranted by docstring scope
- No other changes needed

## Context
Discovered during audit of #624. The docstring references cli.py as an in-process path caller, but cli.py has never existed in the repository. Fabricated evidence of "cli.py L15-16" propagated unverified through researcher, architect, builder, and reviewer stages.
