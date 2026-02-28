---
id: 190
title: Test knowledge entity dedup — fuzzy merge
status: archived
priority: important
created: 2026-02-27T22:17:58.4510294+01:00
updated: 2026-02-28T23:53:39.3549414+01:00
started: 2026-02-27T23:47:18.8056225+01:00
completed: 2026-02-28T23:53:39.3543817+01:00
tags:
    - phase-9
    - knowledge-graph
    - memory
    - test
class: standard
---

Write tests in tests/test_knowledge_dedup.py for src/owlbear/memory/knowledge/dedup.py. Test: (1) deduplicate_entities() detects near-duplicate entity names using difflib.SequenceMatcher (2) Threshold parameter controls merge sensitivity (default 0.85) (3) Canonical entity keeps longer description (4) Metadata dicts are merged (canonical wins on key conflicts) (5) All edges referencing duplicate entity are updated to canonical entity (6) DeduplicationResult has merged_count and canonical_ids fields (7) No merges when all entities are distinct (8) Works on entities already in GraphStore (uses existing CRUD)
