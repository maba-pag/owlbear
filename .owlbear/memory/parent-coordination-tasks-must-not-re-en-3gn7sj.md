---
id: 438dd28a-ce0a-4065-8dbd-39bb49124307
title: Parent coordination tasks must not re-enter review before child completion
categories:
- process
- pitfall
confidence: 0.91
state: curated
scope_agents:
- builder
source_agent: builder
created_at: '2026-05-15T18:20:25.008783Z'
updated_at: '2026-05-15T22:16:46.425037Z'
approved_at: null
---

For decomposed parent tasks tagged as coordination/quality, builder should reject to todo when child implementation/consolidation tasks remain open, and only re-advance with a proof packet mapping parent AC to completed child outcomes.
