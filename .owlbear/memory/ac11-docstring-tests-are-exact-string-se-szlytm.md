---
id: 9ac9b9df-6253-42b1-b98d-e77b47aff879
title: AC11 docstring tests are exact-string sensitive
categories:
- domain-knowledge
confidence: 0.8
state: pending
scope_agents:
- builder
source_agent: builder
created_at: '2026-05-26T21:52:09.201425Z'
updated_at: '2026-05-26T21:52:09.201425Z'
approved_at: null
---

Task 1878 retry failed because AC11 tests assert exact substring 'Never raises LookupError' (without markup). Using backticks in protocol docstring caused false-negative despite equivalent meaning.
