---
id: 2934d703-b07e-4eab-b823-84a20cf794e0
title: 'Reviewer: RED-safe schema negatives still need final exclusion proof'
categories:
- process
- pitfall
confidence: 0.94
state: curated
scope_agents:
- reviewer
- test-writer
source_agent: reviewer
created_at: '2026-05-13T03:11:47.535762Z'
updated_at: '2026-05-13T03:34:49.777728Z'
approved_at: null
---

When a test-writer removes pure negative model-field assertions to preserve RED (for example, `field not in model_fields` that would pass pre-implementation), review should still require a discriminating replacement that proves exact include/exclude shape once the positive field is added. Inclusion-only schema tests can miss AC clauses like 'include X but NOT Y' and should fail to todo as proof gaps.
