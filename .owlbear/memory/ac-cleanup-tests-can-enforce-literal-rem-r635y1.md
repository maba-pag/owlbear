---
approved_at: null
categories: [domain-knowledge, process]
confidence: 0.86
contested_by_task: null
created_at: '2026-05-26T04:00:19.571721Z'
didnt_use_count: 0
id: 3c83adae-5e87-4e78-9335-7b4175d41b0f
outstanding_count: 0
scope_agents: [builder]
score: 0.0
source_agent: builder
state: deleted
title: AC cleanup tests can enforce literal removal in docstrings
unremarkable_count: 0
updated_at: '2026-07-14T22:46:36.707344+00:00'
---

When AC requires removing a deprecated symbol from a test file, task-level checks may assert full-content absence, including docstrings/comments; builder fixes may need documentation-string cleanup, not only executable code edits.
