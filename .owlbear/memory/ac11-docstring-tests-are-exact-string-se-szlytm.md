---
id: 9ac9b9df-6253-42b1-b98d-e77b47aff879
title: Docstring assertion tests are exact-string sensitive
categories:
- pitfall
- domain-knowledge
confidence: 0.82
state: curated
scope_agents:
- builder
- test-writer
source_agent: builder
created_at: '2026-05-26T21:52:09.201425Z'
updated_at: '2026-05-26T23:03:09.540013Z'
approved_at: null
---

Tests that assert protocol docstrings match exact substrings will fail if the implementation uses different markup (e.g., backticks vs. plain text) even when the meaning is equivalent. Match the exact whitespace and punctuation the test expects, or update the test to use a normalized comparison.
