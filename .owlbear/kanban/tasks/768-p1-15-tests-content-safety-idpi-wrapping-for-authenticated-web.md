---
id: 768
title: 'P1-15: Tests — Content safety: IDPI + wrapping for AUTHENTICATED_WEB'
status: research
priority: needed
created: '2026-04-10T10:56:34.256076+00:00'
updated: '2026-04-10T10:56:34.256076+00:00'
tags:
- phase-1
- type:test
- scope:knowledge
- security
parent: 751
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
RED phase. Tests for content safety:
1. AUTHENTICATED_WEB content automatically wrapped as untrusted
2. Content safety predicate defaults to wrapped for unknown source types (inverted default)
3. IDPI scanning called before content enters graph

All tests fail (RED). Depends on schema (#757).

Parent: #751
