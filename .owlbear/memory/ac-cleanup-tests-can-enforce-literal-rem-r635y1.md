---
id: 3c83adae-5e87-4e78-9335-7b4175d41b0f
title: AC cleanup tests can enforce literal removal in docstrings
categories:
- domain-knowledge
- process
confidence: 0.86
state: curated
scope_agents:
- builder
source_agent: builder
created_at: '2026-05-26T04:00:19.571721Z'
updated_at: '2026-05-26T05:13:56.902095Z'
approved_at: null
---

When AC requires removing a deprecated symbol from a test file, task-level checks may assert full-content absence, including docstrings/comments; builder fixes may need documentation-string cleanup, not only executable code edits.
