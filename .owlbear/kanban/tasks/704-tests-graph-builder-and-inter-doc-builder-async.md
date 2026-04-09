---
id: 704
title: 'Tests: graph builder and inter-doc builder async extractor migration'
status: backlog
priority: needed
created: 2026-04-09T00:55:49.1829555+02:00
updated: 2026-04-09T00:55:49.1829555+02:00
tags:
    - scope:knowledge
    - ' type:test'
parent: 676
depends_on:
    - 687
class: standard
---

## Context
TDD RED phase for graph builder async migration. After #687 makes `StructuredExtractor.extract()` async, the graph builders (`graph_builder.py`, `inter_doc_graph_builder.py`) still call `self._extractor.extract(prompt)` without `await`. Their test helper `_make_mock_extractor()` uses sync `MagicMock(spec=StructuredExtractor)`. Tests must be updated to use `AsyncMock` so they fail against the un-awaited production code.

Identified by reviewer of #676 — decomposition gap in the original plan.

## Acceptance Criteria

- [ ] AC1: `_make_mock_extractor()` in `tests/test_graph_builder.py` returns an `AsyncMock` with `extract` as an async callable returning `ExtractionResult`
- [ ] AC2: `_make_mock_extractor()` in `tests/test_inter_doc_graph_builder.py` returns an `AsyncMock` with `extract` as an async callable returning `ExtractionResult`
- [ ] AC3: All tests in `TestFromAC_IntraDocGraphBuilder` that exercise the extractor FAIL — `graph_builder.py` line 122/130 calls `self._extractor.extract(prompt)` without `await`, receiving a coroutine instead of `ExtractionResult`
- [ ] AC4: All tests in `TestFromAC_InterDocGraphBuilder` that exercise the extractor FAIL — `inter_doc_graph_builder.py` line 154 calls `self._extractor.extract(prompt)` without `await`
- [ ] AC5: Guard tests (extractor=None, <2 entities) continue to PASS — extractor is never called

## Affected Files
- tests/test_graph_builder.py (modify `_make_mock_extractor()`)
- tests/test_inter_doc_graph_builder.py (modify `_make_mock_extractor()`)
