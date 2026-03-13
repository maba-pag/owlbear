---
id: 178
title: Knowledge entity deduplication — fuzzy merge of near-duplicates
status: archived
priority: important
created: 2026-02-27T22:10:23.1092815+01:00
updated: 2026-02-28T23:53:26.9445751+01:00
started: 2026-02-27T22:12:08.0760819+01:00
completed: 2026-02-28T23:53:26.9445751+01:00
tags:
    - phase-9
    - knowledge-graph
    - memory
depends_on:
    - 190
class: standard
---

Module: src/owlbear/memory/knowledge/dedup.py | Test: tests/test_knowledge_dedup.py | See docs/research/knowledge-ingestion.md S3.4.

AC:
- deduplicate_entities(graph: GraphStore, threshold: float = 0.85) -> DeduplicationResult function
- Uses difflib.SequenceMatcher for name similarity (stdlib — no new dependency)
- Compares all entity pairs; merges when similarity >= threshold
- Canonical entity: keeps the one with longer description (tie-break: alphabetically first name)
- Metadata dicts merged: canonical entity's metadata wins on key conflicts
- All edges referencing the duplicate entity_id are updated (source_id and target_id) to canonical
- Duplicate entity deleted from entities table after edge redirection
- DeduplicationResult frozen Pydantic model: merged_count: int, canonical_ids: list[str]
- No merges performed when all entity names are distinct (returns merged_count=0)
- Independent of ingest pipeline — operates on any entities in GraphStore
- ruff clean, all tests in tests/test_knowledge_dedup.py pass
