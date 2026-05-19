---
id: 918
title: Add in-memory merge and edge repair helper for EntityExtractor gleaning
status: archived
priority: nice-to-have
created: 2026-03-21T15:57:48.1146702+01:00
updated: 2026-03-21T15:57:48.1146702+01:00
tags:
    - scope:core
    - knowledge
    - benchmark
    - type:build
    - phase-research
parent: 907
depends_on:
    - 906
class: standard
---

See docs/research/entity-extractor-gleaning-prototype.md §5. AC: merge pass outputs by (normalized name, entity_type), prefer higher-importance canonical entities, and remap edges to canonical ids before returning. Affected files: src/owlbear/memory/knowledge/extractor.py, src/owlbear/memory/knowledge/models.py, tests/test_knowledge_extractor.py.
