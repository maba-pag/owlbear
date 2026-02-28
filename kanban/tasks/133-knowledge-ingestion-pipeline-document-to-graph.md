---
id: 133
title: Knowledge ingestion pipeline — document to graph+embeddings
status: archived
priority: important
created: 2026-02-27T14:57:05.2121273+01:00
updated: 2026-02-28T23:52:56.3906913+01:00
started: 2026-02-27T22:11:08.8714339+01:00
completed: 2026-02-28T23:52:56.3906913+01:00
tags:
    - phase-9
    - knowledge-graph
    - memory
class: standard
---

Pipeline: take a document (file, URL, text) -> extract entities and relations -> embed text chunks -> store in knowledge graph + vector DB. This is what makes the knowledge graph actually useful beyond manual insertion.

Decompose into subtasks during research. Key questions: entity extraction approach (LLM-based? rule-based?), chunking strategy, embedding batching.
