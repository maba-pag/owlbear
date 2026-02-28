---
id: 186
title: Test knowledge entity extractor — LLM extraction with mocked agent
status: archived
priority: needed
created: 2026-02-27T22:17:23.4752952+01:00
updated: 2026-02-28T23:53:35.0278317+01:00
started: 2026-02-27T23:11:58.354474+01:00
completed: 2026-02-28T23:53:35.0278317+01:00
tags:
    - phase-9
    - knowledge-graph
    - memory
    - agent
    - test
class: standard
---

Write tests in tests/test_knowledge_extractor.py for src/owlbear/memory/knowledge/extractor.py. Test: (1) extract() returns ExtractionResult with entities: list[Entity] and edges: list[Edge] (2) Uses PydanticAI TestModel/FunctionModel mock — no real LLM calls (3) Returned entities use existing Entity model from models.py (4) Returned edges use existing Edge model from models.py (5) Empty text returns empty ExtractionResult (6) LLM failure returns empty ExtractionResult, no exception (7) Extraction prompt is a module-level constant string
