---
id: 760
title: 'P1-07: Tests — Content extractor + login redirect detection'
status: research
priority: needed
created: '2026-04-10T10:55:57.241623+00:00'
updated: '2026-04-10T10:55:57.241623+00:00'
tags:
- phase-1
- type:test
- scope:browser
parent: 751
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
RED phase. Tests for content extractor:
1. Page content extraction from DOM via static JavaScript
2. Only pre-defined JS — no LLM-influenced scripts in authenticated contexts
3. Login redirect detection aborts extraction, reports SSO expiry
4. Returns cleaned markdown (delegates to cleaner)

Mock-based. All tests fail (RED).

Parent: #751
