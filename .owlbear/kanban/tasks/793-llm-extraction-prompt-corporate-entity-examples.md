---
id: 793
title: LLM extraction prompt corporate entity examples
status: backlog
priority: important
created: '2026-04-10T12:31:51.861669+00:00'
updated: '2026-04-10T12:31:51.861669+00:00'
tags:
- phase-1
- scope:knowledge
parent: 775
depends_on:
- 789
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- `LLM_EXTRACTION_PROMPT` updated with corporate entity disambiguation examples (e.g., "a REQUIREMENT is a mandated specification, not a CONCEPT")
- Prompt includes GOVERNS and SUPERSEDES_VERSION relation examples
- All #789 tests pass; existing extraction tests still pass
- File: `serve/knowledge/src/owlbear_knowledge/llm_extractor.py`

## Context
- WS-B: Pipeline Quality
- Scope item 9 from #775
- See research F3: entity/relation/prompt must ship atomically
