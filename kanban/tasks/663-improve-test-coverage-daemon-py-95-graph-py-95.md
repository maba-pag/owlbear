---
id: 663
title: 'Improve test coverage: daemon.py (95%) + graph.py (95%)'
status: done
priority: nice-to-have
created: 2026-03-08T01:59:46.1349218+01:00
updated: 2026-03-08T13:26:50.580357+01:00
started: 2026-03-08T05:24:18.1721271+01:00
completed: 2026-03-08T13:26:50.580357+01:00
tags:
    - coverage-sprint
    - scope:core
    - knowledge
    - test
class: standard
---

## Coverage Gap
daemon.py: 95% (12 of 255 stmts uncovered)  lines 82-87, 522, 561-576
graph.py: 95% (8 of 155 stmts uncovered)  lines 54, 320-335

## Acceptance Criteria
- [ ] Coverage >= 97% for src/owlbear/daemon.py
- [ ] Coverage >= 97% for src/owlbear/memory/knowledge/graph.py
- [ ] Tests cover daemon.py uncovered startup/shutdown paths
- [ ] Tests cover graph.py uncovered query/edge-case paths
- [ ] All new tests pass, ruff clean
