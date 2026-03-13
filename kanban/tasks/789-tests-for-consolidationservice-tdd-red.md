---
id: 789
title: Tests for ConsolidationService (TDD RED)
status: in-progress
priority: nice-to-have
created: 2026-03-13T20:16:58.2117061+01:00
updated: 2026-03-13T20:43:06.6497748+01:00
tags:
    - scope:core
    - memory
    - knowledge
    - consolidation
    - type:test
class: standard
---

## Goal
Write failing tests for ConsolidationService before implementation.

## AC
- [ ] Test file: tests/test_consolidation.py
- [ ] Test consolidate() reads unconsolidated chunks (consolidated=0) from DB
- [ ] Test consolidate() stores insight row in consolidations table with source_ids JSON array
- [ ] Test consolidate() marks source chunks consolidated=1
- [ ] Test consolidate() returns count of insights created
- [ ] Test consolidate() batch_size parameter limits chunk selection
- [ ] Test consolidate() with no unconsolidated chunks returns 0
- [ ] Test schedule_periodic() calls consolidate() on interval (mock asyncio.sleep)
- [ ] Test LLM failure during consolidation is logged, does not crash the loop
- [ ] All tests RED (fail) -- implementation in #723
- [ ] LLM mocked via PydanticAI test utilities

## Pattern references
- tests/test_schema_v8.py (schema test patterns)
- src/owlbear/memory/knowledge/enrichment.py (GraphEnricher background-task pattern)

## Dependencies
- Schema v8 (#721) archived

[[2026-03-13]] Fri 20:42
## Test-Writer Notes
- Test file: tests/test_consolidation.py
- Classes: TestFromAC_ConsolidateReads, TestFromAC_ConsolidateStoresInsight, TestFromAC_ConsolidateMarksChunks, TestFromAC_ConsolidateReturnsCount, TestFromAC_ConsolidateBatchSize, TestFromAC_ConsolidateEmpty, TestFromAC_SchedulePeriodic, TestFromAC_LLMFailure, TestFromAC_Constructor
- Tests per category: happy 8, edge 3, error 3, boundary 5, constructor 2
- Total: 21 tests, all FAIL (ModuleNotFoundError)
- ruff: clean
