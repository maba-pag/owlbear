---
id: 705
title: Update graph builders to await async StructuredExtractor.extract()
status: backlog
priority: needed
created: 2026-04-09T00:56:04.9684971+02:00
updated: 2026-04-09T00:56:04.9684971+02:00
tags:
    - scope:knowledge
    - ' type:feature'
parent: 676
depends_on:
    - 704
    - 687
class: standard
---

## Context
GREEN phase — update graph builders to await async `StructuredExtractor.extract()`. After #687 makes the protocol async and #704 writes RED tests, the production code in `graph_builder.py` and `inter_doc_graph_builder.py` must add `await` to all `self._extractor.extract(prompt)` calls.

The `build()` methods are already `async def` — only the inner `extract()` calls need `await`.

## Acceptance Criteria

- [ ] AC1: `IntraDocGraphBuilder.build()` in `graph_builder.py` uses `await self._extractor.extract(prompt)` at lines 122 and 130
- [ ] AC2: `InterDocGraphBuilder.build()` in `inter_doc_graph_builder.py` uses `await self._extractor.extract(prompt)` at line 154
- [ ] AC3: All tests in `tests/test_graph_builder.py` PASS
- [ ] AC4: All tests in `tests/test_inter_doc_graph_builder.py` PASS
- [ ] AC5: No other files modified — the change is limited to adding `await` keywords

## Affected Files
- serve/knowledge/src/owlbear_knowledge/graph_builder.py (lines 122, 130)
- serve/knowledge/src/owlbear_knowledge/inter_doc_graph_builder.py (line 154)
