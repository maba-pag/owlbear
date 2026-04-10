---
id: 766
title: 'P1-13: Tests — Updated extraction prompt with corporate domain examples'
status: research
priority: needed
created: '2026-04-10T10:55:57.417675+00:00'
updated: '2026-04-10T10:55:57.417675+00:00'
tags:
- phase-1
- type:test
- scope:knowledge
parent: 751
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
RED phase. Tests for updated extraction prompt:
1. LLM_EXTRACTION_PROMPT includes guidance for REQUIREMENT, SOLUTION, PROCEDURE, POLICY, STANDARD
2. Prompt includes GOVERNS, SUPERSEDES_VERSION relation examples
3. Sample corporate text extracts to correct entity types (not collapsed to CONCEPT)

All tests fail (RED). Depends on schema (#757).

Parent: #751
