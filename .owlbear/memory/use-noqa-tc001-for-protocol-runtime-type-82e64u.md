---
approved_at: null
categories: [domain-knowledge]
confidence: 0.82
contested_by_task: null
created_at: '2026-05-26T21:52:09.207358Z'
didnt_use_count: 0
id: 43c6312c-0bbe-445f-a15e-9d24c52f7c54
outstanding_count: 0
scope_agents: [builder]
score: 0.0
source_agent: builder
state: deleted
title: Use noqa TC001 for protocol runtime type imports
unremarkable_count: 0
updated_at: '2026-07-14T22:39:26.450281+00:00'
---

In serve/knowledge protocol models, moving protocol type imports behind TYPE_CHECKING can risk runtime model resolution. For task-scoped lint cleanup, adding '# noqa: TC001' on required imports is a safe minimal fix.
