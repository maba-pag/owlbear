---
id: 73366e39-a355-4b3b-9fca-400fff7b375c
title: Reject when full-file AC conflicts with explicit out-of-scope sections
categories:
- process
- pitfall
confidence: 0.82
state: curated
scope_agents:
- builder
- architect
- reviewer
source_agent: builder
created_at: '2026-05-28T00:43:03.166007Z'
updated_at: '2026-05-28T01:31:39.879671Z'
approved_at: null
---

If AC requires `pytest <whole-file>` but task scope explicitly excludes a failing section in the same file, treat as AC/scope mismatch: implement in-scope cleanup, provide failure evidence for out-of-scope tests, and reject to backlog with architect follow-up to refine AC or add prereq tasks.
