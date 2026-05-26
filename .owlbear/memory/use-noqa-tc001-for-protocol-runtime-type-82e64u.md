---
id: 43c6312c-0bbe-445f-a15e-9d24c52f7c54
title: Use noqa TC001 for protocol runtime type imports
categories:
- domain-knowledge
confidence: 0.82
state: curated
scope_agents:
- builder
source_agent: builder
created_at: '2026-05-26T21:52:09.207358Z'
updated_at: '2026-05-26T23:03:09.581829Z'
approved_at: null
---

In serve/knowledge protocol models, moving protocol type imports behind TYPE_CHECKING can risk runtime model resolution. For task-scoped lint cleanup, adding '# noqa: TC001' on required imports is a safe minimal fix.
