---
id: 422
title: Test GraphAugmentedRetriever
status: archived
priority: needed
created: 2026-03-01T22:18:50.2498492+01:00
updated: 2026-03-02T09:15:13.4499547+01:00
started: 2026-03-01T22:18:55.4476616+01:00
completed: 2026-03-02T09:15:13.4499547+01:00
tags:
    - phase-9
    - knowledge-graph
    - test
class: standard
---

TDD test task for #372. File: tests/test_graph_augmented_retriever.py. AC: - retrieve() returns original vector search results plus neighbor entity descriptions - expansion_depth=0 returns only vector search results (no graph expansion) - expansion_depth=1 adds 1-hop neighbor descriptions - max_expansion_tokens budget caps total expansion text (word count heuristic) - max_neighbors_per_entity limits per-entity fan-out - expansion_enabled=False disables graph expansion entirely (kill switch) - When no entities found for chunks, returns vector results only - Token budget respected: expansion text never exceeds max_expansion_tokens words
