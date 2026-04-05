---
id: 174
title: Knowledge entity extractor — LLM-based extraction with PydanticAI
status: archived
priority: needed
created: 2026-02-27T22:09:53.6089993+01:00
updated: 2026-02-28T23:53:24.3276327+01:00
started: 2026-02-27T22:11:59.6500623+01:00
completed: 2026-02-28T23:53:24.3276327+01:00
tags:
    - phase-9
    - knowledge-graph
    - memory
    - agent
depends_on:
    - 186
class: standard
---

Module: src/owlbear/memory/knowledge/extractor.py | Test: tests/test_knowledge_extractor.py | See docs/research/knowledge-ingestion.md S3.1.

AC:
- EntityExtractor class accepting a PydanticAI model (or model name string)
- async extract(text: str) -> ExtractionResult method
- ExtractionResult frozen Pydantic model: entities: list[Entity], edges: list[Edge]
- Uses PydanticAI structured output to produce entities and edges from text chunks
- Entity and Edge reuse existing models from models.py (no new model types)
- Extraction prompt is a module-level constant string (EXTRACTION_PROMPT)
- Empty text returns empty ExtractionResult (entities=[], edges=[])
- LLM failure (any exception) returns empty ExtractionResult — no exception propagated to caller
- Logs extraction failures at WARNING level
- ruff clean, all tests in tests/test_knowledge_extractor.py pass
