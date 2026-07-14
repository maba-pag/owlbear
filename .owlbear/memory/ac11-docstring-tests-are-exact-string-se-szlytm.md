---
approved_at: null
categories: [pitfall, domain-knowledge]
confidence: 0.82
contested_by_task: null
created_at: '2026-05-26T21:52:09.201425Z'
didnt_use_count: 0
id: 9ac9b9df-6253-42b1-b98d-e77b47aff879
outstanding_count: 0
scope_agents: [builder]
score: 0.0
source_agent: builder
state: deleted
title: Docstring assertion tests are exact-string sensitive
unremarkable_count: 0
updated_at: '2026-07-14T22:39:26.557999+00:00'
---

Tests that assert protocol docstrings match exact substrings will fail if the implementation uses different markup (e.g., backticks vs. plain text) even when the meaning is equivalent. Match the exact whitespace and punctuation the test expects, or update the test to use a normalized comparison.
