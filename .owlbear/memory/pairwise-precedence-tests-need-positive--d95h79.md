---
id: 7ed37efb-c5f6-416d-80f4-eaeeab527f48
title: Pairwise precedence tests need positive reachability checks
categories:
- pitfall
- process
confidence: 0.85
state: curated
scope_agents:
- reviewer
- test-writer
- architect
source_agent: reviewer
created_at: '2026-05-13T20:58:18.680989Z'
updated_at: '2026-05-13T23:06:58.758008Z'
approved_at: null
---

For ordered-state helpers, adjacent pairwise precedence tests alone can miss an intermediate state that is only returned under an extra hidden condition. Require at least one direct positive assertion for each emitted state, not just competition cases.
