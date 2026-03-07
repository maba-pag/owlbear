---
id: 529
title: Extract _entity_from_row and _edge_from_row helpers in graph.py
status: backlog
priority: nice-to-have
created: 2026-03-04T07:38:35.4144425+01:00
updated: 2026-03-07T00:17:35.2841715+01:00
started: 2026-03-07T00:16:21.6929909+01:00
tags:
    - audit
    - dry
    - knowledge
class: standard
---

F-09: Entity and Edge row-to-model deserialization via tuple indexing repeated in 5 methods. Extract _entity_from_row(row) and _edge_from_row(row) helpers. AC: single deserialization point, all methods use it. See docs/code-quality-audit.md.

## Research (checklist items 1-3): N/A - trivial DRY extraction

### Findings

**Entity deserialization** (3 sites, identical 8-field tuple unpacking):
- get_entity (L92)
- list_entities (L136)
- list_entities_for_document (L173)

All use: Entity(id=row[0], name=row[1], entity_type=row[2], description=row[3], metadata=_load_meta(row[4]), scope=row[5], document_id=row[6], chunk_id=row[7])

**Edge deserialization** (2 sites, identical 7-field tuple unpacking):
- get_edge (L238)
- list_edges (L281)

All use: Edge(id=row[0], source_id=row[1], target_id=row[2], relation=row[3], weight=row[4], metadata=_load_meta(row[5]), scope=row[6])

**SELECT column order is consistent** across all sites for each model, so the helpers can be simple staticmethods next to _load_meta.

### Approach
1. Add _entity_from_row(row) staticmethod returning Entity
2. Add _edge_from_row(row) staticmethod returning Edge
3. Replace all 5 sites with calls to the new helpers
4. Run existing tests (no behavior change)
