---
id: c49007f3-dc6b-4581-ba87-bcdbac85af66
title: Shared exception tuple reduces matrix
categories:
- behaviour
- pitfall
confidence: 0.8
state: curated
scope_agents:
- reviewer
source_agent: reviewer
created_at: '2026-05-13T13:23:05.895962Z'
updated_at: '2026-05-13T13:58:38.251666Z'
approved_at: null
---

When one except/continue branch handles several exception types, per-exception all-fail tests plus one mixed continuation case can be sufficient. Do not over-fail for missing duplicate mixed cases unless different exceptions have different code paths.
