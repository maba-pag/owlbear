---
id: 687
title: Make StructuredExtractor protocol async and update EntityExtractor await
status: backlog
priority: needed
created: 2026-04-08T21:06:18.9396962+02:00
updated: 2026-04-09T05:06:54.1577993+02:00
tags:
    - scope:knowledge
    - ' type:refactor'
    - ' source:research'
depends_on:
    - 676
class: standard
---

## Context

Research for #676 found that `StructuredExtractor.extract()` is sync but real LLM calls are async. PydanticAI's `run_sync()` fails inside an existing event loop (RuntimeError). The protocol must become async before a concrete implementation can work.

## Acceptance Criteria

- [ ] AC1: `StructuredExtractor.extract()` signature changed to `async def extract(self, prompt: str) -> ExtractionResult`
- [ ] AC2: `EntityExtractor.extract()` updated to `await self._extractor.extract(prompt)`
- [ ] AC3: All existing tests updated (mock extractors → AsyncMock where needed)
- [ ] AC4: `@runtime_checkable` isinstance checks still pass

## Affected Files

- `serve/knowledge/src/owlbear_knowledge/protocol.py`
- `serve/knowledge/src/owlbear_knowledge/extractor.py`
- `tests/test_extractor.py`
- `tests/test_structured_extractor_protocol.py`

[[2026-04-09]] Thu 05:06
## Research
- Research doc: .owlbear/research/async-structuredextractor-protocol.md
- Sources: 5 studied, 4 high-relevance
- Recommendation: Expand AC to include 4 missing files (confidence: 0.92)

### Key Finding: Incomplete AC

Codebase grep found 3 additional `_extractor.extract()` call sites NOT in the original AC:
- `graph_builder.py` (L122, L130) — 2 sync calls inside `async def build()`
- `inter_doc_graph_builder.py` (L154) — 1 sync call inside `async def build()`
- `test_graph_builder.py` — uses `MagicMock(spec=StructuredExtractor)`, needs AsyncMock
- `test_inter_doc_graph_builder.py` — uses `MagicMock(spec=StructuredExtractor)`, needs AsyncMock

### Confirmed safe
- `@runtime_checkable` isinstance checks unaffected (PEP 544: structural subtyping checks attribute existence only)
- `ingest.py` uses `EntityExtractor` (already async) — no change needed
- TDD RED tests (`test_extractor.py`, `test_structured_extractor_protocol.py`) already use AsyncMock — ready for GREEN
- Follow-up tasks: none (expanded scope belongs in #687 itself)
- Decision requests: none (T1 refactor)
