---
id: 932
title: Test EntityExtractor gleaning merge and edge repair semantics
status: archived
priority: nice-to-have
created: 2026-03-21T23:58:42.8795366+01:00
updated: 2026-03-21T23:58:42.8795366+01:00
tags:
    - scope:core
    - knowledge
    - benchmark
    - test
    - type:test
    - phase-research
parent: 907
depends_on:
    - 906
class: standard
---

AC: add focused failing tests in tests/test_knowledge_extractor.py that prove gleaning merge logic deduplicates by (name.casefold(), entity_type), keeps the higher-importance entity as canonical, and rewrites all edge source_id and target_id values to the canonical entity ids before returning. Paired GREEN task: #918. Affected files: tests/test_knowledge_extractor.py, src/owlbear/memory/knowledge/extractor.py, src/owlbear/memory/knowledge/models.py.
