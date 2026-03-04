---
id: 529
title: Extract _entity_from_row and _edge_from_row helpers in graph.py
status: ideation
priority: nice-to-have
created: 2026-03-04T07:38:35.4144425+01:00
updated: 2026-03-04T07:38:35.4144425+01:00
tags:
    - audit
    - dry
    - knowledge
class: standard
---

F-09: Entity and Edge row-to-model deserialization via tuple indexing repeated in 5+ methods. Extract _entity_from_row(row) and _edge_from_row(row) helpers. AC: single deserialization point, all methods use it. See docs/code-quality-audit.md.
