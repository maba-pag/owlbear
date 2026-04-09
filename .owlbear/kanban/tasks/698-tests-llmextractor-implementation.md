---
id: 698
title: 'Tests: LLMExtractor implementation'
status: backlog
priority: needed
created: 2026-04-08T21:37:23.930035+02:00
updated: 2026-04-08T21:37:23.930035+02:00
tags:
    - scope:knowledge
    - type:test
parent: 676
depends_on:
    - 687
class: standard
---

## Context
TDD RED phase for #689. Write failing tests for the LLMExtractor class before it exists. Depends on #687 because tests must use the async protocol.

## Acceptance Criteria

- [ ] AC1: Test file `tests/test_llm_extractor.py` created
- [ ] AC2: Tests verify LLMExtractor satisfies the (async) StructuredExtractor protocol
- [ ] AC3: Tests verify PydanticAI Agent is called with correct model and result_type
- [ ] AC4: Tests verify graceful degradation — LLM failure returns empty ExtractionResult
- [ ] AC5: Tests verify system prompt covers all EntityType and RelationType enum values
- [ ] AC6: All tests FAIL (RED phase — LLMExtractor does not yet exist)

## Affected Files
- tests/test_llm_extractor.py (new)
