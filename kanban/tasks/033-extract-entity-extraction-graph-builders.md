---
id: 33
title: Extract entity extraction + graph builders
status: ideation
priority: needed
created: 2026-03-26T18:33:48.3894411+01:00
updated: 2026-03-26T18:33:48.3894411+01:00
tags:
    - phase-1
    - scope:knowledge
    - type:build
depends_on:
    - 32
class: standard
---

## Objective

Extract the entity extraction pipeline and graph building from v1 into packages/knowledge/.

## Acceptance Criteria

- [ ] Extract extractor.py (EntityExtractor — LLM-based entity extraction)
- [ ] Extract graph_builder.py (IntraDocGraphBuilder)
- [ ] Extract inter_doc_graph_builder.py (InterDocGraphBuilder)
- [ ] Extract ingest.py (document ingest pipeline)
- [ ] Extract intake.py (intake coordination)
- [ ] Replace PydanticAI Agent calls with a pluggable LLM interface (protocol/ABC)
- [ ] Unit tests: entity extraction with mock LLM, graph building from entities
- [ ] Ingest pipeline end-to-end test: text in, entities + graph edges out

## Context

Depends on #32 (vector store). Subtask 3/4 of knowledge engine extraction. The entity extractor uses an LLM — v1 uses PydanticAI Agent. v2 needs a pluggable interface so the MCP server or orchestrator can inject the LLM provider.
