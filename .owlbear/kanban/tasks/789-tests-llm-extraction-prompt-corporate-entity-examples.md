---
id: 789
title: Tests — LLM extraction prompt corporate entity examples
status: backlog
priority: needed
created: '2026-04-10T12:31:33.658191+00:00'
updated: '2026-04-10T12:31:33.658191+00:00'
tags:
- phase-1
- scope:knowledge
- type:test
parent: 775
depends_on:
- 784
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- Tests assert `LLM_EXTRACTION_PROMPT` contains example text for REQUIREMENT, SOLUTION, PROCEDURE, POLICY, STANDARD
- Tests assert prompt distinguishes corporate entity types from CONCEPT (prevents LLM collapse per F3)
- Tests verify GOVERNS and SUPERSEDES_VERSION appear in relation type guidance
- File: `tests/test_llm_prompt_corporate_775.py`

## Context
- WS-B: Pipeline Quality
- Scope item 9 from #775
- See research F3: entity/relation/prompt must ship atomically — depends on entity types being defined first
